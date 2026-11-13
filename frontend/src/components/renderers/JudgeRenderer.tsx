import React, { useState } from 'react';
import { Gavel, Award, FileText, Scale, ChevronDown, ChevronUp, BookOpen } from 'lucide-react';

interface JudgeRendererProps {
  payload: any;
  onOpenJudgment?: () => void;
}

export const JudgeRenderer: React.FC<JudgeRendererProps> = ({ payload, onOpenJudgment }) => {
  const [showFullReasons, setShowFullReasons] = useState(false);

  if (!payload) return null;

  const decision = (payload.decision || 'JUDGMENT PRONOUNCED').toUpperCase();
  const isConviction = decision.includes('CONVICTION');
  const isAcquittal = decision.includes('ACQUITTAL');

  const issues: string[] = payload.issues || [];
  const findings: Record<string, string> = payload.findings || {};
  const reasons = payload.reasons || '';
  const citations: string[] = payload.citations || [];

  const verdictColor = isConviction ? '#EF4444' : isAcquittal ? '#10B981' : 'var(--gold-primary)';
  const verdictBg = isConviction ? 'rgba(239, 68, 68, 0.15)' : isAcquittal ? 'rgba(16, 185, 129, 0.15)' : 'rgba(212, 175, 55, 0.15)';
  const verdictBorder = isConviction ? 'rgba(239, 68, 68, 0.35)' : isAcquittal ? 'rgba(16, 185, 129, 0.35)' : 'rgba(212, 175, 55, 0.35)';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginTop: '4px' }}>
      
      {/* Solemn Judicial Header */}
      <div
        style={{
          background: 'linear-gradient(135deg, rgba(212, 175, 55, 0.15) 0%, rgba(15, 23, 42, 0.9) 100%)',
          border: '1.5px solid var(--gold-primary)',
          borderRadius: '10px',
          padding: '16px',
          boxShadow: '0 0 25px rgba(212, 175, 55, 0.15)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              background: 'rgba(212, 175, 55, 0.2)',
              border: '1px solid var(--gold-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Gavel size={20} color="var(--gold-primary)" />
          </div>
          <div>
            <h4 style={{ margin: 0, color: 'var(--gold-primary)', fontSize: '1.05rem', fontWeight: 700, letterSpacing: '0.04em' }}>
              JUDICIAL BENCH ADJUDICATION
            </h4>
            <span style={{ fontSize: '0.74rem', color: '#CBD5E1', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Supreme AI Bench &bull; Final Statutory Pronouncement
            </span>
          </div>
        </div>

        <blockquote
          style={{
            margin: '12px 0 0 0',
            paddingLeft: '14px',
            borderLeft: '3px solid var(--gold-primary)',
            fontStyle: 'italic',
            fontSize: '0.92rem',
            color: '#F8FAFC',
            lineHeight: 1.5,
          }}
        >
          &ldquo;The Court has considered the case materials, submissions, evidence and applicable law.&rdquo;
        </blockquote>
      </div>

      {/* Operative Verdict Announcement Banner */}
      <div
        style={{
          background: verdictBg,
          border: `1.5px solid ${verdictBorder}`,
          borderRadius: '8px',
          padding: '14px 18px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Award size={26} color={verdictColor} />
          <div>
            <div style={{ fontSize: '0.75rem', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Operative Verdict Pronounced
            </div>
            <div style={{ fontSize: '1.25rem', fontWeight: 800, color: verdictColor, letterSpacing: '0.05em' }}>
              {decision}
            </div>
          </div>
        </div>

        {onOpenJudgment && (
          <button
            onClick={onOpenJudgment}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              background: 'linear-gradient(135deg, var(--gold-primary) 0%, #B8860B 100%)',
              color: '#0A0E17',
              border: 'none',
              borderRadius: '6px',
              padding: '10px 18px',
              fontSize: '0.86rem',
              fontWeight: 700,
              cursor: 'pointer',
              boxShadow: '0 0 16px rgba(212, 175, 55, 0.3)',
              transition: 'transform 0.15s ease, box-shadow 0.15s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-1px)';
              e.currentTarget.style.boxShadow = '0 0 22px rgba(212, 175, 55, 0.5)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = '0 0 16px rgba(212, 175, 55, 0.3)';
            }}
          >
            <Scale size={16} />
            <span>VIEW FULL JUDGMENT</span>
          </button>
        )}
      </div>

      {/* Issues for Determination */}
      {issues.length > 0 && (
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '8px',
            padding: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <FileText size={15} color="var(--gold-primary)" />
            <h5 style={{ margin: 0, fontSize: '0.82rem', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Issues Framed for Judicial Determination ({issues.length})
            </h5>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {issues.map((issue, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '8px',
                  fontSize: '0.84rem',
                  color: '#CBD5E1',
                }}
              >
                <span style={{ color: 'var(--gold-primary)', fontWeight: 700, minWidth: '20px' }}>
                  {idx + 1}.
                </span>
                <span>{issue}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Findings per Charge */}
      {Object.keys(findings).length > 0 && (
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '8px',
            padding: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <Scale size={15} color="var(--gold-primary)" />
            <h5 style={{ margin: 0, fontSize: '0.82rem', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Judicial Findings Per Statutory Charge
            </h5>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '8px' }}>
            {Object.entries(findings).map(([charge, result], idx) => {
              const resUpper = String(result).toUpperCase();
              const chargeConvicted = resUpper.includes('GUILTY') || resUpper.includes('CONVICT');
              return (
                <div
                  key={idx}
                  style={{
                    background: chargeConvicted ? 'rgba(239, 68, 68, 0.08)' : 'rgba(16, 185, 129, 0.08)',
                    border: chargeConvicted ? '1px solid rgba(239, 68, 68, 0.25)' : '1px solid rgba(16, 185, 129, 0.25)',
                    borderRadius: '6px',
                    padding: '8px 12px',
                  }}
                >
                  <div style={{ fontSize: '0.82rem', color: '#E2E8F0', fontWeight: 600 }}>
                    {charge}
                  </div>
                  <div
                    style={{
                      fontSize: '0.8rem',
                      fontWeight: 700,
                      color: chargeConvicted ? '#FCA5A5' : '#6EE7B7',
                      marginTop: '4px',
                    }}
                  >
                    Finding: {String(result)}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Ratio Decidendi & Judicial Reasoning */}
      {reasons && (
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
              <BookOpen size={15} color="var(--gold-primary)" />
              <h5 style={{ margin: 0, fontSize: '0.82rem', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Ratio Decidendi & Judicial Reasons
              </h5>
            </div>
            {reasons.length > 250 && (
              <button
                onClick={() => setShowFullReasons(!showFullReasons)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--gold-primary)',
                  fontSize: '0.75rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                <span>{showFullReasons ? 'Show Less' : 'Expand Full Reasons'}</span>
                {showFullReasons ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              </button>
            )}
          </div>

          <p style={{ margin: 0, fontSize: '0.86rem', color: '#E2E8F0', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
            {showFullReasons || reasons.length <= 250
              ? reasons
              : `${reasons.slice(0, 250)}...`}
          </p>
        </div>
      )}

      {/* Legal Citations */}
      {citations.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.75rem', color: '#94A3B8', fontWeight: 600 }}>Authorities Cited:</span>
          {citations.map((cite, idx) => (
            <span
              key={idx}
              style={{
                background: 'rgba(212, 175, 55, 0.1)',
                border: '1px solid rgba(212, 175, 55, 0.25)',
                color: 'var(--gold-primary)',
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
