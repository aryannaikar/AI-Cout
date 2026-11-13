import React, { useEffect, useRef } from 'react';
import { Gavel, Activity, Award } from 'lucide-react';
import type { AgentMessage, Judgment } from '../types/court';
import { AgentMessageCard } from './AgentMessageCard';
import { CourtroomTimeline } from './CourtroomTimeline';

interface CourtroomStreamProps {
  messages: AgentMessage[];
  currentAgent: string | null;
  isStreaming: boolean;
  judgment: Judgment | null;
  onOpenJudgment: () => void;
}

export const CourtroomStream: React.FC<CourtroomStreamProps> = ({
  messages,
  currentAgent,
  isStreaming,
  judgment,
  onOpenJudgment,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom as new agent arguments appear
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentAgent]);

  return (
    <div style={{ margin: '0 20px 24px 20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      
      {/* 10-Node Subtle Courtroom Execution Timeline */}
      <CourtroomTimeline
        messages={messages}
        currentAgent={currentAgent}
        isStreaming={isStreaming}
      />

      {/* Operative Judgment Available Banner */}
      {judgment && (
        <div
          onClick={onOpenJudgment}
          className="glass-panel-court pulse-gold"
          style={{
            padding: '16px 24px',
            background: 'linear-gradient(90deg, rgba(212, 175, 55, 0.18) 0%, rgba(184, 134, 11, 0.1) 100%)',
            border: '1.5px solid var(--gold-primary)',
            borderRadius: '10px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{ padding: '10px', borderRadius: '8px', background: 'rgba(212, 175, 55, 0.25)' }}>
              <Award size={26} color="var(--gold-primary)" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h3 style={{ margin: 0, fontSize: '1.15rem', color: 'var(--gold-primary)', fontWeight: 700 }}>
                  JUDGMENT PRONOUNCED BY THE SUPREME BENCH
                </h3>
                <span style={{
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontSize: '0.78rem',
                  fontWeight: 700,
                  background: judgment.final_decision?.includes('CONVICTION') ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                  color: judgment.final_decision?.includes('CONVICTION') ? '#F87171' : '#34D399',
                  border: judgment.final_decision?.includes('CONVICTION') ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid rgba(16, 185, 129, 0.4)'
                }}>
                  {judgment.final_decision || 'CONCLUDED'}
                </span>
              </div>
              <p style={{ margin: '4px 0 0 0', fontSize: '0.82rem', color: '#CBD5E1' }}>
                The complete 12-section judicial decree is ready. Click to review full ratio decidendi and download certified decree.
              </p>
            </div>
          </div>

          <button className="btn-primary" style={{ padding: '8px 18px', fontSize: '0.88rem' }}>
            <Gavel size={15} />
            <span>Open Decree</span>
          </button>
        </div>
      )}

      {/* Main Debate Transcript Stream */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {messages.map((msg, index) => (
          <AgentMessageCard
            key={msg.id || index}
            message={msg}
            isLatest={index === messages.length - 1}
            onOpenJudgment={onOpenJudgment}
          />
        ))}

        {/* Live Active Agent Indicator */}
        {isStreaming && currentAgent && (
          <div
            className="glass-panel"
            style={{
              padding: '14px 20px',
              border: '1px dashed var(--gold-primary)',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              background: 'rgba(212, 175, 55, 0.05)',
            }}
          >
            <div className="pulse-gold" style={{ padding: '6px', borderRadius: '50%', background: 'rgba(212, 175, 55, 0.2)' }}>
              <Activity size={18} color="var(--gold-primary)" />
            </div>
            <div>
              <span style={{ fontSize: '0.88rem', color: 'var(--gold-primary)', fontWeight: 600 }}>
                {currentAgent.replace(/_/g, ' ').toUpperCase()} IN CHAMBERS...
              </span>
              <p style={{ margin: 0, fontSize: '0.78rem', color: '#94A3B8' }}>
                Deliberating submissions and legal authorities under statutory framework
              </p>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

    </div>
  );
};
