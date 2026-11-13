import type { AgentMessage, Judgment } from '../types/court';
import { getFormattedMessage, type FormattedChatMessage } from './courtroomChatFormatters';

export interface ExportCourtRecordOptions {
  caseTitle?: string | null;
  caseId?: string | null;
  status: string;
  messages: AgentMessage[];
  judgment: Judgment | null;
}

const SEP_DOUBLE = '='.repeat(80);
const SEP_SINGLE = '-'.repeat(80);
const SUB_SEP = '.'.repeat(60);

/**
 * Format a clean timestamp string
 */
function formatTime(isoStr?: string): string {
  if (!isoStr) return new Date().toLocaleTimeString();
  try {
    return new Date(isoStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return isoStr;
  }
}

/**
 * Clean up text for terminal/plain text export
 */
function cleanText(text?: string | null): string {
  if (!text) return '';
  return text.trim();
}

/**
 * Word wrap helper for clean TXT rendering
 */
function wrap(text: string, maxWidth = 76, indent = ''): string {
  const words = text.split(/\s+/);
  const lines: string[] = [];
  let currentLine = indent;

  for (const word of words) {
    if ((currentLine + ' ' + word).trim().length > maxWidth && currentLine.trim().length > 0) {
      lines.push(currentLine);
      currentLine = indent + word;
    } else {
      currentLine = currentLine.trim().length === 0 ? indent + word : currentLine + ' ' + word;
    }
  }
  if (currentLine.trim().length > 0) {
    lines.push(currentLine);
  }
  return lines.join('\n');
}

/**
 * Format a list of messages for text output
 */
function formatMessagesTxt(messages: AgentMessage[], startIndex = 1): { text: string; nextIndex: number } {
  const lines: string[] = [];
  let currentIndex = startIndex;

  for (const msg of messages) {
    const formattedList: FormattedChatMessage[] = getFormattedMessage(msg.agent, msg.payload);
    const time = formatTime(msg.timestamp);

    for (const f of formattedList) {
      lines.push(`[ENTRY #${currentIndex}] [${time}] ${f.speakerName.toUpperCase()} (${f.roleBadge})`);
      if (f.metadataBadge) {
        lines.push(`  Docket Reference: ${f.metadataBadge}`);
      }
      lines.push(`  Side: ${f.side.toUpperCase()}`);
      lines.push(`  ${SUB_SEP}`);

      if (f.chips && f.chips.length > 0) {
        const chipStr = f.chips.map((c) => `${c.label}: ${c.value}`).join(' | ');
        lines.push(`  [Overview: ${chipStr}]`);
      }

      if (f.introText) {
        lines.push(wrap(f.introText, 76, '  '));
      }

      if (f.bodyParagraphs && f.bodyParagraphs.length > 0) {
        for (const p of f.bodyParagraphs) {
          lines.push('');
          lines.push(wrap(p, 76, '  '));
        }
      }

      if (f.substantiveItems && f.substantiveItems.length > 0) {
        lines.push('');
        lines.push('  Submissions / Cited Authorities:');
        for (const item of f.substantiveItems) {
          const tagStr = item.tag ? ` [${item.tag}]` : '';
          lines.push(`   * ${item.label}${tagStr}`);
          if (item.text) {
            lines.push(wrap(item.text, 74, '     '));
          }
        }
      }

      if (f.concludingText) {
        lines.push('');
        lines.push(wrap(f.concludingText, 76, '  '));
      }

      lines.push('');
      currentIndex++;
    }
  }

  return { text: lines.join('\n'), nextIndex: currentIndex };
}

/**
 * Generate comprehensive Plain Text (.txt) containing entire chat & verdict
 */
export function generateCourtRecordTxt(options: ExportCourtRecordOptions): string {
  const { caseTitle, caseId, status, messages, judgment } = options;
  const lines: string[] = [];
  const exportDate = new Date().toLocaleString();

  // 1. Header Banner
  lines.push(SEP_DOUBLE);
  lines.push('                          AI COURT OF INDIA');
  lines.push('                 COURT OF THE SPECIAL JUDICIAL BENCH');
  lines.push('      STATUTORY ADJUDICATION RECORD, PROCEEDINGS & VERDICT TRANSCRIPT');
  lines.push(SEP_DOUBLE);
  lines.push(`Case Docket   : ${caseTitle || 'State vs. Accused'}`);
  lines.push(`Case / Ref ID : ${caseId || judgment?.judgment_id || 'AI-CRT-DEFAULT'}`);
  lines.push(`Trial Status  : ${status}`);
  lines.push(`Exported Date : ${exportDate}`);
  lines.push(`Presiding     : ${judgment?.presiding_court || 'Special Judicial Bench of AI Court of India'}`);
  lines.push('Statutory Code: Bharatiya Nyaya Sanhita (BNS) | BNSS | BSA');
  lines.push(SEP_DOUBLE);
  lines.push('');

  // 2. PART I: VERDICT & JUDICIAL DECREE
  lines.push(SEP_DOUBLE);
  lines.push('            PART I: OFFICIAL VERDICT & FINAL JUDICIAL DECREE');
  lines.push(SEP_DOUBLE);

  if (judgment) {
    lines.push('');
    lines.push('********************************************************************************');
    lines.push(` OPERATIVE FINAL VERDICT: ${judgment.final_decision?.toUpperCase() || 'DELIVERED'}`);
    lines.push(` Date of Decision       : ${judgment.date_of_decision || new Date().toLocaleDateString()}`);
    lines.push('********************************************************************************');
    lines.push('');

    lines.push('SECTION 1: CASE BACKGROUND & PROSECUTION ORIGIN');
    lines.push(SEP_SINGLE);
    lines.push(wrap(cleanText(judgment.case_background) || 'No background recorded.', 78));
    lines.push('');

    lines.push('SECTION 2: POINTS & ISSUES FOR DETERMINATION');
    lines.push(SEP_SINGLE);
    if (judgment.issues_for_determination && judgment.issues_for_determination.length > 0) {
      judgment.issues_for_determination.forEach((pt, idx) => {
        lines.push(`  ${idx + 1}. ${pt}`);
      });
    } else {
      lines.push('  None framed on record.');
    }
    lines.push('');

    lines.push('SECTION 3: APPLICABLE STATUTORY LAW & PROVISIONS');
    lines.push(SEP_SINGLE);
    if (judgment.applicable_law && judgment.applicable_law.length > 0) {
      judgment.applicable_law.forEach((law) => {
        lines.push(`  * ${law}`);
      });
    } else {
      lines.push('  Bharatiya Nyaya Sanhita, 2023.');
    }
    lines.push('');

    lines.push('SECTION 4: JUDICIAL APPRAISAL OF DOCUMENTARY & ELECTRONIC EXHIBITS');
    lines.push(SEP_SINGLE);
    lines.push(wrap(cleanText(judgment.evidence_assessment) || 'Evidence appraisal recorded.', 78));
    lines.push('');

    lines.push('SECTION 5: CREDIBILITY ANALYSIS OF ORAL WITNESS TESTIMONY');
    lines.push(SEP_SINGLE);
    lines.push(wrap(cleanText(judgment.witness_assessment) || 'Witness testimonies evaluated.', 78));
    lines.push('');

    lines.push('SECTION 6: SUBMISSIONS ADVANCED BY THE PROSECUTION');
    lines.push(SEP_SINGLE);
    lines.push(wrap(cleanText(judgment.prosecution_submissions) || 'Prosecution submissions noted.', 78));
    lines.push('');

    lines.push('SECTION 7: SUBMISSIONS ADVANCED BY THE DEFENSE');
    lines.push(SEP_SINGLE);
    lines.push(wrap(cleanText(judgment.defense_submissions) || 'Defense submissions noted.', 78));
    lines.push('');

    lines.push('SECTION 8: ISSUE-BY-ISSUE JUDICIAL DETERMINATION');
    lines.push(SEP_SINGLE);
    if (judgment.issue_analyses && judgment.issue_analyses.length > 0) {
      judgment.issue_analyses.forEach((item) => {
        lines.push(`  Issue #${item.issue_number}: ${item.issue_statement}`);
        lines.push(`    - Governing Law   : ${item.applicable_law}`);
        lines.push(`    - Prosecution Case: ${item.prosecution_submission_summary}`);
        lines.push(`    - Defense Plea    : ${item.defense_submission_summary}`);
        lines.push(`    - Evidence Weight : ${item.evidentiary_evaluation}`);
        lines.push(`    - Judicial Finding: ${item.judicial_finding}`);
        lines.push('');
      });
    } else {
      lines.push('  Issue determinations encapsulated in ratio decidendi.');
      lines.push('');
    }

    lines.push('SECTION 9: FINDINGS ON EACH STATUTORY CHARGE');
    lines.push(SEP_SINGLE);
    if (judgment.findings_per_charge && Object.keys(judgment.findings_per_charge).length > 0) {
      Object.entries(judgment.findings_per_charge).forEach(([charge, finding]) => {
        lines.push(`  * ${charge}: ${finding}`);
      });
    } else {
      lines.push(`  * Statutory Charges: ${judgment.final_decision}`);
    }
    lines.push('');

    lines.push('SECTION 10: RATIO DECIDENDI & DETAILED JUDICIAL REASONING');
    lines.push(SEP_SINGLE);
    lines.push(wrap(cleanText(judgment.reasons) || 'Reasons stated in open court.', 78));
    lines.push('');

    lines.push('SECTION 11: STATUTORY CITATIONS & PRECEDENTS');
    lines.push(SEP_SINGLE);
    if (judgment.legal_citations && judgment.legal_citations.length > 0) {
      judgment.legal_citations.forEach((cit) => {
        lines.push(`  * ${cit}`);
      });
    } else {
      lines.push('  Precedents of the Supreme Court of India.');
    }
    lines.push('');
  } else {
    lines.push('');
    lines.push('  [JUDGMENT STATUS: TRIAL IN PROGRESS / AWAITING BENCH PRONOUNCEMENT]');
    lines.push('  The bench is currently in deliberations or awaiting conclusion of arguments.');
    lines.push('  The courtroom debate and counsel submissions recorded to date appear below.');
    lines.push('');
  }

  // Split messages between courtroom and research
  const courtroomAgentNames = [
    'case_understanding',
    'live_judge',
    'live_prosecutor',
    'live_defense',
    'live_evidence',
    'live_conflict',
    'judge',
  ];
  const mainMessages = messages.filter((m) => courtroomAgentNames.includes(m.agent));
  const researchMessages = messages.filter((m) => !courtroomAgentNames.includes(m.agent));

  // 3. PART II: COURTROOM CHAT & PROCEEDINGS
  lines.push(SEP_DOUBLE);
  lines.push('       PART II: LIVE COURTROOM DEBATE & CHAT TRANSCRIPT');
  lines.push(SEP_DOUBLE);
  lines.push('Official verbatim proceedings of counsel arguments, witness examination,');
  lines.push('procedural motions, and bench directives recorded in open court:');
  lines.push('');

  if (mainMessages.length > 0) {
    const { text: chatText } = formatMessagesTxt(mainMessages, 1);
    lines.push(chatText);
  } else {
    lines.push('  No live courtroom dialogue entries recorded.');
    lines.push('');
  }

  // 4. PART III: RESEARCH CHAMBER & PRECEDENT ANALYSIS
  if (researchMessages.length > 0) {
    lines.push(SEP_DOUBLE);
    lines.push('       PART III: RESEARCH CHAMBER & INVESTIGATIVE MEMORANDA');
    lines.push(SEP_DOUBLE);
    lines.push('Statutory queries, precedent citations, forensic appraisals & conflict logs:');
    lines.push('');
    const { text: researchText } = formatMessagesTxt(researchMessages, 1);
    lines.push(researchText);
  }

  // 5. Official Attestation Footer
  lines.push(SEP_DOUBLE);
  lines.push('                         END OF OFFICIAL RECORD');
  lines.push('      PRONOUNCED AND CERTIFIED BY THE AI COURT OF INDIA TRIBUNAL');
  lines.push('           AUTONOMOUS STATUTORY JUDICIAL ADJUDICATION ENGINE');
  lines.push(SEP_DOUBLE);

  return lines.join('\n');
}

/**
 * Generate Markdown (.md) containing entire chat & verdict
 */
export function generateCourtRecordMd(options: ExportCourtRecordOptions): string {
  const { caseTitle, caseId, status, messages, judgment } = options;
  const exportDate = new Date().toLocaleString();
  const courtroomAgentNames = [
    'case_understanding',
    'live_judge',
    'live_prosecutor',
    'live_defense',
    'live_evidence',
    'live_conflict',
    'judge',
  ];
  const mainMessages = messages.filter((m) => courtroomAgentNames.includes(m.agent));
  const researchMessages = messages.filter((m) => !courtroomAgentNames.includes(m.agent));

  const md: string[] = [];

  md.push(`# AI Court of India — Official Proceedings & Judicial Verdict`);
  md.push(`**Court of the Special Judicial Bench | Statutory Adjudication Engine**\n`);
  md.push(`| Property | Value |`);
  md.push(`| :--- | :--- |`);
  md.push(`| **Case Title** | ${caseTitle || 'State vs. Accused'} |`);
  md.push(`| **Case Docket ID** | \`${caseId || judgment?.judgment_id || 'AI-CRT-001'}\` |`);
  md.push(`| **Trial Status** | **${status}** |`);
  md.push(`| **Presiding Bench** | ${judgment?.presiding_court || 'Special Judicial Bench'} |`);
  md.push(`| **Export Timestamp** | ${exportDate} |`);
  md.push(`| **Governing Codes** | Bharatiya Nyaya Sanhita (BNS), BNSS, BSA |`);
  md.push(`\n---\n`);

  // PART I: VERDICT
  md.push(`## Part I: Supreme Bench Judicial Verdict\n`);
  if (judgment) {
    const isConviction = judgment.final_decision?.toUpperCase().includes('CONVICTION');
    const badgeColor = isConviction ? '🔴' : '🟢';

    md.push(`> ### ${badgeColor} OPERATIVE VERDICT: **${judgment.final_decision?.toUpperCase()}**`);
    md.push(`> **Date of Decision:** ${judgment.date_of_decision || new Date().toLocaleDateString()}\n`);

    md.push(`### 1. Case Background`);
    md.push(judgment.case_background || '_None recorded._');
    md.push(`\n### 2. Issues for Determination`);
    if (judgment.issues_for_determination && judgment.issues_for_determination.length > 0) {
      judgment.issues_for_determination.forEach((issue, i) => md.push(`${i + 1}. ${issue}`));
    } else {
      md.push(`_None explicitly framed._`);
    }

    md.push(`\n### 3. Applicable Statutory Law`);
    if (judgment.applicable_law && judgment.applicable_law.length > 0) {
      judgment.applicable_law.forEach((law) => md.push(`- **${law}**`));
    }

    md.push(`\n### 4. Evidentiary Evaluation`);
    md.push(judgment.evidence_assessment || '_Appraisal noted on record._');

    md.push(`\n### 5. Witness Assessment`);
    md.push(judgment.witness_assessment || '_Witness credibility appraised._');

    md.push(`\n### 6. Prosecution Submissions`);
    md.push(judgment.prosecution_submissions || '_Recorded._');

    md.push(`\n### 7. Defense Submissions`);
    md.push(judgment.defense_submissions || '_Recorded._');

    if (judgment.issue_analyses && judgment.issue_analyses.length > 0) {
      md.push(`\n### 8. Issue-by-Issue Determination`);
      judgment.issue_analyses.forEach((ia) => {
        md.push(`#### Issue #${ia.issue_number}: ${ia.issue_statement}`);
        md.push(`- **Governing Law:** ${ia.applicable_law}`);
        md.push(`- **Prosecution:** ${ia.prosecution_submission_summary}`);
        md.push(`- **Defense:** ${ia.defense_submission_summary}`);
        md.push(`- **Evidentiary Weight:** ${ia.evidentiary_evaluation}`);
        md.push(`- **Judicial Finding:** **${ia.judicial_finding}**\n`);
      });
    }

    if (judgment.findings_per_charge && Object.keys(judgment.findings_per_charge).length > 0) {
      md.push(`\n### 9. Findings on Statutory Charges`);
      Object.entries(judgment.findings_per_charge).forEach(([chg, find]) => {
        md.push(`- **${chg}**: \`${find}\``);
      });
    }

    md.push(`\n### 10. Ratio Decidendi & Judicial Reasoning`);
    md.push(judgment.reasons || '_Delivered in open court._');

    if (judgment.legal_citations && judgment.legal_citations.length > 0) {
      md.push(`\n### 11. Citations & Judicial Precedents`);
      judgment.legal_citations.forEach((c) => md.push(`- ${c}`));
    }
  } else {
    md.push(`> ⏳ **TRIAL IN PROGRESS**: Final judgment is currently pending bench pronouncement.`);
  }

  md.push(`\n---\n`);

  // PART II: COURTROOM TRANSCRIPT
  md.push(`## Part II: Live Courtroom Chat Transcript\n`);
  if (mainMessages.length > 0) {
    let msgCounter = 1;
    mainMessages.forEach((msg) => {
      const formattedList = getFormattedMessage(msg.agent, msg.payload);
      formattedList.forEach((f) => {
        const time = formatTime(msg.timestamp);
        const icon = f.side === 'prosecution' ? '⚔️' : f.side === 'defense' ? '🛡️' : f.isJudge ? '👨‍⚖️' : '📋';
        md.push(`#### ${icon} [Entry #${msgCounter}] ${f.speakerName} — *${f.roleBadge}* (\`${time}\`)`);
        if (f.metadataBadge) {
          md.push(`> **Docket Notice:** \`${f.metadataBadge}\`\n`);
        }
        if (f.introText) {
          md.push(f.introText);
        }
        if (f.bodyParagraphs) {
          f.bodyParagraphs.forEach((p) => md.push(`\n${p}`));
        }
        if (f.substantiveItems && f.substantiveItems.length > 0) {
          md.push(`\n*Submissions:*`);
          f.substantiveItems.forEach((item) => {
            const tag = item.tag ? ` *(${item.tag})*` : '';
            md.push(`- **${item.label}**${tag}: ${item.text}`);
          });
        }
        md.push(`\n`);
        msgCounter++;
      });
    });
  } else {
    md.push(`_No chat messages recorded yet._\n`);
  }

  // PART III: RESEARCH CHAMBER
  if (researchMessages.length > 0) {
    md.push(`\n---\n`);
    md.push(`## Part III: Research Chamber Memoranda\n`);
    researchMessages.forEach((msg, idx) => {
      const formattedList = getFormattedMessage(msg.agent, msg.payload);
      formattedList.forEach((f) => {
        md.push(`### 🔬 [Research Memo #${idx + 1}] ${f.speakerName} (\`${f.roleBadge}\`)`);
        if (f.introText) md.push(f.introText);
        if (f.bodyParagraphs) f.bodyParagraphs.forEach((p) => md.push(`\n${p}`));
        md.push(`\n`);
      });
    });
  }

  md.push(`\n---\n*Certified true transcript generated by the AI Court of India Adjudication Engine.*`);
  return md.join('\n');
}

/**
 * Generate Structured JSON containing entire case record, transcript, and verdict
 */
export function generateCourtRecordJson(options: ExportCourtRecordOptions): string {
  const { caseTitle, caseId, status, messages, judgment } = options;
  const courtroomAgentNames = [
    'case_understanding',
    'live_judge',
    'live_prosecutor',
    'live_defense',
    'live_evidence',
    'live_conflict',
    'judge',
  ];

  const exportObj = {
    court: 'AI Court of India — Supreme Judicial Bench',
    exported_at: new Date().toISOString(),
    case_title: caseTitle || 'State vs. Accused',
    case_id: caseId || judgment?.judgment_id || null,
    status,
    judgment: judgment || null,
    courtroom_chat_transcript: messages
      .filter((m) => courtroomAgentNames.includes(m.agent))
      .map((m) => ({
        id: m.id,
        agent: m.agent,
        timestamp: m.timestamp,
        formatted_messages: getFormattedMessage(m.agent, m.payload),
        raw_payload: m.payload,
      })),
    research_chamber_entries: messages
      .filter((m) => !courtroomAgentNames.includes(m.agent))
      .map((m) => ({
        id: m.id,
        agent: m.agent,
        timestamp: m.timestamp,
        formatted_messages: getFormattedMessage(m.agent, m.payload),
        raw_payload: m.payload,
      })),
  };

  return JSON.stringify(exportObj, null, 2);
}

/**
 * Browser download helper via Blob and URL object
 */
export function triggerFileDownload(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: `${mimeType};charset=utf-8;` });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/**
 * Printable Court Record: opens clean print dialog window
 */
export function printCourtRecord(options: ExportCourtRecordOptions) {
  const txtContent = generateCourtRecordTxt(options);
  const printWin = window.open('', '_blank', 'width=900,height=750');
  if (!printWin) {
    alert('Please allow popups to open the printable court record.');
    return;
  }

  const title = options.caseTitle || 'AI_Court_Record';
  printWin.document.write(`
    <!DOCTYPE html>
    <html>
      <head>
        <title>AI Court Record - ${title}</title>
        <style>
          body {
            font-family: 'Courier New', Courier, monospace;
            background: #ffffff;
            color: #111827;
            padding: 30px;
            font-size: 12px;
            line-height: 1.45;
          }
          pre {
            white-space: pre-wrap;
            word-wrap: break-word;
          }
          @media print {
            body { padding: 0; }
          }
        </style>
      </head>
      <body>
        <pre>${txtContent.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre>
        <script>
          window.onload = function() {
            window.print();
          };
        </script>
      </body>
    </html>
  `);
  printWin.document.close();
}

/**
 * Master download handler supporting multiple formats
 */
export function downloadCourtRecord(
  format: 'txt' | 'md' | 'json' | 'print',
  options: ExportCourtRecordOptions
) {
  const caseSlug = (options.caseTitle || options.caseId || 'Case')
    .replace(/\.[^/.]+$/, '')
    .replace(/[^a-zA-Z0-9_-]/g, '_')
    .slice(0, 32);
  const dateStr = new Date().toISOString().slice(0, 10);

  if (format === 'txt') {
    const text = generateCourtRecordTxt(options);
    triggerFileDownload(text, `AI_Court_Chat_and_Verdict_${caseSlug}_${dateStr}.txt`, 'text/plain');
  } else if (format === 'md') {
    const md = generateCourtRecordMd(options);
    triggerFileDownload(md, `AI_Court_Chat_and_Verdict_${caseSlug}_${dateStr}.md`, 'text/markdown');
  } else if (format === 'json') {
    const json = generateCourtRecordJson(options);
    triggerFileDownload(json, `AI_Court_Chat_and_Verdict_${caseSlug}_${dateStr}.json`, 'application/json');
  } else if (format === 'print') {
    printCourtRecord(options);
  }
}
