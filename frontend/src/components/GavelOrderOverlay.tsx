import React, { useEffect } from 'react';

interface GavelOrderOverlayProps {
  visible: boolean;
  mode: 'start' | 'end';
  verdict?: string | null;
  onDone: () => void;
}

export const GavelOrderOverlay: React.FC<GavelOrderOverlayProps> = ({
  visible,
  mode,
  verdict,
  onDone,
}) => {
  useEffect(() => {
    if (!visible) return;
    const duration = mode === 'end' ? 2500 : 2100;
    const timer = window.setTimeout(onDone, duration);
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onDone();
    };
    window.addEventListener('keydown', handleKey);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener('keydown', handleKey);
    };
  }, [visible, mode, onDone]);

  if (!visible) return null;

  const isStart = mode === 'start';
  const headline = 'ORDER!';
  const subline = isStart ? 'COURT IS NOW IN SESSION' : 'FINAL JUDGMENT PRONOUNCED';

  return (
    <div
      role="status"
      aria-live="polite"
      onClick={onDone}
      className="gavel-overlay-backdrop"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 12000,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background:
          'radial-gradient(circle at 50% 45%, rgba(18, 14, 8, 0.34) 0%, rgba(5, 8, 15, 0.52) 78%)',
        backdropFilter: 'blur(3px)',
        WebkitBackdropFilter: 'blur(3px)',
        cursor: 'pointer',
        padding: '24px',
        textAlign: 'center',
      }}
      title="Click anywhere to dismiss"
    >
      {/* Large Animated Gavel + Sound Block Stage */}
      <div
        style={{
          position: 'relative',
          width: '260px',
          height: '200px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: '8px',
        }}
      >
        {/* Expanding Shockwave Rings on Strike */}
        <div className="gavel-shockwave gavel-shockwave-1" />
        <div className="gavel-shockwave gavel-shockwave-2" />

        {/* Swinging Gavel (HTML wrapper so transform animates reliably in every browser) */}
        <div
          className="big-gavel-swing"
          style={{
            position: 'absolute',
            top: '0px',
            left: '20px',
            width: '210px',
            height: '130px',
            zIndex: 3,
            pointerEvents: 'none',
            transformOrigin: 'top right',
          }}
        >
          <svg viewBox="0 0 190 120" width="210" height="130" aria-hidden="true" style={{ overflow: 'visible' }}>
            <defs>
              <linearGradient id="gavelGold" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#FDE68A" />
                <stop offset="50%" stopColor="#D4AF37" />
                <stop offset="100%" stopColor="#926C15" />
              </linearGradient>
              <linearGradient id="gavelWood" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#5C3A21" />
                <stop offset="50%" stopColor="#8B5A2B" />
                <stop offset="100%" stopColor="#4A2E1B" />
              </linearGradient>
            </defs>

            {/* Handle */}
            <rect
              x="64"
              y="46"
              width="104"
              height="14"
              rx="7"
              transform="rotate(-14 64 53)"
              fill="url(#gavelWood)"
              stroke="url(#gavelGold)"
              strokeWidth="1.6"
            />
            {/* Brass Handle Cap */}
            <circle cx="164" cy="28" r="8" fill="url(#gavelGold)" />

            {/* Gavel Head */}
            <g transform="translate(52, 54) rotate(-14)">
              <rect
                x="-28"
                y="-26"
                width="56"
                height="52"
                rx="8"
                fill="url(#gavelWood)"
                stroke="url(#gavelGold)"
                strokeWidth="2.5"
              />
              <rect x="-32" y="-28" width="64" height="9" rx="4" fill="url(#gavelGold)" />
              <rect x="-32" y="19" width="64" height="9" rx="4" fill="url(#gavelGold)" />
            </g>
          </svg>
        </div>

        {/* Sound Block (Base) */}
        <div
          className="gavel-sound-block"
          style={{
            position: 'absolute',
            bottom: '12px',
            left: '38px',
            width: '130px',
            height: '44px',
            zIndex: 2,
            pointerEvents: 'none',
          }}
        >
          <svg viewBox="0 0 130 44" width="130" height="44" aria-hidden="true">
            <ellipse cx="65" cy="36" rx="56" ry="7" fill="rgba(0,0,0,0.6)" />
            <rect
              x="12"
              y="14"
              width="106"
              height="18"
              rx="6"
              fill="#6E472B"
              stroke="#D4AF37"
              strokeWidth="2"
            />
            <rect
              x="22"
              y="8"
              width="86"
              height="8"
              rx="3"
              fill="#8B5A2B"
              stroke="#FDE68A"
              strokeWidth="1.2"
            />
          </svg>
        </div>
      </div>

      {/* ORDER! Typography */}
      <h1
        className="gavel-order-title"
        style={{
          fontFamily: 'var(--font-serif)',
          fontSize: 'clamp(2.4rem, 6vw, 4rem)',
          fontWeight: 900,
          letterSpacing: '0.22em',
          color: 'var(--gold-primary)',
          textShadow: '0 4px 28px rgba(0, 0, 0, 0.9), 0 0 32px rgba(212, 175, 55, 0.65)',
          margin: '0 0 8px 0',
        }}
      >
        {headline}
      </h1>

      <p
        style={{
          fontFamily: 'var(--font-serif)',
          fontSize: 'clamp(0.85rem, 2vw, 1.05rem)',
          letterSpacing: '0.18em',
          color: '#F8FAFC',
          textShadow: '0 2px 12px rgba(0, 0, 0, 0.9)',
          margin: 0,
        }}
      >
        {subline}
      </p>

      {!isStart && verdict && (
        <div
          style={{
            marginTop: '16px',
            padding: '6px 18px',
            borderRadius: '999px',
            background: verdict.toUpperCase().includes('CONVICTION')
              ? 'rgba(239, 68, 68, 0.28)'
              : 'rgba(16, 185, 129, 0.28)',
            border: verdict.toUpperCase().includes('CONVICTION')
              ? '1px solid rgba(239, 68, 68, 0.65)'
              : '1px solid rgba(16, 185, 129, 0.65)',
            color: verdict.toUpperCase().includes('CONVICTION') ? '#FCA5A5' : '#6EE7B7',
            fontWeight: 700,
            fontSize: '0.88rem',
            letterSpacing: '0.08em',
            backdropFilter: 'blur(4px)',
          }}
        >
          {verdict}
        </div>
      )}

      <span
        style={{
          marginTop: '22px',
          fontSize: '0.72rem',
          color: '#CBD5E1',
          textShadow: '0 1px 6px rgba(0,0,0,0.85)',
          letterSpacing: '0.06em',
        }}
      >
        Click anywhere to continue
      </span>
    </div>
  );
};
