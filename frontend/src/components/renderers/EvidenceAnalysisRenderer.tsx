import React, { useState } from 'react';
import { Microscope, ShieldCheck, AlertCircle, CheckCircle2, ChevronDown, ChevronUp, FileSearch, Info } from 'lucide-react';

interface EvidenceAnalysisRendererProps {
  payload: any;
}

export const EvidenceAnalysisRenderer: React.FC<EvidenceAnalysisRendererProps> = ({ payload }) => {
  const [showAllItems, setShowAllItems] = useState(false);

  if (!payload) return null;

  const summary = payload.summary || '';
  const compliance = payload.documentary_compliance || '';
  const missingGaps: string[] = payload.missing_gaps || [];
  const items: {
    id: string;
    description: string;
    type: string;
    source?: string;
    chain_of_custody_intact?: boolean;
    confidence?: number;
    limitations?: string;
  }[] = payload.items || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '4px' }}>
      
      {/* Non-Adjudicative Forensic Appraisal Disclaimer */}
      <div
        style={{
          background: 'rgba(168, 85, 247, 0.08)',
          borderLeft: '3px solid #A855F7',
          borderTop: '1px solid rgba(168, 85, 247, 0.2)',
          borderRight: '1px solid rgba(168, 85, 247, 0.2)',
          borderBottom: '1px solid rgba(168, 85, 247, 0.2)',
          borderRadius: '0 8px 8px 0',
          padding: '12px 14px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
          <Microscope size={16} color="#C084FC" />
          <span style={{ fontSize: '0.78rem', color: '#D8B4FE', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Evidentiary & Forensic Appraisal (Non-Adjudicative)
          </span>
        </div>
        <p style={{ margin: 0, fontSize: '0.86rem', color: '#E2E8F0', lineHeight: 1.5 }}>
          {summary || 'Forensic examination and chain of custody appraisal of exhibits on record.'}
        </p>
      </div>

      {/* Evidence Items Cards */}
      {items.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileSearch size={15} color="#C084FC" />
              <h5 style={{ margin: 0, fontSize: '0.82rem', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Appraised Evidence Items ({items.length})
              </h5>
            </div>
            {items.length > 4 && (
              <button
                onClick={() => setShowAllItems(!showAllItems)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#C084FC',
                  fontSize: '0.75rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                <span>{showAllItems ? 'Show Less' : `View All (${items.length})`}</span>
                {showAllItems ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              </button>
            )}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
            {(showAllItems ? items : items.slice(0, 4)).map((item, idx) => (
              <div
                key={idx}
                style={{
                  background: 'rgba(15, 23, 42, 0.7)',
                  border: '1px solid rgba(168, 85, 247, 0.25)',
                  borderRadius: '8px',
                  padding: '12px 14px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                }}
              >
                {/* Header: Item ID & Type */}
                <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '6px' }}>
                  <span style={{ color: '#E9D5FF', fontWeight: 700, fontSize: '0.9rem' }}>
                    {item.id}
                  </span>
                  <span
                    style={{
                      background: 'rgba(168, 85, 247, 0.15)',
                      color: '#D8B4FE',
                      fontSize: '0.7rem',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      textTransform: 'uppercase',
                    }}
                  >
                    {item.type || 'Physical Exhibit'}
                  </span>
                </div>

                {/* Description */}
                <div style={{ color: '#F1F5F9', fontSize: '0.84rem', fontWeight: 500, lineHeight: 1.4 }}>
                  {item.description}
                </div>

                {/* Chain of Custody & Source */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', fontSize: '0.76rem' }}>
                  {item.chain_of_custody_intact !== undefined && (
                    <span
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        color: item.chain_of_custody_intact ? '#34D399' : '#F87171',
                      }}
                    >
                      {item.chain_of_custody_intact ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />}
                      <span>Custody: {item.chain_of_custody_intact ? 'Intact' : 'Disputed / Irregular'}</span>
                    </span>
                  )}
                  {item.source && (
                    <span style={{ color: '#94A3B8' }}>
                      Source: {item.source}
                    </span>
                  )}
                </div>

                {/* Evidence Limitation Note */}
                {item.limitations && (
                  <div style={{ marginTop: 'auto', paddingTop: '6px', borderTop: '1px solid rgba(255, 255, 255, 0.05)', fontSize: '0.76rem', color: '#FBBF24', display: 'flex', alignItems: 'flex-start', gap: '4px' }}>
                    <Info size={12} style={{ marginTop: '2px', flexShrink: 0 }} />
                    <span>Evidence limitation: {item.limitations}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Documentary Compliance & Gaps */}
      {(compliance || missingGaps.length > 0) && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
          {compliance && (
            <div
              style={{
                background: 'rgba(15, 23, 42, 0.6)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '8px',
                padding: '12px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                <ShieldCheck size={15} color="#34D399" />
                <h5 style={{ margin: 0, fontSize: '0.8rem', color: '#94A3B8', textTransform: 'uppercase' }}>
                  Documentary Compliance Assessment
                </h5>
              </div>
              <p style={{ margin: 0, fontSize: '0.82rem', color: '#CBD5E1', lineHeight: 1.5 }}>
                {compliance}
              </p>
            </div>
          )}

          {missingGaps.length > 0 && (
            <div
              style={{
                background: 'rgba(15, 23, 42, 0.6)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '8px',
                padding: '12px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                <AlertCircle size={15} color="#F59E0B" />
                <h5 style={{ margin: 0, fontSize: '0.8rem', color: '#94A3B8', textTransform: 'uppercase' }}>
                  Identified Evidentiary Gaps ({missingGaps.length})
                </h5>
              </div>
              <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '0.8rem', color: '#CBD5E1', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                {missingGaps.map((gap, idx) => (
                  <li key={idx}>{gap}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

    </div>
  );
};
