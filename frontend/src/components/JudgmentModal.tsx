import React, { useState } from 'react';
import { 
  X, 
  Scale, 
  Download, 
  Copy, 
  Check, 
  Gavel, 
  FileText, 
  BookOpen, 
  FileCode 
} from 'lucide-react';
import type { Judgment } from '../types/court';
import { ComparisonModal } from './ComparisonModal';

interface JudgmentModalProps {
  judgment: Judgment;
  caseId: string;
  onClose: () => void;
}

export const JudgmentModal: React.FC<JudgmentModalProps> = ({
  judgment,
  caseId,
  onClose,
}) => {
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'issues' | 'citations'>('overview');
  const [isComparisonOpen, setIsComparisonOpen] = useState(false);

  const handleCopy = () => {
    const fullText = `
IN THE AI COURT OF INDIA
COURT OF THE SPECIAL JUDICIAL BENCH
DATED: ${judgment.date_of_decision || new Date().toLocaleDateString()}

CASE: ${judgment.case_title || 'State vs. Accused'}
PRESIDING: ${judgment.presiding_court || 'Supreme AI Tribunal'}

==================================================================
OPERATIVE VERDICT: ${judgment.final_decision}
==================================================================

1. CASE BACKGROUND:
${judgment.case_background}

2. ISSUES FOR DETERMINATION:
${judgment.issues_for_determination?.join('\n- ') || 'None framed'}

3. APPLICABLE LAW:
${judgment.applicable_law?.join('\n- ') || 'None'}

4. EVIDENCE & WITNESS ASSESSMENT:
${judgment.evidence_assessment}
${judgment.witness_assessment}

5. PROSECUTION SUBMISSIONS:
${judgment.prosecution_submissions}

6. DEFENSE SUBMISSIONS:
${judgment.defense_submissions}

7. RATIO DECIDENDI & REASONS:
${judgment.reasons}

8. LEGAL CITATIONS:
${judgment.legal_citations?.join('\n- ') || 'None'}

PRONOUNCED IN OPEN COURT.
`.trim();

    navigator.clipboard.writeText(fullText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isConviction = judgment.final_decision?.toUpperCase().includes('CONVICTION');

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(5, 8, 15, 0.85)',
      backdropFilter: 'blur(10px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '24px',
    }}>
      <div
        className="glass-panel-court animate-fade-in"
        style={{
          width: '100%',
          maxWidth: '960px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: '#0B1120',
          border: '1px solid var(--gold-primary)',
          boxShadow: '0 25px 60px rgba(0, 0, 0, 0.8), 0 0 35px rgba(212, 175, 55, 0.25)',
          borderRadius: '16px',
          overflow: 'hidden',
        }}
      >
        {/* Modal Top Header */}
        <div style={{
          padding: '20px 28px',
          background: 'linear-gradient(180deg, rgba(212, 175, 55, 0.15) 0%, rgba(15, 23, 42, 0.8) 100%)',
          borderBottom: '1px solid rgba(212, 175, 55, 0.3)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
          flexWrap: 'wrap',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{
              padding: '10px',
              borderRadius: '8px',
              background: 'rgba(212, 175, 55, 0.2)',
              border: '1px solid var(--gold-primary)',
            }}>
              <Scale size={24} color="var(--gold-primary)" />
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--gold-primary)', fontWeight: 700 }}>
                {judgment.presiding_court || 'AI COURT OF INDIA — SPECIAL BENCH'}
              </span>
              <h2 style={{ margin: '2px 0 0 0', fontSize: '1.25rem', color: '#F8FAFC' }}>
                {judgment.case_title || 'Judicial Decree & Sentence'}
              </h2>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
            <button
              onClick={handleCopy}
              className="btn-secondary"
              title="Copy decree to clipboard"
            >
              {copied ? <Check size={16} color="#34D399" /> : <Copy size={16} />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>

            <a
              href={`/api/court/cases/${caseId}/download/txt`}
              download
              className="btn-secondary"
              style={{ textDecoration: 'none' }}
              title="Download Plaintext Judgment"
            >
              <Download size={16} />
              <span>TXT</span>
            </a>

            <a
              href={`/api/court/cases/${caseId}/download/json`}
              download
              className="btn-secondary"
              style={{ textDecoration: 'none' }}
              title="Download Structured JSON Judgment"
            >
              <FileCode size={16} />
              <span>JSON</span>
            </a>

            <button
              onClick={() => setIsComparisonOpen(true)}
              style={{
                background: 'linear-gradient(135deg, #D4AF37 0%, #B8860B 100%)',
                color: '#0B1120',
                fontWeight: 700,
                padding: '7px 14px',
                fontSize: '0.82rem',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                boxShadow: '0 0 12px rgba(212, 175, 55, 0.35)',
              }}
              title="Upload Real Court Judgment for substantive comparison"
            >
              <Scale size={16} />
              <span>Compare Real Judgment</span>
            </button>

            <button
              onClick={onClose}
              style={{
                background: 'rgba(255, 255, 255, 0.08)',
                border: 'none',
                color: '#94A3B8',
                padding: '8px',
                borderRadius: '8px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginLeft: '8px',
              }}
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Verdict Callout Banner */}
        <div style={{
          padding: '16px 28px',
          background: isConviction ? 'rgba(220, 38, 38, 0.12)' : 'rgba(16, 185, 129, 0.12)',
          borderBottom: isConviction ? '1px solid rgba(220, 38, 38, 0.3)' : '1px solid rgba(16, 185, 129, 0.3)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Gavel size={22} color={isConviction ? '#F87171' : '#34D399'} />
            <div>
              <span style={{ fontSize: '0.78rem', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                FINAL OPERATIVE DECISION
              </span>
              <div style={{
                fontSize: '1.35rem',
                fontWeight: 800,
                color: isConviction ? '#F87171' : '#34D399',
                fontFamily: 'var(--font-serif)',
                letterSpacing: '0.04em'
              }}>
                {judgment.final_decision}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => setActiveTab('overview')}
              style={{
                padding: '6px 14px',
                borderRadius: '6px',
                border: 'none',
                background: activeTab === 'overview' ? 'rgba(212, 175, 55, 0.25)' : 'transparent',
                color: activeTab === 'overview' ? 'var(--gold-primary)' : '#94A3B8',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.85rem',
              }}
            >
              Core Decree
            </button>
            <button
              onClick={() => setActiveTab('issues')}
              style={{
                padding: '6px 14px',
                borderRadius: '6px',
                border: 'none',
                background: activeTab === 'issues' ? 'rgba(212, 175, 55, 0.25)' : 'transparent',
                color: activeTab === 'issues' ? 'var(--gold-primary)' : '#94A3B8',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.85rem',
              }}
            >
              Issue Analysis ({judgment.issue_analyses?.length || 0})
            </button>
            <button
              onClick={() => setActiveTab('citations')}
              style={{
                padding: '6px 14px',
                borderRadius: '6px',
                border: 'none',
                background: activeTab === 'citations' ? 'rgba(212, 175, 55, 0.25)' : 'transparent',
                color: activeTab === 'citations' ? 'var(--gold-primary)' : '#94A3B8',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.85rem',
              }}
            >
              Statutes & Precedents
            </button>
          </div>
        </div>

        {/* Scrollable Decree Content */}
        <div style={{ padding: '28px', overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '22px' }}>
          
          {activeTab === 'overview' && (
            <>
              {/* Case Background */}
              <div>
                <h4 style={{ color: 'var(--gold-primary)', fontSize: '0.95rem', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <FileText size={16} /> 1. Case Background & Charge Formulation
                </h4>
                <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '8px', padding: '14px', fontSize: '0.9rem', color: '#CBD5E1', lineHeight: '1.7' }}>
                  {judgment.case_background}
                </div>
              </div>

              {/* Evidentiary & Witness Evaluation */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: '16px' }}>
                <div>
                  <h4 style={{ color: '#A855F7', fontSize: '0.9rem', marginBottom: '8px' }}>
                    4. Evidence Assessment
                  </h4>
                  <div style={{ background: 'rgba(168, 85, 247, 0.05)', border: '1px solid rgba(168, 85, 247, 0.2)', borderRadius: '8px', padding: '14px', fontSize: '0.88rem', color: '#E2E8F0', height: '100%' }}>
                    {judgment.evidence_assessment}
                  </div>
                </div>

                <div>
                  <h4 style={{ color: '#38BDF8', fontSize: '0.9rem', marginBottom: '8px' }}>
                    5. Witness Credibility Assessment
                  </h4>
                  <div style={{ background: 'rgba(56, 189, 248, 0.05)', border: '1px solid rgba(56, 189, 248, 0.2)', borderRadius: '8px', padding: '14px', fontSize: '0.88rem', color: '#E2E8F0', height: '100%' }}>
                    {judgment.witness_assessment}
                  </div>
                </div>
              </div>

              {/* Submissions by Parties */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: '16px' }}>
                <div>
                  <h4 style={{ color: '#60A5FA', fontSize: '0.9rem', marginBottom: '8px' }}>
                    6. Prosecution Submissions
                  </h4>
                  <div style={{ background: 'rgba(59, 130, 246, 0.05)', border: '1px solid rgba(59, 130, 246, 0.2)', borderRadius: '8px', padding: '14px', fontSize: '0.88rem', color: '#E2E8F0', height: '100%' }}>
                    {judgment.prosecution_submissions}
                  </div>
                </div>

                <div>
                  <h4 style={{ color: '#34D399', fontSize: '0.9rem', marginBottom: '8px' }}>
                    7. Defense Submissions
                  </h4>
                  <div style={{ background: 'rgba(16, 185, 129, 0.05)', border: '1px solid rgba(16, 185, 129, 0.2)', borderRadius: '8px', padding: '14px', fontSize: '0.88rem', color: '#E2E8F0', height: '100%' }}>
                    {judgment.defense_submissions}
                  </div>
                </div>
              </div>

              {/* Findings per Charge */}
              {judgment.findings_per_charge && Object.keys(judgment.findings_per_charge).length > 0 && (
                <div>
                  <h4 style={{ color: 'var(--gold-primary)', fontSize: '0.95rem', marginBottom: '8px' }}>
                    9. Findings Per Charge
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {Object.entries(judgment.findings_per_charge).map(([charge, finding], idx) => (
                      <div key={idx} style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
                        <span style={{ fontWeight: 600, color: '#F1F5F9', fontSize: '0.9rem' }}>{charge}</span>
                        <span style={{
                          padding: '3px 10px',
                          borderRadius: '4px',
                          fontSize: '0.8rem',
                          fontWeight: 700,
                          background: finding.toLowerCase().includes('guilty') ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                          color: finding.toLowerCase().includes('guilty') ? '#F87171' : '#34D399',
                        }}>
                          {finding}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Ratio Decidendi */}
              <div>
                <h4 style={{ color: 'var(--gold-primary)', fontSize: '0.95rem', marginBottom: '8px' }}>
                  11. Ratio Decidendi & Judicial Reasons
                </h4>
                <div style={{ background: 'rgba(212, 175, 55, 0.05)', border: '1px solid rgba(212, 175, 55, 0.25)', borderRadius: '8px', padding: '16px', fontSize: '0.92rem', color: '#F1F5F9', lineHeight: '1.7', whiteSpace: 'pre-wrap' }}>
                  {judgment.reasons}
                </div>
              </div>
            </>
          )}

          {activeTab === 'issues' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {judgment.issue_analyses && judgment.issue_analyses.length > 0 ? (
                judgment.issue_analyses.map((ia, idx) => (
                  <div key={idx} style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', padding: '18px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
                      <span style={{ color: 'var(--gold-primary)', fontWeight: 700, fontSize: '0.95rem' }}>
                        Issue #{ia.issue_number || idx + 1}: {ia.issue_statement}
                      </span>
                      {ia.applicable_law && (
                        <span style={{ fontSize: '0.75rem', background: 'rgba(129, 140, 248, 0.15)', color: '#C7D2FE', padding: '2px 8px', borderRadius: '4px' }}>
                          {ia.applicable_law}
                        </span>
                      )}
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '0.84rem' }}>
                      <div style={{ background: 'rgba(59, 130, 246, 0.05)', padding: '10px', borderRadius: '6px' }}>
                        <strong style={{ color: '#93C5FD' }}>Prosecution: </strong>
                        <span style={{ color: '#CBD5E1' }}>{ia.prosecution_submission_summary}</span>
                      </div>
                      <div style={{ background: 'rgba(16, 185, 129, 0.05)', padding: '10px', borderRadius: '6px' }}>
                        <strong style={{ color: '#6EE7B7' }}>Defense: </strong>
                        <span style={{ color: '#CBD5E1' }}>{ia.defense_submission_summary}</span>
                      </div>
                    </div>

                    <div style={{ background: 'rgba(212, 175, 55, 0.08)', borderLeft: '3px solid var(--gold-primary)', padding: '10px 14px', borderRadius: '0 6px 6px 0', fontSize: '0.88rem' }}>
                      <strong style={{ color: 'var(--gold-primary)' }}>Judicial Finding: </strong>
                      <span style={{ color: '#F1F5F9' }}>{ia.judicial_finding}</span>
                    </div>
                  </div>
                ))
              ) : (
                <div style={{ textAlign: 'center', color: '#94A3B8', padding: '30px' }}>
                  No isolated issue breakdowns recorded.
                </div>
              )}
            </div>
          )}

          {activeTab === 'citations' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div>
                <h4 style={{ color: '#818CF8', fontSize: '0.95rem', marginBottom: '10px' }}>
                  Statutory Provisions Applied
                </h4>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {judgment.applicable_law?.map((law, idx) => (
                    <span key={idx} style={{ background: 'rgba(129, 140, 248, 0.15)', border: '1px solid rgba(129, 140, 248, 0.3)', padding: '6px 14px', borderRadius: '6px', fontSize: '0.85rem', color: '#C7D2FE' }}>
                      {law}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <h4 style={{ color: 'var(--gold-primary)', fontSize: '0.95rem', marginBottom: '10px' }}>
                  Judicial Precedents & Authorities Cited
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {judgment.legal_citations?.map((cit, idx) => (
                    <div key={idx} style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', padding: '12px 16px', fontSize: '0.88rem', color: '#CBD5E1', display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <BookOpen size={16} color="var(--gold-primary)" />
                      <span>{cit}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

        </div>

      </div>

      {isComparisonOpen && (
        <ComparisonModal
          caseId={caseId}
          judgment={judgment}
          onClose={() => setIsComparisonOpen(false)}
        />
      )}
    </div>
  );
};
