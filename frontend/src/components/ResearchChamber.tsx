import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Search } from 'lucide-react';
import type { AgentMessage } from '../types/court';
import { CourtroomChatBubble } from './CourtroomChatBubble';

interface ResearchChamberProps {
  messages: AgentMessage[];
  currentAgent: string | null;
  isStreaming: boolean;
}

type ResearchFilter = 'all' | 'statutes' | 'web' | 'forensics';

export const ResearchChamber: React.FC<ResearchChamberProps> = ({
  messages,
  currentAgent,
  isStreaming,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [filter, setFilter] = useState<ResearchFilter>('all');

  const filteredMessages = useMemo(() => {
    if (filter === 'all') return messages;
    if (filter === 'statutes') return messages.filter((m) => m.agent.includes('legal_research'));
    if (filter === 'web') return messages.filter((m) => m.agent.includes('web_research'));
    return messages.filter((m) => m.agent === 'evidence' || m.agent === 'conflict');
  }, [messages, filter]);

  // Auto-scroll to newest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentAgent]);

  // Typing indicator label for research agents
  const getTypingInfo = (agentName: string) => {
    if (agentName === 'prosecutor_legal_research') {
      return { label: 'Prosecution Legal Research is querying BNS corpus...', color: '#93C5FD' };
    }
    if (agentName === 'prosecutor_web_research') {
      return { label: 'Prosecution Web Research is searching precedents...', color: '#93C5FD' };
    }
    if (agentName === 'defense_legal_research') {
      return { label: 'Defense Legal Research is analyzing statutory elements...', color: '#6EE7B7' };
    }
    if (agentName === 'defense_web_research') {
      return { label: 'Defense Web Research is reviewing judicial rulings...', color: '#6EE7B7' };
    }
    if (agentName === 'evidence') {
      return { label: 'Forensic appraisal of exhibits & chain of custody...', color: '#D8B4FE' };
    }
    if (agentName === 'conflict') {
      return { label: 'Analyzing contradictions between statements & exhibits...', color: '#FDE68A' };
    }
    return null;
  };

  const typingInfo = currentAgent ? getTypingInfo(currentAgent) : null;

  return (
    <div
      className="research-chamber-sticky"
      style={{
        background: 'rgba(10, 15, 26, 0.55)',
        border: '1px solid rgba(212, 175, 55, 0.16)',
        borderRadius: '12px',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '14px',
        height: '100%',
        overflowY: 'auto',
        backdropFilter: 'blur(12px)',
      }}
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          paddingBottom: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--gold-primary)' }}>
            <Search size={17} />
            <span style={{ fontFamily: 'var(--font-serif)', fontSize: '0.88rem', letterSpacing: '0.06em', fontWeight: 700 }}>
              RESEARCH CHAMBER
            </span>
          </div>
          {messages.length > 0 && (
            <span
              style={{
                fontSize: '0.7rem',
                fontWeight: 600,
                color: '#CBD5E1',
                background: 'rgba(255, 255, 255, 0.07)',
                padding: '2px 8px',
                borderRadius: '999px',
              }}
            >
              {messages.length}
            </span>
          )}
        </div>

        {/* Category Filter Pills */}
        {messages.length > 0 && (
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {([
              { id: 'all', label: 'All' },
              { id: 'statutes', label: 'Statutes' },
              { id: 'web', label: 'Precedents' },
              { id: 'forensics', label: 'Forensics' },
            ] as const).map((tab) => {
              const active = filter === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setFilter(tab.id)}
                  style={{
                    fontSize: '0.72rem',
                    fontWeight: active ? 600 : 500,
                    padding: '3px 9px',
                    borderRadius: '999px',
                    cursor: 'pointer',
                    border: active ? '1px solid rgba(212, 175, 55, 0.55)' : '1px solid rgba(255, 255, 255, 0.08)',
                    background: active ? 'rgba(212, 175, 55, 0.16)' : 'rgba(15, 23, 42, 0.5)',
                    color: active ? 'var(--gold-primary)' : '#94A3B8',
                    transition: 'all 0.15s ease',
                  }}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>
        )}
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {filteredMessages.length === 0 && !typingInfo && (
          <div style={{ textAlign: 'center', color: '#64748B', fontSize: '0.84rem', marginTop: '20px' }}>
            {messages.length === 0 ? 'No active research queries.' : 'No entries match this filter.'}
          </div>
        )}

        {filteredMessages.map((msg) => (
          <CourtroomChatBubble key={msg.id} message={msg} />
        ))}

        {isStreaming && typingInfo && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '8px',
              padding: '10px 12px',
              fontSize: '0.8rem',
              color: typingInfo.color,
              animation: 'fadeIn 0.2s ease-out',
            }}
          >
            <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  background: typingInfo.color,
                  display: 'inline-block',
                  animation: 'pulseGlow 1.2s infinite ease-in-out',
                }}
              />
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  background: typingInfo.color,
                  display: 'inline-block',
                  animation: 'pulseGlow 1.2s infinite ease-in-out 0.2s',
                }}
              />
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  background: typingInfo.color,
                  display: 'inline-block',
                  animation: 'pulseGlow 1.2s infinite ease-in-out 0.4s',
                }}
              />
            </div>
            <span style={{ fontStyle: 'italic', fontSize: '0.75rem' }}>{typingInfo.label}</span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
};
