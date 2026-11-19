import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowLeft,
  BookOpen,
  Camera,
  FileText,
  Gauge,
  Pause,
  Play,
  Radio,
  RotateCcw,
  Sparkles,
  Volume2,
  VolumeX,
} from 'lucide-react';
import type { Judgment } from '../types/court';
import { buildDialogue, buildScreenplayRequest, CHARACTERS, fromServerScreenplay } from './dialogue';
import type { DialogueLine, Lang, ServerScreenplayLine, Speaker } from './dialogue';
import { useReplayEngine } from './useReplayEngine';
import { CourtroomScene } from './CourtroomScene';
import type { CameraMode } from './CourtroomScene';
import './replay.css';

interface Props { caseId: string }

type Load = { kind: 'loading' } | { kind: 'error'; message: string } | { kind: 'ready'; judgment: Judgment };

const goBack = () => {
  try {
    if (window.opener && !window.opener.closed) { window.opener.focus(); window.close(); }
  } catch { /* ignore */ }
  window.setTimeout(() => { window.location.href = '/'; }, 150);
};

export const CourtroomReplayPage: React.FC<Props> = ({ caseId }) => {
  const [load, setLoad] = useState<Load>({ kind: 'loading' });

  // READ-ONLY: single GET against the already-existing persisted-judgment endpoint.
  useEffect(() => {
    const ctl = new AbortController();
    (async () => {
      try {
        const res = await fetch(`/api/court/cases/${encodeURIComponent(caseId)}/judgment`, { signal: ctl.signal });
        if (res.status === 404) throw new Error('No completed AI Court judgment was found for this case yet. Finish the case first, then open the replay.');
        if (!res.ok) throw new Error(`Could not load the completed case (HTTP ${res.status}).`);
        setLoad({ kind: 'ready', judgment: await res.json() });
      } catch (e) {
        if ((e as Error).name === 'AbortError') return;
        setLoad({ kind: 'error', message: (e as Error).message || 'Could not load the case.' });
      }
    })();
    return () => ctl.abort();
  }, [caseId]);

  return (
    <div className="rp-page">
      <header className="rp-topbar">
        <button className="rp-btn rp-btn-ghost" onClick={goBack}><ArrowLeft size={16} /> Back to AI Court</button>
        <div className="rp-title">
          <div className="rp-kicker-row">
            <span className="rp-kicker">AI COURTROOM LIVE</span>
            <span className="rp-live-pill"><Radio size={11} /> INTERACTIVE SCENE</span>
          </div>
          <h1>{load.kind === 'ready' ? load.judgment.case_title || caseId : caseId}</h1>
        </div>
        <span className="rp-badge" title="This is a simplified dramatization of the AI Court's completed output, not a real courtroom recording or a new legal decision.">
          <Sparkles size={13} /> AI-generated dramatization
        </span>
      </header>

      {load.kind === 'loading' && <div className="rp-state">Loading completed case…</div>}
      {load.kind === 'error' && (
        <div className="rp-state rp-state-error">
          <p>{load.message}</p>
          <button className="rp-btn" onClick={goBack}><ArrowLeft size={16} /> Back to AI Court</button>
        </div>
      )}
      {load.kind === 'ready' && <Player judgment={load.judgment} caseId={caseId} />}
    </div>
  );
};

const Player: React.FC<{ judgment: Judgment; caseId: string }> = ({ judgment, caseId }) => {
  const base = useMemo(() => buildDialogue(judgment), [judgment]);
  const [lang, setLang] = useState<Lang>('en');
  const [prep, setPrep] = useState<{ key: string; lines: DialogueLine[] | null } | null>(null);
  const key = `${caseId}|${lang}`;

  useEffect(() => {
    let cancelled = false;
    const verdictKey = (judgment.final_decision || '').slice(0, 24);
    const cacheKey = `rp-sp-v3|${key}|${verdictKey}`;
    const cached = sessionStorage.getItem(cacheKey);
    if (cached) {
      try {
        const parsed = fromServerScreenplay(JSON.parse(cached) as ServerScreenplayLine[], lang);
        if (parsed) {
          setPrep({ key, lines: parsed });
          return () => { cancelled = true; };
        }
      } catch { /* ignore stale cache entry */ }
    }

    const ctl = new AbortController();
    const timer = window.setTimeout(() => ctl.abort(), 40000);
    (async () => {
      let lines: DialogueLine[] | null = null;
      try {
        const res = await fetch('/api/replay/screenplay', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          signal: ctl.signal,
          body: JSON.stringify(buildScreenplayRequest(judgment, lang)),
        });
        if (res.ok) {
          const data = await res.json();
          if (data.source === 'llm' && Array.isArray(data.lines)) {
            lines = fromServerScreenplay(data.lines as ServerScreenplayLine[], lang);
            if (lines) sessionStorage.setItem(cacheKey, JSON.stringify(data.lines));
          }
        }
      } catch { /* cleanly fall back below */ }
      window.clearTimeout(timer);
      if (!cancelled) setPrep({ key, lines });
    })();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      ctl.abort();
    };
  }, [key, lang, judgment]);

  const ready = prep?.key === key;
  const hasServerLines = ready && Boolean(prep?.lines?.length);
  const usedLang: Lang = hasServerLines ? lang : 'en';
  const script = hasServerLines ? prep!.lines! : base;

  return (
    <Stage
      key={`${usedLang}|${ready ? 'r' : 'p'}`}
      script={script}
      judgment={judgment}
      lang={lang}
      usedLang={usedLang}
      ready={ready}
      onChangeLang={setLang}
    />
  );
};

interface StageProps {
  script: DialogueLine[];
  judgment: Judgment;
  lang: Lang;
  usedLang: Lang;
  ready: boolean;
  onChangeLang: (lang: Lang) => void;
}

const Stage: React.FC<StageProps> = ({ script, judgment, lang, usedLang, ready, onChangeLang }) => {
  const [speed, setSpeed] = useState<number>(1);
  const [soundFx, setSoundFx] = useState<boolean>(true);
  const [cameraMode, setCameraMode] = useState<CameraMode>('auto');
  const [drawerTab, setDrawerTab] = useState<'script' | 'dossier'>('script');
  const [showDossier, setShowDossier] = useState<boolean>(true);

  const { state, start, pause, resume, replay, jumpToLine } = useReplayEngine(script, { speed, soundFx });
  const [gavelTick, setGavelTick] = useState(0);
  const line = state.status === 'idle' ? null : script[state.lineIndex] ?? null;
  const lastGavel = useRef(-1);
  const activeScriptRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (state.status !== 'idle' && state.status !== 'finished' && line?.gavel && lastGavel.current !== line.id) {
      lastGavel.current = line.id;
      setGavelTick((n) => n + 1);
    }
    if (state.status === 'idle') lastGavel.current = -1;
  }, [line, state.status]);

  useEffect(() => {
    activeScriptRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [state.lineIndex]);

  // Unique clickable scene chapters in order of first appearance
  const chapters = useMemo(() => {
    const out: Array<{ label: string; firstIdx: number; speaker: Speaker }> = [];
    for (let i = 0; i < script.length; i++) {
      const label = script[i].chapter || CHARACTERS[script[i].speaker].role;
      if (!out.some((c) => c.label === label)) {
        out.push({ label, firstIdx: i, speaker: script[i].speaker });
      }
    }
    return out;
  }, [script]);

  const handleSelectSpeaker = (who: Speaker) => {
    if (!ready) return;
    const after = script.findIndex((l, i) => i > state.lineIndex && l.speaker === who);
    const first = script.findIndex((l) => l.speaker === who);
    const target = after >= 0 ? after : first;
    if (target >= 0) jumpToLine(target);
  };

  const playing = state.status === 'playing' || state.status === 'paused';
  const activeSpeaker: Speaker | null = state.status === 'playing' || state.status === 'paused' ? state.speaker : null;
  const spoken = line ? line.text.slice(0, Math.min(line.text.length, state.spokenChars + 1)) : '';
  const rest = line ? line.text.slice(spoken.length) : '';
  const isMouthMoving = state.status === 'playing' && state.mouth !== 'closed';
  const estSec = Math.max(30, Math.round(script.reduce((n, l) => n + l.text.length, 0) / (14.5 * speed)));

  return (
    <main className={`rp-shell ${showDossier ? 'with-dossier' : ''}`}>
      {/* Studio Toolbar */}
      <div className="rp-toolbar">
        <div className="rp-lang" role="group" aria-label="Language">
          <button className={lang === 'en' ? 'on' : ''} onClick={() => onChangeLang('en')}>English</button>
          <button className={lang === 'hi' ? 'on' : ''} onClick={() => onChangeLang('hi')}>हिन्दी (Hinglish)</button>
          {!ready && (
            <span className="rp-lang-note">
              {lang === 'hi' ? 'सीन तैयार हो रहा है…' : 'Setting up the courtroom scene…'}
            </span>
          )}
          {ready && lang === 'hi' && usedLang === 'en' && (
            <span className="rp-lang-note">Hindi version is unavailable right now — showing English.</span>
          )}
        </div>

        <div className="rp-studio-tools">
          <div className="rp-pill-group" title="Director Camera Mode">
            <Camera size={13} />
            {(['auto', 'wide', 'focus'] as CameraMode[]).map((m) => (
              <button key={m} className={cameraMode === m ? 'on' : ''} onClick={() => setCameraMode(m)}>
                {m === 'auto' ? 'Auto Cam' : m === 'wide' ? 'Wide' : 'Close-up'}
              </button>
            ))}
          </div>

          <div className="rp-pill-group" title="Playback Speed">
            <Gauge size={13} />
            {[0.85, 1, 1.2].map((sp) => (
              <button key={sp} className={speed === sp ? 'on' : ''} onClick={() => setSpeed(sp)}>
                {sp}x
              </button>
            ))}
          </div>

          <button
            className={`rp-chip ${soundFx ? 'on' : ''}`}
            onClick={() => setSoundFx((v) => !v)}
            title="Toggle courtroom gavel & objection sound effects"
          >
            {soundFx ? <Volume2 size={13} /> : <VolumeX size={13} />} FX
          </button>

          <button
            className={`rp-chip ${showDossier ? 'on' : ''}`}
            onClick={() => setShowDossier((v) => !v)}
            title="Show/Hide Live Script & Case Dossier"
          >
            <BookOpen size={13} /> {showDossier ? 'Hide Panel' : 'Script & Facts'}
          </button>
        </div>
      </div>

      {/* Interactive Workspace */}
      <div className="rp-workspace">
        <div className="rp-stage-col">
          <div className="rp-stage">
            <CourtroomScene
              line={line}
              speaker={activeSpeaker}
              mouth={state.status === 'playing' ? state.mouth : 'closed'}
              gavelTick={gavelTick}
              playing={playing}
              cameraMode={cameraMode}
              onSelectSpeaker={handleSelectSpeaker}
            />

            {/* Character Nameplates */}
            {(['prosecutor', 'defense'] as Speaker[]).map((who) => (
              <button
                key={who}
                type="button"
                onClick={() => handleSelectSpeaker(who)}
                className={`rp-tag rp-tag-${who} ${activeSpeaker === who ? 'on' : ''}`}
                title={`Click to hear ${CHARACTERS[who].role}`}
              >
                <b>{CHARACTERS[who].name}</b>
                <span>{CHARACTERS[who].role}</span>
              </button>
            ))}

            {/* Idle Start Overlay */}
            {state.status === 'idle' && (
              <div className="rp-overlay">
                <button
                  className="rp-play-big"
                  disabled={!ready}
                  style={ready ? undefined : { opacity: 0.5, cursor: 'wait', animation: 'none' }}
                  onClick={start}
                  aria-label="Start courtroom replay"
                >
                  <Play size={40} fill="currentColor" />
                </button>
                <p>Watch Courtroom Live</p>
                <small>{script.length} scenes · ~{estSec}s · click any character or chapter to jump</small>
              </div>
            )}

            {/* End-of-Trial Verdict Seal */}
            {state.status === 'finished' && (
              <div className="rp-overlay rp-overlay-end">
                <div className="rp-verdict-seal">
                  <span className="rp-seal-kicker">AI COURT FINAL VERDICT</span>
                  <strong>{judgment.final_decision || 'DECIDED'}</strong>
                </div>
                <div className="rp-end-actions">
                  <button className="rp-btn rp-btn-gold" onClick={replay}><RotateCcw size={16} /> Watch Again</button>
                  <button className="rp-btn" onClick={goBack}><ArrowLeft size={16} /> Back to AI Court</button>
                </div>
              </div>
            )}

            {/* Live Subtitles + Voice Equalizer */}
            {line && state.status !== 'finished' && (
              <div className={`rp-subs rp-subs-${line.speaker}`}>
                <div className="rp-subs-head">
                  <div className="rp-subs-name">
                    <i /> {CHARACTERS[line.speaker].name} <em>· {CHARACTERS[line.speaker].role}</em>
                  </div>
                  <div className={`rp-wave ${isMouthMoving ? 'active' : ''}`} aria-hidden="true">
                    <span /><span /><span /><span /><span />
                  </div>
                </div>
                <p><span className="done">{spoken}</span><span>{rest}</span></p>
                <div className="rp-subs-bar"><i style={{ width: `${Math.round(state.lineProgress * 100)}%` }} /></div>
              </div>
            )}
          </div>

          {/* Clickable Chapter Beat Timeline */}
          <div className="rp-chapters-bar" role="navigation" aria-label="Scene beats">
            {chapters.map((ch, idx) => {
              const isCurrent = state.status !== 'idle' && (script[state.lineIndex]?.chapter || CHARACTERS[script[state.lineIndex]?.speaker || 'judge'].role) === ch.label;
              const isPast = state.status === 'finished' || (state.status !== 'idle' && state.lineIndex > ch.firstIdx && !isCurrent);
              return (
                <button
                  key={`${ch.label}-${ch.firstIdx}`}
                  type="button"
                  disabled={!ready}
                  onClick={() => jumpToLine(ch.firstIdx)}
                  className={`rp-beat ${ch.speaker} ${isCurrent ? 'now' : ''} ${isPast ? 'past' : ''}`}
                  title={`Jump to: ${ch.label}`}
                >
                  <span>{idx + 1}.</span> {ch.label}
                </button>
              );
            })}
          </div>

          {/* Transport Controls */}
          <div className="rp-controls">
            {state.status === 'playing' && <button className="rp-btn rp-btn-gold" onClick={pause}><Pause size={16} /> Pause</button>}
            {state.status === 'paused' && <button className="rp-btn rp-btn-gold" onClick={resume}><Play size={16} /> Resume</button>}
            {state.status === 'idle' && <button className="rp-btn rp-btn-gold" disabled={!ready} onClick={start}><Play size={16} /> Play Scene</button>}
            {state.status === 'finished' && <button className="rp-btn rp-btn-gold" onClick={replay}><RotateCcw size={16} /> Replay</button>}
            {(state.status === 'playing' || state.status === 'paused') && <button className="rp-btn" onClick={replay}><RotateCcw size={16} /> Restart</button>}

            <div className="rp-dots" aria-label="Interactive line scrubber">
              {script.map((l, idx) => (
                <button
                  key={l.id}
                  type="button"
                  disabled={!ready}
                  onClick={() => jumpToLine(idx)}
                  className={`${l.speaker} ${state.status !== 'idle' && idx < state.lineIndex ? 'past' : ''} ${state.status !== 'idle' && idx === state.lineIndex ? 'now' : ''}`}
                  title={`Line ${idx + 1}: ${CHARACTERS[l.speaker].role}`}
                />
              ))}
            </div>

            <span className="rp-voice-note" title={Object.entries(state.voiceNames).map(([k, v]) => `${k}: ${v || 'default'}`).join('\n')}>
              {state.voiceMode === 'speech' ? <Volume2 size={14} /> : <VolumeX size={14} />}
              {state.voiceMode === 'speech' ? '3 AI voices' : 'Subtitles only'}
            </span>
          </div>
        </div>

        {/* Interactive Live Script & Read-Only Case Dossier Drawer */}
        {showDossier && (
          <aside className="rp-dossier">
            <div className="rp-dossier-tabs">
              <button className={drawerTab === 'script' ? 'on' : ''} onClick={() => setDrawerTab('script')}>
                <Radio size={14} /> Live Script
              </button>
              <button className={drawerTab === 'dossier' ? 'on' : ''} onClick={() => setDrawerTab('dossier')}>
                <FileText size={14} /> Case Facts
              </button>
            </div>

            {drawerTab === 'script' ? (
              <div className="rp-script-list">
                {script.map((l, idx) => {
                  const active = state.status !== 'idle' && state.status !== 'finished' && state.lineIndex === idx;
                  return (
                    <button
                      key={l.id}
                      ref={active ? activeScriptRef : undefined}
                      type="button"
                      disabled={!ready}
                      onClick={() => jumpToLine(idx)}
                      className={`rp-script-item ${l.speaker} ${active ? 'active' : ''}`}
                    >
                      <div className="rp-script-meta">
                        <span>{CHARACTERS[l.speaker].role}</span>
                        {active && <em>SPEAKING</em>}
                      </div>
                      <p>{l.text}</p>
                    </button>
                  );
                })}
              </div>
            ) : (
              <div className="rp-facts-body">
                <div className="rp-fact-card">
                  <small>PRESIDING COURT</small>
                  <p>{judgment.presiding_court || 'AI Court of India'}</p>
                </div>
                <div className="rp-fact-card">
                  <small>FINAL VERDICT (READ-ONLY)</small>
                  <p className="rp-verdict-text">{judgment.final_decision}</p>
                </div>
                {Array.isArray(judgment.issues_for_determination) && judgment.issues_for_determination.length > 0 && (
                  <div className="rp-fact-card">
                    <small>KEY ISSUES</small>
                    <ul>
                      {judgment.issues_for_determination.slice(0, 3).map((iss, i) => (
                        <li key={i}>{iss}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {Array.isArray(judgment.legal_citations) && judgment.legal_citations.length > 0 && (
                  <div className="rp-fact-card">
                    <small>LAWS CITED</small>
                    <ul>
                      {judgment.legal_citations.slice(0, 4).map((cit, i) => (
                        <li key={i}>{cit}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </aside>
        )}
      </div>

      <p className="rp-disclaimer">
        A simplified dramatization built only from this case&apos;s completed AI Court judgment. Characters, voices and
        dialogue are AI-generated for explanation — not a real courtroom recording and not a new legal decision.
      </p>
    </main>
  );
};

export default CourtroomReplayPage;
