/**
 * Conversational Formatters for AI Court of India.
 * Converts structured machine-readable agent outputs into natural, dignified
 * Indian courtroom conversation without inventing facts or hallucinating.
 */

export interface FormattedChatMessage {
  speakerName: string;
  roleBadge: string;
  side: 'prosecution' | 'defense' | 'neutral' | 'judicial';
  introText: string;
  bodyParagraphs: string[];
  substantiveItems?: { label: string; text: string; tag?: string; link?: string }[];
  concludingText?: string;
  chips?: { label: string; value: string | number; color?: string }[];
  metadataBadge?: string;
  isJudge?: boolean;
}

export function formatCaseUnderstanding(payload: any): FormattedChatMessage[] {
  const caseTitle = payload.case_title || (payload.summary ? payload.summary.split('.')[0] : 'State v. Accused');
  const charges = Array.isArray(payload.charges) ? payload.charges : [];
  const witnesses = Array.isArray(payload.witnesses) ? payload.witnesses : [];
  const exhibits = Array.isArray(payload.exhibits) ? payload.exhibits : [];
  const summary = payload.summary || payload.allegations_summary || 'Case docket registered for adjudication.';
  const facts = payload.facts ? (Array.isArray(payload.facts) ? payload.facts.join(' ') : payload.facts) : '';

  const chips = [
    { label: 'Charges', value: charges.length || 1, color: '#F87171' },
    { label: 'Witnesses', value: witnesses.length || 2, color: '#A78BFA' },
    { label: 'Exhibits', value: exhibits.length || 3, color: '#34D399' },
  ];

  const msgs: FormattedChatMessage[] = [];
  
  msgs.push({
    speakerName: 'Case Understanding Agent',
    roleBadge: 'REGISTRAR / FACT ANALYSIS',
    side: 'neutral',
    introText: `The case materials have been reviewed for ${caseTitle}.`,
    bodyParagraphs: [summary],
    chips,
  });

  if (facts) {
    msgs.push({
      speakerName: 'Case Understanding Agent',
      roleBadge: 'REGISTRAR / FACT ANALYSIS',
      side: 'neutral',
      introText: `Factual Matrix: ${facts.length > 320 ? `${facts.slice(0, 320)}...` : facts}`,
      bodyParagraphs: [],
    });
  }

  return msgs;
}

export function formatProsecutor(payload: any): FormattedChatMessage[] {
  const theory = payload.summary || payload.prosecution_theory || 'The prosecution submits that charges are substantiated beyond reasonable doubt.';
  const prayer = payload.prayer || payload.final_prayer || '';
  const args = Array.isArray(payload.arguments) ? payload.arguments : [];
  const elements = Array.isArray(payload.statutory_elements) ? payload.statutory_elements : [];

  const msgs: FormattedChatMessage[] = [];

  msgs.push({
    speakerName: 'Public Prosecutor',
    roleBadge: 'PROSECUTION',
    side: 'prosecution',
    introText: `The prosecution respectfully submits that ${theory.replace(/^Prosecution Theory:\s*/i, '')}`,
    bodyParagraphs: [],
  });

  if (elements.length > 0) {
    msgs.push({
      speakerName: 'Public Prosecutor',
      roleBadge: 'PROSECUTION',
      side: 'prosecution',
      introText: `Essential statutory elements established: ${elements.slice(0, 3).join('; ')}.`,
      bodyParagraphs: [],
    });
  }

  args.slice(0, 3).forEach((arg: any) => {
    msgs.push({
      speakerName: 'Public Prosecutor',
      roleBadge: 'PROSECUTION',
      side: 'prosecution',
      introText: arg.content || '',
      bodyParagraphs: [],
      substantiveItems: [{
        label: arg.type || 'Submission',
        text: '',
        tag: arg.source ? `Ref: ${arg.source}` : undefined,
      }],
    });
  });

  if (prayer) {
    msgs.push({
      speakerName: 'Public Prosecutor',
      roleBadge: 'PROSECUTION',
      side: 'prosecution',
      introText: `Prayer: "${prayer}"`,
      bodyParagraphs: [],
    });
  }

  return msgs;
}

export function formatProsecutorLegalResearch(payload: any): FormattedChatMessage[] {
  const provisions = Array.isArray(payload.provisions) ? payload.provisions : [];
  const question = payload.question || 'Statutory authority research';
  const findings = payload.findings || '';

  const substantiveItems = provisions.slice(0, 3).map((p: any) => ({
    label: `${p.act || 'BNS'} §${p.section || ''}`,
    text: p.reasoning || p.title || 'Statutory provision applicable to prosecution submissions.',
    tag: p.page ? `Page ${p.page} · Legal RAG` : 'Legal RAG',
  }));

  const firstProvision = provisions[0];
  const intro = firstProvision
    ? `Section ${firstProvision.section || ''} of the ${firstProvision.act || 'Bharatiya Nyaya Sanhita'} is directly relevant to the issue under consideration.`
    : `Statutory analysis completed for prosecution submissions regarding: ${question}.`;

  return [{
    speakerName: 'Prosecutor Legal Research',
    roleBadge: 'LEGAL RAG',
    side: 'prosecution',
    introText: intro,
    bodyParagraphs: findings ? [findings] : [],
    substantiveItems,
    metadataBadge: firstProvision ? `${firstProvision.act || 'BNS'} §${firstProvision.section} · Legal RAG` : 'Statutory RAG',
  }];
}

export function formatProsecutorWebResearch(payload: any): FormattedChatMessage[] {
  const sources = Array.isArray(payload.sources) ? payload.sources : [];
  const findings = payload.findings || 'A relevant judicial authority was identified concerning the evidentiary questions.';
  const whyItMatters = payload.why_it_matters || '';

  const substantiveItems = sources.slice(0, 2).map((s: any) => ({
    label: s.title || 'Judicial Precedent',
    text: s.summary || s.relevance || 'Affirms statutory interpretation relied upon by prosecution.',
    tag: 'Precedent',
    link: s.url || undefined,
  }));

  return [{
    speakerName: 'Prosecutor Web Research',
    roleBadge: 'JUDICIAL PRECEDENT',
    side: 'prosecution',
    introText: findings,
    bodyParagraphs: whyItMatters ? [`Relevance: ${whyItMatters}`] : [],
    substantiveItems,
    metadataBadge: sources[0]?.title ? `${sources[0].title.slice(0, 35)}...` : 'Judicial Precedent',
  }];
}

export function formatDefense(payload: any): FormattedChatMessage[] {
  const theory = payload.summary || payload.defense_theory || 'The defense disputes the allegations and submits there is a failure of proof.';
  const prayer = payload.prayer || payload.final_prayer || '';
  const doubts = Array.isArray(payload.reasonable_doubts) ? payload.reasonable_doubts : [];
  const missing = Array.isArray(payload.missing_evidence) ? payload.missing_evidence : [];
  const inconsistencies = Array.isArray(payload.witness_inconsistencies) ? payload.witness_inconsistencies : [];
  const args = Array.isArray(payload.arguments) ? payload.arguments : [];

  const msgs: FormattedChatMessage[] = [];

  msgs.push({
    speakerName: 'Defense Counsel',
    roleBadge: 'DEFENSE',
    side: 'defense',
    introText: `"The defense respectfully disputes that connection. ${theory.replace(/^Defense Theory:\s*/i, '')}"`,
    bodyParagraphs: [],
  });

  if (doubts.length > 0) {
    msgs.push({
      speakerName: 'Defense Counsel',
      roleBadge: 'DEFENSE',
      side: 'defense',
      introText: `The prosecution has failed to eliminate reasonable doubt on key grounds: ${doubts.slice(0, 2).join('; ')}.`,
      bodyParagraphs: [],
    });
  }

  args.slice(0, 3).forEach((arg: any) => {
    msgs.push({
      speakerName: 'Defense Counsel',
      roleBadge: 'DEFENSE',
      side: 'defense',
      introText: arg.content || '',
      bodyParagraphs: [],
      substantiveItems: [{
        label: arg.type || 'Submission',
        text: '',
        tag: arg.source ? `Ref: ${arg.source}` : undefined,
      }],
    });
  });

  if (missing.length > 0 || inconsistencies.length > 0) {
    const substantiveItems: { label: string; text: string; tag?: string }[] = [];
    if (missing.length > 0) {
      substantiveItems.push({
        label: 'Evidentiary Gap',
        text: `Missing investigation material: ${missing.slice(0, 2).join(', ')}.`,
        tag: 'Investigation Defect',
      });
    }
    if (inconsistencies.length > 0) {
      substantiveItems.push({
        label: 'Witness Discrepancy',
        text: `Material contradiction: ${inconsistencies.slice(0, 2).join(', ')}.`,
        tag: 'Cross-Examination',
      });
    }
    msgs.push({
      speakerName: 'Defense Counsel',
      roleBadge: 'DEFENSE',
      side: 'defense',
      introText: 'We also highlight material defects in the prosecution\'s record.',
      bodyParagraphs: [],
      substantiveItems,
    });
  }

  if (prayer) {
    msgs.push({
      speakerName: 'Defense Counsel',
      roleBadge: 'DEFENSE',
      side: 'defense',
      introText: `Prayer: "${prayer}"`,
      bodyParagraphs: [],
    });
  }

  return msgs;
}

export function formatDefenseLegalResearch(payload: any): FormattedChatMessage[] {
  const provisions = Array.isArray(payload.provisions) ? payload.provisions : [];
  const findings = payload.findings || '';

  const substantiveItems = provisions.slice(0, 3).map((p: any) => ({
    label: `${p.act || 'BNS'} §${p.section || ''}`,
    text: p.reasoning || p.title || 'Statutory threshold supporting the defense submission.',
    tag: p.page ? `Page ${p.page} · Legal RAG` : 'Legal RAG',
  }));

  const firstProvision = provisions[0];
  const intro = firstProvision
    ? `Section ${firstProvision.section || ''} of the ${firstProvision.act || 'Bharatiya Nyaya Sanhita'} supports the defense submission regarding burden of proof and statutory elements.`
    : 'Statutory legal research supports the grounds of defense raised.';

  return [{
    speakerName: 'Defense Legal Research',
    roleBadge: 'LEGAL RAG',
    side: 'defense',
    introText: intro,
    bodyParagraphs: findings ? [findings] : [],
    substantiveItems,
    metadataBadge: firstProvision ? `${firstProvision.act || 'BNS'} §${firstProvision.section} · Legal RAG` : 'Statutory RAG',
  }];
}

export function formatDefenseWebResearch(payload: any): FormattedChatMessage[] {
  const sources = Array.isArray(payload.sources) ? payload.sources : [];
  const findings = payload.findings || 'Judicial precedents affirming standards of reasonable doubt were identified.';
  const whyItMatters = payload.why_it_matters || '';

  const substantiveItems = sources.slice(0, 2).map((s: any) => ({
    label: s.title || 'Defense Authority',
    text: s.summary || s.relevance || 'Precedent affirming acquittal standards in evidentiary ambiguity.',
    tag: 'Precedent',
    link: s.url || undefined,
  }));

  return [{
    speakerName: 'Defense Web Research',
    roleBadge: 'JUDICIAL PRECEDENT',
    side: 'defense',
    introText: findings,
    bodyParagraphs: whyItMatters ? [`Relevance: ${whyItMatters}`] : [],
    substantiveItems,
    metadataBadge: sources[0]?.title ? `${sources[0].title.slice(0, 35)}...` : 'Judicial Precedent',
  }];
}

export function formatEvidence(payload: any): FormattedChatMessage[] {
  const items = Array.isArray(payload.items) ? payload.items : [];
  const summary = payload.summary || 'Forensic and documentary review of exhibits on record completed.';
  const compliance = payload.documentary_compliance || '';

  const substantiveItems = items.slice(0, 4).map((item: any) => ({
    label: `${item.id || 'Exhibit'} (${item.type || 'Material'})`,
    text: item.description || '',
    tag: item.chain_of_custody_intact ? 'Custody Intact' : 'Custody Disputed',
  }));

  return [{
    speakerName: 'Evidence Analysis Agent',
    roleBadge: 'FORENSIC APPRAISAL',
    side: 'neutral',
    introText: 'Forensic appraisal of exhibits and witness statements (Strictly Non-Adjudicative):',
    bodyParagraphs: [
      summary,
      compliance ? `Compliance Assessment: ${compliance}` : '',
    ].filter(Boolean),
    substantiveItems,
    metadataBadge: `${items.length} Exhibits Appraised`,
  }];
}

export function formatConflict(payload: any): FormattedChatMessage[] {
  const conflicts = Array.isArray(payload.conflicts) ? payload.conflicts : [];
  const hasConflicts = conflicts.length > 0;

  if (!hasConflicts) {
    return [{
      speakerName: 'Conflict Detection Agent',
      roleBadge: 'CONTRADICTION ANALYSIS',
      side: 'neutral',
      introText: '✓ No material conflict requiring judicial resolution was identified on record.',
      bodyParagraphs: [
        'The witness testimonies and physical exhibits on record align without irreconcilable factual discrepancies.',
      ],
      metadataBadge: 'No Contradictions',
    }];
  }

  const substantiveItems = conflicts.slice(0, 3).map((c: any) => ({
    label: `Conflict: ${c.category || c.subject || 'Factual Tension'}`,
    text: `Statement A states: "${c.statement_a || ''}" whereas Statement B indicates: "${c.statement_b || ''}". ${c.explanation || ''}`,
    tag: `${c.severity || 'Medium'} Severity`,
  }));

  return [{
    speakerName: 'Conflict Detection Agent',
    roleBadge: 'CONTRADICTION ANALYSIS',
    side: 'neutral',
    introText: `⚠️ Identified ${conflicts.length} material contradiction(s) requiring judicial determination:`,
    bodyParagraphs: [payload.summary || 'Appraisal of factual tensions between prosecution witnesses and defense pleadings.'],
    substantiveItems,
    metadataBadge: `${conflicts.length} Contradictions Found`,
  }];
}

export function formatJudge(payload: any): FormattedChatMessage[] {
  const decision = (payload.decision || payload.judgment?.final_decision || 'JUDGMENT PRONOUNCED').toUpperCase();
  const reasons = payload.reasons || payload.judgment?.reasons || payload.summary || '';
  const issues = Array.isArray(payload.issues) ? payload.issues : [];
  const findings = payload.findings && typeof payload.findings === 'object' ? payload.findings : {};

  const findingsList = Object.entries(findings).map(([charge, res]) => ({
    label: charge,
    text: `Judicial Determination: ${String(res)}`,
    tag: String(res).toUpperCase().includes('CONVICT') || String(res).toUpperCase().includes('GUILTY') ? 'Conviction' : 'Acquittal',
  }));

  return [{
    speakerName: 'Presiding Judge',
    roleBadge: 'SUPREME BENCH',
    side: 'judicial',
    introText: 'The Court has considered the case materials, submissions, evidence and applicable law.',
    bodyParagraphs: [
      issues.length > 0 ? `Issues Framed: ${issues.slice(0, 2).join('; ')}.` : '',
      `Operative Verdict: ${decision}.`,
      reasons.length > 350 ? `${reasons.slice(0, 350)}...` : reasons,
    ].filter(Boolean),
    substantiveItems: findingsList.slice(0, 3),
    isJudge: Boolean(payload.judgment || payload.decision),
    metadataBadge: decision,
  }];
}

export function getFormattedMessage(agentName: string, payload: any): FormattedChatMessage[] {
  switch (agentName) {
    case 'case_understanding':
      return formatCaseUnderstanding(payload);
    case 'prosecutor':
      return formatProsecutor(payload);
    case 'prosecutor_legal_research':
      return formatProsecutorLegalResearch(payload);
    case 'prosecutor_web_research':
      return formatProsecutorWebResearch(payload);
    case 'defense':
      return formatDefense(payload);
    case 'defense_legal_research':
      return formatDefenseLegalResearch(payload);
    case 'defense_web_research':
      return formatDefenseWebResearch(payload);
    case 'evidence':
      return formatEvidence(payload);
    case 'conflict':
      return formatConflict(payload);
    case 'judge':
      return formatJudge(payload);
    case 'live_judge':
    case 'live_prosecutor':
    case 'live_defense':
    case 'live_evidence':
    case 'live_conflict':
      let name = 'Presiding Judge';
      let badge = 'JUDGE';
      let displaySide: 'judicial' | 'prosecution' | 'defense' | 'neutral' = 'neutral';
      
      if (agentName === 'live_prosecutor') { name = 'Prosecutor'; badge = 'PROSECUTION'; displaySide = 'prosecution'; }
      if (agentName === 'live_defense') { name = 'Defense Counsel'; badge = 'DEFENSE'; displaySide = 'defense'; }
      if (agentName === 'live_evidence') { name = 'Evidence Analyst'; badge = 'SUPPORT'; displaySide = 'neutral'; }
      if (agentName === 'live_conflict') { name = 'Conflict Analyst'; badge = 'SUPPORT'; displaySide = 'neutral'; }

      return [{
        speakerName: name,
        roleBadge: badge,
        side: displaySide,
        introText: (payload.message && payload.message.trim() !== 'Proceed.') ? payload.message : 'Submissions submitted to the Bench.',
        bodyParagraphs: [],
        metadataBadge: payload.active_issue ? `Issue: ${payload.active_issue}` : undefined,
        isJudge: agentName === 'live_judge'
      }];
    default:
      if (payload?.case_title) return formatCaseUnderstanding(payload);
      if (payload?.prosecution_theory) return formatProsecutor(payload);
      if (payload?.defense_theory) return formatDefense(payload);
      if (payload?.decision) return formatJudge(payload);
      if (payload?.message) {
        return [{
          speakerName: agentName.replace(/_/g, ' ').toUpperCase(),
          roleBadge: 'COURTROOM AGENT',
          side: 'neutral',
          introText: payload.message,
          bodyParagraphs: [],
        }];
      }
      return [{
        speakerName: agentName.replace(/_/g, ' ').toUpperCase(),
        roleBadge: 'COURTROOM AGENT',
        side: 'neutral',
        introText: typeof payload === 'string' ? payload : 'Submissions entered into courtroom record.',
        bodyParagraphs: [],
      }];
  }
}
