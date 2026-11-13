import React, { useState } from 'react';
import { Shield, ChevronDown, ChevronUp, AlertCircle, CheckCircle, FileX, Scale } from 'lucide-react';

interface DefenseRendererProps {
  payload: any;
}

export const DefenseRenderer: React.FC<DefenseRendererProps> = ({ payload }) => {
  const [showAllArgs, setShowAllArgs] = useState(false);

  if (!payload) return null;

  const summary = payload.summary || payload.defense_theory || '';
  const prayer = payload.prayer || payload.final_prayer || '';
  const argumentsList: { type: string; content: string; source?: string }[] = payload.arguments || [];
  const reasonableDoubts: string[] = payload.reasonable_doubts || [];
  const missingEvidence: string[] = payload.missing_evidence || [];
  const witnessInconsistencies: string[] = payload.witness_inconsistencies || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '4px' }}>
      
      {/* Defense Theory Banner */}
      <div
        style={{
          background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(15, 23, 42, 0.6) 100%)',
          borderLeft: '4px solid var(--def-color, #10B981)',
          borderTop: '1px solid rgba(16, 185, 129, 0.25)',
          borderRight: '1px solid rgba(16, 185, 129, 0.25)',
          borderBottom: '1px solid rgba(16, 185, 129, 0.25)',
          borderRadius: '0 8px 8px 0',
          padding: '12px 16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
          <Shield size={16} color="var(--def-color, #10B981)" />
          <span style={{ color: '#6EE7B7', fontWeight: 700, fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Theory of the Defense & Ground of Reasonable Doubt
          </span>
        </div>
        <p style={{ margin: 0, fontSize: '0.88rem', color: '#E2E8F0', lineHeight: 1.55 }}>
          {summary}
        </p>
      </div>

      {/* Reasonable Doubts Raised */}
      {reasonableDoubts.length > 0 && (
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '8px',
            padding: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <Scale size={15} color="#34D399" />
            <h5 style={{ margin: 0, fontSize: '0.82rem', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Grounds of Reasonable Doubt Established
            </h5>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {reasonableDoubts.map((ground, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '8px',
                  fontSize: '0.83rem',
                  color: '#CBD5E1',
                }}
              >
                <CheckCircle size={14} color="#10B981" style={{ marginTop: '2px', flexShrink: 0 }} />
                <span>{ground}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Defense Arguments Relied Upon */}
      {argumentsList.length > 0 && (
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '8px',
            padding: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Shield size={15} color="#10B981" />
              <h5 style={{ margin: 0, fontSize: '0.82rem', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Defense Submissions ({argumentsList.length})
              </h5>
            </div>
            {argumentsList.length > 3 && (
              <button
                onClick={() => setShowAllArgs(!showAllArgs)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  background: 'transparent',
                  border: 'none',
                  color: '#34D399',
                  fontSize: '0.76rem',
                  cursor: 'pointer',
                }}
              >
                <span>{showAllArgs ? 'Show Less' : `View All (${argumentsList.length})`}</span>
                {showAllArgs ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              </button>
            )}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {(showAllArgs ? argumentsList : argumentsList.slice(0, 3)).map((arg, idx) => (
              <div
                key={idx}
                style={{
                  background: 'rgba(16, 185, 129, 0.06)',
                  border: '1px solid rgba(16, 185, 129, 0.18)',
                  borderRadius: '6px',
                  padding: '10px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span
                    style={{
                      background: 'rgba(16, 185, 129, 0.2)',
                      color: '#6EE7B7',
                      fontSize: '0.7rem',
                      fontWeight: 600,
                      padding: '2px 6px',
                      borderRadius: '4px',
                      textTransform: 'uppercase',
                    }}
                  >
                    {arg.type || 'Defense Argument'}
                  </span>
                  {arg.source && (
                    <span style={{ fontSize: '0.72rem', color: '#94A3B8', fontFamily: 'monospace' }}>
                      Ref: {arg.source}
                    </span>
                  )}
                </div>
                <p style={{ margin: 0, fontSize: '0.84rem', color: '#E2E8F0', lineHeight: 1.5 }}>
                  {arg.content}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Disputed Facts & Investigation Gaps */}
      {(missingEvidence.length > 0 || witnessInconsistencies.length > 0) && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
          {missingEvidence.length > 0 && (
            <div
              style={{
                background: 'rgba(15, 23, 42, 0.6)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '8px',
                padding: '12px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <FileX size={14} color="#F87171" />
                <h5 style={{ margin: 0, fontSize: '0.8rem', color: '#94A3B8', textTransform: 'uppercase' }}>
                  Critical Missing Evidence Gaps
                </h5>
              </div>
              <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '0.82rem', color: '#CBD5E1', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {missingEvidence.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {witnessInconsistencies.length > 0 && (
            <div
              style={{
                background: 'rgba(15, 23, 42, 0.6)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '8px',
                padding: '12px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <AlertCircle size={14} color="#FBBF24" />
                <h5 style={{ margin: 0, fontSize: '0.8rem', color: '#94A3B8', textTransform: 'uppercase' }}>
                  Witness Contradictions Highlighted
                </h5>
              </div>
              <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '0.82rem', color: '#CBD5E1', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {witnessInconsistencies.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Formal Acquittal Prayer */}
      {prayer && (
        <div
          style={{
            background: 'rgba(16, 185, 129, 0.05)',
            border: '1px solid rgba(16, 185, 129, 0.2)',
            borderRadius: '6px',
            padding: '10px 14px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
          }}
        >
          <Shield size={16} color="#34D399" style={{ flexShrink: 0 }} />
          <div style={{ fontSize: '0.83rem', color: '#CBD5E1' }}>
            <span style={{ color: '#6EE7B7', fontWeight: 600 }}>Defense Prayer: </span>
            <span>{prayer}</span>
          </div>
        </div>
      )}

    </div>
  );
};
