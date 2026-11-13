import React from 'react';
import { AlertTriangle, CheckCircle } from 'lucide-react';

interface ConflictDetectionRendererProps {
  payload: any;
}

export const ConflictDetectionRenderer: React.FC<ConflictDetectionRendererProps> = ({ payload }) => {
  if (!payload) return null;

  const conflicts: {
    id: string;
    category?: string;
    statement_a?: string;
    statement_b?: string;
    severity?: string;
    explanation?: string;
    subject?: string;
    description?: string;
  }[] = payload.conflicts || [];

  const hasConflicts = conflicts.length > 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '4px' }}>
      
      {/* Status Summary Banner */}
      {!hasConflicts ? (
        <div
          style={{
            background: 'rgba(16, 185, 129, 0.08)',
            border: '1px solid rgba(16, 185, 129, 0.25)',
            borderRadius: '8px',
            padding: '12px 16px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          <CheckCircle size={20} color="#10B981" />
          <div>
            <div style={{ color: '#34D399', fontWeight: 600, fontSize: '0.88rem' }}>
              ✓ No material evidentiary conflicts detected on record
            </div>
            <div style={{ color: '#94A3B8', fontSize: '0.78rem', marginTop: '2px' }}>
              Testimonial statements and documentary records align without irreconcilable factual discrepancies.
            </div>
          </div>
        </div>
      ) : (
        <div
          style={{
            background: 'rgba(245, 158, 11, 0.08)',
            borderLeft: '4px solid #F59E0B',
            borderTop: '1px solid rgba(245, 158, 11, 0.25)',
            borderRight: '1px solid rgba(245, 158, 11, 0.25)',
            borderBottom: '1px solid rgba(245, 158, 11, 0.25)',
            borderRadius: '0 8px 8px 0',
            padding: '12px 16px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <AlertTriangle size={17} color="#F59E0B" />
            <span style={{ color: '#FDE68A', fontWeight: 700, fontSize: '0.88rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              ⚠️ Potential Adversarial Contradictions ({conflicts.length})
            </span>
          </div>
          <p style={{ margin: 0, fontSize: '0.84rem', color: '#E2E8F0', lineHeight: 1.5 }}>
            {payload.summary || 'Appraisal of factual tensions between prosecution witnesses, forensic exhibits, and defense pleadings.'}
          </p>
        </div>
      )}

      {/* Conflict Comparison Cards */}
      {hasConflicts && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {conflicts.map((c, idx) => (
            <div
              key={idx}
              style={{
                background: 'rgba(15, 23, 42, 0.7)',
                border: '1px solid rgba(245, 158, 11, 0.2)',
                borderRadius: '8px',
                padding: '12px 14px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
              }}
            >
              {/* Card Header: Category & Severity */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ color: '#FDE68A', fontWeight: 600, fontSize: '0.85rem' }}>
                  Issue: {c.category || c.subject || `Contradiction #${idx + 1}`}
                </span>
                {c.severity && (
                  <span
                    style={{
                      background: c.severity.toLowerCase().includes('critical') || c.severity.toLowerCase().includes('high')
                        ? 'rgba(239, 68, 68, 0.2)'
                        : 'rgba(245, 158, 11, 0.2)',
                      color: c.severity.toLowerCase().includes('critical') || c.severity.toLowerCase().includes('high')
                        ? '#FCA5A5'
                        : '#FDE68A',
                      fontSize: '0.7rem',
                      fontWeight: 600,
                      padding: '2px 6px',
                      borderRadius: '4px',
                      textTransform: 'uppercase',
                    }}
                  >
                    {c.severity} Severity
                  </span>
                )}
              </div>

              {/* Side by Side Statement Comparison */}
              {(c.statement_a || c.statement_b) && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '8px' }}>
                  <div
                    style={{
                      background: 'rgba(59, 130, 246, 0.08)',
                      border: '1px solid rgba(59, 130, 246, 0.2)',
                      borderRadius: '6px',
                      padding: '8px 10px',
                    }}
                  >
                    <div style={{ fontSize: '0.72rem', color: '#93C5FD', fontWeight: 600, textTransform: 'uppercase', marginBottom: '2px' }}>
                      Statement / Source A
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#E2E8F0', lineHeight: 1.4 }}>
                      {c.statement_a}
                    </div>
                  </div>

                  <div
                    style={{
                      background: 'rgba(239, 68, 68, 0.08)',
                      border: '1px solid rgba(239, 68, 68, 0.2)',
                      borderRadius: '6px',
                      padding: '8px 10px',
                    }}
                  >
                    <div style={{ fontSize: '0.72rem', color: '#FCA5A5', fontWeight: 600, textTransform: 'uppercase', marginBottom: '2px' }}>
                      Statement / Source B
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#E2E8F0', lineHeight: 1.4 }}>
                      {c.statement_b}
                    </div>
                  </div>
                </div>
              )}

              {/* Explanation Description */}
              {(c.explanation || c.description) && (
                <div style={{ fontSize: '0.8rem', color: '#CBD5E1', lineHeight: 1.45, paddingTop: '4px' }}>
                  <span style={{ color: '#94A3B8', fontWeight: 500 }}>Factual Appraisal: </span>
                  <span>{c.explanation || c.description}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

    </div>
  );
};
