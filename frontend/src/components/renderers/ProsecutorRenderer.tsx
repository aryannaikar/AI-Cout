import React, { useState } from 'react';
import { Briefcase, ChevronDown, ChevronUp, Scale, CheckCircle, ShieldAlert, FileText, Eye } from 'lucide-react';

interface ProsecutorRendererProps {
  payload: any;
}

export const ProsecutorRenderer: React.FC<ProsecutorRendererProps> = ({ payload }) => {
  const [showAllArgs, setShowAllArgs] = useState(false);

  if (!payload) return null;

  const summary = payload.summary || payload.prosecution_theory || '';
  const prayer = payload.prayer || payload.final_prayer || '';
  const argumentsList: { type: string; content: string; source?: string }[] = payload.arguments || [];
  const statutoryElements: string[] = payload.statutory_elements || [];
  const supportingWitnesses: string[] = payload.supporting_witnesses || [];
  const supportingExhibits: string[] = payload.supporting_exhibits || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '4px' }}>
      
      {/* Prosecution Theory Banner */}
      <div
        style={{
          background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.12) 0%, rgba(15, 23, 42, 0.6) 100%)',
          borderLeft: '4px solid var(--pros-color, #3B82F6)',
          borderTop: '1px solid rgba(59, 130, 246, 0.25)',
          borderRight: '1px solid rgba(59, 130, 246, 0.25)',
          borderBottom: '1px solid rgba(59, 130, 246, 0.25)',
          borderRadius: '0 8px 8px 0',
          padding: '12px 16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
          <Briefcase size={16} color="var(--pros-color, #3B82F6)" />
          <span style={{ color: '#93C5FD', fontWeight: 700, fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Theory of the Prosecution & Submissions
          </span>
        </div>
        <p style={{ margin: 0, fontSize: '0.88rem', color: '#E2E8F0', lineHeight: 1.55 }}>
          {summary}
        </p>
      </div>

      {/* Statutory Elements to Establish */}
      {statutoryElements.length > 0 && (
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '8px',
            padding: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <Scale size={15} color="#60A5FA" />
            <h5 style={{ margin: 0, fontSize: '0.82rem', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Statutory Elements Under BNS Charged
            </h5>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {statutoryElements.map((elem, idx) => (
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
                <CheckCircle size={14} color="#3B82F6" style={{ marginTop: '2px', flexShrink: 0 }} />
                <span>{elem}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Categorized Arguments Relied Upon */}
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
              <FileText size={15} color="#3B82F6" />
              <h5 style={{ margin: 0, fontSize: '0.82rem', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Substantive Arguments ({argumentsList.length})
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
                  color: '#60A5FA',
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
                  background: 'rgba(59, 130, 246, 0.06)',
                  border: '1px solid rgba(59, 130, 246, 0.18)',
                  borderRadius: '6px',
                  padding: '10px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span
                    style={{
                      background: 'rgba(59, 130, 246, 0.2)',
                      color: '#93C5FD',
                      fontSize: '0.7rem',
                      fontWeight: 600,
                      padding: '2px 6px',
                      borderRadius: '4px',
                      textTransform: 'uppercase',
                    }}
                  >
                    {arg.type || 'Factual Submission'}
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

      {/* Supporting Witnesses and Exhibits Grid */}
      {(supportingWitnesses.length > 0 || supportingExhibits.length > 0) && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
          {supportingWitnesses.length > 0 && (
            <div
              style={{
                background: 'rgba(15, 23, 42, 0.6)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '8px',
                padding: '12px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <Eye size={14} color="#60A5FA" />
                <h5 style={{ margin: 0, fontSize: '0.8rem', color: '#94A3B8', textTransform: 'uppercase' }}>
                  Witnesses Relied Upon
                </h5>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {supportingWitnesses.map((w, idx) => (
                  <span
                    key={idx}
                    style={{
                      background: 'rgba(59, 130, 246, 0.1)',
                      border: '1px solid rgba(59, 130, 246, 0.25)',
                      padding: '2px 8px',
                      borderRadius: '4px',
                      fontSize: '0.78rem',
                      color: '#BFDBFE',
                    }}
                  >
                    {w}
                  </span>
                ))}
              </div>
            </div>
          )}

          {supportingExhibits.length > 0 && (
            <div
              style={{
                background: 'rgba(15, 23, 42, 0.6)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '8px',
                padding: '12px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <FileText size={14} color="#60A5FA" />
                <h5 style={{ margin: 0, fontSize: '0.8rem', color: '#94A3B8', textTransform: 'uppercase' }}>
                  Documentary Evidence Relied Upon
                </h5>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {supportingExhibits.map((e, idx) => (
                  <span
                    key={idx}
                    style={{
                      background: 'rgba(59, 130, 246, 0.1)',
                      border: '1px solid rgba(59, 130, 246, 0.25)',
                      padding: '2px 8px',
                      borderRadius: '4px',
                      fontSize: '0.78rem',
                      color: '#BFDBFE',
                    }}
                  >
                    {e}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Formal Prayer */}
      {prayer && (
        <div
          style={{
            background: 'rgba(59, 130, 246, 0.05)',
            border: '1px solid rgba(59, 130, 246, 0.2)',
            borderRadius: '6px',
            padding: '10px 14px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
          }}
        >
          <ShieldAlert size={16} color="#60A5FA" style={{ flexShrink: 0 }} />
          <div style={{ fontSize: '0.83rem', color: '#CBD5E1' }}>
            <span style={{ color: '#93C5FD', fontWeight: 600 }}>Prosecution Prayer: </span>
            <span>{prayer}</span>
          </div>
        </div>
      )}

    </div>
  );
};
