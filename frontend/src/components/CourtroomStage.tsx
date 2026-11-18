import React, { useState } from 'react';
import { Gavel, Scale, Shield, Briefcase, ChevronUp, ChevronDown, Microscope, AlertTriangle } from 'lucide-react';
import type { Judgment } from '../types/court';

interface CourtroomStageProps {
  currentAgent: string | null;
  isStreaming: boolean;
  judgment: Judgment | null;
  activeStageIndex: number;
  totalStages: number;
  activeStageLabel: string;
}

export const CourtroomStage: React.FC<CourtroomStageProps> = ({
  currentAgent,
  isStreaming,
  judgment,
  activeStageIndex,
  totalStages,
  activeStageLabel,
}) => {
  const [collapsed, setCollapsed] = useState(false);

  const isDefenseActive = Boolean(
    currentAgent && (currentAgent === 'live_defense' || currentAgent.startsWith('defense')),
  );
  const isProsecutionActive = Boolean(
    currentAgent && (currentAgent === 'live_prosecutor' || currentAgent.startsWith('prosecutor')),
  );
  const isForensicsActive = Boolean(
    currentAgent && ['live_evidence', 'evidence', 'live_conflict', 'conflict'].includes(currentAgent),
  );
  const isBenchActive = Boolean(
    judgment ||
      !currentAgent ||
      ['case_understanding', 'live_judge', 'judge'].includes(currentAgent),
  );

  const statusBanner = judgment
    ? 'FINAL JUDGMENT PRONOUNCED — COURT ORDER ON RECORD'
    : isStreaming
      ? 'ALL RISE — PROCEEDINGS IN OPEN COURT'
      : 'CHAMBERS STANDING BY';

  return (
    <div
      className="glass-panel-court animate-bench-settle"
      style={{
        overflow: 'hidden',
        borderColor: 'rgba(212, 175, 55, 0.28)',
        background:
          'linear-gradient(180deg, rgba(16, 20, 32, 0.94) 0%, rgba(9, 13, 22, 0.96) 100%)',
      }}
    >
      {/* Top Bar with Stage Counter & Collapse Toggle */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 16px',
          borderBottom: collapsed ? 'none' : '1px solid rgba(212, 175, 55, 0.14)',
          background: 'rgba(7, 11, 20, 0.55)',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '0.68rem',
              letterSpacing: '0.08em',
              color: 'var(--gold-primary)',
              background: 'rgba(212, 175, 55, 0.12)',
              border: '1px solid rgba(212, 175, 55, 0.3)',
              padding: '2px 8px',
              borderRadius: '999px',
              fontWeight: 600,
            }}
          >
            STAGE {Math.max(1, activeStageIndex)} OF {totalStages}
          </span>
          <span
            style={{
              fontFamily: 'var(--font-serif)',
              fontSize: '0.8rem',
              color: '#E2E8F0',
              letterSpacing: '0.04em',
            }}
          >
            {activeStageLabel}
          </span>
        </div>

        <button
          type="button"
          onClick={() => setCollapsed((prev) => !prev)}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            color: '#CBD5E1',
            borderRadius: '6px',
            padding: '3px 9px',
            fontSize: '0.72rem',
            cursor: 'pointer',
          }}
        >
          <span>{collapsed ? 'Show Stage' : 'Hide Stage'}</span>
          {collapsed ? <ChevronDown size={13} /> : <ChevronUp size={13} />}
        </button>
      </div>

      {/* Architectural 3-Bench Courtroom Stage */}
      {!collapsed && (
        <div
          style={{
            position: 'relative',
            padding: '20px 18px 14px 18px',
            background:
              'radial-gradient(ellipse 65% 75% at 50% 15%, rgba(212, 175, 55, 0.11), transparent 70%), linear-gradient(180deg, rgba(18, 22, 34, 0.9) 0%, rgba(10, 14, 24, 0.98) 100%)',
          }}
        >
          {/* Subtle Arched Windows Backdrop */}
          <div
            aria-hidden="true"
            style={{
              position: 'absolute',
              inset: '14px 24px auto 24px',
              display: 'flex',
              justifyContent: 'space-between',
              pointerEvents: 'none',
              opacity: 0.22,
            }}
          >
            <div
              style={{
                width: '46px',
                height: '76px',
                borderRadius: '24px 24px 2px 2px',
                border: '1px solid rgba(212, 175, 55, 0.35)',
                background: 'linear-gradient(180deg, rgba(212, 175, 55, 0.16), transparent)',
              }}
            />
            <div
              style={{
                width: '46px',
                height: '76px',
                borderRadius: '24px 24px 2px 2px',
                border: '1px solid rgba(212, 175, 55, 0.35)',
                background: 'linear-gradient(180deg, rgba(212, 175, 55, 0.16), transparent)',
              }}
            />
          </div>

          {/* 3-Bench Grid */}
          <div
            style={{
              position: 'relative',
              display: 'grid',
              gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
              alignItems: 'end',
              gap: '14px',
              maxWidth: '820px',
              margin: '0 auto',
            }}
          >
            {/* LEFT: DEFENSE COUNSEL */}
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '8px',
                opacity: isDefenseActive ? 1 : 0.62,
                transform: isDefenseActive ? 'translateY(-3px)' : 'translateY(0)',
                transition: 'all 0.3s ease',
              }}
            >
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '0.62rem', letterSpacing: '0.1em', color: '#6EE7B7', fontWeight: 700 }}>
                  DEFENSE COUNSEL
                </div>
                <div style={{ fontSize: '0.68rem', color: '#94A3B8' }}>Responding to charges</div>
              </div>

              <div
                className={isDefenseActive ? 'active-speaker-card' : undefined}
                style={{
                  width: '48px',
                  height: '48px',
                  borderRadius: '50%',
                  background: isDefenseActive ? 'rgba(16, 185, 129, 0.22)' : 'rgba(15, 23, 42, 0.85)',
                  border: `1.5px solid ${isDefenseActive ? '#34D399' : 'rgba(16, 185, 129, 0.35)'}`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: isDefenseActive ? '0 0 22px rgba(16, 185, 129, 0.38)' : 'none',
                }}
              >
                <Shield size={20} color="#34D399" />
              </div>

              {/* Wooden / Dark Desk Plaque */}
              <div
                style={{
                  width: '100%',
                  padding: '8px 6px',
                  borderRadius: '6px 6px 2px 2px',
                  background: 'linear-gradient(180deg, rgba(34, 24, 18, 0.92) 0%, rgba(20, 15, 12, 0.96) 100%)',
                  borderTop: `2px solid ${isDefenseActive ? '#34D399' : 'rgba(148, 163, 184, 0.25)'}`,
                  borderLeft: '1px solid rgba(255, 255, 255, 0.06)',
                  borderRight: '1px solid rgba(255, 255, 255, 0.06)',
                  textAlign: 'center',
                }}
              >
                <span
                  style={{
                    fontFamily: 'var(--font-serif)',
                    fontSize: '0.68rem',
                    letterSpacing: '0.12em',
                    color: isDefenseActive ? '#6EE7B7' : '#CBD5E1',
                    fontWeight: 700,
                  }}
                >
                  DEFENSE
                </span>
              </div>
            </div>

            {/* CENTER: THE BENCH (Elevated) */}
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '8px',
                paddingBottom: '12px',
                opacity: isBenchActive || isForensicsActive ? 1 : 0.72,
                transform: isBenchActive ? 'translateY(-4px)' : 'translateY(0)',
                transition: 'all 0.3s ease',
              }}
            >
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '0.64rem', letterSpacing: '0.12em', color: 'var(--gold-primary)', fontWeight: 700 }}>
                  THE HONOURABLE
                </div>
                <div style={{ fontSize: '0.68rem', color: '#CBD5E1' }}>
                  {isForensicsActive ? 'Reviewing forensics & record' : 'Guides the hearing'}
                </div>
              </div>

              <div
                className={isBenchActive && isStreaming ? 'emblem-breathe' : undefined}
                style={{
                  width: '58px',
                  height: '58px',
                  borderRadius: '50%',
                  background:
                    'radial-gradient(circle, rgba(212, 175, 55, 0.26) 0%, rgba(15, 23, 42, 0.92) 75%)',
                  border: '2px solid var(--gold-primary)',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '2px',
                  boxShadow: isBenchActive ? '0 0 26px rgba(212, 175, 55, 0.35)' : 'none',
                }}
              >
                {isForensicsActive ? (
                  currentAgent?.includes('conflict') ? (
                    <AlertTriangle size={22} color="#FBBF24" />
                  ) : (
                    <Microscope size={22} color="#D8B4FE" />
                  )
                ) : isBenchActive && isStreaming ? (
                  <span className="gavel-hammer-loop">
                    <Gavel size={22} color="var(--gold-primary)" />
                  </span>
                ) : (
                  <Scale size={24} color="var(--gold-primary)" />
                )}
              </div>

              {/* Elevated Bench Podium */}
              <div
                style={{
                  width: '100%',
                  padding: '10px 8px',
                  borderRadius: '8px 8px 3px 3px',
                  background: 'linear-gradient(180deg, rgba(44, 30, 18, 0.95) 0%, rgba(22, 15, 10, 0.98) 100%)',
                  borderTop: '2.5px solid var(--gold-primary)',
                  borderLeft: '1px solid rgba(212, 175, 55, 0.28)',
                  borderRight: '1px solid rgba(212, 175, 55, 0.28)',
                  boxShadow: '0 8px 20px rgba(0, 0, 0, 0.45)',
                  textAlign: 'center',
                }}
              >
                <span
                  style={{
                    fontFamily: 'var(--font-serif)',
                    fontSize: '0.76rem',
                    letterSpacing: '0.16em',
                    color: 'var(--gold-primary)',
                    fontWeight: 800,
                  }}
                >
                  THE BENCH
                </span>
              </div>
            </div>

            {/* RIGHT: PUBLIC PROSECUTOR */}
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '8px',
                opacity: isProsecutionActive ? 1 : 0.62,
                transform: isProsecutionActive ? 'translateY(-3px)' : 'translateY(0)',
                transition: 'all 0.3s ease',
              }}
            >
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '0.62rem', letterSpacing: '0.1em', color: '#93C5FD', fontWeight: 700 }}>
                  PUBLIC PROSECUTOR
                </div>
                <div style={{ fontSize: '0.68rem', color: '#94A3B8' }}>Making the accusation</div>
              </div>

              <div
                className={isProsecutionActive ? 'active-speaker-card' : undefined}
                style={{
                  width: '48px',
                  height: '48px',
                  borderRadius: '50%',
                  background: isProsecutionActive ? 'rgba(59, 130, 246, 0.22)' : 'rgba(15, 23, 42, 0.85)',
                  border: `1.5px solid ${isProsecutionActive ? '#60A5FA' : 'rgba(59, 130, 246, 0.35)'}`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: isProsecutionActive ? '0 0 22px rgba(59, 130, 246, 0.38)' : 'none',
                }}
              >
                <Briefcase size={20} color="#60A5FA" />
              </div>

              {/* Wooden / Dark Desk Plaque */}
              <div
                style={{
                  width: '100%',
                  padding: '8px 6px',
                  borderRadius: '6px 6px 2px 2px',
                  background: 'linear-gradient(180deg, rgba(34, 24, 18, 0.92) 0%, rgba(20, 15, 12, 0.96) 100%)',
                  borderTop: `2px solid ${isProsecutionActive ? '#60A5FA' : 'rgba(148, 163, 184, 0.25)'}`,
                  borderLeft: '1px solid rgba(255, 255, 255, 0.06)',
                  borderRight: '1px solid rgba(255, 255, 255, 0.06)',
                  textAlign: 'center',
                }}
              >
                <span
                  style={{
                    fontFamily: 'var(--font-serif)',
                    fontSize: '0.68rem',
                    letterSpacing: '0.12em',
                    color: isProsecutionActive ? '#93C5FD' : '#CBD5E1',
                    fontWeight: 700,
                  }}
                >
                  PROSECUTION
                </span>
              </div>
            </div>
          </div>

          {/* Aisle Decorum Notice */}
          <div
            style={{
              textAlign: 'center',
              marginTop: '12px',
              fontSize: '0.66rem',
              letterSpacing: '0.16em',
              color: 'rgba(212, 175, 55, 0.72)',
              fontFamily: 'var(--font-serif)',
            }}
          >
            {statusBanner}
          </div>
        </div>
      )}
    </div>
  );
};
