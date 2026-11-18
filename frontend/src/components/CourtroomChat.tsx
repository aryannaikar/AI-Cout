import React, { useEffect, useMemo, useRef } from 'react';
import { Gavel, Award, Scale } from 'lucide-react';
import type { AgentMessage, Judgment, SideResearchContext } from '../types/court';
import { CourtroomChatBubble } from './CourtroomChatBubble';

interface CourtroomChatProps {
  messages: AgentMessage[];
  researchMessages?: AgentMessage[];
  currentAgent: string | null;
  isStreaming: boolean;
  judgment: Judgment | null;
  onOpenJudgment: () => void;
  onOpenComparison?: () => void;
  caseTitle?: string;
}

function parseSourceFileFromCitation(citation?: string): string | undefined {
  if (!citation) return undefined;
  const match = citation.match(/Source:\s*([^\]]+)\]/i);
  return match ? match[1].trim() : undefined;
}

function buildSideResearch(
  side: 'prosecution' | 'defense',
  researchMessages: AgentMessage[],
  caseTitle?: string,
): SideResearchContext | undefined {
  const legalAgent = side === 'prosecution' ? 'prosecutor_legal_research' : 'defense_legal_research';
  const webAgent = side === 'prosecution' ? 'prosecutor_web_research' : 'defense_web_research';

  const legalMsg = [...researchMessages].reverse().find((m) => m.agent === legalAgent);
  const webMsg = [...researchMessages].reverse().find((m) => m.agent === webAgent);

  if (!legalMsg && !webMsg && !caseTitle) return undefined;

  const rawProvisions = Array.isArray(legalMsg?.payload?.provisions) ? legalMsg.payload.provisions : [];
  const provisions = rawProvisions.map((p: any) => ({
    act: p.act || p.act_name || 'Statute',
    short_name: p.short_name,
    section: p.section || p.section_or_article || '',
    title: p.title,
    page: p.page,
    source_file: p.source_file || parseSourceFileFromCitation(p.citation),
    citation: p.citation,
    reasoning: p.reasoning,
  }));

  const rawSources = Array.isArray(webMsg?.payload?.sources) ? webMsg.payload.sources : [];
  const webSources = rawSources.map((s: any) => ({
    title: s.title || 'Judicial Precedent',
    url: s.url,
    summary: s.summary,
  }));

  return {
    side,
    legalResearchAgent: legalMsg
      ? side === 'prosecution'
        ? 'Prosecutor Legal Research (Hybrid RAG)'
        : 'Defense Legal Research (Hybrid RAG)'
      : undefined,
    retrievalMethod: legalMsg?.payload?.retrieval_method,
    provisions,
    webResearchAgent: webMsg
      ? side === 'prosecution'
        ? 'Prosecutor Web Research'
        : 'Defense Web Research'
      : undefined,
    webSources,
    casePacketPdf: caseTitle,
  };
}

export const CourtroomChat: React.FC<CourtroomChatProps> = ({
  messages,
  researchMessages = [],
  currentAgent,
  isStreaming,
  judgment,
  onOpenJudgment,
  onOpenComparison,
  caseTitle,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  const sideResearchBySide = useMemo(() => ({
    prosecution: buildSideResearch('prosecution', researchMessages, caseTitle),
    defense: buildSideResearch('defense', researchMessages, caseTitle),
  }), [researchMessages, caseTitle]);

  // Auto-scroll to newest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentAgent, judgment]);

  // Typing indicator label and side
  const getTypingInfo = (agentName: string) => {
    if (agentName === 'live_prosecutor') {
      return { label: '⚔️ Public Prosecutor is addressing the bench...', align: 'flex-end', color: '#93C5FD' };
    }
    if (agentName === 'live_defense') {
      return { label: '🛡️ Defense Counsel is presenting counter-argument...', align: 'flex-start', color: '#6EE7B7' };
    }
    if (agentName === 'live_evidence') {
      return { label: '🔬 Evidence Analyst is testifying on record...', align: 'center', color: '#D8B4FE' };
    }
    if (agentName === 'live_conflict') {
      return { label: '⚠️ Conflict Detection is addressing the bench...', align: 'center', color: '#FDE68A' };
    }
    if (agentName === 'live_judge') {
      return { label: '👨‍⚖️ Presiding Judge is directing proceedings...', align: 'center', color: 'var(--gold-primary)' };
    }
    if (agentName === 'judge') {
      return { label: '👨‍⚖️ Supreme Bench is delivering final judgment...', align: 'center', color: 'var(--gold-primary)' };
    }
    if (agentName === 'case_understanding') {
      return { label: '📋 Registrar is examining case packet & records...', align: 'center', color: 'var(--gold-primary)' };
    }
    if (['prosecutor', 'defense', 'prosecutor_legal_research', 'prosecutor_web_research', 'defense_legal_research', 'defense_web_research', 'evidence', 'conflict'].includes(agentName)) {
      return { label: '⚖️ Counsel & Research Chamber are preparing case record...', align: 'center', color: '#94A3B8' };
    }
    return null;
  };

  const typingInfo = currentAgent ? getTypingInfo(currentAgent) : null;

  return (
    <div
      style={{
        maxWidth: '1000px',
        width: '100%',
        margin: '0 auto',
        padding: '20px 16px 60px 16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
        minHeight: '600px',
      }}
    >
      {/* Subtle Courtroom Watermark / Session Notice */}
      <div
        style={{
          textAlign: 'center',
          padding: '16px 0 8px 0',
          borderBottom: '1px solid rgba(212, 175, 55, 0.15)',
          marginBottom: '8px',
        }}
      >
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', color: 'var(--gold-primary)', opacity: 0.85 }}>
          <Gavel size={15} />
          <span style={{ fontFamily: 'var(--font-serif)', fontSize: '0.86rem', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            Proceedings in Open Court
          </span>
          <Gavel size={15} />
        </div>
        {caseTitle && (
          <div style={{ fontSize: '0.78rem', color: '#94A3B8', marginTop: '4px' }}>
            Matter: <span style={{ color: '#E2E8F0', fontWeight: 500 }}>{caseTitle}</span>
          </div>
        )}
      </div>

      {/* Main Conversational Stream */}
      {messages.map((msg) => {
        const isProsAgent = msg.agent === 'prosecutor' || msg.agent === 'live_prosecutor';
        const isDefAgent = msg.agent === 'defense' || msg.agent === 'live_defense';
        const sideResearch = isProsAgent
          ? sideResearchBySide.prosecution
          : isDefAgent
            ? sideResearchBySide.defense
            : undefined;
        return (
          <CourtroomChatBubble
            key={msg.id}
            message={msg}
            onOpenJudgment={onOpenJudgment}
            sideResearch={sideResearch}
          />
        );
      })}

      {/* Real-time Typing Indicator */}
      {isStreaming && typingInfo && (
        <div
          style={{
            alignSelf: typingInfo.align as any,
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            background: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '20px',
            padding: '8px 16px',
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
          <span style={{ fontStyle: 'italic' }}>{typingInfo.label}</span>
        </div>
      )}

      {/* Cinematic Judgment Pronouncement Moment */}
      {judgment && (
        <div
          style={{
            alignSelf: 'center',
            width: '100%',
            maxWidth: '560px',
            margin: '28px auto 16px auto',
            textAlign: 'center',
            background: 'linear-gradient(180deg, rgba(30, 24, 12, 0.9) 0%, rgba(12, 16, 26, 0.95) 100%)',
            border: '1.5px solid var(--gold-primary)',
            borderRadius: '16px',
            padding: '32px 24px',
            boxShadow: '0 0 35px rgba(212, 175, 55, 0.25)',
            animation: 'fadeIn 0.5s ease-out forwards',
          }}
        >
          <div
            style={{
              width: '54px',
              height: '54px',
              borderRadius: '50%',
              background: 'rgba(212, 175, 55, 0.18)',
              border: '1px solid var(--gold-primary)',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '16px',
            }}
          >
            <Award size={28} color="var(--gold-primary)" />
          </div>

          <h2
            style={{
              margin: '0 0 4px 0',
              fontFamily: 'var(--font-serif)',
              fontSize: '1.4rem',
              color: 'var(--gold-primary)',
              letterSpacing: '0.08em',
              fontWeight: 800,
            }}
          >
            FINAL AI JUDGMENT
          </h2>

          <div
            style={{
              display: 'inline-block',
              margin: '8px 0 14px 0',
              padding: '4px 14px',
              borderRadius: '6px',
              background: judgment.final_decision?.toUpperCase().includes('CONVICTION')
                ? 'rgba(239, 68, 68, 0.2)'
                : 'rgba(16, 185, 129, 0.2)',
              border: judgment.final_decision?.toUpperCase().includes('CONVICTION')
                ? '1px solid rgba(239, 68, 68, 0.4)'
                : '1px solid rgba(16, 185, 129, 0.4)',
              color: judgment.final_decision?.toUpperCase().includes('CONVICTION')
                ? '#FCA5A5'
                : '#6EE7B7',
              fontWeight: 700,
              fontSize: '0.92rem',
              letterSpacing: '0.05em',
            }}
          >
            {judgment.final_decision}
          </div>

          <p
            style={{
              margin: '0 auto 20px auto',
              fontSize: '0.86rem',
              color: '#CBD5E1',
              maxWidth: '420px',
              lineHeight: 1.5,
            }}
          >
            The Supreme AI Bench has completed its independent deliberation across all framed charges and evidentiary submissions.
          </p>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '14px', flexWrap: 'wrap' }}>
            <button
              onClick={onOpenJudgment}
              style={{
                background: 'linear-gradient(135deg, var(--gold-primary) 0%, #B8860B 100%)',
                color: '#0A0E17',
                border: 'none',
                borderRadius: '8px',
                padding: '12px 28px',
                fontSize: '0.94rem',
                fontFamily: 'var(--font-serif)',
                fontWeight: 700,
                cursor: 'pointer',
                boxShadow: '0 0 20px rgba(212, 175, 55, 0.4)',
                transition: 'transform 0.15s ease, box-shadow 0.15s ease',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-1px)';
                e.currentTarget.style.boxShadow = '0 0 28px rgba(212, 175, 55, 0.6)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 0 20px rgba(212, 175, 55, 0.4)';
              }}
            >
              <Gavel size={18} />
              <span>VIEW JUDGMENT</span>
            </button>

            {judgment && onOpenComparison && (
              <button
                onClick={onOpenComparison}
                style={{
                  background: 'rgba(212, 175, 55, 0.15)',
                  color: 'var(--gold-primary)',
                  border: '1.5px solid var(--gold-primary)',
                  borderRadius: '8px',
                  padding: '12px 28px',
                  fontSize: '0.94rem',
                  fontFamily: 'var(--font-serif)',
                  fontWeight: 700,
                  cursor: 'pointer',
                  boxShadow: '0 0 16px rgba(212, 175, 55, 0.25)',
                  transition: 'transform 0.15s ease, background 0.15s ease, box-shadow 0.15s ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-1px)';
                  e.currentTarget.style.background = 'rgba(212, 175, 55, 0.25)';
                  e.currentTarget.style.boxShadow = '0 0 24px rgba(212, 175, 55, 0.45)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.background = 'rgba(212, 175, 55, 0.15)';
                  e.currentTarget.style.boxShadow = '0 0 16px rgba(212, 175, 55, 0.25)';
                }}
                title="Upload authoritative Real Court Judgment to run 10-dimensional comparison"
              >
                <Scale size={18} />
                <span>COMPARE REAL JUDGMENT</span>
              </button>
            )}
          </div>
        </div>
      )}

      {!judgment && !isStreaming && messages.some((message) => message.agent === 'judge') && (
        <div style={{ alignSelf: 'center', width: '100%', maxWidth: '560px', padding: '18px 22px', borderRadius: '12px', border: '1px solid rgba(248, 113, 113, 0.45)', background: 'rgba(127, 29, 29, 0.16)', color: '#FCA5A5', textAlign: 'center' }}>
          The judge did not return a final judgment. Review the error above and rerun the case after resolving it.
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
};
