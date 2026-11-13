import { useState } from 'react';
import { AlertCircle } from 'lucide-react';
import type { 
  AgentMessage, 
  Judgment, 
  UploadedCaseInfo 
} from './types/court';
import { Header } from './components/Header';
import { CaseUpload } from './components/CaseUpload';
import { CourtroomChat } from './components/CourtroomChat';
import { ResearchChamber } from './components/ResearchChamber';
import { JudgmentModal } from './components/JudgmentModal';
import { ComparisonModal } from './components/ComparisonModal';

export function App() {
  const [uploadedCase, setUploadedCase] = useState<UploadedCaseInfo | null>(null);
  const [resolvedCaseId, setResolvedCaseId] = useState<string | null>(null);
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [currentAgent, setCurrentAgent] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [judgment, setJudgment] = useState<Judgment | null>(null);
  const [isJudgmentModalOpen, setIsJudgmentModalOpen] = useState<boolean>(false);
  const [isComparisonModalOpen, setIsComparisonModalOpen] = useState<boolean>(false);
  const [courtError, setCourtError] = useState<string | null>(null);

  // Reset state for new case
  const handleResetSession = () => {
    if (isStreaming) return;
    setUploadedCase(null);
    setResolvedCaseId(null);
    setMessages([]);
    setCurrentAgent(null);
    setJudgment(null);
    setIsJudgmentModalOpen(false);
    setIsComparisonModalOpen(false);
    setCourtError(null);
  };

  const handleStartCourt = async () => {
    if (!uploadedCase || isStreaming) return;

    setIsStreaming(true);
    setCourtError(null);
    setMessages([]);
    setCurrentAgent('case_understanding');
    setJudgment(null);

    const caseId = uploadedCase.upload_id;
    const streamUrl = `/api/court/stream`;

    try {
      const response = await fetch(streamUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ upload_id: caseId }),
      });
      if (!response.ok) {
        throw new Error(`Failed to initiate court proceedings (HTTP ${response.status})`);
      }

      if (!response.body) {
        throw new Error('ReadableStream not supported by browser.');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const block of lines) {
          if (!block.trim()) continue;

          let eventType = 'message';
          let eventData = '';

          const blockLines = block.split('\n');
          for (const line of blockLines) {
            if (line.startsWith('event:')) {
              eventType = line.replace('event:', '').trim();
            } else if (line.startsWith('data:')) {
              eventData = line.replace('data:', '').trim();
            }
          }

          if (eventData) {
            try {
              const parsed = JSON.parse(eventData);
              handleSSEEvent(eventType, parsed);
            } catch (err) {
              console.warn('Error parsing SSE event data:', err, eventData);
            }
          }
        }
      }
    } catch (err: any) {
      console.error('Court stream error:', err);
      setCourtError(err.message || 'Court proceedings interrupted unexpectedly.');
    } finally {
      setIsStreaming(false);
      setCurrentAgent(null);
    }
  };

  const handleSSEEvent = (eventType: string, data: any) => {
    const type = data?.type || eventType;

    if (type === 'session_started') {
      setCurrentAgent('case_understanding');
    } else if (type === 'agent_started') {
      setCurrentAgent(data.agent);
    } else if (type === 'agent_message') {
      const newMsg: AgentMessage = {
        id: `${data.agent}_${Date.now()}`,
        agent: data.agent,
        metadata: data.metadata || {
          title: data.agent.replace(/_/g, ' ').toUpperCase(),
          role: 'Courtroom Agent',
          side: 'neutral',
          avatar: 'scale',
        },
        payload: data.payload,
        timestamp: data.timestamp || new Date().toISOString(),
        status: 'completed',
      };
      setMessages((prev) => [...prev, newMsg]);
    } else if (type === 'agent_completed') {
      // Progress to next stage
    } else if (type === 'court_completed') {
      if (data.judgment) {
        setJudgment(data.judgment);
      }
      if (data.case_id) {
        setResolvedCaseId(data.case_id);
      }
      setIsStreaming(false);
      setCurrentAgent(null);
    } else if (type === 'error' || type === 'court_error') {
      setCourtError(data.error || data.message || 'Judicial proceeding encountered a system exception.');
      setIsStreaming(false);
      setCurrentAgent(null);
    }
  };

  // Determine current status
  const courtStatus = judgment
    ? 'COMPLETED'
    : isStreaming
    ? 'IN_SESSION'
    : uploadedCase
    ? 'READY'
    : 'STANDBY';

  const courtroomAgentNames = [
    'case_understanding',
    'live_judge',
    'live_prosecutor',
    'live_defense',
    'live_evidence',
    'live_conflict',
    'judge',
  ];

  const researchAgentNames = [
    'prosecutor_legal_research',
    'prosecutor_web_research',
    'defense_legal_research',
    'defense_web_research',
    'evidence',
    'conflict',
  ];

  const mainMessages = messages.filter((m) => courtroomAgentNames.includes(m.agent));
  const researchMessages = messages.filter((m) => researchAgentNames.includes(m.agent));

  const activeCaseId = resolvedCaseId || uploadedCase?.upload_id || 'CASE-001';

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg-court)' }}>
      
      {/* Authoritative Courtroom Header */}
      <Header
        caseTitle={uploadedCase ? uploadedCase.filename : null}
        caseId={activeCaseId}
        status={courtStatus}
        onResetSession={handleResetSession}
        isStreaming={isStreaming}
        messages={messages}
        judgment={judgment}
        onOpenComparison={() => setIsComparisonModalOpen(true)}
      />

      {/* Main Courtroom Container */}
      <main style={{ flex: 1, width: '100%', display: 'flex', flexDirection: 'column' }}>
        
        {/* Case Upload Area (Landing screen when no messages / ready to start) */}
        {messages.length === 0 && !isStreaming ? (
          <CaseUpload
            onCaseUploaded={(info) => setUploadedCase(info)}
            onStartCourt={handleStartCourt}
            uploadedCase={uploadedCase}
            isStreaming={isStreaming}
          />
        ) : (
          <div className="layout-container">
            <div className="courtroom-main">
              {/* Live Conversational Courtroom Chat */}
              <CourtroomChat
                messages={mainMessages}
                currentAgent={currentAgent}
                isStreaming={isStreaming}
                judgment={judgment}
                onOpenJudgment={() => setIsJudgmentModalOpen(true)}
                onOpenComparison={() => setIsComparisonModalOpen(true)}
                caseTitle={uploadedCase?.filename}
              />
            </div>
            <div className="research-chamber-sidebar">
              <ResearchChamber
                messages={researchMessages}
                currentAgent={currentAgent}
                isStreaming={isStreaming}
              />
            </div>
          </div>
        )}

        {/* Global Exception Alert */}
        {courtError && (
          <div
            style={{
              maxWidth: '800px',
              margin: '16px auto',
              padding: '14px 20px',
              borderRadius: '8px',
              background: 'rgba(220, 38, 38, 0.15)',
              border: '1px solid rgba(220, 38, 38, 0.4)',
              color: '#FCA5A5',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
            }}
          >
            <AlertCircle size={20} color="#EF4444" style={{ flexShrink: 0 }} />
            <div>
              <strong style={{ color: '#F87171' }}>Judicial Exception: </strong>
              <span>{courtError}</span>
            </div>
          </div>
        )}

      </main>

      {/* 12-Section Supreme Bench Judgment Modal */}
      {isJudgmentModalOpen && judgment && (
        <JudgmentModal
          judgment={judgment}
          caseId={activeCaseId}
          onClose={() => setIsJudgmentModalOpen(false)}
        />
      )}

      {/* Phase 5 Real Court Judgment Comparison Modal */}
      {isComparisonModalOpen && judgment && (
        <ComparisonModal
          caseId={activeCaseId}
          judgment={judgment}
          onClose={() => setIsComparisonModalOpen(false)}
        />
      )}

      {/* Dignified Courtroom Footer */}
      <footer
        style={{
          padding: '14px 24px',
          textAlign: 'center',
          fontSize: '0.74rem',
          color: '#64748B',
          borderTop: '1px solid rgba(255, 255, 255, 0.05)',
          marginTop: 'auto',
          background: 'rgba(7, 11, 20, 0.95)',
        }}
      >
        <span>
          AI Court of India &bull; Statutory Adjudication Engine &bull; Bharatiya Nyaya Sanhita (BNS) &bull; Bharatiya Nagarik Suraksha Sanhita (BNSS) &bull; Bharatiya Sakshya Adhiniyam (BSA)
        </span>
      </footer>

    </div>
  );
}

export default App;
