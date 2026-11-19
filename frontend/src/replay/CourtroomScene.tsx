import React from 'react';
import { Character } from './Character';
import type { DialogueLine, Emotion, Speaker } from './dialogue';
import { CHARACTERS } from './dialogue';
import type { Mouth } from './useReplayEngine';

export type CameraMode = 'auto' | 'wide' | 'focus';

interface SceneProps {
  line: DialogueLine | null;
  speaker: Speaker | null;
  mouth: Mouth;
  gavelTick: number;
  playing: boolean;
  cameraMode?: CameraMode;
  onSelectSpeaker?: (who: Speaker) => void;
}

const lookFor = (who: Speaker, speaker: Speaker | null): number => {
  if (!speaker || speaker === who) return 0;
  if (who === 'judge') return speaker === 'prosecutor' ? -2.8 : 2.8;
  if (who === 'prosecutor') return speaker === 'defense' ? 2.8 : 1.6;
  return speaker === 'prosecutor' ? -2.8 : -1.6;
};

const reactionFor = (who: Speaker, speaker: Speaker | null): Emotion => {
  if (!speaker || speaker === who) return 'neutral';
  if (who === 'judge') return 'thinking';
  if (who === 'defense' && speaker === 'prosecutor') return 'stern';
  if (who === 'prosecutor' && speaker === 'defense') return 'surprised';
  return 'neutral';
};

const ORIGINS: Record<Speaker, string> = { judge: '50% 38%', prosecutor: '20% 68%', defense: '80% 68%' };
const SPOT_X: Record<Speaker, string> = { judge: '50%', prosecutor: '22%', defense: '78%' };

export const CourtroomScene: React.FC<SceneProps> = ({
  line,
  speaker,
  mouth,
  gavelTick,
  playing,
  cameraMode = 'auto',
  onSelectSpeaker,
}) => {
  const camera = line?.camera ?? 'wide';
  let zoom = 1;
  if (playing && speaker) {
    if (cameraMode === 'wide') zoom = 1.03;
    else if (cameraMode === 'focus') zoom = camera === 'verdict' ? 1.78 : 1.48;
    else zoom = camera === 'verdict' ? 1.75 : camera === 'speaker' ? 1.38 : 1.04;
  }
  const origin = camera === 'verdict' ? ORIGINS.judge : speaker ? ORIGINS[speaker] : '50% 50%';
  const snapCam = playing && (line?.cue === 'interrupt' || line?.camera === 'verdict');
  const isInterrupt = playing && line?.cue === 'interrupt';
  const objectionText = line?.lang === 'hi' ? 'ऑब्जेक्शन!' : 'OBJECTION!';
  const spotX = speaker ? SPOT_X[speaker] : '50%';

  const render = (who: Speaker) => (
    <Character
      kind={who}
      speaking={speaker === who}
      mouth={mouth}
      emotion={line?.emotion ?? 'neutral'}
      gesture={line?.gesture ?? 'none'}
      lookX={lookFor(who, speaker)}
      reaction={reactionFor(who, speaker)}
    />
  );

  return (
    <div key={gavelTick > 0 ? `sc-${gavelTick}` : 'sc-0'} className={`rp-scene ${gavelTick > 0 && playing ? 'rp-shake' : ''}`}>
      <div
        className={`rp-camera ${snapCam ? 'rp-camera-snap' : ''}`}
        style={{ transform: `scale(${zoom})`, transformOrigin: origin }}
      >
        {/* Back wall + wood paneling + tall arched windows */}
        <div className="rp-wall">
          <div className="rp-panels" />
          <div className="rp-molding" />
          <div className="rp-sunbeam rp-sunbeam-l" />
          <div className="rp-sunbeam rp-sunbeam-r" />
          <svg className="rp-window rp-window-l" viewBox="0 0 70 130">
            <rect x="3" y="3" width="64" height="124" rx="32" fill="url(#sky)" stroke="#5A391E" strokeWidth="5" />
            <path d="M35 3 V127 M3 65 H67 M14 36 H56" stroke="#5A391E" strokeWidth="2.8" />
          </svg>
          <svg className="rp-window rp-window-r" viewBox="0 0 70 130">
            <rect x="3" y="3" width="64" height="124" rx="32" fill="url(#sky)" stroke="#5A391E" strokeWidth="5" />
            <path d="M35 3 V127 M3 65 H67 M14 36 H56" stroke="#5A391E" strokeWidth="2.8" />
          </svg>
          <svg width="0" height="0" style={{ position: 'absolute' }}>
            <defs>
              <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="#FDE9B8" />
                <stop offset="0.6" stopColor="#F8C882" />
                <stop offset="1" stopColor="#DF9252" />
              </linearGradient>
            </defs>
          </svg>

          {/* Emblem above the judge */}
          <div className="rp-emblem">
            <svg viewBox="0 0 120 120">
              <circle cx="60" cy="60" r="52" fill="#9A7016" stroke="#E5C158" strokeWidth="4" />
              <circle cx="60" cy="60" r="43" fill="#681818" stroke="#E5C158" strokeWidth="2" />
              <path d="M60 28 V90 M36 41 H84 M36 41 L28 66 H44 Z M84 41 L76 66 H92 Z" stroke="#FEF08A" strokeWidth="3" fill="none" strokeLinejoin="round" />
              <path d="M44 90 H76" stroke="#FEF08A" strokeWidth="4" strokeLinecap="round" />
            </svg>
            <span>SATYAMEVA JAYATE</span>
          </div>
        </div>

        {/* Polished wooden courtroom floor */}
        <div className="rp-floor" />

        {/* Dynamic overhead spotlight sweeping to active speaker */}
        <div
          className={`rp-spotlight ${playing && speaker ? 'on' : ''}`}
          style={{ left: spotX }}
        />

        {/* Prosecutor (left) */}
        <div
          className={`rp-actor rp-actor-prosecutor ${speaker === 'prosecutor' ? 'active' : playing ? 'dim' : ''}`}
          onClick={() => onSelectSpeaker?.('prosecutor')}
          title="Jump to Prosecutor's argument"
        >
          {render('prosecutor')}
        </div>
        <div className="rp-podium rp-podium-l">
          <i />
          <div className="rp-mic">
            <span className={`rp-mic-led ${speaker === 'prosecutor' && playing ? 'on' : ''}`} />
          </div>
          <div className="rp-files" />
        </div>

        {/* Defence (right) */}
        <div
          className={`rp-actor rp-actor-defense ${speaker === 'defense' ? 'active' : playing ? 'dim' : ''}`}
          onClick={() => onSelectSpeaker?.('defense')}
          title="Jump to Defence's argument"
        >
          {render('defense')}
        </div>
        <div className="rp-podium rp-podium-r">
          <i />
          <div className="rp-mic rp-mic-r">
            <span className={`rp-mic-led ${speaker === 'defense' && playing ? 'on' : ''}`} />
          </div>
          <div className="rp-files rp-files-r" />
        </div>

        {/* Judge (centre, behind elevated mahogany bench) */}
        <div
          className={`rp-actor rp-actor-judge ${speaker === 'judge' ? 'active' : playing ? 'dim' : ''}`}
          onClick={() => onSelectSpeaker?.('judge')}
          title="Jump to Judge"
        >
          {render('judge')}
        </div>
        <div className="rp-bench">
          <div className="rp-bench-top" />
          <div className="rp-bench-front">
            <div className="rp-bench-trim" />
            <span>{CHARACTERS.judge.name.toUpperCase()}</span>
          </div>
          <div className="rp-bench-mic">
            <span className={`rp-mic-led ${speaker === 'judge' && playing ? 'on' : ''}`} />
          </div>
          <div className="rp-sounding-block" />
          <div key={gavelTick} className={`rp-gavel ${gavelTick > 0 ? 'bang' : ''}`}>
            <svg viewBox="0 0 80 50">
              <rect x="8" y="4" width="34" height="16" rx="4" fill="#8B5E34" stroke="#4A2E14" strokeWidth="2" transform="rotate(-20 25 12)" />
              <rect x="36" y="20" width="38" height="6" rx="3" fill="#A0703F" transform="rotate(-20 55 23)" />
            </svg>
          </div>
        </div>
      </div>

      <div className="rp-vignette" />
      {playing && line?.chapter && (
        <div className={`rp-chapter rp-chapter-${line.speaker}`}>
          <span className="rp-chapter-dot" />
          {line.chapter}
        </div>
      )}
      {isInterrupt && (
        <div key={`obj-${line!.id}`} className="rp-objection-flash" aria-hidden="true">
          {objectionText}
        </div>
      )}
    </div>
  );
};
