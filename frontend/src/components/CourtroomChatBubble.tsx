import React, { useState } from 'react';
import { 
  Gavel, 
  Shield, 
  Briefcase, 
  BookOpen, 
  Globe, 
  Microscope, 
  AlertTriangle, 
  CheckCircle2, 
  ExternalLink,
  Code2,
  Copy,
  Check,
  Award
} from 'lucide-react';
import type { AgentMessage } from '../types/court';
import { getFormattedMessage } from '../utils/courtroomChatFormatters';
import type { FormattedChatMessage } from '../utils/courtroomChatFormatters';

interface CourtroomChatBubbleProps {
  message: AgentMessage;
  onOpenJudgment?: () => void;
}

export const CourtroomChatBubble: React.FC<CourtroomChatBubbleProps> = ({
  message,
  onOpenJudgment,
}) => {
  const [visibleCount, setVisibleCount] = useState(1);
  const { agent, payload, timestamp } = message;
  const formattedMessages = getFormattedMessage(agent, payload);

  React.useEffect(() => {
    if (visibleCount < formattedMessages.length) {
      const timer = setTimeout(() => {
        setVisibleCount((prev) => prev + 1);
      }, 1500); // 1.5s delay for progressive reading
      return () => clearTimeout(timer);
    }
  }, [visibleCount, formattedMessages.length]);

  if (!formattedMessages || formattedMessages.length === 0) return null;

  const getAlignSelf = (side: string) => {
    if (side === 'prosecution') return 'flex-end';
    if (side === 'defense') return 'flex-start';
    return 'center';
  };

  return (
    <>
      {formattedMessages.slice(0, visibleCount).map((formatted, index) => {
        const isLastInSequence = index === formattedMessages.length - 1;
        return (
          <SingleBubble 
            key={`${message.id}-${index}`}
            formatted={formatted}
            agent={agent}
            payload={payload}
            timestamp={timestamp}
            isLast={isLastInSequence}
            onOpenJudgment={isLastInSequence ? onOpenJudgment : undefined}
          />
        );
      })}
      
      {/* Typing Indicator if still queuing */}
      {visibleCount < formattedMessages.length && (
        <div style={{
          alignSelf: getAlignSelf(formattedMessages[0]?.side),
          color: '#94A3B8',
          fontSize: '0.8rem',
          fontStyle: 'italic',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          background: 'rgba(15, 23, 42, 0.6)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '20px',
          padding: '6px 14px',
          marginTop: '4px',
          marginBottom: '8px',
          animation: 'fadeIn 0.25s ease-out',
        }}>
           [thinking...]
        </div>
      )}
    </>
  );
};

interface SingleBubbleProps {
  formatted: FormattedChatMessage;
  agent: string;
  payload: any;
  timestamp?: string;
  isLast: boolean;
  onOpenJudgment?: () => void;
}

const SingleBubble: React.FC<SingleBubbleProps> = ({
  formatted,
  agent,
  payload,
  timestamp,
  isLast,
  onOpenJudgment
}) => {
  const [showRawData, setShowRawData] = useState(false);
  const [copiedRaw, setCopiedRaw] = useState(false);

  // Time formatted
  const timeStr = timestamp ? new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

  // Alignment and styling logic
  const isPros = formatted.side === 'prosecution';
  const isDef = formatted.side === 'defense';
  const isJudge = formatted.side === 'judicial' || formatted.isJudge;
  const isNeutral = formatted.side === 'neutral' && !isJudge;

  const isResearch = agent.includes('research');

  // Alignments: Prosecutor slightly right, Defense slightly left, Neutral/Judge centered
  let alignSelf = 'flex-start';
  let maxWidth = isResearch ? '100%' : '82%';
  let minWidth = isResearch ? '100%' : '320px';
  let bg = 'rgba(19, 24, 36, 0.75)';
  let borderColor = 'rgba(255, 255, 255, 0.08)';
  let roleBadgeBg = 'rgba(255, 255, 255, 0.08)';
  let roleBadgeColor = '#CBD5E1';
  let speakerColor = '#F8FAFC';

  if (isJudge) {
    alignSelf = 'center';
    maxWidth = '92%';
    bg = 'linear-gradient(180deg, rgba(30, 25, 15, 0.85) 0%, rgba(15, 20, 30, 0.9) 100%)';
    borderColor = 'rgba(212, 175, 55, 0.5)';
    roleBadgeBg = 'rgba(212, 175, 55, 0.2)';
    roleBadgeColor = 'var(--gold-primary)';
    speakerColor = 'var(--gold-primary)';
  } else if (isPros) {
    alignSelf = 'flex-end';
    maxWidth = isResearch ? '100%' : '84%';
    bg = 'linear-gradient(135deg, rgba(23, 37, 84, 0.45) 0%, rgba(15, 23, 42, 0.75) 100%)';
    borderColor = 'rgba(59, 130, 246, 0.3)';
    roleBadgeBg = 'rgba(59, 130, 246, 0.15)';
    roleBadgeColor = '#93C5FD';
    speakerColor = '#93C5FD';
  } else if (isDef) {
    alignSelf = 'flex-start';
    maxWidth = isResearch ? '100%' : '84%';
    bg = 'linear-gradient(135deg, rgba(6, 78, 59, 0.35) 0%, rgba(15, 23, 42, 0.75) 100%)';
    borderColor = 'rgba(16, 185, 129, 0.3)';
    roleBadgeBg = 'rgba(16, 185, 129, 0.15)';
    roleBadgeColor = '#6EE7B7';
    speakerColor = '#6EE7B7';
  } else if (agent === 'conflict') {
    alignSelf = 'center';
    maxWidth = '88%';
    borderColor = 'rgba(245, 158, 11, 0.35)';
    bg = 'rgba(30, 24, 15, 0.6)';
    roleBadgeColor = '#FDE68A';
  } else if (agent === 'evidence') {
    alignSelf = 'center';
    maxWidth = '88%';
    borderColor = 'rgba(168, 85, 247, 0.3)';
    bg = 'rgba(26, 18, 40, 0.6)';
    roleBadgeColor = '#D8B4FE';
  } else {
    // Case understanding
    alignSelf = 'center';
    maxWidth = '90%';
    borderColor = 'rgba(212, 175, 55, 0.25)';
  }

  // Speaker icons
  const getSpeakerIcon = () => {
    const size = 16;
    if (isJudge) return <Gavel size={size} color="var(--gold-primary)" />;
    if (agent === 'prosecutor') return <Briefcase size={size} color="#60A5FA" />;
    if (agent === 'defense') return <Shield size={size} color="#34D399" />;
    if (agent.includes('legal_research')) return <BookOpen size={size} color={isDef ? '#34D399' : '#818CF8'} />;
    if (agent.includes('web_research')) return <Globe size={size} color={isDef ? '#34D399' : '#38BDF8'} />;
    if (agent === 'evidence') return <Microscope size={size} color="#C084FC" />;
    if (agent === 'conflict') return <AlertTriangle size={size} color="#F59E0B" />;
    return <CheckCircle2 size={size} color="var(--gold-primary)" />;
  };

  const handleCopyRaw = () => {
    navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
    setCopiedRaw(true);
    setTimeout(() => setCopiedRaw(false), 2000);
  };

  return (
    <div
      style={{
        alignSelf,
        maxWidth,
        width: isJudge || isNeutral || isResearch ? '100%' : 'auto',
        minWidth,
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
        animation: 'fadeIn 0.25s ease-out forwards',
      }}
    >
      {/* Bubble Container */}
      <div
        style={{
          background: bg,
          border: `1px solid ${borderColor}`,
          borderRadius: isJudge ? '14px' : isPros ? '14px 14px 4px 14px' : '14px 14px 14px 4px',
          padding: isJudge ? '16px 20px' : '14px 18px',
          boxShadow: isJudge ? '0 4px 20px rgba(0,0,0,0.5), 0 0 15px rgba(212, 175, 55, 0.15)' : '0 4px 16px rgba(0,0,0,0.35)',
          backdropFilter: 'blur(10px)',
          position: 'relative',
        }}
      >
        {/* Header: Speaker icon, name, role badge, timestamp, debug toggle */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              {getSpeakerIcon()}
              <span
                style={{
                  fontWeight: isJudge ? 700 : 600,
                  fontSize: isJudge ? '0.98rem' : '0.88rem',
                  color: speakerColor,
                  fontFamily: isJudge ? 'var(--font-serif)' : 'var(--font-sans)',
                  letterSpacing: isJudge ? '0.04em' : 'normal',
                }}
              >
                {formatted.speakerName}
              </span>
            </div>

            <span
              style={{
                fontSize: '0.66rem',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                background: roleBadgeBg,
                color: roleBadgeColor,
                padding: '1px 6px',
                borderRadius: '4px',
              }}
            >
              {formatted.roleBadge}
            </span>

            {formatted.metadataBadge && (
              <span
                style={{
                  fontSize: '0.68rem',
                  color: '#94A3B8',
                  background: 'rgba(255, 255, 255, 0.04)',
                  padding: '1px 6px',
                  borderRadius: '4px',
                  fontFamily: 'monospace',
                }}
              >
                {formatted.metadataBadge}
              </span>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.72rem', color: '#64748B', whiteSpace: 'nowrap' }}>
              {timeStr}
            </span>
            {isLast && (
              <button
                onClick={() => setShowRawData(!showRawData)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#64748B',
                  cursor: 'pointer',
                  padding: '2px 4px',
                  borderRadius: '3px',
                  fontSize: '0.75rem',
                }}
                title="View structured data (developer inspect)"
                onMouseEnter={(e) => (e.currentTarget.style.color = '#CBD5E1')}
                onMouseLeave={(e) => (e.currentTarget.style.color = '#64748B')}
              >
                <Code2 size={13} />
              </button>
            )}
          </div>
        </div>

        {/* Compact Chips for Case Introduction */}
        {formatted.chips && formatted.chips.length > 0 && (
          <div style={{ display: 'flex', gap: '8px', marginBottom: '10px', flexWrap: 'wrap' }}>
            {formatted.chips.map((chip, idx) => (
              <span
                key={idx}
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '6px',
                  padding: '2px 8px',
                  fontSize: '0.76rem',
                  color: '#E2E8F0',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px',
                }}
              >
                <span style={{ color: '#94A3B8' }}>{chip.label}:</span>
                <span style={{ fontWeight: 700, color: chip.color || 'var(--gold-primary)' }}>
                  {chip.value}
                </span>
              </span>
            ))}
          </div>
        )}

        {/* Conversational Intro Text */}
        {formatted.introText && (
          <p
            style={{
              margin: '0 0 8px 0',
              fontSize: isJudge ? '0.94rem' : '0.88rem',
              fontWeight: isJudge ? 500 : 400,
              fontStyle: isJudge ? 'italic' : 'normal',
              color: isJudge ? '#FFFBEB' : '#F1F5F9',
              lineHeight: 1.55,
              fontFamily: isJudge ? 'var(--font-serif)' : 'inherit',
            }}
          >
            {formatted.introText}
          </p>
        )}

        {/* Body Paragraphs */}
        {formatted.bodyParagraphs && formatted.bodyParagraphs.map((para, idx) => (
          <p
            key={idx}
            style={{
              margin: idx === formatted.bodyParagraphs.length - 1 ? '0' : '0 0 8px 0',
              fontSize: '0.86rem',
              color: '#CBD5E1',
              lineHeight: 1.55,
            }}
          >
            {para}
          </p>
        ))}

        {/* Substantive Submissions / Cards */}
        {formatted.substantiveItems && formatted.substantiveItems.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '10px' }}>
            {formatted.substantiveItems.map((item, idx) => (
              <div
                key={idx}
                style={{
                  background: 'rgba(0, 0, 0, 0.25)',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                  borderRadius: '6px',
                  padding: '8px 12px',
                  fontSize: '0.82rem',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '3px' }}>
                  <span style={{ fontWeight: 600, color: isJudge ? 'var(--gold-primary)' : isPros ? '#93C5FD' : isDef ? '#6EE7B7' : '#DDD6FE' }}>
                    {item.label}
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {item.tag && (
                      <span style={{ fontSize: '0.7rem', color: '#94A3B8' }}>
                        {item.tag}
                      </span>
                    )}
                    {item.link && (
                      <a
                        href={item.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '3px',
                          color: 'var(--gold-primary)',
                          fontSize: '0.72rem',
                          textDecoration: 'none',
                        }}
                      >
                        <span>View</span>
                        <ExternalLink size={10} />
                      </a>
                    )}
                  </div>
                </div>
                {item.text && (
                  <div style={{ color: '#E2E8F0', lineHeight: 1.45 }}>
                    {item.text}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Concluding Prayer / Note */}
        {formatted.concludingText && (
          <div
            style={{
              marginTop: '10px',
              paddingTop: '8px',
              borderTop: '1px solid rgba(255, 255, 255, 0.06)',
              fontSize: '0.82rem',
              color: '#94A3B8',
              fontStyle: 'italic',
            }}
          >
            {formatted.concludingText}
          </div>
        )}

        {/* Special Judge Pronouncement Call to Action */}
        {isJudge && onOpenJudgment && payload?.judgment && (
          <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'flex-end' }}>
            <button
              onClick={onOpenJudgment}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                background: 'linear-gradient(135deg, var(--gold-primary) 0%, #B8860B 100%)',
                color: '#0A0E17',
                border: 'none',
                borderRadius: '6px',
                padding: '9px 18px',
                fontSize: '0.84rem',
                fontWeight: 700,
                cursor: 'pointer',
                boxShadow: '0 0 16px rgba(212, 175, 55, 0.35)',
                transition: 'all 0.15s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-1px)';
                e.currentTarget.style.boxShadow = '0 0 22px rgba(212, 175, 55, 0.55)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 0 16px rgba(212, 175, 55, 0.35)';
              }}
            >
              <Award size={15} />
              <span>VIEW FULL JUDGMENT</span>
            </button>
          </div>
        )}

        {/* Developer Raw Data Drawer */}
        {showRawData && isLast && (
          <div
            style={{
              marginTop: '12px',
              borderTop: '1px solid rgba(255, 255, 255, 0.08)',
              paddingTop: '10px',
              background: 'rgba(5, 8, 15, 0.9)',
              borderRadius: '6px',
              padding: '10px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <span style={{ fontSize: '0.72rem', color: '#64748B', fontFamily: 'monospace' }}>
                STRUCTURED AGENT OUTPUT JSON
              </span>
              <button
                onClick={handleCopyRaw}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  background: 'rgba(255, 255, 255, 0.06)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  color: copiedRaw ? '#10B981' : '#CBD5E1',
                  borderRadius: '4px',
                  padding: '2px 6px',
                  fontSize: '0.7rem',
                  cursor: 'pointer',
                }}
              >
                {copiedRaw ? <Check size={11} /> : <Copy size={11} />}
                <span>{copiedRaw ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
            <pre
              style={{
                margin: 0,
                fontSize: '0.75rem',
                color: '#A5B4FC',
                fontFamily: 'Consolas, monospace',
                maxHeight: '220px',
                overflowY: 'auto',
                whiteSpace: 'pre-wrap',
                lineHeight: 1.4,
              }}
            >
              {JSON.stringify(payload, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};
