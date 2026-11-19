/**
 * Courtroom Replay — playback engine: browser text-to-speech (3 distinct voices),
 * interactive line seeking, playback speed, subtle Web Audio gavel/objection cues,
 * subtitle/speaker state and phoneme-style lip-sync driver.
 * Pure client-side; touches no backend state.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import type { DialogueLine, Speaker } from './dialogue';

export type Mouth = 'closed' | 'small' | 'wide' | 'round' | 'smile';
export type PlayStatus = 'idle' | 'playing' | 'paused' | 'finished';

const FEMALE_RE = /(zira|susan|hazel|aria|jenny|samantha|karen|heera|libby|sonia|female|natasha|moira|tessa|veena|neerja|swara|catherine|linda)/i;
const MALE_RE = /(david|mark|george|guy|ryan|james|daniel|ravi|rishi|prabhat|male|alex|christopher|eric|fred|thomas|oliver|richard|brian|aaron)/i;

interface VoicePick { voice: SpeechSynthesisVoice | null; pitch: number; rate: number }
type VoiceMap = Record<Speaker, VoicePick>;
const HI_FEMALE_RE = /(kalpana|swara|heera|lekha|female|neerja|google \u0939\u093f\u0928\u094d\u0926\u0940)/i;
const HI_MALE_RE = /(hemant|madhur|prabhat|ravi|male)/i;

const NATURAL_RE = /(natural|online|google|neural)/i;

function pickVoices(all: SpeechSynthesisVoice[], lang: 'en' | 'hi' = 'en'): VoiceMap {
  const own = all.filter((v) => new RegExp('^' + lang, 'i').test(v.lang));
  const rawPool = own.length ? own : all;
  // Prefer realistic Natural / Neural / Google voices over older robotic voices
  const pool = [...rawPool].sort((a, b) => Number(NATURAL_RE.test(b.name)) - Number(NATURAL_RE.test(a.name)));
  const fRe = lang === 'hi' ? HI_FEMALE_RE : FEMALE_RE;
  const mRe = lang === 'hi' ? HI_MALE_RE : MALE_RE;
  const female = pool.find((v) => fRe.test(v.name)) ?? null;
  const males = pool.filter((v) => mRe.test(v.name) && !fRe.test(v.name));
  const m1 = males[0] ?? pool.find((v) => v !== female) ?? null;
  const m2 = males.find((v) => v !== m1) ?? null;
  const fallback = pool[0] ?? null;
  if (lang === 'hi') {
    return {
      judge: { voice: female ?? fallback, pitch: 0.9, rate: 0.94 },
      prosecutor: { voice: m1 ?? fallback, pitch: m2 ? 0.78 : 0.72, rate: 0.98 },
      defense: { voice: m2 ?? m1 ?? fallback, pitch: m2 ? 0.86 : 0.81, rate: 1.01 },
    };
  }
  return {
    judge: { voice: female ?? fallback, pitch: 1.03, rate: 0.98 },
    prosecutor: { voice: m1 ?? fallback, pitch: m2 ? 0.95 : 0.9, rate: 1.02 },
    defense: { voice: m2 ?? m1 ?? fallback, pitch: m2 ? 1.01 : 1.06, rate: 1.04 },
  };
}

/** Synthesize crisp courtroom sound cues (gavel knock / dramatic objection chime) via Web Audio API. */
function playSoundCue(kind: 'gavel' | 'interrupt') {
  try {
    const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const now = ctx.currentTime;

    if (kind === 'gavel') {
      [0, 0.22].forEach((offset) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(165, now + offset);
        osc.frequency.exponentialRampToValueAtTime(52, now + offset + 0.11);
        gain.gain.setValueAtTime(0.28, now + offset);
        gain.gain.exponentialRampToValueAtTime(0.001, now + offset + 0.14);
        osc.connect(gain).connect(ctx.destination);
        osc.start(now + offset);
        osc.stop(now + offset + 0.15);
      });
    } else {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(520, now);
      osc.frequency.exponentialRampToValueAtTime(760, now + 0.09);
      gain.gain.setValueAtTime(0.12, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.18);
      osc.connect(gain).connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.2);
    }
    window.setTimeout(() => void ctx.close().catch(() => {}), 700);
  } catch { /* ignore audio context restrictions */ }
}

/** Rough viseme for a character of the spoken text. */
function visemeFor(ch: string): Mouth {
  const c = ch.toLowerCase();
  if ('aáàäe'.includes(c)) return 'wide';
  if ('iy'.includes(c)) return 'smile';
  if ('ou'.includes(c)) return 'round';
  if ('mbp'.includes(c)) return 'closed';
  if ('fv'.includes(c)) return 'small';
  if (/[a-z]/.test(c)) return 'small';
  const code = ch.charCodeAt(0);
  if (code >= 0x0900 && code <= 0x097f) {
    if (code === 0x0964 || code === 0x0965) return 'closed';
    return (['wide', 'small', 'round', 'smile', 'small'] as Mouth[])[code % 5];
  }
  return 'closed';
}

const ttsSupported = () => typeof window !== 'undefined' && 'speechSynthesis' in window;

export interface ReplayState {
  status: PlayStatus;
  lineIndex: number;
  speaker: Speaker | null;
  mouth: Mouth;
  lineProgress: number;
  spokenChars: number;
  voiceMode: 'speech' | 'silent';
  voiceNames: Record<Speaker, string>;
}

export function useReplayEngine(
  script: DialogueLine[],
  options?: { speed?: number; soundFx?: boolean },
) {
  const speed = options?.speed ?? 1;
  const soundFx = options?.soundFx ?? true;

  const [state, setState] = useState<ReplayState>({
    status: 'idle', lineIndex: 0, speaker: null, mouth: 'closed', lineProgress: 0, spokenChars: 0,
    voiceMode: ttsSupported() ? 'speech' : 'silent',
    voiceNames: { judge: '', prosecutor: '', defense: '' },
  });

  const scriptRef = useRef(script);
  const speedRef = useRef(speed);
  const soundFxRef = useRef(soundFx);
  const voicesRef = useRef<Record<'en' | 'hi', VoiceMap> | null>(null);
  const runIdRef = useRef(0);
  const pausedRef = useRef(false);
  const uttRef = useRef<SpeechSynthesisUtterance | null>(null);
  const raf = useRef<number | null>(null);
  const lineStart = useRef(0);
  const lastBoundary = useRef({ char: 0, time: 0 });
  const estDuration = useRef(1);
  const timerRef = useRef<number | null>(null);

  useEffect(() => { scriptRef.current = script; }, [script]);
  useEffect(() => { speedRef.current = speed; }, [speed]);
  useEffect(() => { soundFxRef.current = soundFx; }, [soundFx]);

  useEffect(() => {
    if (!ttsSupported()) return;
    const load = () => {
      const all = window.speechSynthesis.getVoices();
      if (!all.length) return;
      voicesRef.current = { en: pickVoices(all, 'en'), hi: pickVoices(all, 'hi') };
      const v = voicesRef.current.en;
      setState((s) => ({
        ...s,
        voiceNames: {
          judge: v.judge.voice?.name ?? 'default', prosecutor: v.prosecutor.voice?.name ?? 'default', defense: v.defense.voice?.name ?? 'default',
        },
      }));
    };
    load();
    window.speechSynthesis.addEventListener('voiceschanged', load);
    return () => window.speechSynthesis.removeEventListener('voiceschanged', load);
  }, []);

  const stopLoops = useCallback(() => {
    if (raf.current) cancelAnimationFrame(raf.current);
    raf.current = null;
    if (timerRef.current) window.clearTimeout(timerRef.current);
    timerRef.current = null;
  }, []);

  const hardStop = useCallback(() => {
    runIdRef.current += 1;
    stopLoops();
    if (ttsSupported()) window.speechSynthesis.cancel();
  }, [stopLoops]);

  const animateMouth = useCallback((text: string, runId: number) => {
    const tick = () => {
      if (runId !== runIdRef.current) return;
      if (!pausedRef.current) {
        const now = performance.now();
        const elapsed = (now - lineStart.current) / 1000;
        const cps = text.length / Math.max(estDuration.current, 1);
        const since = (now - lastBoundary.current.time) / 1000;
        const idx = Math.min(text.length - 1, Math.floor(lastBoundary.current.char + since * cps * 0.9));
        const prev = text.charAt(Math.max(0, idx - 1));
        let mouth = visemeFor(text.charAt(Math.max(0, idx)));
        if (text.charAt(idx) === ' ' || /[,.;!?।]/.test(text.charAt(idx)) || (prev === ' ' && mouth === 'small' && idx % 2)) mouth = 'closed';
        setState((s) => (s.mouth === mouth && Math.abs(s.lineProgress - elapsed / estDuration.current) < 0.02
          ? s
          : { ...s, mouth, lineProgress: Math.min(1, elapsed / estDuration.current), spokenChars: Math.max(idx, 0) }));
      }
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
  }, []);

  const playLine = useCallback((index: number, runId: number) => {
    const lines = scriptRef.current;
    if (runId !== runIdRef.current) return;
    if (index >= lines.length) {
      stopLoops();
      setState((s) => ({ ...s, status: 'finished', speaker: null, mouth: 'closed', lineProgress: 1, spokenChars: 0 }));
      return;
    }
    const line = lines[index];
    stopLoops();
    lineStart.current = performance.now();
    lastBoundary.current = { char: 0, time: lineStart.current };
    estDuration.current = Math.max(1.4, line.text.length / (14.5 * speedRef.current));
    setState((s) => ({ ...s, status: 'playing', lineIndex: index, speaker: line.speaker, mouth: 'closed', lineProgress: 0, spokenChars: 0 }));

    if (soundFxRef.current) {
      if (line.gavel) playSoundCue('gavel');
      else if (line.cue === 'interrupt') playSoundCue('interrupt');
    }

    const next = () => {
      if (runId !== runIdRef.current) return;
      stopLoops();
      setState((s) => ({ ...s, mouth: 'closed' }));
      const upcoming = lines[index + 1];
      const pauseMs = upcoming?.cue === 'interrupt' ? 140 : upcoming?.camera === 'verdict' ? 700 : 380;
      timerRef.current = window.setTimeout(() => playLine(index + 1, runId), pauseMs);
    };

    animateMouth(line.text, runId);

    if (!ttsSupported()) {
      const waitUntil = () => {
        if (runId !== runIdRef.current) return;
        if (pausedRef.current) { timerRef.current = window.setTimeout(waitUntil, 150); return; }
        if (performance.now() - lineStart.current >= estDuration.current * 1000) next();
        else timerRef.current = window.setTimeout(waitUntil, 120);
      };
      waitUntil();
      return;
    }

    const utt = new SpeechSynthesisUtterance(line.text);
    const lineLang = line.lang ?? 'en';
    const pick = voicesRef.current?.[lineLang]?.[line.speaker];
    if (pick?.voice) { utt.voice = pick.voice; utt.lang = pick.voice.lang; } else if (lineLang === 'hi') { utt.lang = 'hi-IN'; }
    utt.pitch = pick?.pitch ?? 1;
    utt.rate = Math.min(1.5, Math.max(0.7, (pick?.rate ?? 1) * speedRef.current));
    utt.onboundary = (e) => { lastBoundary.current = { char: e.charIndex, time: performance.now() }; };
    utt.onend = next;
    utt.onerror = (e) => {
      if ((e as SpeechSynthesisErrorEvent).error === 'canceled' || (e as SpeechSynthesisErrorEvent).error === 'interrupted') return;
      next();
    };
    uttRef.current = utt;
    window.speechSynthesis.speak(utt);
    const guardMs = estDuration.current * 2200 + 4000;
    const guardStart = lineStart.current;
    window.setTimeout(() => {
      if (runId === runIdRef.current && lineStart.current === guardStart && !pausedRef.current) {
        window.speechSynthesis.cancel();
        next();
      }
    }, guardMs);
  }, [animateMouth, stopLoops]);

  const jumpToLine = useCallback((index: number) => {
    const safeIdx = Math.max(0, Math.min(index, scriptRef.current.length - 1));
    hardStop();
    pausedRef.current = false;
    playLine(safeIdx, runIdRef.current);
  }, [hardStop, playLine]);

  const start = useCallback(() => jumpToLine(0), [jumpToLine]);

  const pause = useCallback(() => {
    if (state.status !== 'playing') return;
    pausedRef.current = true;
    if (ttsSupported()) window.speechSynthesis.pause();
    setState((s) => ({ ...s, status: 'paused', mouth: 'closed' }));
  }, [state.status]);

  const resume = useCallback(() => {
    if (state.status !== 'paused') return;
    pausedRef.current = false;
    if (ttsSupported()) window.speechSynthesis.resume();
    lastBoundary.current = { ...lastBoundary.current, time: performance.now() };
    setState((s) => ({ ...s, status: 'playing' }));
  }, [state.status]);

  const replay = useCallback(() => start(), [start]);

  useEffect(() => () => { runIdRef.current += 1; if (raf.current) cancelAnimationFrame(raf.current); if (ttsSupported()) window.speechSynthesis.cancel(); }, []);

  return { state, start, pause, resume, replay, jumpToLine };
}
