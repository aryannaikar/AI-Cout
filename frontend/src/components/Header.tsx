import React, { useState, useRef, useEffect } from 'react';
import { 
  Scale, 
  RefreshCw, 
  Download, 
  ChevronDown, 
  Check, 
  FileText, 
  FileCode, 
  Printer 
} from 'lucide-react';
import type { AgentMessage, Judgment } from '../types/court';
import { downloadCourtRecord } from '../utils/exportCourtRecord';

interface HeaderProps {
  caseTitle?: string | null;
  caseId?: string | null;
  status: 'READY' | 'IN_SESSION' | 'COMPLETED' | 'STANDBY';
  onResetSession: () => void;
  isStreaming: boolean;
  messages?: AgentMessage[];
  judgment?: Judgment | null;
  onOpenComparison?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  caseTitle,
  caseId,
  status,
  onResetSession,
  isStreaming,
  messages = [],
  judgment = null,
  onOpenComparison,
}) => {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [downloaded, setDownloaded] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const hasContent = (messages && messages.length > 0) || Boolean(judgment);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    if (isDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isDropdownOpen]);

  const handleDownload = (format: 'txt' | 'md' | 'json' | 'print' = 'txt') => {
    if (!hasContent) return;
    downloadCourtRecord(format, {
      caseTitle,
      caseId,
      status,
      messages,
      judgment,
    });
    setIsDropdownOpen(false);
    setDownloaded(true);
    setTimeout(() => setDownloaded(false), 2200);
  };

  // Compute status pill
  const renderStatusPill = () => {
    switch (status) {
      case 'IN_SESSION':
        return (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '5px 12px',
              borderRadius: '20px',
              background: 'rgba(212, 175, 55, 0.12)',
              border: '1px solid var(--gold-primary)',
              fontSize: '0.76rem',
              fontWeight: 700,
              color: 'var(--gold-primary)',
              letterSpacing: '0.04em',
            }}
          >
            <span
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                background: 'var(--gold-primary)',
                display: 'inline-block',
              }}
              className="pulse-gold"
            />
            <span>● IN SESSION</span>
          </div>
        );
      case 'COMPLETED':
        return (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '5px 12px',
              borderRadius: '20px',
              background: 'rgba(16, 185, 129, 0.12)',
              border: '1px solid #10B981',
              fontSize: '0.76rem',
              fontWeight: 700,
              color: '#34D399',
              letterSpacing: '0.04em',
            }}
          >
            <span>✓ JUDGMENT READY</span>
          </div>
        );
      case 'READY':
        return (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '5px 12px',
              borderRadius: '20px',
              background: 'rgba(59, 130, 246, 0.12)',
              border: '1px solid rgba(59, 130, 246, 0.4)',
              fontSize: '0.76rem',
              fontWeight: 600,
              color: '#93C5FD',
              letterSpacing: '0.04em',
            }}
          >
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#3B82F6', display: 'inline-block' }} />
            <span>COURT READY</span>
          </div>
        );
      default:
        return (
          <div
            style={{
              padding: '4px 10px',
              borderRadius: '20px',
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              fontSize: '0.74rem',
              color: '#94A3B8',
            }}
          >
            STANDBY
          </div>
        );
    }
  };

  const dropdownItemStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '8px 12px',
    background: 'transparent',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    width: '100%',
    textAlign: 'left',
    transition: 'background 0.15s ease',
  };

  return (
    <header
      style={{
        background: 'linear-gradient(180deg, rgba(16, 21, 32, 0.95) 0%, rgba(10, 14, 23, 0.9) 100%)',
        borderBottom: '1px solid rgba(212, 175, 55, 0.2)',
        padding: '14px 24px',
        position: 'sticky',
        top: 0,
        zIndex: 40,
        backdropFilter: 'blur(16px)',
      }}
    >
      <div
        style={{
          maxWidth: '1200px',
          margin: '0 auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        {/* Left: Emblem & Court Title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, rgba(212, 175, 55, 0.2) 0%, rgba(184, 134, 11, 0.1) 100%)',
              border: '1px solid var(--gold-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 12px rgba(212, 175, 55, 0.2)',
            }}
          >
            <Scale size={20} color="var(--gold-primary)" />
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h1
                style={{
                  fontSize: '1.2rem',
                  fontWeight: 800,
                  color: 'var(--gold-primary)',
                  margin: 0,
                  fontFamily: 'var(--font-serif)',
                  letterSpacing: '0.06em',
                }}
              >
                AI COURT OF INDIA
              </h1>
              <span
                style={{
                  fontSize: '0.62rem',
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  padding: '2px 6px',
                  borderRadius: '3px',
                  background: 'rgba(212, 175, 55, 0.12)',
                  color: 'var(--gold-primary)',
                  border: '1px solid rgba(212, 175, 55, 0.25)',
                  fontWeight: 700,
                }}
              >
                SUPREME BENCH
              </span>
            </div>

            {caseTitle && (
              <p style={{ margin: '2px 0 0 0', fontSize: '0.78rem', color: '#94A3B8' }}>
                Case: <span style={{ color: '#E2E8F0', fontWeight: 500 }}>{caseTitle}</span>
              </p>
            )}
          </div>
        </div>

        {/* Right: Actions (Status Pill, Download Button, New Case Reset) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          {renderStatusPill()}

          {/* Unified Download Chat & Verdict Button Group */}
          <div ref={dropdownRef} style={{ position: 'relative', display: 'flex' }}>
            {/* Primary Download Button: 1-click downloads complete Chat + Verdict */}
            <button
              onClick={() => handleDownload('txt')}
              disabled={!hasContent}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '7px',
                padding: '6px 13px',
                borderRadius: '6px 0 0 6px',
                background: hasContent
                  ? judgment
                    ? 'linear-gradient(135deg, rgba(212, 175, 55, 0.25) 0%, rgba(184, 134, 11, 0.15) 100%)'
                    : 'rgba(212, 175, 55, 0.12)'
                  : 'rgba(255, 255, 255, 0.03)',
                border: hasContent ? '1px solid var(--gold-primary)' : '1px solid rgba(255, 255, 255, 0.1)',
                borderRight: hasContent ? '1px solid rgba(212, 175, 55, 0.4)' : 'none',
                color: hasContent ? 'var(--gold-primary)' : '#64748B',
                fontWeight: 600,
                fontSize: '0.78rem',
                cursor: hasContent ? 'pointer' : 'not-allowed',
                transition: 'all 0.15s ease',
                boxShadow: hasContent && judgment ? '0 0 14px rgba(212, 175, 55, 0.25)' : 'none',
              }}
              title={
                hasContent
                  ? 'Click to download entire courtroom chat and verdict in a single file'
                  : 'Download will be available once courtroom proceedings begin'
              }
              onMouseEnter={(e) => {
                if (hasContent) {
                  e.currentTarget.style.background = 'rgba(212, 175, 55, 0.28)';
                  e.currentTarget.style.boxShadow = '0 0 16px rgba(212, 175, 55, 0.4)';
                }
              }}
              onMouseLeave={(e) => {
                if (hasContent) {
                  e.currentTarget.style.background = judgment
                    ? 'linear-gradient(135deg, rgba(212, 175, 55, 0.25) 0%, rgba(184, 134, 11, 0.15) 100%)'
                    : 'rgba(212, 175, 55, 0.12)';
                  e.currentTarget.style.boxShadow = judgment ? '0 0 14px rgba(212, 175, 55, 0.25)' : 'none';
                }
              }}
            >
              {downloaded ? (
                <>
                  <Check size={14} color="#34D399" />
                  <span style={{ color: '#34D399' }}>Downloaded!</span>
                </>
              ) : (
                <>
                  <Download size={14} color={hasContent ? 'var(--gold-primary)' : '#64748B'} />
                  <span>Download Chat & Verdict</span>
                </>
              )}
            </button>

            {/* Caret Button for format options */}
            <button
              onClick={() => hasContent && setIsDropdownOpen(!isDropdownOpen)}
              disabled={!hasContent}
              style={{
                padding: '6px 8px',
                borderRadius: '0 6px 6px 0',
                background: hasContent
                  ? judgment
                    ? 'linear-gradient(135deg, rgba(212, 175, 55, 0.25) 0%, rgba(184, 134, 11, 0.15) 100%)'
                    : 'rgba(212, 175, 55, 0.12)'
                  : 'rgba(255, 255, 255, 0.03)',
                border: hasContent ? '1px solid var(--gold-primary)' : '1px solid rgba(255, 255, 255, 0.1)',
                borderLeft: 'none',
                color: hasContent ? 'var(--gold-primary)' : '#64748B',
                cursor: hasContent ? 'pointer' : 'not-allowed',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.15s ease',
              }}
              title="Choose download format (.txt, .md, .json, Print/PDF)"
              onMouseEnter={(e) => {
                if (hasContent) e.currentTarget.style.background = 'rgba(212, 175, 55, 0.28)';
              }}
              onMouseLeave={(e) => {
                if (hasContent) {
                  e.currentTarget.style.background = judgment
                    ? 'linear-gradient(135deg, rgba(212, 175, 55, 0.25) 0%, rgba(184, 134, 11, 0.15) 100%)'
                    : 'rgba(212, 175, 55, 0.12)';
                }
              }}
            >
              <ChevronDown
                size={12}
                style={{
                  transform: isDropdownOpen ? 'rotate(180deg)' : 'none',
                  transition: 'transform 0.15s ease',
                }}
              />
            </button>

            {/* Dropdown Menu for Format Options */}
            {isDropdownOpen && (
              <div
                style={{
                  position: 'absolute',
                  top: 'calc(100% + 6px)',
                  right: 0,
                  background: '#0B1120',
                  border: '1px solid var(--gold-primary)',
                  borderRadius: '8px',
                  boxShadow: '0 12px 35px rgba(0, 0, 0, 0.75), 0 0 20px rgba(212, 175, 55, 0.2)',
                  zIndex: 100,
                  minWidth: '235px',
                  overflow: 'hidden',
                  padding: '5px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '3px',
                  animation: 'fadeIn 0.15s ease-out',
                }}
              >
                <div
                  style={{
                    padding: '6px 10px',
                    fontSize: '0.67rem',
                    fontWeight: 700,
                    color: 'var(--gold-primary)',
                    letterSpacing: '0.06em',
                    textTransform: 'uppercase',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                    marginBottom: '2px',
                  }}
                >
                  Download Chat & Verdict
                </div>

                <button
                  onClick={() => handleDownload('txt')}
                  style={dropdownItemStyle}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(212, 175, 55, 0.15)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <FileText size={15} color="var(--gold-primary)" />
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ fontWeight: 600, color: '#F1F5F9', fontSize: '0.79rem' }}>
                      Plain Text (.txt) <span style={{ fontSize: '0.65rem', color: 'var(--gold-primary)' }}>[Default]</span>
                    </span>
                    <span style={{ fontSize: '0.68rem', color: '#94A3B8' }}>
                      Full courtroom chat & 12-section verdict
                    </span>
                  </div>
                </button>

                <button
                  onClick={() => handleDownload('md')}
                  style={dropdownItemStyle}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(59, 130, 246, 0.15)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <FileText size={15} color="#60A5FA" />
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ fontWeight: 600, color: '#F1F5F9', fontSize: '0.79rem' }}>
                      Markdown (.md)
                    </span>
                    <span style={{ fontSize: '0.68rem', color: '#94A3B8' }}>
                      Formatted headings, quotes & tables
                    </span>
                  </div>
                </button>

                <button
                  onClick={() => handleDownload('json')}
                  style={dropdownItemStyle}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(167, 139, 250, 0.15)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <FileCode size={15} color="#A78BFA" />
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ fontWeight: 600, color: '#F1F5F9', fontSize: '0.79rem' }}>
                      Structured JSON (.json)
                    </span>
                    <span style={{ fontSize: '0.68rem', color: '#94A3B8' }}>
                      Machine-readable case archive
                    </span>
                  </div>
                </button>

                <button
                  onClick={() => handleDownload('print')}
                  style={dropdownItemStyle}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(16, 185, 129, 0.15)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <Printer size={15} color="#34D399" />
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ fontWeight: 600, color: '#F1F5F9', fontSize: '0.79rem' }}>
                      Print / Save as PDF
                    </span>
                    <span style={{ fontSize: '0.68rem', color: '#94A3B8' }}>
                      Official printable tribunal decree
                    </span>
                  </div>
                </button>
              </div>
            )}
          </div>

          {/* Real Judgment Comparison Button (Available once verdict is reached) */}
          {onOpenComparison && (status === 'COMPLETED' || judgment) && (
            <button
              onClick={onOpenComparison}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 14px',
                borderRadius: '6px',
                background: 'linear-gradient(135deg, rgba(212, 175, 55, 0.25) 0%, rgba(184, 134, 11, 0.15) 100%)',
                border: '1px solid var(--gold-primary)',
                color: 'var(--gold-primary)',
                fontWeight: 700,
                fontSize: '0.78rem',
                cursor: 'pointer',
                boxShadow: '0 0 14px rgba(212, 175, 55, 0.25)',
                transition: 'all 0.15s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(212, 175, 55, 0.32)';
                e.currentTarget.style.boxShadow = '0 0 20px rgba(212, 175, 55, 0.45)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'linear-gradient(135deg, rgba(212, 175, 55, 0.25) 0%, rgba(184, 134, 11, 0.15) 100%)';
                e.currentTarget.style.boxShadow = '0 0 14px rgba(212, 175, 55, 0.25)';
              }}
              title="Upload authoritative Real Court Judgment to benchmark against the AI verdict"
            >
              <Scale size={14} color="var(--gold-primary)" />
              <span>Compare Real Judgment</span>
            </button>
          )}

          {/* New Case Reset Button */}
          {caseTitle && (
            <button
              onClick={onResetSession}
              disabled={isStreaming}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                color: '#CBD5E1',
                padding: '6px 12px',
                borderRadius: '6px',
                fontSize: '0.78rem',
                cursor: isStreaming ? 'not-allowed' : 'pointer',
                opacity: isStreaming ? 0.5 : 1,
                transition: 'all 0.15s ease',
              }}
              title="Reset session and load new case"
              onMouseEnter={(e) => {
                if (!isStreaming) e.currentTarget.style.borderColor = 'var(--gold-primary)';
              }}
              onMouseLeave={(e) => {
                if (!isStreaming) e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.12)';
              }}
            >
              <RefreshCw size={13} />
              <span>New Case</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
