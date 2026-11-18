import React from 'react';
import { Globe, ExternalLink, BookMarked, Lightbulb } from 'lucide-react';
import { resolvePrecedentUrl } from '../../utils/courtroomChatFormatters';

interface WebResearchRendererProps {
  payload: any;
  side?: 'prosecution' | 'defense';
}

export const WebResearchRenderer: React.FC<WebResearchRendererProps> = ({ payload, side = 'prosecution' }) => {
  if (!payload) return null;

  const isPros = side === 'prosecution';
  const themeColor = isPros ? '#38BDF8' : '#34D399';
  const themeBorder = isPros ? 'rgba(56, 189, 248, 0.25)' : 'rgba(52, 211, 153, 0.25)';

  const question = payload.question || 'Precedent and judicial authority search on statutory interpretation';
  const findings = payload.findings || '';
  const whyItMatters = payload.why_it_matters || '';
  const sources: {
    title: string;
    url: string;
    summary?: string;
    relevance?: string;
    date?: string;
  }[] = payload.sources || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '4px' }}>
      
      {/* Research Question & Executive Summary */}
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
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
          <Globe size={15} color={themeColor} />
          <span style={{ fontSize: '0.78rem', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            External Precedent Search
          </span>
        </div>
        <p style={{ margin: 0, fontSize: '0.88rem', color: '#E2E8F0', fontWeight: 600 }}>
          {question}
        </p>
        {findings && (
          <p style={{ margin: '8px 0 0 0', fontSize: '0.84rem', color: '#CBD5E1', lineHeight: 1.5 }}>
            {findings}
          </p>
        )}
      </div>

      {/* Strategic Relevance ("Why It Matters") */}
      {whyItMatters && (
        <div
          style={{
            background: 'rgba(56, 189, 248, 0.06)',
            border: '1px solid rgba(56, 189, 248, 0.2)',
            borderRadius: '6px',
            padding: '10px 14px',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '10px',
          }}
        >
          <Lightbulb size={16} color={themeColor} style={{ marginTop: '2px', flexShrink: 0 }} />
          <div style={{ fontSize: '0.83rem', color: '#CBD5E1', lineHeight: 1.45 }}>
            <span style={{ color: themeColor, fontWeight: 600 }}>Strategic Relevance: </span>
            <span>{whyItMatters}</span>
          </div>
        </div>
      )}

      {/* Precedent / Judicial Source Cards */}
      {sources.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <BookMarked size={15} color={themeColor} />
            <h5 style={{ margin: 0, fontSize: '0.82rem', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Identified Judicial Authorities & Sources ({sources.length})
            </h5>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(290px, 1fr))', gap: '12px' }}>
            {sources.map((src, idx) => (
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
                {/* Source Title & Outlink */}
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '8px' }}>
                  <span style={{ color: '#F1F5F9', fontWeight: 600, fontSize: '0.86rem', lineHeight: 1.4 }}>
                    {src.title || 'Legal Precedent / Authority'}
                  </span>
                  {src.url && (
                    <a
                      href={resolvePrecedentUrl(src.url, src.title)}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        color: themeColor,
                        fontSize: '0.74rem',
                        textDecoration: 'none',
                        background: 'rgba(255, 255, 255, 0.05)',
                        padding: '3px 6px',
                        borderRadius: '4px',
                        flexShrink: 0,
                      }}
                      title="Open external legal source"
                    >
                      <span>Link</span>
                      <ExternalLink size={11} />
                    </a>
                  )}
                </div>

                {/* Summary Passage */}
                {src.summary && (
                  <p style={{ margin: 0, fontSize: '0.81rem', color: '#CBD5E1', lineHeight: 1.45 }}>
                    {src.summary}
                  </p>
                )}

                {/* Relevance Reasoning */}
                {src.relevance && (
                  <div style={{ marginTop: 'auto', paddingTop: '6px', borderTop: '1px solid rgba(255, 255, 255, 0.05)', fontSize: '0.78rem', color: '#94A3B8' }}>
                    <span style={{ color: themeColor, fontWeight: 500 }}>Relevance: </span>
                    <span>{src.relevance}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
};
