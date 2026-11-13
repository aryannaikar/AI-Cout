import React, { useState } from 'react';
import { 
  Gavel, 
  Shield, 
  Briefcase, 
  BookOpen, 
  Globe, 
  Microscope, 
  AlertTriangle, 
  ChevronDown, 
  ChevronUp, 
  Clock, 
  FileText
} from 'lucide-react';
import type { AgentMessage, AgentSide } from '../types/court';
import { CaseUnderstandingRenderer } from './renderers/CaseUnderstandingRenderer';
import { ProsecutorRenderer } from './renderers/ProsecutorRenderer';
import { LegalResearchRenderer } from './renderers/LegalResearchRenderer';
import { WebResearchRenderer } from './renderers/WebResearchRenderer';
import { DefenseRenderer } from './renderers/DefenseRenderer';
import { EvidenceAnalysisRenderer } from './renderers/EvidenceAnalysisRenderer';
import { ConflictDetectionRenderer } from './renderers/ConflictDetectionRenderer';
import { JudgeRenderer } from './renderers/JudgeRenderer';
import { RawDataCollapsible } from './renderers/RawDataCollapsible';

interface AgentMessageCardProps {
  message: AgentMessage;
  isLatest?: boolean;
  onOpenJudgment?: () => void;
}

export const AgentMessageCard: React.FC<AgentMessageCardProps> = ({ message, isLatest, onOpenJudgment }) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const { metadata, payload, timestamp, status, agent } = message;

  // Icon selector based on agent node identity
  const renderAgentIcon = (nodeName: string, side: AgentSide) => {
    const size = 20;
    if (nodeName === 'judge' || side === 'judicial') return <Gavel size={size} color="var(--gold-primary)" />;
    if (nodeName === 'prosecutor') return <Briefcase size={size} color="#60A5FA" />;
    if (nodeName === 'defense') return <Shield size={size} color="#34D399" />;
    if (nodeName.includes('legal_research')) return <BookOpen size={size} color={side === 'defense' ? '#34D399' : '#818CF8'} />;
    if (nodeName.includes('web_research')) return <Globe size={size} color={side === 'defense' ? '#34D399' : '#38BDF8'} />;
    if (nodeName === 'evidence') return <Microscope size={size} color="#C084FC" />;
    if (nodeName === 'conflict') return <AlertTriangle size={size} color="#F59E0B" />;
    return <FileText size={size} color="var(--gold-primary)" />;
  };

  // Border & styling by side
  const getSideStyles = (side: AgentSide, nodeName: string) => {
    if (nodeName === 'judge' || side === 'judicial') {
      return {
        borderClass: 'border-judge',
        bg: 'rgba(212, 175, 55, 0.05)',
        badgeBg: 'rgba(212, 175, 55, 0.2)',
        badgeColor: 'var(--gold-primary)',
        titleColor: 'var(--gold-primary)',
        indicatorColor: 'var(--gold-primary)',
      };
    }
    if (side === 'prosecution') {
      return {
        borderClass: 'border-pros',
        bg: 'rgba(59, 130, 246, 0.05)',
        badgeBg: 'rgba(59, 130, 246, 0.2)',
        badgeColor: '#60A5FA',
        titleColor: '#93C5FD',
        indicatorColor: '#3B82F6',
      };
    }
    if (side === 'defense') {
      return {
        borderClass: 'border-def',
        bg: 'rgba(16, 185, 129, 0.05)',
        badgeBg: 'rgba(16, 185, 129, 0.2)',
        badgeColor: '#34D399',
        titleColor: '#6EE7B7',
        indicatorColor: '#10B981',
      };
    }
    return {
      borderClass: 'border-neutral',
      bg: 'rgba(148, 163, 184, 0.03)',
      badgeBg: 'rgba(148, 163, 184, 0.15)',
      badgeColor: '#CBD5E1',
      titleColor: '#E2E8F0',
      indicatorColor: '#94A3B8',
    };
  };

  const style = getSideStyles(metadata.side, agent);

  // Dispatch to the proper presentation renderer
  const renderStructuredContent = () => {
    if (!payload) return null;

    switch (agent) {
      case 'case_understanding':
        return <CaseUnderstandingRenderer payload={payload} />;

      case 'prosecutor':
        return <ProsecutorRenderer payload={payload} />;

      case 'prosecutor_legal_research':
        return <LegalResearchRenderer payload={payload} side="prosecution" />;

      case 'prosecutor_web_research':
        return <WebResearchRenderer payload={payload} side="prosecution" />;

      case 'defense':
        return <DefenseRenderer payload={payload} />;

      case 'defense_legal_research':
        return <LegalResearchRenderer payload={payload} side="defense" />;

      case 'defense_web_research':
        return <WebResearchRenderer payload={payload} side="defense" />;

      case 'evidence':
        return <EvidenceAnalysisRenderer payload={payload} />;

      case 'conflict':
        return <ConflictDetectionRenderer payload={payload} />;

      case 'judge':
        return <JudgeRenderer payload={payload} onOpenJudgment={onOpenJudgment} />;

      default:
        // Fallback for custom or unrecognized node
        if (payload.case_title && payload.charges) {
          return <CaseUnderstandingRenderer payload={payload} />;
        }
        if (payload.prosecution_theory) {
          return <ProsecutorRenderer payload={payload} />;
        }
        if (payload.defense_theory) {
          return <DefenseRenderer payload={payload} />;
        }
        if (payload.items) {
          return <EvidenceAnalysisRenderer payload={payload} />;
        }
        if (payload.conflicts) {
          return <ConflictDetectionRenderer payload={payload} />;
        }
        return (
          <div style={{ background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: '6px', fontSize: '0.84rem' }}>
            <p style={{ margin: 0, color: '#CBD5E1', whiteSpace: 'pre-wrap' }}>
              {typeof payload === 'string' ? payload : JSON.stringify(payload, null, 2)}
            </p>
          </div>
        );
    }
  };

  // Status indicator badge
  const renderStatusBadge = () => {
    switch (status) {
      case 'thinking':
        return (
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.72rem', color: 'var(--gold-primary)' }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--gold-primary)' }} className="pulse-gold" />
            <span>Deliberating</span>
          </span>
        );
      case 'error':
        return (
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.72rem', color: '#EF4444' }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#EF4444' }} />
            <span>Error</span>
          </span>
        );
      case 'completed':
      default:
        return (
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.72rem', color: '#10B981' }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10B981' }} />
            <span>Completed</span>
          </span>
        );
    }
  };

  return (
    <div
      className={`glass-panel-court ${style.borderClass}`}
      style={{
        background: style.bg,
        borderRadius: '10px',
        padding: '16px 18px',
        position: 'relative',
        animation: isLatest ? 'fadeIn 0.3s ease-out' : 'none',
      }}
    >
      {/* Header bar: Agent Icon, Title, Role Badge, Status, Collapse */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer',
          userSelect: 'none',
        }}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Agent Icon Badge */}
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '8px',
              background: style.badgeBg,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            {renderAgentIcon(agent, metadata.side)}
          </div>

          {/* Titles & Roles */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <span style={{ fontWeight: 700, fontSize: '0.94rem', color: style.titleColor }}>
                {metadata.title}
              </span>
              <span
                style={{
                  fontSize: '0.68rem',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  background: style.badgeBg,
                  color: style.badgeColor,
                  letterSpacing: '0.04em',
                }}
              >
                {metadata.role}
              </span>
            </div>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '2px' }}>
              {renderStatusBadge()}
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.72rem', color: '#64748B' }}>
                <Clock size={11} />
                <span>{new Date(timestamp).toLocaleTimeString()}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Toggle Button */}
        <button
          style={{
            background: 'rgba(255, 255, 255, 0.04)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            color: '#94A3B8',
            borderRadius: '6px',
            width: '28px',
            height: '28px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
          }}
          title={isExpanded ? 'Collapse' : 'Expand'}
        >
          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>

      {/* Expanded Content Area */}
      {isExpanded && (
        <div style={{ marginTop: '12px', borderTop: '1px solid rgba(255, 255, 255, 0.06)', paddingTop: '12px' }}>
          {/* Main Structured Presentation */}
          {renderStructuredContent()}

          {/* Optional Collapsible Developer Raw Data Drawer */}
          <RawDataCollapsible data={payload} />
        </div>
      )}
    </div>
  );
};
