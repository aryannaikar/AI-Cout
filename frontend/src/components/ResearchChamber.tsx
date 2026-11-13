import React, { useEffect, useRef } from 'react';
import { Search } from 'lucide-react';
import type { AgentMessage } from '../types/court';
import { CourtroomChatBubble } from './CourtroomChatBubble';

interface ResearchChamberProps {
  messages: AgentMessage[];
  currentAgent: string | null;
  isStreaming: boolean;
}

export const ResearchChamber: React.FC<ResearchChamberProps> = ({
  messages,
  currentAgent,
  isStreaming,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

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
      style={{
        background: 'rgba(10, 15, 26, 0.4)',
        border: '1px solid rgba(255, 255, 255, 0.05)',
        borderRadius: '12px',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        height: '100%',
        maxHeight: '800px',
        overflowY: 'auto',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          color: '#94A3B8',
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
          paddingBottom: '12px',
          marginBottom: '8px',
        }}
      >
        <Search size={18} />
        <span style={{ fontFamily: 'var(--font-serif)', fontSize: '0.9rem', letterSpacing: '0.05em', fontWeight: 600 }}>
          RESEARCH CHAMBER
        </span>
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {messages.length === 0 && !typingInfo && (
          <div style={{ textAlign: 'center', color: '#64748B', fontSize: '0.85rem', marginTop: '20px' }}>
            No active research queries.
          </div>
        )}

        {messages.map((msg) => (
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
