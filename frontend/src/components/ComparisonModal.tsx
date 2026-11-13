import React, { useState, useEffect } from 'react';
import {
  X,
  Scale,
  Upload,
  FileCheck,
  AlertTriangle,
  Download,
  CheckCircle2,
  AlertCircle,
  FileText,
  FileCode,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react';
import type { ComparisonReport } from '../types/court';

interface ComparisonModalProps {
  caseId: string;
  onClose: () => void;
}

export const ComparisonModal: React.FC<ComparisonModalProps> = ({ caseId, onClose }) => {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<ComparisonReport | null>(null);

  useEffect(() => {
    let isMounted = true;
    const fetchExistingComparison = async () => {
      try {
        setLoading(true);
        const response = await fetch(`/api/cases/${caseId}/comparison`);
        if (response.ok) {
          const data: ComparisonReport = await response.json();
          if (isMounted) {
            setReport(data);
          }
        }
      } catch (err) {
        // No existing comparison generated yet
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };
    if (caseId) {
      fetchExistingComparison();
    }
    return () => {
      isMounted = false;
    };
  }, [caseId]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleCompare = async () => {
    if (!file) {
      setError('Please select a Real Court Judgment file (.pdf, .txt, or .json).');
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('real_judgment_file', file);

    try {
      const response = await fetch(`/api/cases/${caseId}/compare`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Comparison failed with HTTP ${response.status}`);
      }

      const data: ComparisonReport = await response.json();
      setReport(data);
    } catch (err: any) {
      console.error('Comparison error:', err);
      setError(err.message || 'Failed to compare judgments.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(5, 8, 15, 0.88)',
        backdropFilter: 'blur(12px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 10000,
        padding: '20px',
      }}
    >
      <div
        className="glass-panel-court animate-fade-in"
        style={{
          width: '100%',
          maxWidth: '1020px',
          maxHeight: '92vh',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: '#0B1120',
          border: '1px solid var(--gold-primary)',
          boxShadow: '0 25px 60px rgba(0, 0, 0, 0.85), 0 0 40px rgba(212, 175, 55, 0.25)',
          borderRadius: '16px',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '18px 26px',
            background: 'linear-gradient(180deg, rgba(212, 175, 55, 0.18) 0%, rgba(15, 23, 42, 0.9) 100%)',
            borderBottom: '1px solid rgba(212, 175, 55, 0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div
              style={{
                padding: '10px',
                borderRadius: '8px',
                background: 'rgba(212, 175, 55, 0.2)',
                border: '1px solid var(--gold-primary)',
              }}
            >
              <Scale size={24} color="var(--gold-primary)" />
            </div>
            <div>
              <span
                style={{
                  fontSize: '0.74rem',
                  letterSpacing: '0.12em',
                  textTransform: 'uppercase',
                  color: 'var(--gold-primary)',
                  fontWeight: 700,
                }}
              >
                PHASE 5 COMPARISON ENGINE
              </span>
              <h2 style={{ margin: '2px 0 0 0', fontSize: '1.25rem', color: '#F8FAFC' }}>
                AI Judgment vs Real Court Judgment Comparison
              </h2>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {report && (
              <>
                <a
                  href={`/api/cases/${caseId}/comparison/download/txt`}
                  download
                  className="btn-secondary"
                  style={{ textDecoration: 'none' }}
                  title="Download Report TXT"
                >
                  <Download size={15} />
                  <span>TXT</span>
                </a>
                <a
                  href={`/api/cases/${caseId}/comparison/download/pdf`}
                  download
                  className="btn-secondary"
                  style={{ textDecoration: 'none' }}
                  title="Download Formal PDF Report"
                >
                  <FileText size={15} />
                  <span>PDF</span>
                </a>
                <a
                  href={`/api/cases/${caseId}/comparison/download/json`}
                  download
                  className="btn-secondary"
                  style={{ textDecoration: 'none' }}
                  title="Download JSON Report"
                >
                  <FileCode size={15} />
                  <span>JSON</span>
                </a>
              </>
            )}

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

        {/* Modal Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Upload Section (if no report yet) */}
          {!report && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '640px', margin: '40px auto', width: '100%' }}>
              <div
                style={{
                  padding: '24px',
                  borderRadius: '12px',
                  background: 'rgba(15, 23, 42, 0.6)',
                  border: '1px dashed rgba(212, 175, 55, 0.4)',
                  textAlign: 'center',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '12px',
                }}
              >
                <Upload size={36} color="var(--gold-primary)" />
                <h3 style={{ margin: 0, color: '#F8FAFC' }}>Upload Authoritative Real Court Judgment</h3>
                <p style={{ margin: 0, fontSize: '0.85rem', color: '#94A3B8', maxWidth: '480px' }}>
                  Upload the official court judgment or ground-truth ruling (.pdf, .txt, or .json) to evaluate how accurately the AI Court reasoned and decided this case.
                </p>

                <input
                  type="file"
                  id="real-court-judgment-upload"
                  accept=".pdf,.txt,.json"
                  onChange={handleFileChange}
                  style={{ display: 'none' }}
                />

                <label
                  htmlFor="real-court-judgment-upload"
                  className="btn-secondary"
                  style={{ cursor: 'pointer', marginTop: '8px', padding: '10px 20px' }}
                >
                  <FileCheck size={16} />
                  <span>{file ? file.name : 'Select Real Judgment File'}</span>
                </label>

                {file && (
                  <span style={{ fontSize: '0.8rem', color: '#34D399' }}>
                    Selected: {file.name} ({(file.size / 1024).toFixed(1)} KB)
                  </span>
                )}
              </div>

              {error && (
                <div
                  style={{
                    padding: '12px 16px',
                    borderRadius: '8px',
                    background: 'rgba(239, 68, 68, 0.15)',
                    border: '1px solid rgba(239, 68, 68, 0.4)',
                    color: '#FCA5A5',
                    fontSize: '0.85rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                  }}
                >
                  <AlertCircle size={18} color="#EF4444" />
                  <span>{error}</span>
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'center' }}>
                <button
                  onClick={handleCompare}
                  disabled={!file || loading}
                  className="btn-primary"
                  style={{
                    padding: '12px 28px',
                    fontSize: '0.95rem',
                    opacity: !file || loading ? 0.6 : 1,
                    cursor: !file || loading ? 'not-allowed' : 'pointer',
                  }}
                >
                  {loading ? (
                    <span>Evaluating Legal Content & Reasoning...</span>
                  ) : (
                    <>
                      <span>Compare AI vs Real Court</span>
                      <ArrowRight size={18} />
                    </>
                  )}
                </button>
              </div>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  justifyContent: 'center',
                  fontSize: '0.78rem',
                  color: '#64748B',
                }}
              >
                <ShieldCheck size={14} color="#34D399" />
                <span>Strict Blind Isolation: Real Court Judgment is never exposed to the AI trial nodes.</span>
              </div>
            </div>
          )}

          {/* Report Results View */}
          {report && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              
              {/* Executive Summary Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>
                
                {/* Overall Score */}
                {(() => {
                  const isPartial = (report.scores.excluded_categories?.length ?? 0) > 0;
                  const excludedCount = report.scores.excluded_categories?.length ?? 0;
                  return (
                    <div
                      style={{
                        padding: '18px',
                        borderRadius: '12px',
                        background: 'linear-gradient(135deg, rgba(212, 175, 55, 0.15) 0%, rgba(15, 23, 42, 0.8) 100%)',
                        border: '1px solid rgba(212, 175, 55, 0.4)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                      }}
                    >
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontSize: '0.74rem', textTransform: 'uppercase', color: 'var(--gold-primary)', fontWeight: 700 }}>
                            {isPartial ? 'PARTIAL BENCHMARK' : 'OVERALL BENCHMARK'}
                          </span>
                          {isPartial && (
                            <span
                              style={{
                                fontSize: '0.65rem',
                                padding: '1px 6px',
                                borderRadius: '4px',
                                background: 'rgba(251, 191, 36, 0.2)',
                                color: '#FDE68A',
                                fontWeight: 600,
                              }}
                            >
                              {excludedCount} EXCLUDED
                            </span>
                          )}
                        </div>
                        <div style={{ fontSize: '2.2rem', fontWeight: 800, color: '#F8FAFC' }}>
                          {report.scores.overall_score.toFixed(1)}%
                        </div>
                        <span style={{ fontSize: '0.75rem', color: '#94A3B8', display: 'block' }}>
                          {isPartial
                            ? `Re-normalized over ${10 - excludedCount} assessable categories`
                            : 'Balanced 10-Factor Score'}
                        </span>
                        {report.scores.substantive_score != null && (
                          <div style={{ fontSize: '0.78rem', color: '#CBD5E1', marginTop: '4px' }}>
                            Substantive Quality: <strong style={{ color: '#38BDF8' }}>{report.scores.substantive_score.toFixed(1)}%</strong>
                          </div>
                        )}
                      </div>
                      <div
                        style={{
                          width: '64px',
                          height: '64px',
                          borderRadius: '50%',
                          background: 'rgba(212, 175, 55, 0.15)',
                          border: '2px solid var(--gold-primary)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          flexShrink: 0,
                        }}
                      >
                        <Scale size={28} color="var(--gold-primary)" />
                      </div>
                    </div>
                  );
                })()}

                {/* Verdict Alignment */}
                {(() => {
                  const isExtractionError = report.verdict_comparison.status === 'EXTRACTION_ERROR' ||
                    report.verdict_comparison.real_verdict === 'EXTRACTION_ERROR' ||
                    report.verdict_comparison.real_verdict === 'UNKNOWN';
                  const isAligned = report.verdict_comparison.alignment === 'aligned';

                  return (
                    <div
                      style={{
                        padding: '18px',
                        borderRadius: '12px',
                        background: isAligned
                          ? 'rgba(16, 185, 129, 0.12)'
                          : isExtractionError
                          ? 'rgba(245, 158, 11, 0.12)'
                          : 'rgba(239, 68, 68, 0.12)',
                        border: isAligned
                          ? '1px solid rgba(16, 185, 129, 0.4)'
                          : isExtractionError
                          ? '1px solid rgba(245, 158, 11, 0.4)'
                          : '1px solid rgba(239, 68, 68, 0.4)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                      }}
                    >
                      <div style={{ flex: 1, paddingRight: '12px' }}>
                        <span style={{ fontSize: '0.74rem', textTransform: 'uppercase', color: '#94A3B8', fontWeight: 700 }}>
                          OPERATIVE VERDICT
                        </span>
                        <div
                          style={{
                            fontSize: '1.4rem',
                            fontWeight: 800,
                            color: isAligned ? '#34D399' : isExtractionError ? '#FBBF24' : '#F87171',
                          }}
                        >
                          {isExtractionError ? 'EXTRACTION ERROR' : report.verdict_comparison.alignment.toUpperCase()}
                        </div>
                        <span style={{ fontSize: '0.75rem', color: '#94A3B8', display: 'block' }}>
                          AI: {report.verdict_comparison.ai_verdict} | Real: {report.verdict_comparison.real_verdict}
                        </span>
                        {report.verdict_comparison.verdict_normalization_explanation && (
                          <span style={{ fontSize: '0.7rem', color: '#CBD5E1', display: 'block', marginTop: '4px', fontStyle: 'italic' }}>
                            {report.verdict_comparison.verdict_normalization_explanation}
                          </span>
                        )}
                      </div>
                      {isAligned ? (
                        <CheckCircle2 size={32} color="#34D399" style={{ flexShrink: 0 }} />
                      ) : isExtractionError ? (
                        <AlertCircle size={32} color="#FBBF24" style={{ flexShrink: 0 }} />
                      ) : (
                        <AlertTriangle size={32} color="#F87171" style={{ flexShrink: 0 }} />
                      )}
                    </div>
                  );
                })()}

                {/* Legal Reasoning Alignment */}
                <div
                  style={{
                    padding: '18px',
                    borderRadius: '12px',
                    background: 'rgba(15, 23, 42, 0.8)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div>
                    <span style={{ fontSize: '0.74rem', textTransform: 'uppercase', color: '#94A3B8', fontWeight: 700 }}>
                      LEGAL REASONING
                    </span>
                    <div style={{ fontSize: '2.2rem', fontWeight: 800, color: '#38BDF8' }}>
                      {report.scores.reasoning_alignment.toFixed(1)}%
                    </div>
                    <span style={{ fontSize: '0.75rem', color: '#94A3B8' }}>Ratio Decidendi Match</span>
                  </div>
                  <FileText size={28} color="#38BDF8" />
                </div>
              </div>

              {/* Assessment Message */}
              <div
                style={{
                  padding: '16px 20px',
                  borderRadius: '10px',
                  background: 'rgba(15, 23, 42, 0.7)',
                  border: '1px solid rgba(212, 175, 55, 0.3)',
                  fontSize: '0.9rem',
                  lineHeight: '1.5',
                  color: '#E2E8F0',
                }}
              >
                <strong style={{ color: 'var(--gold-primary)', display: 'block', marginBottom: '4px' }}>
                  JUDICIAL ASSESSMENT:
                </strong>
                {report.overall_assessment}
              </div>

              {/* 10-Dimension Score Breakdown */}
              <div
                style={{
                  padding: '20px',
                  borderRadius: '12px',
                  background: 'rgba(15, 23, 42, 0.6)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <h4 style={{ margin: 0, fontSize: '0.95rem', color: 'var(--gold-primary)' }}>
                    10-DIMENSIONAL BENCHMARK SCORES
                  </h4>
                  {report.scores.excluded_categories && report.scores.excluded_categories.length > 0 && (
                    <span style={{ fontSize: '0.74rem', color: '#94A3B8' }}>
                      Excluded from denominator: {report.scores.excluded_categories.join(', ')}
                    </span>
                  )}
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '14px' }}>
                  {[
                    { key: 'verdict_alignment', label: 'Verdict', val: report.scores.verdict_alignment, defaultWt: '20%' },
                    { key: 'reasoning_alignment', label: 'Reasoning', val: report.scores.reasoning_alignment, defaultWt: '20%' },
                    { key: 'factual_accuracy', label: 'Factual Accuracy', val: report.scores.factual_accuracy, defaultWt: '12%' },
                    { key: 'issue_alignment', label: 'Issue Framing', val: report.scores.issue_alignment, defaultWt: '10%' },
                    { key: 'evidence_alignment', label: 'Evidence', val: report.scores.evidence_alignment, defaultWt: '10%' },
                    { key: 'finding_alignment', label: 'Findings', val: report.scores.finding_alignment, defaultWt: '8%' },
                    { key: 'charge_alignment', label: 'Charges', val: report.scores.charge_alignment, defaultWt: '5%' },
                    { key: 'witness_alignment', label: 'Witnesses', val: report.scores.witness_alignment, defaultWt: '5%' },
                    { key: 'legal_alignment', label: 'Legal Citations', val: report.scores.legal_alignment, defaultWt: '5%' },
                    { key: 'final_order_alignment', label: 'Final Order', val: report.scores.final_order_alignment, defaultWt: '5%' },
                  ].map((item, idx) => {
                    const isExcluded = report.scores.excluded_categories?.includes(item.key);
                    const activeWeight = report.scores.active_weights?.[item.key];
                    const weightDisplay = isExcluded
                      ? 'Excluded (Insufficient Data)'
                      : activeWeight !== undefined
                      ? `Active: ${(activeWeight * 100).toFixed(1)}%`
                      : item.defaultWt;

                    const scoreDisplay = isExcluded ? 'Not assessed' : `${item.val.toFixed(1)}%`;

                    return (
                      <div
                        key={idx}
                        style={{
                          padding: '12px',
                          borderRadius: '8px',
                          background: isExcluded ? 'rgba(255, 255, 255, 0.02)' : 'rgba(255, 255, 255, 0.03)',
                          border: isExcluded ? '1px dashed rgba(255, 255, 255, 0.1)' : '1px solid rgba(255, 255, 255, 0.06)',
                        }}
                      >
                        <div style={{ fontSize: '0.74rem', color: '#94A3B8' }}>
                          {item.label} ({weightDisplay})
                        </div>
                        <div
                          style={{
                            fontSize: '1.25rem',
                            fontWeight: 700,
                            color: isExcluded
                              ? '#94A3B8'
                              : item.val >= 70
                              ? '#34D399'
                              : item.val >= 40
                              ? '#FBBF24'
                              : '#F87171',
                          }}
                        >
                          {scoreDisplay}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Factual Correctness & Completeness Breakdown */}
              {report.factual_comparison && (
                <div
                  style={{
                    padding: '18px 20px',
                    borderRadius: '12px',
                    background: 'rgba(15, 23, 42, 0.6)',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <h4 style={{ margin: 0, fontSize: '0.95rem', color: 'var(--gold-primary)' }}>
                      FACTUAL ACCURACY EVALUATION (PRECISION & RECALL)
                    </h4>
                    <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#34D399' }}>
                      Composite Score: {report.scores.factual_accuracy.toFixed(1)}%
                    </span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginBottom: '12px' }}>
                    <div style={{ padding: '10px', borderRadius: '8px', background: 'rgba(255, 255, 255, 0.03)' }}>
                      <span style={{ fontSize: '0.72rem', color: '#94A3B8' }}>Factual Correctness (Precision)</span>
                      <div style={{ fontSize: '1.2rem', fontWeight: 700, color: (report.factual_comparison.correctness_score ?? 100) >= 70 ? '#34D399' : '#F87171' }}>
                        {(report.factual_comparison.correctness_score ?? 100).toFixed(1)}%
                      </div>
                      <span style={{ fontSize: '0.7rem', color: '#64748B' }}>Verified vs Invented/Unsupported</span>
                    </div>
                    <div style={{ padding: '10px', borderRadius: '8px', background: 'rgba(255, 255, 255, 0.03)' }}>
                      <span style={{ fontSize: '0.72rem', color: '#94A3B8' }}>Factual Completeness (Recall)</span>
                      <div style={{ fontSize: '1.2rem', fontWeight: 700, color: (report.factual_comparison.completeness_score ?? 100) >= 70 ? '#34D399' : '#F87171' }}>
                        {(report.factual_comparison.completeness_score ?? 100).toFixed(1)}%
                      </div>
                      <span style={{ fontSize: '0.7rem', color: '#64748B' }}>Coverage of authoritative facts</span>
                    </div>
                    <div style={{ padding: '10px', borderRadius: '8px', background: 'rgba(255, 255, 255, 0.03)' }}>
                      <span style={{ fontSize: '0.72rem', color: '#94A3B8' }}>Fact Quantities</span>
                      <div style={{ fontSize: '0.85rem', color: '#CBD5E1', marginTop: '4px' }}>
                        Verified: <strong style={{ color: '#34D399' }}>{report.factual_comparison.correct_facts?.length ?? 0}</strong> |
                        Invented: <strong style={{ color: (report.factual_comparison.invented_facts?.length ?? 0) > 0 ? '#F87171' : '#34D399' }}>{report.factual_comparison.invented_facts?.length ?? 0}</strong>
                      </div>
                      <div style={{ fontSize: '0.85rem', color: '#CBD5E1' }}>
                        Unsupported: <strong style={{ color: (report.factual_comparison.unsupported_facts?.length ?? 0) > 0 ? '#FBBF24' : '#34D399' }}>{report.factual_comparison.unsupported_facts?.length ?? 0}</strong> |
                        Omitted: <strong style={{ color: (report.factual_comparison.omitted_material_facts?.length ?? 0) > 0 ? '#F87171' : '#34D399' }}>{report.factual_comparison.omitted_material_facts?.length ?? 0}</strong>
                      </div>
                    </div>
                  </div>
                  <p style={{ margin: 0, fontSize: '0.82rem', color: '#94A3B8' }}>
                    {report.factual_comparison.explanation}
                  </p>
                </div>
              )}

              {/* Major Errors & Historical Mismatches */}
              {report.major_errors && report.major_errors.length > 0 && (
                <div
                  style={{
                    padding: '20px',
                    borderRadius: '12px',
                    background: 'rgba(239, 68, 68, 0.05)',
                    border: '1px solid rgba(239, 68, 68, 0.25)',
                  }}
                >
                  <h4 style={{ margin: '0 0 14px 0', fontSize: '0.95rem', color: '#F87171', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <AlertTriangle size={18} />
                    <span>DETECTED LEGAL & EPISTEMIC DISCREPANCIES ({report.major_errors.length})</span>
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {report.major_errors.map((err, idx) => (
                      <div
                        key={idx}
                        style={{
                          padding: '12px 16px',
                          borderRadius: '8px',
                          background: 'rgba(15, 23, 42, 0.8)',
                          border: '1px solid rgba(239, 68, 68, 0.2)',
                          fontSize: '0.85rem',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                          <strong style={{ color: '#F87171' }}>{err.type.replace(/_/g, ' ').toUpperCase()}</strong>
                          <span
                            style={{
                              fontSize: '0.7rem',
                              padding: '2px 8px',
                              borderRadius: '4px',
                              background: err.severity === 'critical' ? 'rgba(239, 68, 68, 0.3)' : 'rgba(251, 191, 36, 0.3)',
                              color: err.severity === 'critical' ? '#FCA5A5' : '#FDE68A',
                              textTransform: 'uppercase',
                              fontWeight: 700,
                            }}
                          >
                            {err.severity}
                          </span>
                        </div>
                        <p style={{ margin: '4px 0', color: '#CBD5E1' }}>{err.explanation}</p>
                        <div style={{ fontSize: '0.78rem', color: '#94A3B8', marginTop: '6px' }}>
                          <div><strong>AI Claim:</strong> {err.ai_claim}</div>
                          <div><strong>Real Court:</strong> {err.real_court_position}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Reset to compare another */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '8px' }}>
                <button
                  onClick={() => {
                    setReport(null);
                    setFile(null);
                  }}
                  className="btn-secondary"
                >
                  <span>Compare Another Judgment</span>
                </button>
              </div>

            </div>
          )}

        </div>
      </div>
    </div>
  );
};
