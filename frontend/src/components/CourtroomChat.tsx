import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Gavel, Award, Scale, ArrowDown, Check } from 'lucide-react';
import type { AgentMessage, Judgment, SideResearchContext } from '../types/court';
import { CourtroomChatBubble } from './CourtroomChatBubble';
import { CourtroomStage } from './CourtroomStage';
import { resolvePrecedentUrl } from '../utils/courtroomChatFormatters';

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
    url: resolvePrecedentUrl(s.url, s.title),
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
  const [showJumpButton, setShowJumpButton] = useState(false);
  const [sideFilter, setSideFilter] = useState<'all' | 'bench' | 'prosecution' | 'defense'>('all');
  const isNearBottomRef = useRef(true);

  const visibleMessages = useMemo(() => {
    if (sideFilter === 'all') return messages;
    if (sideFilter === 'prosecution') {
      return messages.filter((m) => m.agent === 'prosecutor' || m.agent === 'live_prosecutor');
    }
    if (sideFilter === 'defense') {
      return messages.filter((m) => m.agent === 'defense' || m.agent === 'live_defense');
    }
    return messages.filter(
      (m) =>
        m.agent === 'live_judge' ||
        m.agent === 'judge' ||
        m.agent === 'case_understanding' ||
        m.agent === 'live_evidence' ||
        m.agent === 'live_conflict',
    );
  }, [messages, sideFilter]);

  const sideResearchBySide = useMemo(() => ({
    prosecution: buildSideResearch('prosecution', researchMessages, caseTitle),
    defense: buildSideResearch('defense', researchMessages, caseTitle),
  }), [researchMessages, caseTitle]);

  // Track scroll position so we don't yank users reading earlier arguments
  useEffect(() => {
    const handleScroll = () => {
      const distanceFromBottom =
        document.documentElement.scrollHeight - (window.scrollY + window.innerHeight);
      const nearBottom = distanceFromBottom < 220;
      isNearBottomRef.current = nearBottom;
      setShowJumpButton(!nearBottom && (messages.length > 1 || isStreaming));
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [messages.length, isStreaming]);

  // Auto-scroll to newest message only when user is near bottom
  useEffect(() => {
    if (isNearBottomRef.current) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, currentAgent, judgment]);

  const scrollToLatest = () => {
    isNearBottomRef.current = true;
    setShowJumpButton(false);
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Derive 6-stage Hearing Lifecycle Stepper from existing messages & currentAgent
  const hearingStages = useMemo(() => {
    const allAgents = new Set([
      ...messages.map((m) => m.agent),
      ...researchMessages.map((m) => m.agent),
    ]);
    const stages = [
      {
        id: 'admission',
        label: 'Case Admission',
        agents: ['case_understanding'],
      },
      {
        id: 'research',
        label: 'Legal Research',
        agents: [
          'prosecutor_legal_research',
          'prosecutor_web_research',
          'defense_legal_research',
          'defense_web_research',
          'evidence',
          'conflict',
        ],
      },
      {
        id: 'prosecution',
        label: 'Prosecution',
        agents: ['live_prosecutor', 'prosecutor'],
      },
      {
        id: 'defense',
        label: 'Defense',
        agents: ['live_defense', 'defense'],
      },
      {
        id: 'bench',
        label: 'Bench & Forensics',
        agents: ['live_judge', 'live_evidence', 'live_conflict'],
      },
      {
        id: 'order',
        label: 'Final Order',
        agents: ['judge'],
      },
    ];

    return stages.map((stage) => {
      const isDone =
        (stage.id === 'order' && Boolean(judgment)) ||
        stage.agents.some((a) => allAgents.has(a));
      const isActive = Boolean(currentAgent && stage.agents.includes(currentAgent));
      return {
        ...stage,
        status: isActive ? 'active' : isDone ? 'done' : 'pending',
      };
    });
  }, [messages, researchMessages, currentAgent, judgment]);

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

  const activeStageIdx = hearingStages.findIndex((s) => s.status === 'active');
  const lastDoneIdx = hearingStages.reduce(
    (acc, s, idx) => (s.status === 'done' ? idx : acc),
    0,
  );
  const resolvedStageIdx = activeStageIdx >= 0 ? activeStageIdx : lastDoneIdx;
  const activeStageLabel = hearingStages[resolvedStageIdx]?.label || 'Case Admission';

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
      {/* Interactive 3-Bench Courtroom Stage */}
      <CourtroomStage
        currentAgent={currentAgent}
        isStreaming={isStreaming}
        judgment={judgment}
        activeStageIndex={resolvedStageIdx + 1}
        totalStages={hearingStages.length}
        activeStageLabel={activeStageLabel}
      />

      {/* Hearing Lifecycle Stepper */}
      <div
        className="glass-panel"
        style={{
          padding: '10px 14px',
          overflowX: 'auto',
          borderColor: 'rgba(212, 175, 55, 0.18)',
        }}
        aria-label="Hearing stages"
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '6px',
            minWidth: '640px',
          }}
        >
          {hearingStages.map((stage, idx) => {
            const isActive = stage.status === 'active';
            const isDone = stage.status === 'done';
            return (
              <React.Fragment key={stage.id}>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '4px 10px',
                    borderRadius: '999px',
                    background: isActive
                      ? 'rgba(212, 175, 55, 0.16)'
                      : isDone
                        ? 'rgba(16, 185, 129, 0.1)'
                        : 'rgba(255, 255, 255, 0.03)',
                    border: isActive
                      ? '1px solid rgba(212, 175, 55, 0.65)'
                      : isDone
                        ? '1px solid rgba(16, 185, 129, 0.3)'
                        : '1px solid rgba(255, 255, 255, 0.06)',
                    transition: 'all 0.2s ease',
                  }}
                >
                  <span
                    style={{
                      width: '16px',
                      height: '16px',
                      borderRadius: '50%',
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '0.68rem',
                      fontWeight: 700,
                      background: isActive
                        ? 'rgba(212, 175, 55, 0.25)'
                        : isDone
                          ? 'rgba(16, 185, 129, 0.22)'
                          : 'rgba(148, 163, 184, 0.12)',
                      color: isActive ? 'var(--gold-primary)' : isDone ? '#34D399' : '#64748B',
                    }}
                  >
                    {isDone && !isActive ? <Check size={10} strokeWidth={3} /> : idx + 1}
                  </span>
                  <span
                    style={{
                      fontSize: '0.74rem',
                      fontWeight: isActive ? 700 : isDone ? 600 : 400,
                      color: isActive ? 'var(--gold-primary)' : isDone ? '#E2E8F0' : '#94A3B8',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {stage.label}
                  </span>
                </div>
                {idx < hearingStages.length - 1 && (
                  <div
                    className={isStreaming && isActive ? 'stepper-connector-active' : undefined}
                    style={{
                      flex: 1,
                      height: isStreaming && isActive ? '2px' : '1px',
                      minWidth: '10px',
                      borderRadius: '999px',
                      background: isDone
                        ? 'rgba(16, 185, 129, 0.35)'
                        : 'rgba(255, 255, 255, 0.08)',
                    }}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Subtle Courtroom Watermark / Session Notice */}
      <div
        style={{
          textAlign: 'center',
          padding: '12px 0 10px 0',
          borderBottom: '1px solid rgba(212, 175, 55, 0.15)',
          marginBottom: '4px',
        }}
      >
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', color: 'var(--gold-primary)', opacity: 0.9 }}>
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
        {/* Spatial Bench Orientation Legend */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            gap: '16px',
            flexWrap: 'wrap',
            marginTop: '10px',
            fontSize: '0.72rem',
            color: '#94A3B8',
          }}
        >
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: '#10B981' }} />
            Defense Counsel (Left)
          </span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: 'var(--gold-primary)' }} />
            Supreme Bench (Center)
          </span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: '#3B82F6' }} />
            Public Prosecutor (Right)
          </span>
        </div>

        {/* Party / Bench Filter Pills */}
        {messages.length > 2 && (
          <div
            style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              gap: '6px',
              flexWrap: 'wrap',
              marginTop: '12px',
            }}
          >
            {([
              { id: 'all', label: 'All Proceedings' },
              { id: 'bench', label: 'Bench & Neutral' },
              { id: 'prosecution', label: 'Prosecution' },
              { id: 'defense', label: 'Defense' },
            ] as const).map((tab) => {
              const active = sideFilter === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setSideFilter(tab.id)}
                  style={{
                    fontSize: '0.72rem',
                    fontWeight: active ? 600 : 500,
                    padding: '3px 11px',
                    borderRadius: '999px',
                    cursor: 'pointer',
                    border: active
                      ? '1px solid rgba(212, 175, 55, 0.55)'
                      : '1px solid rgba(255, 255, 255, 0.08)',
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

      {/* Main Conversational Stream */}
      {visibleMessages.map((msg) => {
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
          className="animate-verdict-card"
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
          }}
        >
          <div
            className="animate-gavel-ring"
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

      {showJumpButton && (
        <button
          type="button"
          onClick={scrollToLatest}
          className="jump-latest-btn"
          aria-label="Jump to latest proceeding"
        >
          <span>Jump to Latest Proceeding</span>
          <ArrowDown size={14} />
        </button>
      )}

      <div ref={bottomRef} />
    </div>
  );
};
