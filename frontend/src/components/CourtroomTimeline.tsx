import React from 'react';
import { Check } from 'lucide-react';
import type { AgentMessage } from '../types/court';

interface CourtroomTimelineProps {
  messages: AgentMessage[];
  currentAgent: string | null;
  isStreaming?: boolean;
}

const TIMELINE_STEPS = [
  { id: 'case_understanding', label: 'Case Understanding', side: 'neutral' },
  { id: 'prosecutor', label: 'Prosecutor', side: 'prosecution' },
  { id: 'prosecutor_legal_research', label: 'Prosecutor Legal Research', side: 'prosecution' },
  { id: 'prosecutor_web_research', label: 'Prosecutor Web Research', side: 'prosecution' },
  { id: 'defense', label: 'Defense', side: 'defense' },
  { id: 'defense_legal_research', label: 'Defense Legal Research', side: 'defense' },
  { id: 'defense_web_research', label: 'Defense Web Research', side: 'defense' },
  { id: 'evidence', label: 'Evidence Analysis', side: 'neutral' },
  { id: 'conflict', label: 'Conflict Detection', side: 'neutral' },
  { id: 'judge', label: 'Judge', side: 'judicial' },
];

export const CourtroomTimeline: React.FC<CourtroomTimelineProps> = ({
  messages,
  currentAgent,
}) => {
  // Determine completion and active status
  const completedNodes = new Set(messages.map((m) => m.agent));

  return (
    <div
      className="glass-panel"
      style={{
        padding: '12px 18px',
        marginBottom: '16px',
        overflowX: 'auto',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', minWidth: '780px' }}>
        {TIMELINE_STEPS.map((step, idx) => {
          const isCompleted = completedNodes.has(step.id);
          const isActive = currentAgent === step.id;

          // Side-based accents
          const getAccentColor = () => {
            if (isCompleted) return '#10B981';
            if (isActive) return 'var(--gold-primary)';
            return '#64748B';
          };

          return (
            <div
              key={step.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 8px',
                borderRadius: '6px',
                background: isActive
                  ? 'rgba(212, 175, 55, 0.12)'
                  : isCompleted
                  ? 'rgba(16, 185, 129, 0.08)'
                  : 'transparent',
                border: isActive
                  ? '1px solid var(--gold-primary)'
                  : isCompleted
                  ? '1px solid rgba(16, 185, 129, 0.2)'
                  : '1px solid transparent',
                transition: 'all 0.2s ease',
              }}
              title={`${step.label}: ${isCompleted ? 'Completed' : isActive ? 'Deliberating' : 'Pending'}`}
            >
              {/* Status Symbol: ✓, ●, or ○ */}
              <div
                style={{
                  width: '18px',
                  height: '18px',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  background: isCompleted
                    ? 'rgba(16, 185, 129, 0.2)'
                    : isActive
                    ? 'rgba(212, 175, 55, 0.2)'
                    : 'rgba(255, 255, 255, 0.04)',
                  color: getAccentColor(),
                }}
              >
                {isCompleted ? (
                  <Check size={11} strokeWidth={3} />
                ) : isActive ? (
                  <span style={{ fontSize: '0.65rem' }}>●</span>
                ) : (
                  <span style={{ fontSize: '0.75rem', opacity: 0.5 }}>○</span>
                )}
              </div>

              {/* Label */}
              <span
                style={{
                  fontSize: '0.74rem',
                  fontWeight: isActive ? 700 : isCompleted ? 600 : 400,
                  color: isActive ? 'var(--gold-primary)' : isCompleted ? '#E2E8F0' : '#64748B',
                  whiteSpace: 'nowrap',
                }}
              >
                {step.label}
              </span>

              {/* Connecting line between steps */}
              {idx < TIMELINE_STEPS.length - 1 && (
                <span style={{ color: 'rgba(255, 255, 255, 0.1)', marginLeft: '4px', fontSize: '0.7rem' }}>
                  &rarr;
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
