import React from 'react';
import {
  Lightbulb,
  Bot,
  Landmark,
  GitCompareArrows,
  GraduationCap,
  BookOpen,
  Info,
  Loader2,
  AlertCircle,
  RefreshCw,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import type { ComparisonReport, DifferenceBasis, DifferenceExplanation } from '../types/court';

interface Props {
  caseId: string;
  report: ComparisonReport;
}

const BASIS: Record<DifferenceBasis, { label: string; color: string; bg: string }> = {
  from_judgments: { label: 'From the judgments', color: '#6EE7B7', bg: 'rgba(16, 185, 129, 0.14)' },
  ai_analysis: { label: 'AI analysis', color: '#93C5FD', bg: 'rgba(59, 130, 246, 0.14)' },
  information_unavailable: { label: 'Not available', color: '#FDE68A', bg: 'rgba(251, 191, 36, 0.14)' },
};

const card: React.CSSProperties = {
  padding: '18px 20px',
  borderRadius: '12px',
  background: 'rgba(15, 23, 42, 0.65)',
  border: '1px solid rgba(255, 255, 255, 0.08)',
};

const sectionTitle = (icon: React.ReactNode, text: string, color = 'var(--gold-primary)') => (
  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px', color }}>
    {icon}
    <h4 style={{ margin: 0, fontSize: '0.95rem', letterSpacing: '0.02em' }}>{text}</h4>
  </div>
);

const bodyText: React.CSSProperties = { margin: 0, fontSize: '0.9rem', lineHeight: 1.65, color: '#E2E8F0' };

export const UnderstandDifferencePanel: React.FC<Props> = ({ caseId, report }) => {
  const [data, setData] = React.useState<DifferenceExplanation | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [showDetails, setShowDetails] = React.useState(false);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/cases/${encodeURIComponent(caseId)}/comparison/explain`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report }),
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `Could not generate the explanation (HTTP ${response.status}).`);
      }
      setData(await response.json());
    } catch (e: any) {
      setError(e?.message || 'Could not generate the explanation. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [caseId, report]);

  React.useEffect(() => {
    load();
  }, [load]);

  if (loading && !data) {
    return (
      <div style={{ ...card, display: 'flex', alignItems: 'center', gap: '12px', color: '#CBD5E1' }}>
        <Loader2 size={20} className="spin" style={{ animation: 'spin 1s linear infinite' }} />
        <div>
          <strong style={{ color: 'var(--gold-primary)' }}>Preparing a plain-language explanation…</strong>
          <div style={{ fontSize: '0.82rem', color: '#94A3B8' }}>
            Reading both judgments and the comparison findings. This can take up to a minute.
          </div>
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div style={{ ...card, border: '1px solid rgba(248, 113, 113, 0.45)', display: 'flex', gap: '12px', alignItems: 'center' }}>
        <AlertCircle size={20} color="#F87171" />
        <div style={{ flex: 1, color: '#FCA5A5', fontSize: '0.9rem' }}>{error}</div>
        <button className="btn-secondary" onClick={load} style={{ display: 'inline-flex', gap: '6px', alignItems: 'center' }}>
          <RefreshCw size={14} /> Try again
        </button>
      </div>
    );
  }

  if (!data) return null;

  const verdictTone = data.verdicts_differ === true ? '#FBBF24' : data.verdicts_differ === false ? '#34D399' : '#94A3B8';
  const verdictLabel =
    data.verdicts_differ === true ? 'Different decisions' : data.verdicts_differ === false ? 'Same decision' : 'Decision unclear';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* SIMPLE VIEW: what a non-lawyer needs in 20 seconds */}
      <div
        style={{
          ...card,
          background: 'linear-gradient(135deg, rgba(212, 175, 55, 0.14) 0%, rgba(15, 23, 42, 0.85) 100%)',
          border: '1px solid rgba(212, 175, 55, 0.45)',
        }}
      >
        {sectionTitle(<Lightbulb size={19} />, 'Why are the judgments different?')}
        <span
          style={{
            display: 'inline-block',
            marginBottom: '10px',
            padding: '2px 10px',
            borderRadius: '999px',
            fontSize: '0.72rem',
            fontWeight: 700,
            color: verdictTone,
            border: `1px solid ${verdictTone}`,
          }}
        >
          {verdictLabel}
        </span>

        {/* AI vs Court at a glance */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '10px', marginBottom: '12px' }}>
          <div style={{ padding: '10px 12px', borderRadius: '8px', background: 'rgba(59, 130, 246, 0.12)', border: '1px solid rgba(96, 165, 250, 0.4)' }}>
            <div style={{ fontSize: '0.7rem', color: '#93C5FD', fontWeight: 700, textTransform: 'uppercase' }}>AI Court said</div>
            <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#F8FAFC' }}>{data.ai_verdict || 'Not available'}</div>
          </div>
          <div style={{ padding: '10px 12px', borderRadius: '8px', background: 'rgba(212, 175, 55, 0.12)', border: '1px solid rgba(212, 175, 55, 0.4)' }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--gold-primary)', fontWeight: 700, textTransform: 'uppercase' }}>Real court said</div>
            <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#F8FAFC' }}>{data.real_verdict || 'Not available'}</div>
          </div>
        </div>

        <p style={bodyText}>{data.simple_summary || data.why_judgments_differ}</p>
      </div>

      {data.main_reasons.length > 0 && (
        <div style={card}>
          {sectionTitle(<GitCompareArrows size={18} />, 'Main reasons (in short)')}
          <ol style={{ margin: 0, paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {data.main_reasons.map((r, i) => (
              <li key={i} style={{ ...bodyText, fontSize: '0.88rem' }}>{r}</li>
            ))}
          </ol>
          {data.analogy && (
            <div style={{ marginTop: '12px', padding: '10px 12px', borderRadius: '8px', background: 'rgba(56, 189, 248, 0.08)', border: '1px solid rgba(56, 189, 248, 0.25)', fontSize: '0.84rem', color: '#CBD5E1', lineHeight: 1.55 }}>
              <strong style={{ color: '#38BDF8' }}>In engineering terms: </strong>
              {data.analogy}
            </div>
          )}
        </div>
      )}

      <div style={{ ...card, border: '1px solid rgba(52, 211, 153, 0.4)' }}>
        {sectionTitle(<GraduationCap size={19} />, 'What can we learn?', '#6EE7B7')}
        <p style={bodyText}>{data.what_we_can_learn}</p>
      </div>

      <button
        type="button"
        className="btn-secondary"
        onClick={() => setShowDetails((v) => !v)}
        style={{ alignSelf: 'flex-start', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
      >
        {showDetails ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
        <span>{showDetails ? 'Hide detailed breakdown' : 'Show detailed breakdown'}</span>
      </button>

      {showDetails && (
        <>
      {/* Two sides */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
        <div style={{ ...card, border: '1px solid rgba(96, 165, 250, 0.4)' }}>
          {sectionTitle(<Bot size={18} />, 'What AI Court concluded', '#93C5FD')}
          <div style={{ fontSize: '0.78rem', color: '#93C5FD', fontWeight: 700, marginBottom: '6px' }}>
            Decision: {data.ai_verdict || 'Not available'}
          </div>
          <p style={bodyText}>{data.ai_court_concluded}</p>
        </div>
        <div style={{ ...card, border: '1px solid rgba(212, 175, 55, 0.4)' }}>
          {sectionTitle(<Landmark size={18} />, 'What the real court concluded')}
          <div style={{ fontSize: '0.78rem', color: 'var(--gold-primary)', fontWeight: 700, marginBottom: '6px' }}>
            Decision: {data.real_verdict || 'Not available'}
          </div>
          <p style={bodyText}>{data.real_court_concluded}</p>
        </div>
      </div>

      {/* Key differences */}
      <div style={card}>
        {sectionTitle(<GitCompareArrows size={18} />, 'Key differences explained')}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {data.key_differences.map((d, i) => {
            const b = BASIS[d.basis] || BASIS.ai_analysis;
            return (
              <div
                key={i}
                style={{ padding: '14px', borderRadius: '10px', background: 'rgba(0, 0, 0, 0.25)', border: '1px solid rgba(255,255,255,0.07)' }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginBottom: '10px' }}>
                  <strong style={{ color: '#F8FAFC', fontSize: '0.92rem' }}>
                    {i + 1}. {d.title}
                  </strong>
                  <span style={{ fontSize: '0.68rem', fontWeight: 700, padding: '2px 8px', borderRadius: '999px', color: b.color, background: b.bg }}>
                    {b.label}
                  </span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '10px' }}>
                  <div style={{ borderLeft: '3px solid #60A5FA', paddingLeft: '10px' }}>
                    <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#93C5FD', fontWeight: 700 }}>What AI thought</div>
                    <p style={{ ...bodyText, fontSize: '0.85rem' }}>{d.ai_view}</p>
                  </div>
                  <div style={{ borderLeft: '3px solid var(--gold-primary)', paddingLeft: '10px' }}>
                    <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--gold-primary)', fontWeight: 700 }}>
                      What the real court decided
                    </div>
                    <p style={{ ...bodyText, fontSize: '0.85rem' }}>{d.real_court_view}</p>
                  </div>
                </div>
                <div style={{ marginTop: '10px', padding: '10px 12px', borderRadius: '8px', background: 'rgba(56, 189, 248, 0.08)', border: '1px solid rgba(56, 189, 248, 0.25)' }}>
                  <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#38BDF8', fontWeight: 700, marginBottom: '2px' }}>
                    Why they differ
                  </div>
                  <p style={{ ...bodyText, fontSize: '0.85rem' }}>{d.why_different}</p>
                </div>
              </div>
            );
          })}
        </div>
        {data.how_it_led_to_different_verdicts && (
          <div style={{ marginTop: '14px', padding: '12px 14px', borderRadius: '8px', background: 'rgba(212, 175, 55, 0.08)', border: '1px solid rgba(212, 175, 55, 0.3)' }}>
            <strong style={{ color: 'var(--gold-primary)', fontSize: '0.82rem' }}>How this led to the final decisions</strong>
            <p style={{ ...bodyText, marginTop: '4px' }}>{data.how_it_led_to_different_verdicts}</p>
          </div>
        )}
      </div>

        </>
      )}

      {/* Terms + unavailable info */}
      {showDetails && (data.legal_terms.length > 0 || data.unavailable_information.length > 0) && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
          {data.legal_terms.length > 0 && (
            <div style={card}>
              {sectionTitle(<BookOpen size={17} />, 'Words explained', '#C4B5FD')}
              <dl style={{ margin: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {data.legal_terms.map((t, i) => (
                  <div key={i}>
                    <dt style={{ color: '#DDD6FE', fontWeight: 700, fontSize: '0.84rem' }}>{t.term}</dt>
                    <dd style={{ margin: 0, color: '#CBD5E1', fontSize: '0.83rem', lineHeight: 1.5 }}>{t.meaning}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
          {data.unavailable_information.length > 0 && (
            <div style={{ ...card, border: '1px solid rgba(251, 191, 36, 0.35)' }}>
              {sectionTitle(<Info size={17} />, 'What we could not know', '#FDE68A')}
              <ul style={{ margin: 0, paddingLeft: '18px', color: '#E2E8F0', fontSize: '0.85rem', lineHeight: 1.6 }}>
                {data.unavailable_information.map((u, i) => (
                  <li key={i}>{u}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <div style={{ fontSize: '0.74rem', color: '#94A3B8', lineHeight: 1.5 }}>
        {data.model_note} {data.disclaimer}
      </div>
    </div>
  );
};
