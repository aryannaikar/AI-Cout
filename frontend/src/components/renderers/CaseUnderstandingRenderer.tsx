import React, { useState } from 'react';
import { Users, FileBadge, FileText, Eye, ChevronDown, ChevronUp, ScrollText, Layers, Scale } from 'lucide-react';

interface CaseUnderstandingRendererProps {
  payload: any;
}

export const CaseUnderstandingRenderer: React.FC<CaseUnderstandingRendererProps> = ({ payload }) => {
  const [showFullFacts, setShowFullFacts] = useState(false);
  const [showAllWitnesses, setShowAllWitnesses] = useState(false);
  const [showAllExhibits, setShowAllExhibits] = useState(false);

  if (!payload) return null;

  // Extract charges
  const rawCharges = payload.charges || [];
  const charges: { statute: string; section: string; description: string }[] = rawCharges.map((c: any) => {
    if (typeof c === 'string') {
      const parts = c.split(':');
      const header = parts[0] || '';
      const desc = parts.slice(1).join(':').trim() || '';
      return {
        statute: header.includes(' ') ? header.substring(0, header.lastIndexOf(' ')) : 'BNS',
        section: header.includes(' ') ? header.substring(header.lastIndexOf(' ') + 1) : header,
        description: desc,
      };
    }
    return {
      statute: c.statute || 'Statute',
      section: c.section ? `Section ${c.section}` : '',
      description: c.description || '',
    };
  });

  // Extract witnesses
  const witnesses: string[] = Array.isArray(payload.witnesses)
    ? payload.witnesses.map((w: any) => (typeof w === 'string' ? w : `${w.witness_id || 'PW'}: ${w.name || w.witness_name || 'Witness'} (${w.role || 'Testimony'})`))
    : [];

  // Extract exhibits
  const exhibits: string[] = Array.isArray(payload.exhibits)
    ? payload.exhibits.map((e: any) => (typeof e === 'string' ? e : `${e.exhibit_id || 'Ex'}: ${e.title || 'Exhibit'} (${e.exhibit_type || 'Material'})`))
    : [];

  // Facts
  const prosecutionFacts = Array.isArray(payload.facts)
    ? payload.facts.join('\n\n')
    : payload.facts || payload.allegations_summary || '';
  const defensePlea = payload.defense_plea || '';

  // Parties
  const caseTitle = payload.case_title || (payload.summary ? payload.summary.split('.')[0] : 'State v. Accused');
  const accusedList = payload.accused
    ? (Array.isArray(payload.accused) ? payload.accused.join(', ') : payload.accused)
    : 'Accused on Record';
  const mlCaseType: string = typeof payload.ml_case_type === 'string' ? payload.ml_case_type : '';
  const mlPredictedStatutes: string[] = Array.isArray(payload.ml_predicted_statutes) ? payload.ml_predicted_statutes : [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '4px' }}>
      
      {/* Case Overview Banner */}
      <div
        style={{
          background: 'linear-gradient(135deg, rgba(212, 175, 55, 0.08) 0%, rgba(15, 23, 42, 0.6) 100%)',
          border: '1px solid rgba(212, 175, 55, 0.25)',
          borderRadius: '8px',
          padding: '12px 14px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
          <ScrollText size={16} color="var(--gold-primary)" />
          <span style={{ color: 'var(--gold-primary)', fontWeight: 700, fontSize: '0.92rem' }}>
            {caseTitle}
          </span>
        </div>
        {payload.summary && (
          <p style={{ margin: 0, fontSize: '0.84rem', color: '#CBD5E1', lineHeight: 1.5 }}>
            {payload.summary}
          </p>
        )}
      </div>

      {/* Stage-0 ML Statutory & Companion-Section Predictions */}
      {(mlCaseType || mlPredictedStatutes.length > 0) && (
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid rgba(56, 189, 248, 0.25)',
            borderRadius: '8px',
            padding: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', marginBottom: mlPredictedStatutes.length > 0 ? '8px' : '0', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Scale size={15} color="#38BDF8" />
              <h5 style={{ margin: 0, fontSize: '0.82rem', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Stage-0 ML Statutory & Companion-Section Predictor
              </h5>
            </div>
            {mlCaseType && (
              <span
                style={{
                  background: 'rgba(212, 175, 55, 0.14)',
                  border: '1px solid rgba(212, 175, 55, 0.35)',
                  borderRadius: '4px',
                  padding: '2px 8px',
                  fontSize: '0.74rem',
                  fontWeight: 600,
                  color: '#FDE68A',
                }}
              >
                {mlCaseType}
              </span>
            )}
          </div>
          {mlPredictedStatutes.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {mlPredictedStatutes.map((statute, idx) => (
                <span
                  key={idx}
                  style={{
                    background: 'rgba(56, 189, 248, 0.12)',
                    border: '1px solid rgba(56, 189, 248, 0.35)',
                    borderRadius: '5px',
                    padding: '3px 9px',
                    fontSize: '0.77rem',
                    fontWeight: 600,
                    color: '#BAE6FD',
                  }}
                >
                  {statute}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Grid: Parties & Framed Charges */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
        
        {/* Parties Card */}
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '8px',
            padding: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <Users size={15} color="#38BDF8" />
            <h5 style={{ margin: 0, fontSize: '0.82rem', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Parties to Proceeding
            </h5>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.84rem' }}>
            <div>
              <span style={{ color: '#60A5FA', fontWeight: 600 }}>Prosecuting Authority: </span>
              <span style={{ color: '#E2E8F0' }}>State / Complainant</span>
            </div>
            <div>
              <span style={{ color: '#F87171', fontWeight: 600 }}>Accused / Defense: </span>
              <span style={{ color: '#E2E8F0' }}>{accusedList}</span>
            </div>
          </div>
        </div>

        {/* Framed Statutory Charges */}
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '8px',
            padding: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <FileBadge size={15} color="#F59E0B" />
            <h5 style={{ margin: 0, fontSize: '0.82rem', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Framed Statutory Charges ({charges.length})
            </h5>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {charges.map((charge, idx) => (
              <div
                key={idx}
                style={{
                  background: 'rgba(239, 68, 68, 0.08)',
                  border: '1px solid rgba(239, 68, 68, 0.25)',
                  borderRadius: '6px',
                  padding: '6px 10px',
                  fontSize: '0.82rem',
                }}
              >
                <div style={{ color: '#FCA5A5', fontWeight: 600 }}>
                  {charge.statute} &bull; {charge.section}
                </div>
                {charge.description && (
                  <div style={{ color: '#CBD5E1', fontSize: '0.78rem', marginTop: '2px' }}>
                    {charge.description}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

      </div>

      {/* Case Facts Relied Upon */}
      {(prosecutionFacts || defensePlea) && (
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '8px',
            padding: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileText size={15} color="var(--gold-primary)" />
              <h5 style={{ margin: 0, fontSize: '0.82rem', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Factual Matrix on Record
              </h5>
            </div>
            {prosecutionFacts.length > 280 && (
              <button
                onClick={() => setShowFullFacts(!showFullFacts)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--gold-primary)',
                  fontSize: '0.76rem',
                  cursor: 'pointer',
                }}
              >
                <span>{showFullFacts ? 'Show Less' : 'Expand Facts'}</span>
                {showFullFacts ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              </button>
            )}
          </div>

          <div style={{ fontSize: '0.84rem', color: '#E2E8F0', lineHeight: 1.55 }}>
            <p style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
              {showFullFacts || prosecutionFacts.length <= 280
                ? prosecutionFacts
                : `${prosecutionFacts.slice(0, 280)}...`}
            </p>
          </div>

          {defensePlea && (
            <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: '1px solid rgba(255, 255, 255, 0.06)' }}>
              <span style={{ color: '#34D399', fontWeight: 600, fontSize: '0.8rem' }}>Defense Plea / Stand: </span>
              <span style={{ color: '#CBD5E1', fontSize: '0.83rem' }}>{defensePlea}</span>
            </div>
          )}
        </div>
      )}

      {/* Witnesses & Exhibits Chips */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
        
        {/* Witnesses */}
        {witnesses.length > 0 && (
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '8px',
              padding: '12px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Eye size={15} color="#A78BFA" />
                <h5 style={{ margin: 0, fontSize: '0.82rem', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Witnesses ({witnesses.length})
                </h5>
              </div>
              {witnesses.length > 3 && (
                <button
                  onClick={() => setShowAllWitnesses(!showAllWitnesses)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#A78BFA',
                    fontSize: '0.74rem',
                    cursor: 'pointer',
                  }}
                >
                  {showAllWitnesses ? 'Less' : `+${witnesses.length - 3} More`}
                </button>
              )}
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {(showAllWitnesses ? witnesses : witnesses.slice(0, 3)).map((w, idx) => (
                <span
                  key={idx}
                  style={{
                    background: 'rgba(167, 139, 250, 0.1)',
                    border: '1px solid rgba(167, 139, 250, 0.25)',
                    padding: '3px 8px',
                    borderRadius: '4px',
                    fontSize: '0.78rem',
                    color: '#DDD6FE',
                  }}
                >
                  {w}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Exhibits */}
        {exhibits.length > 0 && (
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '8px',
              padding: '12px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Layers size={15} color="#34D399" />
                <h5 style={{ margin: 0, fontSize: '0.82rem', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Exhibits & Documents ({exhibits.length})
                </h5>
              </div>
              {exhibits.length > 3 && (
                <button
                  onClick={() => setShowAllExhibits(!showAllExhibits)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#34D399',
                    fontSize: '0.74rem',
                    cursor: 'pointer',
                  }}
                >
                  {showAllExhibits ? 'Less' : `+${exhibits.length - 3} More`}
                </button>
              )}
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {(showAllExhibits ? exhibits : exhibits.slice(0, 3)).map((e, idx) => (
                <span
                  key={idx}
                  style={{
                    background: 'rgba(52, 211, 153, 0.1)',
                    border: '1px solid rgba(52, 211, 153, 0.25)',
                    padding: '3px 8px',
                    borderRadius: '4px',
                    fontSize: '0.78rem',
                    color: '#A7F3D0',
                  }}
                >
                  {e}
                </span>
              ))}
            </div>
          </div>
        )}

      </div>

    </div>
  );
};
