/**
 * Courtroom Replay — dialogue preparation (READ-ONLY).
 *
 * Builds a short, simple-English courtroom scene from an ALREADY COMPLETED
 * AI Court judgment. It never calls an agent, never calls an LLM and never
 * writes anything back. Every sentence spoken by a character is copied (and
 * lightly simplified / shortened) from the saved judgment, so no new facts,
 * witnesses, evidence or verdicts can be introduced.
 */
import type { Judgment } from '../types/court';

export type Speaker = 'judge' | 'prosecutor' | 'defense';
export type Emotion = 'neutral' | 'confident' | 'stern' | 'thinking' | 'surprised';
export type Gesture = 'none' | 'point' | 'open' | 'emphasis';

export interface DialogueLine {
  id: number;
  speaker: Speaker;
  text: string;
  emotion: Emotion;
  gesture: Gesture;
  /** Camera framing for this line. */
  camera: 'wide' | 'speaker' | 'verdict';
  /** Lines flagged optional are dropped first when the scene is too long. */
  optional?: boolean;
  /** Judge bangs the gavel when this line starts. */
  gavel?: boolean;
  /** Dramatic pacing cue: 'intro', 'interrupt' (snappy objection pan), 'verdict', or 'normal'. */
  cue?: 'normal' | 'intro' | 'interrupt' | 'verdict';
  /** Short scene-beat label shown in the corner while playing. */
  chapter?: string;
  /**
   * Locked lines (stock courtroom phrases and the verdict) are NEVER rewritten by the LLM
   * and are never sent to the backend. Only a fixed Hindi version (`hi`) is swapped in.
   */
  locked?: boolean;
  /** Fixed Hindi text for locked lines. */
  hi?: string;
  /** Language the current `text` is written in (drives which TTS voice is used). */
  lang?: Lang;
}

export type Lang = 'en' | 'hi';

export interface ServerScreenplayLine {
  id: number;
  speaker: Speaker;
  text: string;
  emotion?: Emotion;
  gesture?: Gesture;
  camera?: 'wide' | 'speaker' | 'verdict';
  gavel?: boolean;
  cue?: 'normal' | 'intro' | 'interrupt' | 'verdict';
  chapter?: string;
}

export interface ScreenplayRequestPayload {
  lang: Lang;
  case_title: string;
  case_background: string;
  issues: string[];
  prosecution_submissions: string;
  defense_submissions: string;
  evidence_assessment: string;
  witness_assessment: string;
  issue_summaries: Array<{ prosecution?: string; defense?: string; evidence?: string; finding?: string }>;
  reasons: string;
  final_decision: string;
}

export const CHARACTERS: Record<Speaker, { name: string; role: string }> = {
  judge: { name: 'Justice Meera Rao', role: 'Judge' },
  prosecutor: { name: 'Adv. Vikram Malhotra', role: 'Prosecutor' },
  defense: { name: 'Adv. Arjun Sharma', role: 'Defence Lawyer' },
};

const SIMPLIFY: Array<[RegExp, string]> = [
  [/\bthe learned (?:counsel|advocate|senior counsel)(?: for [^,.;]+)?/gi, 'the lawyer'],
  [/\bhereinafter (?:referred to as|called)[^,.;)]*/gi, ''],
  [/\binter alia\b/gi, 'among other things'],
  [/\bin the instant case\b/gi, 'in this case'],
  [/\bthe prosecution (?:has )?(?:submitted|contended|argued) that\b/gi, ''],
  [/\bthe defen[cs]e (?:has )?(?:submitted|contended|argued) that\b/gi, ''],
  [/\bit is (?:submitted|contended) that\b/gi, ''],
  [/\bthe said\b/gi, 'the'],
  [/\bsuch that\b/gi, 'so that'],
  [/\bnotwithstanding\b/gi, 'despite'],
  [/\bpursuant to\b/gi, 'under'],
  [/\bthereof\b/gi, ''],
  [/\bwhereas\b/gi, 'while'],
  [/\bappellant\b/gi, 'accused'],
  [/\bimpugned\b/gi, 'challenged'],
  [/\badduced\b/gi, 'presented'],
  [/\bcorroborat(?:e|ed|ion)\b/gi, 'support'],
  [/\bculpab(?:le|ility)\b/gi, 'guilt'],
  [/\bfoundational ingredient\b/gi, 'basic requirement'],
  [/\bbeyond reasonable doubt\b/gi, 'beyond reasonable doubt'],
  [/\u20B9\s*/g, 'Rs. '],
  [/\bI(?=\d{2,}[\d,]*\b)/g, 'Rs. '],
];

const clean = (t: unknown): string => {
  if (typeof t !== 'string') return '';
  let s = t.replace(/\s+/g, ' ').replace(/\*\*|__|`/g, '').replace(/\[[^\]]{0,40}\]/g, '').trim();
  for (const [re, rep] of SIMPLIFY) s = s.replace(re, rep);
  return s.replace(/\s+([,.;:])/g, '$1').replace(/\s{2,}/g, ' ').replace(/^[\s,;:.-]+/, '').trim();
};

/** Take whole sentences from `text` until `maxChars` is reached (always at least one, trimmed). */
export const brief = (text: unknown, maxChars = 170): string => {
  const s = clean(text);
  if (!s) return '';
  // Don't split sentences after abbreviations / initials / numbering (No., Md., M., Sec. 3 ...).
  const protectedText = s.replace(/\b(?:No|Nos|Md|Sd|Mr|Mrs|Ms|Dr|Sh|Smt|St|vs|Ors|Anr|Sec|Art|Cr|Crl|Dt|Rs|Ltd|[A-Z])\.(?=\s|$|[A-Z]\b)/g, (m) => m.slice(0, -1) + '\u0001');
  const sentences = (protectedText.match(/[^.!?]+[.!?]+|[^.!?]+$/g) ?? [protectedText]).map((x) => x.replace(/\u0001/g, '.'));
  let out = '';
  for (const sent of sentences) {
    const next = (out ? out + ' ' : '') + sent.trim();
    if (next.length > maxChars && out) break;
    out = next;
    if (out.length >= maxChars * 0.6) break;
  }
  if (out.length > maxChars + 30) {
    // Prefer ending at a natural clause break so the spoken line never stops mid-thought.
    const window = out.slice(0, maxChars + 20);
    const breaks = [window.lastIndexOf(';'), window.lastIndexOf(', and '), window.lastIndexOf(', but '), window.lastIndexOf(', while '), window.lastIndexOf(', so '), window.lastIndexOf(',')];
    const at = breaks.find((i) => i > 55) ?? -1;
    if (at > 0) {
      out = out.slice(0, at).replace(/[,;:\s]+$/, '') + '.';
    } else if (out.length > maxChars * 1.8) {
      const cut = out.slice(0, maxChars);
      const lastSpace = cut.lastIndexOf(' ');
      out = cut.slice(0, lastSpace > 60 ? lastSpace : maxChars).replace(/[,;:\s]+$/, '') + '.';
    } // otherwise keep the whole (slightly long) sentence intact
  }
  const first = out.charAt(0);
  return first.toUpperCase() + out.slice(1);
};


/** Light, deterministic "spoken" touch-ups (first person, contractions). Never changes meaning. */
const humanize = (text: string, speaker: Speaker): string => {
  let t = text;
  if (speaker === 'prosecutor') {
    t = t.replace(/(^|\. |, )(?:The )?[Pp]rosecution (?:submits|says|asserts|contends|alleges|states)(?: that)?\s+/g, '$1We say ');
    t = t.replace(/(^|\. |, )(?:The )?[Pp]rosecution relies on\s+/g, "$1We're relying on ");
    t = t.replace(/\b[Tt]he prosecution\b/g, 'we');
  } else if (speaker === 'defense') {
    t = t.replace(/(^|\. |, )(?:The )?[Dd]efen[cs]e (?:submits|says|asserts|contends|states)(?: that)?\s+/g, '$1Our position is that ');
    t = t.replace(/\b[Tt]he prosecution\b/g, 'the prosecution');
  }
  const contractions: Array<[RegExp, string]> = [
    [/\bdoes not\b/g, "doesn't"], [/\bdo not\b/g, "don't"], [/\bdid not\b/g, "didn't"], [/\bis not\b/g, "isn't"],
    [/\bare not\b/g, "aren't"], [/\bwas not\b/g, "wasn't"], [/\bwere not\b/g, "weren't"], [/\bhas not\b/g, "hasn't"],
    [/\bhave not\b/g, "haven't"], [/\bcannot\b/g, "can't"], [/\bwill not\b/g, "won't"], [/\bit is\b/g, "it's"],
  ];
  for (const [re, rep] of contractions) t = t.replace(re, rep);
  return t.replace(/\s{2,}/g, ' ').replace(/^we say\b/, 'We say').replace(/([.!?]\s+)we\b/g, '$1We');
};
const asSentence = (s: string) => (/[.!?…]$/.test(s) ? s : s + '.');

/** Short, speakable case name (drops bracketed registry details). */
const shortTitle = (t: string): string => {
  const s = clean(t).replace(/\([^)]*\)/g, '').replace(/\s{2,}/g, ' ').trim();
  if (s.length <= 90) return s || 'this case';
  const cut = s.slice(0, 90);
  return cut.slice(0, Math.max(40, cut.lastIndexOf(' '))).trim();
};

export const humanVerdict = (decision: string | undefined, lang: Lang = 'en'): string => {
  const d = (decision || '').toUpperCase();
  const hi = lang === 'hi';
  if (!d) return hi ? 'अदालत का फाइनल डिसीज़न' : 'the final decision recorded by this court';
  if (d.includes('PARTIAL')) return hi ? 'पार्शियल कन्विक्शन — यानी कुछ चार्जेज़ में गिल्टी' : 'partly guilty — a partial conviction';
  if (d.includes('CONVICT')) return hi ? 'गिल्टी — यानी आरोपी दोषी है' : 'guilty — a conviction';
  if (d.includes('ACQUIT')) return hi ? 'नॉट गिल्टी — यानी अक्यूज़्ड को बरी किया जाता है' : 'not guilty — the accused is acquitted';
  if (d.includes('BAIL') && d.includes('GRANT')) return hi ? 'बेल ग्रांट की जाती है — यानी ज़मानत मंज़ूर' : 'bail is granted';
  if (d.includes('BAIL') && (d.includes('REJECT') || d.includes('DENI'))) return hi ? 'बेल रिजेक्ट की जाती है — यानी ज़मानत नामंज़ूर' : 'bail is rejected';
  if (d.includes('QUASH')) return hi ? 'केस कैंसल यानी क्वैश किया जाता है' : 'the case is quashed';
  return decision!.toLowerCase().replace(/_/g, ' ');
};

const MAX_TOTAL_CHARS = 1150; // ≈ 60–80 seconds of speech at a lively movie pace
const MIN_TOTAL_CHARS = 380;

type Draft = Omit<DialogueLine, 'id'>;

/** Builds the deterministic fallback script. Always opens with the Judge explaining the case simply. */
export function buildDialogue(j: Judgment): DialogueLine[] {
  const lines: Draft[] = [];
  const add = (l: Draft) => { if (l.text.trim()) lines.push({ lang: 'en', cue: 'normal', ...l, text: l.locked ? l.text : humanize(l.text, l.speaker) }); };

  const issues = Array.isArray(j.issue_analyses) ? j.issue_analyses : [];
  const title = shortTitle(j.case_title);
  const background = brief(j.case_background, 150) || brief(j.issues_for_determination?.[0], 140);
  const prosOpening = brief(j.prosecution_submissions, 150);
  const defOpening = brief(j.defense_submissions, 150);
  const issue1 = issues[0];
  const issue2 = issues[1];

  // 1. Judge opens & explains the case in simple terms (non-optional)
  add({
    speaker: 'judge', emotion: 'stern', gesture: 'emphasis', camera: 'speaker', gavel: true, cue: 'intro', chapter: 'THE CASE', locked: true,
    text: `Order, order! Let's settle down. Today this court is hearing ${title}.`,
    hi: 'ऑर्डर, ऑर्डर! प्लीज़ बैठ जाइए। आज कोर्ट में हम यह केस सुन रहे हैं।',
  });
  if (background) {
    add({
      speaker: 'judge', emotion: 'neutral', gesture: 'open', camera: 'speaker', cue: 'intro', chapter: 'THE CASE',
      text: `To put it simply: ${background.charAt(0).toLowerCase() + background.slice(1)}`,
    });
  }
  add({
    speaker: 'judge', emotion: 'neutral', gesture: 'open', camera: 'wide', cue: 'intro', chapter: 'THE CASE', locked: true,
    text: 'Prosecutor, go ahead. Tell us your side.',
    hi: 'प्रोसिक्यूटर, चलिए शुरू कीजिए — आपका पॉइंट क्या है?',
  });

  // 2. Prosecution
  add({
    speaker: 'prosecutor', emotion: 'confident', gesture: 'point', camera: 'speaker', chapter: 'PROSECUTION',
    text: prosOpening ? `Thank you, Your Honour. ${asSentence(prosOpening)}` : 'Thank you, Your Honour. We stand by the case we have placed before this court.',
  });
  const pros1 = brief(issue1?.prosecution_submission_summary, 140);
  if (pros1 && pros1 !== prosOpening) {
    add({ speaker: 'prosecutor', emotion: 'confident', gesture: 'emphasis', camera: 'speaker', chapter: 'PROSECUTION', optional: true, text: asSentence(pros1) });
  }

  // 3. Dramatic Defence Objection
  add({
    speaker: 'defense', emotion: 'stern', gesture: 'point', camera: 'speaker', cue: 'interrupt', chapter: 'OBJECTION!',
    text: defOpening ? `Objection, Your Honour! ${asSentence(defOpening)}` : 'Objection, Your Honour! The prosecution has not proved this case.',
  });
  const def1 = brief(issue1?.defense_submission_summary, 140);
  if (def1 && def1 !== defOpening) {
    add({ speaker: 'defense', emotion: 'confident', gesture: 'emphasis', camera: 'speaker', chapter: 'DEFENCE', optional: true, text: asSentence(def1) });
  }

  // 4. Judge probes the evidence
  const evid = brief(issue1?.evidentiary_evaluation || j.evidence_assessment, 140);
  if (evid) {
    add({
      speaker: 'judge', emotion: 'thinking', gesture: 'open', camera: 'wide', chapter: 'THE EVIDENCE', optional: true,
      text: `Hold on — let me check the evidence on record. ${asSentence(evid)}`,
    });
  }

  // 5. Quick second round if saved output has a second issue
  const pros2 = brief(issue2?.prosecution_submission_summary, 120);
  const def2 = brief(issue2?.defense_submission_summary, 120);
  if (pros2) add({ speaker: 'prosecutor', emotion: 'surprised', gesture: 'point', camera: 'speaker', chapter: 'PROSECUTION', optional: true, text: asSentence(pros2) });
  if (def2) add({ speaker: 'defense', emotion: 'stern', gesture: 'emphasis', camera: 'speaker', chapter: 'DEFENCE', optional: true, text: asSentence(def2) });

  // 6. Judge's reasoning before verdict
  const rawFinding = brief(issue1?.judicial_finding, 140);
  const finding = rawFinding.length >= 30 && rawFinding !== rawFinding.toUpperCase() ? rawFinding : '';
  const reasons = brief(j.reasons, 160);
  if (finding) {
    add({ speaker: 'judge', emotion: 'neutral', gesture: 'open', camera: 'speaker', chapter: 'FINDING', text: `Alright, I've heard both sides. ${asSentence(finding)}` });
  } else if (!reasons) {
    add({
      speaker: 'judge', emotion: 'neutral', gesture: 'open', camera: 'speaker', chapter: 'FINDING', locked: true,
      text: 'Alright, I have listened to both sides carefully.',
      hi: 'ठीक है, मैंने दोनों साइड्स को ध्यान से सुन लिया है।',
    });
  }
  if (reasons) {
    add({ speaker: 'judge', emotion: 'stern', gesture: 'open', camera: 'speaker', chapter: 'FINDING', text: asSentence(reasons) });
  }

  // 7. Locked Verdict Line
  add({
    speaker: 'judge', emotion: 'stern', gesture: 'emphasis', camera: 'verdict', gavel: true, cue: 'verdict', chapter: 'FINAL VERDICT', locked: true,
    text: `So after hearing both sides, here is the Court's final decision: ${humanVerdict(j.final_decision, 'en')}. This court is adjourned!`,
    hi: `तो सब कुछ देखने के बाद, कोर्ट का फाइनल डिसीज़न यह है: ${humanVerdict(j.final_decision, 'hi')}। कोर्ट एडजर्न होती है!`,
  });

  // Fit duration: drop optional lines (last first) until under budget.
  const total = (ls: Draft[]) => ls.reduce((n, l) => n + l.text.length, 0);
  let out = [...lines];
  while (total(out) > MAX_TOTAL_CHARS) {
    let idx = -1;
    for (let i = out.length - 1; i >= 0; i--) if (out[i].optional) { idx = i; break; }
    if (idx === -1) break;
    out.splice(idx, 1);
  }
  let guard = 0;
  while (total(out) > MAX_TOTAL_CHARS * 1.1 && guard++ < 20) {
    const li = out.reduce((best, l, i) => (!l.locked && l.text.length > (out[best]?.text.length ?? 0) ? i : best), 0);
    if (out[li].locked) break;
    out[li] = { ...out[li], text: brief(out[li].text, Math.max(90, out[li].text.length - 50)) };
  }
  if (total(out) < MIN_TOTAL_CHARS) out = [...lines];
  return out.map((l, i) => ({ ...l, id: i }));
}

/** Packages read-only completed-case judgment fields for `POST /api/replay/screenplay`. */
export function buildScreenplayRequest(j: Judgment, lang: Lang): ScreenplayRequestPayload {
  const issuesList = Array.isArray(j.issues_for_determination) ? j.issues_for_determination.slice(0, 4) : [];
  const analyses = Array.isArray(j.issue_analyses) ? j.issue_analyses.slice(0, 2) : [];
  return {
    lang,
    case_title: String(j.case_title ?? ''),
    case_background: String(j.case_background ?? ''),
    issues: issuesList.map((x) => String(x ?? '').slice(0, 280)),
    prosecution_submissions: String(j.prosecution_submissions ?? ''),
    defense_submissions: String(j.defense_submissions ?? ''),
    evidence_assessment: String(j.evidence_assessment ?? ''),
    witness_assessment: String(j.witness_assessment ?? ''),
    issue_summaries: analyses.map((a) => ({
      prosecution: String(a?.prosecution_submission_summary ?? ''),
      defense: String(a?.defense_submission_summary ?? ''),
      evidence: String(a?.evidentiary_evaluation ?? ''),
      finding: String(a?.judicial_finding ?? ''),
    })),
    reasons: String(j.reasons ?? ''),
    final_decision: String(j.final_decision ?? ''),
  };
}

/** Converts validated server screenplay lines into playback-ready `DialogueLine[]`. */
export function fromServerScreenplay(lines: ServerScreenplayLine[] | undefined, lang: Lang): DialogueLine[] | null {
  if (!Array.isArray(lines) || lines.length < 6) return null;
  return lines.map((l, idx) => ({
    id: typeof l.id === 'number' ? l.id : idx,
    speaker: l.speaker,
    text: String(l.text || '').trim(),
    emotion: l.emotion ?? 'neutral',
    gesture: l.gesture ?? 'none',
    camera: l.camera ?? 'speaker',
    gavel: Boolean(l.gavel),
    cue: l.cue ?? 'normal',
    chapter: l.chapter ?? '',
    lang,
  }));
}

/** Lines the backend may rewrite (kept for /api/replay/localize backwards compatibility). */
export const rewritableLines = (script: DialogueLine[]) => script.filter((l) => !l.locked).map((l) => ({ id: l.id, speaker: l.speaker, text: l.text }));

/**
 * Applies the (optional) LLM rewrite. `rewritten` maps line id → new text, or is null if the
 * backend/LLM was unavailable. English falls back to the base text. Hindi without a rewrite
 * falls back to the complete English script so a case is never half-translated by guesswork.
 */
export function applyLocalization(base: DialogueLine[], lang: Lang, rewritten: Record<number, string> | null): { script: DialogueLine[]; usedLang: Lang } {
  if (lang === 'en') {
    return {
      usedLang: 'en',
      script: base.map((l) => (!l.locked && rewritten?.[l.id] ? { ...l, text: rewritten[l.id], lang: 'en' as Lang } : l)),
    };
  }
  if (!rewritten || Object.keys(rewritten).length === 0) return { usedLang: 'en', script: base };
  return {
    usedLang: 'hi',
    script: base.map((l) => {
      if (l.locked) return l.hi ? { ...l, text: l.hi, lang: 'hi' as Lang } : l;
      const t = rewritten[l.id];
      return t && t !== l.text ? { ...l, text: t, lang: 'hi' as Lang } : l;
    }),
  };
}
