import React, { useState, useRef } from 'react';
import { UploadCloud, CheckCircle2, AlertTriangle, Play, Gavel } from 'lucide-react';
import type { UploadedCaseInfo } from '../types/court';

interface CaseUploadProps {
  onCaseUploaded: (caseInfo: UploadedCaseInfo) => void;
  onStartCourt: () => void;
  uploadedCase: UploadedCaseInfo | null;
  isStreaming: boolean;
  disabled?: boolean;
}

export const CaseUpload: React.FC<CaseUploadProps> = ({
  onCaseUploaded,
  onStartCourt,
  uploadedCase,
  isStreaming,
  disabled = false,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    setErrorMessage(null);

    const lowerName = file.name.toLowerCase();
    if (
      lowerName.includes('ground_truth') ||
      lowerName.includes('groundtruth') ||
      lowerName.includes('real_verdict') ||
      lowerName.includes('hidden_verdict') ||
      lowerName.includes('actual_judgment')
    ) {
      setErrorMessage(
        'Upload rejected: The filename indicates a Ground Truth verdict file. ' +
        'Please upload only the unadjudicated Case Evidence Packet (e.g. Case_Packet.pdf).'
      );
      return;
    }

    if (!lowerName.endsWith('.pdf')) {
      setErrorMessage('Invalid file format. Please upload an official case record PDF (e.g. Case_Packet.pdf).');
      return;
    }

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/court/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({ detail: 'Upload failed' }));
        const rawDetail: string = errData.detail || `Upload failed with status ${response.status}`;

        if (response.status === 403) {
          throw new Error(
            'Security violation: Document appears to contain final court verdict content. ' +
            'Please upload only the unadjudicated Case Evidence Packet.'
          );
        }
        throw new Error(rawDetail);
      }

      const caseData: UploadedCaseInfo = await response.json();
      onCaseUploaded(caseData);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to upload case packet.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (disabled || isStreaming) return;
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFile(e.target.files[0]);
    }
  };

  return (
    <div style={{ maxWidth: '800px', width: '100%', margin: '0 auto', padding: '24px 20px' }}>
      
      {/* Landing State: Large Minimal Courtroom Entrance */}
      {!uploadedCase ? (
        <div style={{ textAlign: 'center', paddingTop: '32px', paddingBottom: '32px' }}>
          
          {/* Top Courtroom Brand */}
          <div
            className="emblem-breathe"
            style={{
              width: '68px',
              height: '68px',
              borderRadius: '50%',
              background: 'linear-gradient(135deg, rgba(212, 175, 55, 0.25) 0%, rgba(184, 134, 11, 0.1) 100%)',
              border: '1.5px solid var(--gold-primary)',
              display: 'inline-flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '3px',
              boxShadow: '0 0 24px rgba(212, 175, 55, 0.25)',
              marginBottom: '16px',
            }}
          >
            <span className="gavel-hammer-loop">
              <Gavel size={28} color="var(--gold-primary)" />
            </span>
            <div className="gavel-block-ripple" />
          </div>

          <h2
            style={{
              fontFamily: 'var(--font-serif)',
              fontSize: '1.85rem',
              color: 'var(--gold-primary)',
              letterSpacing: '0.06em',
              fontWeight: 800,
              margin: '0 0 6px 0',
            }}
          >
            AI COURT OF INDIA
          </h2>
          
          <p style={{ color: '#94A3B8', fontSize: '0.95rem', margin: '0 0 18px 0', letterSpacing: '0.02em' }}>
            AI Legal Reasoning &amp; Autonomous Courtroom Simulation
          </p>

          {/* Capability Badges */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'center',
              flexWrap: 'wrap',
              gap: '8px',
              marginBottom: '28px',
            }}
          >
            {[
              'BNS • BNSS • BSA Corpus',
              'Hybrid Legal RAG & Precedents',
              '12-Section Judicial Decree',
            ].map((badge) => (
              <span
                key={badge}
                style={{
                  fontSize: '0.75rem',
                  color: '#CBD5E1',
                  background: 'rgba(15, 23, 42, 0.72)',
                  border: '1px solid rgba(212, 175, 55, 0.22)',
                  padding: '4px 12px',
                  borderRadius: '999px',
                  letterSpacing: '0.02em',
                }}
              >
                {badge}
              </span>
            ))}
          </div>

          {/* Large Premium Case Packet Upload Area */}
          <div
            role="button"
            tabIndex={disabled || isStreaming ? -1 : 0}
            aria-label="Upload unadjudicated case packet PDF"
            onKeyDown={(e) => {
              if ((e.key === 'Enter' || e.key === ' ') && !disabled && !isStreaming) {
                e.preventDefault();
                fileInputRef.current?.click();
              }
            }}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => {
              if (!disabled && !isStreaming) fileInputRef.current?.click();
            }}
            style={{
              border: isDragging ? '2px dashed var(--gold-primary)' : '1.5px dashed rgba(212, 175, 55, 0.35)',
              borderRadius: '16px',
              padding: '48px 24px',
              textAlign: 'center',
              backgroundColor: isDragging ? 'rgba(212, 175, 55, 0.08)' : 'rgba(15, 23, 42, 0.5)',
              cursor: disabled || isStreaming ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s ease',
              boxShadow: isDragging ? '0 0 30px rgba(212, 175, 55, 0.2)' : '0 10px 30px rgba(0, 0, 0, 0.3)',
              backdropFilter: 'blur(12px)',
            }}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileInputChange}
              accept=".pdf"
              style={{ display: 'none' }}
              disabled={disabled || isStreaming}
            />

            <div
              style={{
                width: '56px',
                height: '56px',
                borderRadius: '50%',
                background: 'rgba(212, 175, 55, 0.12)',
                border: '1px solid rgba(212, 175, 55, 0.3)',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '16px',
              }}
            >
              <UploadCloud size={28} color="var(--gold-primary)" />
            </div>

            <h3
              style={{
                fontSize: '1.25rem',
                fontFamily: 'var(--font-serif)',
                color: '#F8FAFC',
                letterSpacing: '0.04em',
                margin: '0 0 8px 0',
                fontWeight: 700,
              }}
            >
              {isUploading ? 'Validating Case Record...' : 'UPLOAD CASE PACKET'}
            </h3>

            {isUploading && (
              <div className="upload-scanning-track" aria-label="Validating PDF">
                <div className="upload-scanning-bar" />
              </div>
            )}

            <p style={{ color: '#94A3B8', fontSize: '0.88rem', maxWidth: '420px', margin: '0 auto 16px auto', lineHeight: 1.5 }}>
              Upload the case materials to begin the courtroom simulation.
            </p>

            <span
              style={{
                display: 'inline-block',
                background: 'rgba(212, 175, 55, 0.12)',
                border: '1px solid rgba(212, 175, 55, 0.25)',
                color: 'var(--gold-primary)',
                fontSize: '0.82rem',
                fontWeight: 600,
                padding: '6px 16px',
                borderRadius: '6px',
              }}
            >
              Drag & drop PDF or Browse
            </span>
          </div>

        </div>
      ) : (
        /* Post-Upload Staged Bar */
        <div
          className="animate-verdict-card"
          style={{
            background: 'rgba(15, 23, 42, 0.78)',
            border: '1.5px solid rgba(212, 175, 55, 0.42)',
            borderRadius: '12px',
            padding: '16px 20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '14px',
            backdropFilter: 'blur(12px)',
            boxShadow: '0 8px 28px rgba(0, 0, 0, 0.35), 0 0 20px rgba(212, 175, 55, 0.12)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div
              className="animate-gavel-ring"
              style={{
                padding: '10px',
                borderRadius: '10px',
                background: 'rgba(212, 175, 55, 0.15)',
                border: '1px solid rgba(212, 175, 55, 0.4)',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '3px',
              }}
              title="Case admitted — Bench ready"
            >
              <span className="gavel-hammer-once">
                <Gavel size={22} color="var(--gold-primary)" />
              </span>
              <div className="gavel-block-ripple" style={{ width: '20px' }} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '0.98rem', fontWeight: 600, color: '#F1F5F9' }}>
                  {uploadedCase.filename}
                </span>
                <span
                  style={{
                    fontSize: '0.72rem',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    background: 'rgba(16, 185, 129, 0.15)',
                    color: '#34D399',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  <CheckCircle2 size={12} /> Case packet validated
                </span>
              </div>
              <p style={{ margin: '2px 0 0 0', fontSize: '0.78rem', color: '#94A3B8' }}>
                {uploadedCase.page_count} Pages &bull; {(uploadedCase.file_size / 1024).toFixed(1)} KB &bull;{' '}
                <span style={{ color: 'var(--gold-primary)' }}>Bench Ready to Convene</span>
              </p>
            </div>
          </div>

          <button
            onClick={onStartCourt}
            disabled={isStreaming}
            className="btn-primary"
            style={{
              padding: '10px 24px',
              fontSize: '0.92rem',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            {isStreaming ? (
              <Gavel size={16} className="gavel-hammer-loop" />
            ) : (
              <Play size={16} fill="#070B14" />
            )}
            <span>{isStreaming ? 'Court In Session...' : 'START AI COURT'}</span>
          </button>
        </div>
      )}

      {/* Error Notice */}
      {errorMessage && (
        <div
          style={{
            marginTop: '14px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            background: 'rgba(239, 68, 68, 0.12)',
            border: '1px solid rgba(239, 68, 68, 0.35)',
            borderRadius: '8px',
            padding: '12px 16px',
            color: '#FCA5A5',
            fontSize: '0.84rem',
          }}
        >
          <AlertTriangle size={18} color="#EF4444" style={{ flexShrink: 0 }} />
          <span>{errorMessage}</span>
        </div>
      )}

    </div>
  );
};
