import React, { useState } from 'react';
import { Code2, ChevronDown, ChevronUp, Copy, Check } from 'lucide-react';

interface RawDataCollapsibleProps {
  data: any;
  label?: string;
}

export const RawDataCollapsible: React.FC<RawDataCollapsibleProps> = ({
  data,
  label = 'View structured data',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  if (!data || (typeof data === 'object' && Object.keys(data).length === 0)) {
    return null;
  }

  const jsonString = typeof data === 'string' ? data : JSON.stringify(data, null, 2);

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div style={{ marginTop: '14px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '10px' }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          background: 'transparent',
          border: 'none',
          color: '#94A3B8',
          fontSize: '0.78rem',
          cursor: 'pointer',
          padding: '4px 8px',
          borderRadius: '4px',
          transition: 'all 0.15s ease',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.color = '#E2E8F0';
          e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.color = '#94A3B8';
          e.currentTarget.style.background = 'transparent';
        }}
        title="Toggle machine-readable structured JSON"
      >
        <Code2 size={13} />
        <span>{label}</span>
        {isOpen ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
      </button>

      {isOpen && (
        <div
          style={{
            marginTop: '8px',
            background: 'rgba(10, 14, 23, 0.85)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '8px',
            padding: '12px',
            position: 'relative',
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '8px',
              borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
              paddingBottom: '6px',
            }}
          >
            <span style={{ fontSize: '0.72rem', color: '#64748B', fontFamily: 'monospace' }}>
              SOURCE PAYLOAD JSON
            </span>
            <button
              onClick={handleCopy}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                background: 'rgba(255, 255, 255, 0.06)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                color: copied ? '#10B981' : '#CBD5E1',
                borderRadius: '4px',
                padding: '2px 8px',
                fontSize: '0.72rem',
                cursor: 'pointer',
              }}
            >
              {copied ? <Check size={12} /> : <Copy size={12} />}
              <span>{copied ? 'Copied' : 'Copy JSON'}</span>
            </button>
          </div>
          <pre
            style={{
              margin: 0,
              fontSize: '0.78rem',
              color: '#A5B4FC',
              fontFamily: 'Consolas, Monaco, monospace',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              maxHeight: '320px',
              overflowY: 'auto',
              lineHeight: 1.45,
            }}
          >
            {jsonString}
          </pre>
        </div>
      )}
    </div>
  );
};
