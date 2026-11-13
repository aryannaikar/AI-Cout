import React, { useState } from 'react';
import { BookOpen, Search, ChevronDown, ChevronUp } from 'lucide-react';

interface LegalResearchRendererProps {
  payload: any;
  side?: 'prosecution' | 'defense';
}

export const LegalResearchRenderer: React.FC<LegalResearchRendererProps> = ({ payload, side = 'prosecution' }) => {
  const [showFullFindings, setShowFullFindings] = useState(false);
  const [showAllProvisions, setShowAllProvisions] = useState(false);

  if (!payload) return null;

  const isPros = side === 'prosecution';
  const themeColor = isPros ? '#60A5FA' : '#34D399';
  const themeBorder = isPros ? 'rgba(59, 130, 246, 0.25)' : 'rgba(16, 185, 129, 0.25)';
  const themeBg = isPros ? 'rgba(59, 130, 246, 0.08)' : 'rgba(16, 185, 129, 0.08)';

  const question = payload.question || 'Statutory legal research on framed charges and evidentiary admissibility';
  const findings = payload.findings || '';
  const provisions: {
    act: string;
    section: string;
    title?: string;
    citation?: string;
    page?: number | string;
    reasoning?: string;
  }[] = payload.provisions || [];
  const citations: string[] = payload.citations || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '4px' }}>
      
      {/* Research Inquiry Banner */}
      <div
        style={{
          background: 'rgba(15, 23, 42, 0.7)',
          borderLeft: `3px solid ${themeColor}`,
          borderTop: '1px solid rgba(255, 255, 255, 0.08)',
          borderRight: '1px solid rgba(255, 255, 255, 0.08)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '0 8px 8px 0',
          padding: '12px 14px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
          <Search size={15} color={themeColor} />
          <span style={{ fontSize: '0.78rem', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Statutory Inquiry
          </span>
        </div>
        <p style={{ margin: 0, fontSize: '0.88rem', color: '#E2E8F0', fontWeight: 500 }}>
          {question}
        </p>
      </div>

      {/* Relevant Provisions Grid */}
      {provisions.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <BookOpen size={15} color={themeColor} />
              <h5 style={{ margin: 0, fontSize: '0.82rem', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Relevant Statutory Provisions ({provisions.length})
              </h5>
            </div>
            {provisions.length > 3 && (
              <button
                onClick={() => setShowAllProvisions(!showAllProvisions)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: themeColor,
                  fontSize: '0.75rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                <span>{showAllProvisions ? 'Show Less' : `View All (${provisions.length})`}</span>
                {showAllProvisions ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              </button>
            )}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
            {(showAllProvisions ? provisions : provisions.slice(0, 3)).map((p, idx) => (
              <div
                key={idx}
                style={{
                  background: 'rgba(15, 23, 42, 0.7)',
                  border: `1px solid ${themeBorder}`,
                  borderRadius: '8px',
                  padding: '12px 14px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                }}
              >
                {/* Header: Act & Section */}
                <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '6px' }}>
                  <span style={{ color: themeColor, fontWeight: 700, fontSize: '0.88rem' }}>
                    {p.act || 'Act'} &bull; {p.section ? `Section ${p.section}` : 'General Provision'}
                  </span>
                  {p.page !== undefined && p.page !== null && (
                    <span style={{ fontSize: '0.72rem', color: '#94A3B8', fontFamily: 'monospace' }}>
                      Page {p.page}
                    </span>
                  )}
                </div>

                {/* Title / Description */}
                {p.title && (
                  <div style={{ color: '#E2E8F0', fontSize: '0.82rem', fontWeight: 500 }}>
                    {p.title}
                  </div>
                )}

                {/* Relevance Reasoning */}
                {p.reasoning && (
                  <div style={{ fontSize: '0.8rem', color: '#CBD5E1', lineHeight: 1.45 }}>
                    <span style={{ color: '#94A3B8', fontWeight: 600 }}>Relevant to: </span>
                    <span>{p.reasoning}</span>
                  </div>
                )}

                {/* Source & Citation Footer */}
                <div style={{ marginTop: 'auto', paddingTop: '6px', fontSize: '0.72rem', color: '#64748B', display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap' }}>
                  <span>Source: {p.act || 'Official Statute'}</span>
                  {p.citation && <span>Cite: {p.citation}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Synthesis Findings Drawer */}
      {findings && (
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '8px',
            padding: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ fontSize: '0.8rem', color: '#94A3B8', fontWeight: 600, textTransform: 'uppercase' }}>
              Legal Synthesis & Reasoning
            </span>
            <button
              onClick={() => setShowFullFindings(!showFullFindings)}
              style={{
                background: 'transparent',
                border: 'none',
                color: themeColor,
                fontSize: '0.75rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <span>{showFullFindings ? 'Collapse' : 'Expand Full Findings'}</span>
              {showFullFindings ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
          </div>
          <p style={{ margin: 0, fontSize: '0.84rem', color: '#E2E8F0', lineHeight: 1.55 }}>
            {showFullFindings || findings.length <= 220
              ? findings
              : `${findings.slice(0, 220)}...`}
          </p>
        </div>
      )}

      {/* Citations Chips */}
      {citations.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.75rem', color: '#94A3B8', fontWeight: 600 }}>Citations:</span>
          {citations.map((cite, idx) => (
            <span
              key={idx}
              style={{
                background: themeBg,
                border: `1px solid ${themeBorder}`,
                color: themeColor,
                fontSize: '0.75rem',
                padding: '2px 8px',
                borderRadius: '4px',
              }}
            >
              {cite}
            </span>
          ))}
        </div>
      )}

    </div>
  );
};
