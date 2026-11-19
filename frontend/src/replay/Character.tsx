import React from 'react';
import type { Emotion, Gesture, Speaker } from './dialogue';
import type { Mouth } from './useReplayEngine';

interface Palette {
  skinHi: string;
  skinMid: string;
  skinShade: string;
  hair: string;
  hairHi: string;
  suit: string;
  suitShade: string;
  lapel: string;
  accent: string;
  shirt: string;
  lip: string;
}

const PALETTES: Record<Speaker, Palette> = {
  judge: {
    skinHi: '#D9A47C',
    skinMid: '#C68C63',
    skinShade: '#A36B46',
    hair: '#1E1614',
    hairHi: '#4B3A35',
    suit: '#161822',
    suitShade: '#0A0B10',
    lapel: '#232635',
    accent: '#D4AF37',
    shirt: '#F8FAFC',
    lip: '#8E413B',
  },
  prosecutor: {
    skinHi: '#E6B38E',
    skinMid: '#D49B72',
    skinShade: '#B07752',
    hair: '#141214',
    hairHi: '#342E34',
    suit: '#171C28',
    suitShade: '#0C1018',
    lapel: '#252C3F',
    accent: '#B91C1C',
    shirt: '#F8FAFC',
    lip: '#8F4D42',
  },
  defense: {
    skinHi: '#F3CFAF',
    skinMid: '#E2B790',
    skinShade: '#BE9068',
    hair: '#432A19',
    hairHi: '#70492E',
    suit: '#1D2432',
    suitShade: '#10151F',
    lapel: '#2C364A',
    accent: '#D4AF37',
    shirt: '#F8FAFC',
    lip: '#945448',
  },
};

const MOUTH_PATHS = (lip: string): Record<Mouth, React.ReactNode> => ({
  closed: (
    <g>
      <path d="M90 123 Q100 125.5 110 123" stroke={lip} strokeWidth="2.1" fill="none" strokeLinecap="round" />
      <path d="M95 127 Q100 128.5 105 127" stroke={lip} strokeWidth="1" opacity="0.45" fill="none" strokeLinecap="round" />
    </g>
  ),
  small: (
    <g>
      <ellipse cx="100" cy="123.5" rx="5.2" ry="2.8" fill="#461816" />
      <path d="M94 122 Q100 120.5 106 122" stroke={lip} strokeWidth="1.5" fill="none" />
    </g>
  ),
  wide: (
    <g>
      <path d="M90 120 Q100 118 110 120 Q109 131 100 131 Q91 131 90 120 Z" fill="#461816" stroke={lip} strokeWidth="1.4" />
      <path d="M93 120.5 Q100 122 107 120.5 L106 122.5 L94 122.5 Z" fill="#F8FAFC" opacity="0.92" />
      <ellipse cx="100" cy="128.5" rx="5" ry="2" fill="#C95B61" opacity="0.85" />
    </g>
  ),
  round: (
    <g>
      <ellipse cx="100" cy="124" rx="4.8" ry="6.2" fill="#461816" stroke={lip} strokeWidth="1.4" />
    </g>
  ),
  smile: (
    <g>
      <path d="M89 120.5 Q100 129.5 111 120.5 Q100 123.5 89 120.5 Z" fill="#461816" stroke={lip} strokeWidth="1.4" strokeLinejoin="round" />
      <path d="M92 121.2 Q100 123 108 121.2 L106.5 123 L93.5 123 Z" fill="#F8FAFC" opacity="0.92" />
    </g>
  ),
});

interface Props {
  kind: Speaker;
  speaking: boolean;
  mouth: Mouth;
  emotion: Emotion;
  gesture: Gesture;
  lookX?: number;
  reaction?: Emotion;
}

const browTransform = (emo: Emotion, side: 'l' | 'r'): string => {
  const s = side === 'l' ? 1 : -1;
  switch (emo) {
    case 'stern':
      return `translate(0,2) rotate(${s * 12}deg)`;
    case 'confident':
      return side === 'r' ? 'translate(0,-2.5)' : 'translate(0,0)';
    case 'thinking':
      return side === 'l' ? 'translate(0,-3.5) rotate(-5deg)' : 'translate(0,1)';
    case 'surprised':
      return 'translate(0,-4.5)';
    default:
      return 'none';
  }
};

export const Character: React.FC<Props> = ({
  kind,
  speaking,
  mouth,
  emotion,
  gesture,
  lookX = 0,
  reaction = 'neutral',
}) => {
  const p = PALETTES[kind];
  const emo = speaking ? emotion : reaction;
  const female = kind === 'judge';
  const shownMouth: Mouth = speaking ? mouth : emo === 'surprised' ? 'round' : 'closed';
  const idleSmirk = !speaking && emo === 'confident';
  const blinkDelay = kind === 'judge' ? '0.4s' : kind === 'prosecutor' ? '1.7s' : '2.6s';
  const mouths = MOUTH_PATHS(p.lip);

  const skinGradId = `skin-${kind}`;
  const suitGradId = `suit-${kind}`;
  const hairGradId = `hair-${kind}`;

  return (
    <svg
      viewBox="0 0 200 280"
      className={`rp-char rp-${kind} ${speaking ? 'is-speaking' : 'is-listening'} g-${speaking ? gesture : 'none'}`}
      role="img"
      aria-label={`${kind} character`}
    >
      <defs>
        <linearGradient id={skinGradId} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor={p.skinHi} />
          <stop offset="55%" stopColor={p.skinMid} />
          <stop offset="100%" stopColor={p.skinShade} />
        </linearGradient>
        <linearGradient id={suitGradId} x1="0" y1="0" x2="0.8" y2="1">
          <stop offset="0%" stopColor={p.lapel} />
          <stop offset="45%" stopColor={p.suit} />
          <stop offset="100%" stopColor={p.suitShade} />
        </linearGradient>
        <linearGradient id={hairGradId} x1="0.2" y1="0" x2="0.8" y2="1">
          <stop offset="0%" stopColor={p.hairHi} />
          <stop offset="60%" stopColor={p.hair} />
          <stop offset="100%" stopColor="#0B0908" />
        </linearGradient>
      </defs>

      <g className="rp-breathe">
        {/* Back hair / chignon for female judge */}
        {female && (
          <g>
            <ellipse cx="100" cy="44" rx="22" ry="17" fill={`url(#${hairGradId})`} />
            <path d="M58 92 Q52 132 62 152 L138 152 Q148 132 142 92 Z" fill={p.hair} />
          </g>
        )}

        {/* LEFT ARM (character's left = screen right) */}
        <g className="rp-arm rp-arm-l" style={{ transformOrigin: '148px 168px' }}>
          <path d="M148 168 Q170 204 162 238" stroke={`url(#${suitGradId})`} strokeWidth="24" strokeLinecap="round" fill="none" />
          <path d="M161 232 L164 240" stroke={p.shirt} strokeWidth="14" strokeLinecap="round" />
          {/* Stylized hand */}
          <path d="M155 240 Q162 236 169 241 L170 253 Q162 259 154 252 Z" fill={p.skinMid} stroke={p.skinShade} strokeWidth="0.9" />
        </g>

        {/* RIGHT ARM */}
        <g className="rp-arm rp-arm-r" style={{ transformOrigin: '52px 168px' }}>
          <path d="M52 168 Q30 204 38 238" stroke={`url(#${suitGradId})`} strokeWidth="24" strokeLinecap="round" fill="none" />
          <path d="M39 232 L36 240" stroke={p.shirt} strokeWidth="14" strokeLinecap="round" />
          {/* Articulated hand */}
          {gesture === 'point' && speaking ? (
            <g>
              <path d="M30 241 Q37 236 45 241 L44 253 Q36 257 30 251 Z" fill={p.skinMid} stroke={p.skinShade} strokeWidth="0.9" />
              <rect x="35" y="224" width="5.5" height="19" rx="2.7" fill={p.skinHi} stroke={p.skinShade} strokeWidth="0.7" />
            </g>
          ) : (
            <path d="M31 241 Q38 236 45 240 L46 252 Q38 259 30 253 Z" fill={p.skinMid} stroke={p.skinShade} strokeWidth="0.9" />
          )}
        </g>

        {/* TORSO / COAT & ROBE */}
        <path d="M38 280 L44 182 Q48 152 100 148 Q152 152 156 182 L162 280 Z" fill={`url(#${suitGradId})`} />
        {/* Subtle shoulder rim light */}
        <path d="M46 180 Q52 153 84 150" stroke="rgba(255,255,255,0.16)" strokeWidth="1.6" fill="none" />
        <path d="M154 180 Q148 153 116 150" stroke="rgba(255,255,255,0.12)" strokeWidth="1.6" fill="none" />

        {/* INDIAN COURT ATTIRE (white collar + advocate bands / judicial robe) */}
        {kind === 'judge' ? (
          <g>
            {/* Inner shirt V */}
            <path d="M84 150 L100 188 L116 150 Z" fill={p.shirt} />
            {/* Gold-trimmed judicial robe panels */}
            <path d="M62 152 L88 232 L82 280 L58 280 L54 176 Z" fill={p.suitShade} opacity="0.65" />
            <path d="M138 152 L112 232 L118 280 L142 280 L146 176 Z" fill={p.suitShade} opacity="0.65" />
            <path d="M74 152 L92 214" stroke={p.accent} strokeWidth="2.2" opacity="0.85" />
            <path d="M126 152 L108 214" stroke={p.accent} strokeWidth="2.2" opacity="0.85" />
            {/* Judicial white neckband (two crisp strips) */}
            <path d="M93 156 L99 156 L97 186 L90 185 Z" fill="#FFFFFF" stroke="#CBD5E1" strokeWidth="0.6" />
            <path d="M101 156 L107 156 L110 185 L103 186 Z" fill="#FFFFFF" stroke="#CBD5E1" strokeWidth="0.6" />
            <rect x="94" y="151" width="12" height="5" rx="1.5" fill="#F1F5F9" />
          </g>
        ) : (
          <g>
            {/* Waistcoat / inner shirt */}
            <path d="M80 150 L100 198 L120 150 Z" fill={p.shirt} />
            {/* Coat lapels */}
            <path d="M72 152 L92 198 L77 184 Z" fill={p.lapel} stroke={p.suitShade} strokeWidth="0.8" />
            <path d="M128 152 L108 198 L123 184 Z" fill={p.lapel} stroke={p.suitShade} strokeWidth="0.8" />
            {/* Indian Advocate white neckband */}
            <path d="M93.5 156 L99.2 156 L97.5 186 L91 185 Z" fill="#FFFFFF" stroke="#CBD5E1" strokeWidth="0.6" />
            <path d="M100.8 156 L106.5 156 L109 185 L102.5 186 Z" fill="#FFFFFF" stroke="#CBD5E1" strokeWidth="0.6" />
            <rect x="94" y="151" width="12" height="5" rx="1.5" fill="#F1F5F9" />
            {/* Pocket square accent */}
            <path d="M121 214 L137 210 L134 220 L122 220 Z" fill={p.accent} opacity="0.9" />
          </g>
        )}

        {/* NECK & CAST SHADOW */}
        <path d="M88 130 L112 130 L114 156 Q100 162 86 156 Z" fill={p.skinShade} />
        <ellipse cx="100" cy="140" rx="13" ry="5" fill="rgba(45,20,10,0.22)" />

        {/* HEAD */}
        <g className="rp-head">
          {/* Ears */}
          <path d="M60 95 Q52 95 53 107 Q54 116 61 114 Z" fill={p.skinShade} />
          <path d="M140 95 Q148 95 147 107 Q146 116 139 114 Z" fill={p.skinShade} />
          {female && (
            <g>
              <circle cx="57.5" cy="115" r="2.3" fill={p.accent} />
              <circle cx="142.5" cy="115" r="2.3" fill={p.accent} />
            </g>
          )}

          {/* Sculpted face silhouette (angular jaw for lawyers, softer tapered oval for judge) */}
          {female ? (
            <path
              d="M61 92 Q61 58 100 56 Q139 58 139 92 Q138 124 114 137 Q100 143 86 137 Q62 124 61 92 Z"
              fill={`url(#${skinGradId})`}
            />
          ) : (
            <path
              d="M60 90 Q60 56 100 54 Q140 56 140 90 L137 118 Q128 135 108 142 L92 142 Q72 135 63 118 Z"
              fill={`url(#${skinGradId})`}
            />
          )}

          {/* Subtle cheekbone contour & jawline shading (instead of cartoon circles) */}
          <path d="M66 112 Q72 126 86 134" stroke={p.skinShade} strokeWidth="1.8" opacity="0.25" fill="none" strokeLinecap="round" />
          <path d="M134 112 Q128 126 114 134" stroke={p.skinShade} strokeWidth="1.8" opacity="0.25" fill="none" strokeLinecap="round" />
          {kind === 'prosecutor' && (
            <path d="M65 117 Q100 148 135 117 L133 124 Q100 152 67 124 Z" fill={p.skinShade} opacity="0.22" />
          )}

          {/* Subtle bindi for female judge */}
          {female && <circle cx="100" cy="83" r="1.9" fill="#8B1E1E" />}

          {/* Eyes (refined almond shape, upper lash line, iris + pupil + glint) */}
          <g className="rp-eyes" style={{ animationDelay: blinkDelay, transformOrigin: '100px 97px' }}>
            <path d="M73 97 Q82 90 91 97 Q82 104 73 97 Z" fill="#FFFFFF" />
            <path d="M109 97 Q118 90 127 97 Q118 104 109 97 Z" fill="#FFFFFF" />
            <circle cx={82 + lookX} cy="97.5" r="4.3" fill="#3B2518" />
            <circle cx={118 + lookX} cy="97.5" r="4.3" fill="#3B2518" />
            <circle cx={82 + lookX} cy="97.5" r="2.1" fill="#120B07" />
            <circle cx={118 + lookX} cy="97.5" r="2.1" fill="#120B07" />
            <circle cx={83.4 + lookX} cy="95.8" r="1.1" fill="#FFFFFF" />
            <circle cx={119.4 + lookX} cy="95.8" r="1.1" fill="#FFFFFF" />
            {/* Upper eyelid crease & lashes */}
            <path d="M72.5 96.5 Q82 89.5 91.5 96.5" stroke="#1E1410" strokeWidth={female ? '2.2' : '1.7'} fill="none" strokeLinecap="round" />
            <path d="M108.5 96.5 Q118 89.5 127.5 96.5" stroke="#1E1410" strokeWidth={female ? '2.2' : '1.7'} fill="none" strokeLinecap="round" />
          </g>

          {/* Sleek metallic half-rim spectacles for Defence Lawyer */}
          {kind === 'defense' && (
            <g>
              <rect x="70" y="89.5" width="24" height="16" rx="4.5" fill="rgba(186,230,253,0.10)" stroke="#475569" strokeWidth="1.6" />
              <rect x="106" y="89.5" width="24" height="16" rx="4.5" fill="rgba(186,230,253,0.10)" stroke="#475569" strokeWidth="1.6" />
              <path d="M94 95.5 Q100 94 106 95.5" stroke="#64748B" strokeWidth="1.6" fill="none" />
              <path d="M73 92 L78 96" stroke="rgba(255,255,255,0.35)" strokeWidth="1.2" strokeLinecap="round" />
              <path d="M109 92 L114 96" stroke="rgba(255,255,255,0.35)" strokeWidth="1.2" strokeLinecap="round" />
            </g>
          )}

          {/* Expressive eyebrows */}
          <g className="rp-brows" stroke={p.hair} strokeWidth={kind === 'prosecutor' ? '3.8' : '3'} strokeLinecap="round" fill="none">
            <path d="M72 85 Q82 80.5 92 84" style={{ transform: browTransform(emo, 'l'), transformOrigin: '82px 83px', transition: 'transform .3s' }} />
            <path d="M108 84 Q118 80.5 128 85" style={{ transform: browTransform(emo, 'r'), transformOrigin: '118px 83px', transition: 'transform .3s' }} />
          </g>

          {/* Sculpted nose bridge & tip */}
          <path d="M100 94 L98 110 Q100 113.5 103.5 111" stroke={p.skinShade} strokeWidth="2" fill="none" strokeLinecap="round" opacity="0.85" />

          {/* Mouth */}
          <g className="rp-mouth">
            {mouths[shownMouth]}
            {idleSmirk && <path d="M109 122 Q113 120 115 117.5" stroke={p.lip} strokeWidth="1.6" fill="none" strokeLinecap="round" />}
          </g>

          {/* Hair front — sculpted styles with silver-temple realism on Judge */}
          {kind === 'judge' && (
            <g>
              <path d="M58 95 Q55 52 100 47 Q145 52 142 95 Q134 66 102 63 Q70 65 58 95 Z" fill={`url(#${hairGradId})`} />
              <path d="M102 62 Q82 65 65 86 Q76 62 102 56 Z" fill={p.hair} />
              {/* Mature silver temple streaks */}
              <path d="M61 86 Q65 73 74 68" stroke="#CBD5E1" strokeWidth="2.4" fill="none" strokeLinecap="round" opacity="0.7" />
              <path d="M139 86 Q135 73 126 68" stroke="#CBD5E1" strokeWidth="2.4" fill="none" strokeLinecap="round" opacity="0.7" />
            </g>
          )}
          {kind === 'prosecutor' && (
            <g>
              <path d="M58 90 Q54 46 100 42 Q146 46 142 90 Q135 61 100 58 Q65 61 58 90 Z" fill={`url(#${hairGradId})`} />
              <path d="M68 62 Q94 46 128 58 Q104 51 78 63 Z" fill={p.hairHi} opacity="0.55" />
            </g>
          )}
          {kind === 'defense' && (
            <g>
              <path
                d="M58 91 Q54 44 103 44 Q146 46 142 91 Q136 67 116 61 Q88 55 68 69 Z"
                fill={`url(#${hairGradId})`}
              />
              <path d="M74 60 Q98 48 128 59 Q105 53 84 63 Z" fill={p.hairHi} opacity="0.6" />
            </g>
          )}
        </g>
      </g>
    </svg>
  );
};
