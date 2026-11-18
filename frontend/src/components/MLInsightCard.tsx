import React, { useState } from 'react';
import { Brain, ChevronDown, ChevronUp, Cpu, ArrowRight } from 'lucide-react';
import type { MLInsightPanel } from '../utils/courtroomChatFormatters';

const accentFor = (kind: MLInsightPanel['kind']) =>
  kind === 'statute'
    ? { main: '#38BDF8', soft: 'rgba(56, 189, 248, 0.10)', border: 'rgba(56, 189, 248, 0.45)' }
    : { main: '#F472B6', soft: 'rgba(244, 114, 182, 0.10)', border: 'rgba(244, 114, 182, 0.45)' };

export const MLInsightCard: React.FC<{ panel: MLInsightPanel }> = ({ panel }) => {
  const [open, setOpen] = useState(true);
  const c = accentFor(panel.kind);

  return (
    <div
      style={{
        marginTop: '12px',
        background: `linear-gradient(135deg, ${c.soft} 0%, rgba(10, 14, 23, 0.75) 100%)`,
        border: `1px solid ${c.border}`,
        borderRadius: '10px',
        padding: '12px 14px',
        boxShadow: `0 0 18px ${c.soft}`,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Brain size={17} color={c.main} />
          <span style={{ fontWeight: 700, fontSize: '0.84rem', color: c.main }}>{panel.title}</span>
          <span
            style={{
              fontSize: '0.62rem',
              fontWeight: 700,
              letterSpacing: '0.06em',
              background: c.main,
              color: '#0A0E17',
              padding: '1px 6px',
              borderRadius: '4px',
            }}
          >
            AI / ML
          </span>
        </div>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          title={open ? 'Collapse explanation' : 'Expand explanation'}
          style={{ background: 'transparent', border: 'none', color: '#94A3B8', cursor: 'pointer', display: 'flex' }}
        >
          {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>
      <p style={{ margin: '4px 0 10px', fontSize: '0.78rem', color: '#CBD5E1', fontStyle: 'italic' }}>{panel.subtitle}</p>

      {/* ML output with confidence bars */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        {panel.items.map((it, idx) => {
          const pct = typeof it.score === 'number' ? Math.round(it.score * 100) : null;
          return (
            <div key={idx}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', color: '#E2E8F0' }}>
                <span>
                  {it.label}
                  {it.note && <span style={{ color: '#64748B', marginLeft: '6px', fontSize: '0.68rem' }}>· {it.note}</span>}
                </span>
                {pct !== null && <span style={{ color: c.main, fontWeight: 700 }}>{pct}%</span>}
              </div>
              {pct !== null && (
                <div style={{ height: '5px', background: 'rgba(255,255,255,0.07)', borderRadius: '3px', marginTop: '2px' }}>
                  <div style={{ width: `${pct}%`, height: '100%', background: c.main, borderRadius: '3px' }} />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {open && (
        <div style={{ marginTop: '12px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '10px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.7rem', fontWeight: 700, color: '#94A3B8', textTransform: 'uppercase', marginBottom: '4px' }}>
              <Cpu size={12} /> About the model
            </div>
            <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '0.74rem', color: '#CBD5E1', lineHeight: 1.5 }}>
              {panel.modelFacts.map((f, i) => <li key={i}>{f}</li>)}
            </ul>
          </div>
          <div>
            <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#94A3B8', textTransform: 'uppercase', marginBottom: '4px' }}>
              How it works
            </div>
            <ol style={{ margin: 0, paddingLeft: '16px', fontSize: '0.74rem', color: '#CBD5E1', lineHeight: 1.5 }}>
              {panel.pipeline.map((f, i) => <li key={i}>{f}</li>)}
            </ol>
          </div>
          <div style={{ gridColumn: '1 / -1' }}>
            <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#94A3B8', textTransform: 'uppercase', marginBottom: '4px' }}>
              Where the output is used
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
              {panel.usedBy.map((u, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.74rem', color: '#E2E8F0' }}>
                  <ArrowRight size={12} color={c.main} style={{ flexShrink: 0 }} /> {u}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
