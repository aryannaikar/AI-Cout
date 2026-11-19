"""
Courtroom Replay — dialogue localisation & screenplay formatting (additive, stateless, read-only).

Takes an ALREADY COMPLETED AI Court judgment's saved text (never ground truth, never raw case packets)
and formats/rewrites it into a lively, movie-style courtroom scene in natural English or everyday
conversational Indian Hindi (Hinglish in Devanagari script).

SAFETY: this endpoint never reads or writes case files, never runs agents / the LangGraph workflow / RAG,
and never lets the LLM choose the verdict (the final verdict line is appended deterministically on the
server from `final_decision`). On any validation failure or LLM error, it safely falls back without
crashing or affecting any existing AI Court state.
"""

from __future__ import annotations

import inspect
import json
import logging
import os
import re
from typing import Dict, List, Literal, Optional, Type, TypeVar

from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()

_MAX_LINES = 16
_MAX_CHARS = 600

SpeakerLiteral = Literal["judge", "prosecutor", "defense"]
EmotionLiteral = Literal["neutral", "confident", "stern", "thinking", "surprised"]
GestureLiteral = Literal["none", "point", "open", "emphasis"]
CameraLiteral = Literal["wide", "speaker", "verdict"]
CueLiteral = Literal["normal", "intro", "interrupt", "verdict"]


# ---------------------------------------------------------------------------
# Existing /localize endpoint (kept backwards-compatible)
# ---------------------------------------------------------------------------


class LocalizeLine(BaseModel):
    id: int
    speaker: SpeakerLiteral
    text: str = Field(max_length=_MAX_CHARS)


class LocalizeRequest(BaseModel):
    lang: Literal["en", "hi"]
    lines: List[LocalizeLine] = Field(max_length=_MAX_LINES)


class LocalizedLine(BaseModel):
    id: int
    text: str


class LocalizeResponse(BaseModel):
    lang: str
    source: Literal["llm", "fallback"]
    lines: List[LocalizedLine]


class _LLMLines(BaseModel):
    lines: List[LocalizedLine]


_DEVANAGARI_DIGITS = str.maketrans("\u0966\u0967\u0968\u0969\u096a\u096b\u096c\u096d\u096e\u096f", "0123456789")
_NEG_RE = re.compile(
    r"\b(not|no|never|none|neither|nor|without|cannot|can't|failed|fails|fail|lacks?|lacking|false(?:ly)?|unproved|denied|denies)\b|n't\b",
    re.I,
)
_NUM_RE = re.compile(r"\d[\d,./-]*\d|\d")


def _numbers(text: str) -> List[str]:
    t = text.translate(_DEVANAGARI_DIGITS)
    return [n.replace(",", "") for n in _NUM_RE.findall(t)]


def _valid(src: str, out: str, lang: str) -> bool:
    out = (out or "").strip()
    if not out or len(out) > max(80, int(len(src) * 1.9)):
        return False
    out_nums = " ".join(_numbers(out))
    for n in _numbers(src):
        if n not in out_nums:
            return False
    if lang == "en":
        if bool(_NEG_RE.search(src)) != bool(_NEG_RE.search(out)):
            return False
    return True


_STYLE = {
    "judge": "calm, wise, fair, a little warm; speaks plainly like a respected senior person",
    "prosecutor": "confident and firm, speaks directly, a bit passionate",
    "defense": "sharp and sincere, politely challenging, quick to point out gaps",
}


def _prompt(req: LocalizeRequest) -> str:
    if req.lang == "hi":
        lang_rule = (
            "Write in natural, everyday conversational Indian Hindi mixed with common English words (local Hinglish, "
            "written in Devanagari script like a Bollywood courtroom movie — e.g. Jolly LLB or Pink). "
            "Use familiar spoken words like कोर्ट, केस, प्रोसिक्यूटर, डिफेंस, एविडेंस, प्रूफ, ऑब्जेक्शन, योर ऑनर, विटनेस, रिपोर्ट, अक्यूज़्ड, बेल, FIR. "
            "NEVER use heavy pure Sanskritized words like अभियोजन पक्ष, बचाव पक्ष, न्यायालय, साक्ष्य, आरोपपत्र, दोषसिद्धि, दोषमुक्त. "
            "Write numbers with ordinary digits (0-9). Write names and places in Devanagari."
        )
    else:
        lang_rule = (
            "Write in simple, natural spoken English like real people talking in a courtroom scene in a movie: short sentences, "
            "everyday words, contractions (it's, doesn't, we're) are welcome. No legalese, no stiff phrases like 'the prosecution submits that'."
        )
    items = [{"id": l.id, "speaker": l.speaker, "style": _STYLE[l.speaker], "text": l.text} for l in req.lines]
    return (
        "Rewrite each courtroom line so it sounds like a real person speaking aloud in a gripping movie scene.\n"
        f"{lang_rule}\n"
        "STRICT RULES: keep exactly the SAME meaning and facts; add NOTHING new (no new witnesses, evidence, confessions, "
        "arguments, events or opinions); do not drop or flip any 'not' / 'no' / 'failed' meaning; keep every number, date, "
        "section, amount and name; do not change who is speaking; each line stays at most 2 short sentences; "
        "keep the same ids and the same number of lines. Output JSON only: {\"lines\":[{\"id\":0,\"text\":\"...\"}]}\n\n"
        + json.dumps(items, ensure_ascii=False)
    )


@router.post("/localize", response_model=LocalizeResponse)
def localize_dialogue(req: LocalizeRequest) -> LocalizeResponse:
    original = [LocalizedLine(id=l.id, text=l.text) for l in req.lines]
    fallback = LocalizeResponse(lang=req.lang, source="fallback", lines=original)
    if not req.lines:
        return fallback
    try:
        from app.core.llm_provider import LLMConfig
        from app.services.llm_service import LLMService

        if LLMConfig.provider() == "mock":
            return fallback
        out = LLMService(agent_name="courtroom_replay_localizer").generate_structured(
            prompt=_prompt(req),
            response_schema=_LLMLines,
            system_prompt=(
                "You are a careful script editor. You rephrase existing courtroom dialogue into natural spoken language "
                "without changing any fact. Output valid JSON only."
            ),
        )
    except Exception as exc:  # noqa: BLE001 - replay must never raise into the app
        logger.warning("Replay localisation unavailable, using original lines: %s", exc)
        return fallback

    by_id = {l.id: l.text.strip() for l in out.lines}
    result: List[LocalizedLine] = []
    changed = 0
    for l in req.lines:
        cand = by_id.get(l.id, "")
        if _valid(l.text, cand, req.lang):
            result.append(LocalizedLine(id=l.id, text=cand))
            changed += 1
        else:
            if cand:
                logger.info("Replay line %s rejected by validation; keeping original", l.id)
            result.append(LocalizedLine(id=l.id, text=l.text))
    return LocalizeResponse(lang=req.lang, source="llm" if changed else "fallback", lines=result)


# ---------------------------------------------------------------------------
# Movie-drama /screenplay endpoint
# ---------------------------------------------------------------------------


class ScreenplayRequest(BaseModel):
    lang: Literal["en", "hi"] = "en"
    case_title: str = ""
    case_background: str = ""
    issues: List[str] = Field(default_factory=list)
    prosecution_submissions: str = ""
    defense_submissions: str = ""
    evidence_assessment: str = ""
    witness_assessment: str = ""
    issue_summaries: List[Dict[str, str]] = Field(default_factory=list)
    reasons: str = ""
    final_decision: str = ""


class ScreenplayLine(BaseModel):
    id: int
    speaker: SpeakerLiteral
    text: str
    emotion: EmotionLiteral = "neutral"
    gesture: GestureLiteral = "none"
    camera: CameraLiteral = "speaker"
    gavel: bool = False
    cue: CueLiteral = "normal"
    chapter: str = ""


class ScreenplayResponse(BaseModel):
    lang: Literal["en", "hi"]
    source: Literal["llm", "fallback"]
    lines: List[ScreenplayLine]


class _LLMScreenplayLine(BaseModel):
    speaker: str = "judge"
    text: str = ""
    emotion: str = "neutral"
    gesture: str = "none"
    camera: str = "speaker"
    cue: str = "normal"
    chapter: str = ""


class _LLMScreenplay(BaseModel):
    lines: List[_LLMScreenplayLine]


_DEVANAGARI_RE = re.compile(r"[\u0900-\u097f]")
_LATIN_ALPHA_RE = re.compile(r"[A-Za-z]")


def _deva_ratio(text: str) -> float:
    deva = len(_DEVANAGARI_RE.findall(text or ""))
    latin = len(_LATIN_ALPHA_RE.findall(text or ""))
    total = deva + latin
    return (deva / total) if total else 0.0
_STAGE_DIR_RE = re.compile(r"(?:\*[^*\n]{1,60}\*|\[[^\]\n]{1,50}\]|\((?:bangs|calmly|sternly|laughs|sighs|points|looking|turns|interrupts|quietly|loudly|pause|gavel)[^)\n]{0,40}\))", re.I)

_BOOKISH_HINDI_SWAPS: List[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?<![\u0900-\u097f])आप्शन(?![\u0900-\u097f])"), "ऑब्जेक्शन"),
    (re.compile(r"एक्सीडेंटेड"), "अक्यूज़्ड"),
    (re.compile(r"गिल्टीि"), "गिल्टी"),
    (re.compile(r"अभियोजन पक्ष"), "प्रोसिक्यूशन"),
    (re.compile(r"(?<![\u0900-\u097f])अभियोजन(?![\u0900-\u097f])"), "प्रोसिक्यूशन"),
    (re.compile(r"बचाव पक्ष"), "डिफेंस"),
    (re.compile(r"न्यायालय"), "कोर्ट"),
    (re.compile(r"माननीय न्यायाधीश"), "योर ऑनर"),
    (re.compile(r"अधिवक्ता"), "लॉयर"),
    (re.compile(r"साक्ष्य"), "सबूत"),
    (re.compile(r"आरोपपत्र"), "चार्जशीट"),
    (re.compile(r"परिवादी"), "कम्प्लेनेंट"),
    (re.compile(r"प्रत्यर्थी"), "रेस्पॉन्डेंट"),
    (re.compile(r"स्वतंत्र गवाह"), "इंडिपेंडेंट विटनेस"),
    (re.compile(r"दोषसिद्ध"), "गिल्टी"),
    (re.compile(r"दोषमुक्त"), "बरी"),
    (re.compile(r"निराधार"), "बेबुनियाद"),
    (re.compile(r"कार्यवाही समाप्त"), "कोर्ट एडजर्न"),
]


_LEGAL_PLAIN_SWAPS: List[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bfoundational ingredient\b", re.I), "basic proof"),
    (re.compile(r"\bdispositive\b", re.I), "decisive"),
    (re.compile(r"\bantecedents\b", re.I), "past cases on record"),
    (re.compile(r"\bsubstantive proof\b", re.I), "standalone proof"),
    (re.compile(r"\binadmissible\b", re.I), "not usable as proof"),
    (re.compile(r"\bcorroborat(?:e|ed|ion)\b", re.I), "independent backup"),
    (re.compile(r"\buncorroborated\b", re.I), "without any backup"),
    (re.compile(r"\bbeyond reasonable doubt\b", re.I), "clearly beyond doubt"),
    (re.compile(r"\bdishonest intent\b", re.I), "wrongful intent"),
    (re.compile(r"\bsubmits that\b", re.I), "says"),
    (re.compile(r"\bcontends that\b", re.I), "argues"),
]


def _clip_text(val: str, limit: int, simplify_legalese: bool = False) -> str:
    s = re.sub(r"\s+", " ", (val or "")).strip()
    # Fix common PDF-OCR currency glyph ('I25,000' -> 'Rs. 25,000') before showing to LLM
    s = s.replace("\u20b9", "Rs. ")
    s = re.sub(r"\bI(?=\d[\d,]*\b)", "Rs. ", s)
    if simplify_legalese:
        for pat, rep in _LEGAL_PLAIN_SWAPS:
            s = pat.sub(rep, s)
        s = re.sub(r"\s{2,}", " ", s).strip()
    if len(s) <= limit:
        return s
    cut = s[:limit].rsplit(" ", 1)[0].strip()
    return cut or s[:limit].strip()


def _strip_stage_directions(text: str) -> str:
    cleaned = _STAGE_DIR_RE.sub("", text or "")
    # Clean leftover quotes/whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip().strip('"').strip()
    return cleaned


def _polish_hinglish(text: str) -> str:
    out = text
    for pat, rep in _BOOKISH_HINDI_SWAPS:
        out = pat.sub(rep, out)
    out = re.sub(r"([\u0900-\u097f])([A-Za-z])", r"\1 \2", out)
    return re.sub(r"\s{2,}", " ", out).strip()


def _norm_speaker(raw: str) -> Optional[SpeakerLiteral]:
    s = (raw or "").strip().lower()
    if any(k in s for k in ("judge", "court", "justice", "honour", "honor", "magistrate", "जज")):
        return "judge"
    if any(k in s for k in ("prosecut", "state", "pp", "प्रोसिक्यूट", "सरकारी")):
        return "prosecutor"
    if any(k in s for k in ("defen", "accused", "petitioner", "appellant", "डिफेंस", "बचाव")):
        return "defense"
    return None


def _norm_emotion(raw: str) -> EmotionLiteral:
    s = (raw or "").strip().lower()
    if s in ("neutral", "confident", "stern", "thinking", "surprised"):
        return s  # type: ignore[return-value]
    if any(k in s for k in ("angry", "firm", "serious", "strict", "sharp")):
        return "stern"
    if any(k in s for k in ("curious", "question", "thoughtful", "doubt")):
        return "thinking"
    if any(k in s for k in ("shock", "alarm", "defensive")):
        return "surprised"
    if any(k in s for k in ("strong", "passionate", "assertive")):
        return "confident"
    return "neutral"


def _norm_gesture(raw: str) -> GestureLiteral:
    s = (raw or "").strip().lower()
    if s in ("none", "point", "open", "emphasis"):
        return s  # type: ignore[return-value]
    if "hand" in s or "warn" in s or "object" in s:
        return "emphasis"
    return "open"


def _norm_camera(raw: str) -> CameraLiteral:
    s = (raw or "").strip().lower()
    if s in ("wide", "speaker", "verdict"):
        return s  # type: ignore[return-value]
    return "speaker"


def _norm_cue(raw: str) -> CueLiteral:
    s = (raw or "").strip().lower()
    if s in ("normal", "intro", "interrupt", "verdict"):
        return s  # type: ignore[return-value]
    if "object" in s or "interject" in s:
        return "interrupt"
    return "normal"


def _human_verdict(decision: str, lang: Literal["en", "hi"]) -> str:
    d = (decision or "").upper()
    hi = lang == "hi"
    if not d:
        return "अदालत का फाइनल डिसीज़न" if hi else "the final decision recorded by this Court"
    if "PARTIAL" in d:
        return "पार्शियल कन्विक्शन — यानी कुछ चार्जेज़ में गिल्टी" if hi else "partly guilty — a partial conviction"
    if "CONVICT" in d:
        return "गिल्टी — यानी आरोपी दोषी है" if hi else "guilty — a conviction"
    if "ACQUIT" in d:
        return "नॉट गिल्टी — यानी अक्यूज़्ड को बरी किया जाता है" if hi else "not guilty — the accused is acquitted"
    if "BAIL" in d and "GRANT" in d:
        return "बेल ग्रांट की जाती है — यानी ज़मानत मंज़ूर" if hi else "bail is granted"
    if "BAIL" in d and ("REJECT" in d or "DENI" in d):
        return "बेल रिजेक्ट की जाती है — यानी ज़मानत नामंज़ूर" if hi else "bail is rejected"
    if "QUASH" in d:
        return "केस कैंसल यानी क्वैश किया जाता है" if hi else "the case is quashed"
    return decision.lower().replace("_", " ")


def build_locked_verdict_line(final_decision: str, lang: Literal["en", "hi"], line_id: int) -> ScreenplayLine:
    verdict_phrase = _human_verdict(final_decision, lang)
    if lang == "hi":
        text = f"तो सब कुछ देखने के बाद, कोर्ट का फाइनल डिसीज़न यह है: {verdict_phrase}। कोर्ट एडजर्न होती है!"
        chapter = "फाइनल डिसीज़न"
    else:
        text = f"So after hearing both sides, here is the Court's final decision: {verdict_phrase}. This court is adjourned!"
        chapter = "FINAL VERDICT"
    return ScreenplayLine(
        id=line_id,
        speaker="judge",
        text=text,
        emotion="stern",
        gesture="emphasis",
        camera="verdict",
        gavel=True,
        cue="verdict",
        chapter=chapter,
    )


def _default_chapter(speaker: SpeakerLiteral, idx: int, cue: CueLiteral, lang: Literal["en", "hi"]) -> str:
    if lang == "hi":
        if idx == 0 or cue == "intro":
            return "केस की कहानी"
        if cue == "interrupt":
            return "ऑब्जेक्शन!"
        if speaker == "prosecutor":
            return "प्रोसिक्यूशन"
        if speaker == "defense":
            return "डिफेंस"
        return "जज का सवाल" if idx <= 5 else "निष्कर्ष"
    if idx == 0 or cue == "intro":
        return "THE CASE"
    if cue == "interrupt":
        return "OBJECTION!"
    if speaker == "prosecutor":
        return "PROSECUTION"
    if speaker == "defense":
        return "DEFENCE"
    return "THE EVIDENCE" if idx <= 5 else "FINDING"


def _screenplay_prompt(req: ScreenplayRequest, force_lang: Optional[Literal["en", "hi"]] = None) -> str:
    target_lang = force_lang or req.lang
    facts_payload = {
        "case_title": _clip_text(req.case_title, 180),
        "case_background": _clip_text(req.case_background, 800, simplify_legalese=True),
        "main_questions": [_clip_text(i, 220, simplify_legalese=True) for i in req.issues[:4] if (i or "").strip()],
        "prosecution_side": _clip_text(req.prosecution_submissions, 750, simplify_legalese=True),
        "defense_side": _clip_text(req.defense_submissions, 750, simplify_legalese=True),
        "evidence_assessment": _clip_text(req.evidence_assessment, 650, simplify_legalese=True),
        "witness_assessment": _clip_text(req.witness_assessment, 550, simplify_legalese=True),
        "key_issues_breakdown": [
            {k: _clip_text(str(v), 240, simplify_legalese=True) for k, v in item.items() if v}
            for item in req.issue_summaries[:2]
        ],
        "court_reasoning": _clip_text(req.reasons, 750, simplify_legalese=True),
        "final_decision": _clip_text(req.final_decision, 80),
    }

    if target_lang == "hi":
        language_block = (
            "LANGUAGE & TONE (MOST IMPORTANT — READ CAREFULLY):\n"
            "- Write in everyday, spoken Indian Hindi mixed naturally with light English words — just like Bollywood courtroom dramas "
            "(Jolly LLB / Pink) or daily Indian conversation. Write ALL Hindi and English loanwords in DEVANAGARI script.\n"
        )
        verdict_note = (
            "IMPORTANT: Do NOT announce the final verdict ('Court adjourned', 'बरी किया जाता है', etc.) in your lines — "
            "your last Judge line MUST simply explain WHY before handing down the verdict."
        )
    else:
        language_block = (
            "LANGUAGE & TONE (MOST IMPORTANT — READ CAREFULLY):\n"
            "- Write like a gripping, natural modern courtroom drama movie: short spoken sentences, everyday contractions "
            "('it's', 'didn't', 'doesn't', 'we're', 'that's'), and crisp dramatic tension.\n"
            "- ZERO stiff legalese! REWRITE sentences freshly in plain everyday conversation — NEVER copy-paste from `court_reasoning`:\n"
            "  * Instead of 'coupled with / collectively establish' -> say 'backed by' or 'points right to'\n"
            "  * Instead of 'inadmissible as substantive proof / uncorroborated' -> say 'can't count on its own' or 'has zero independent backup'\n"
            "  * Instead of 'foundational ingredient / dispositive / beyond reasonable doubt' -> say 'basic requirement / decisive / proven clearly'\n"
            "  * Instead of 'dishonest intent / prior criminal antecedents / substantiate' -> say 'wrongful intent / past police cases / back that up'\n"
            "  * Instead of listing statute sections ('BNS Sections 331(4), 305, 62') -> name the plain act (theft, attempted break-in, receiving stolen money)!\n"
            "- NEVER let the Judge's intro spoil or judge witnesses yet — first neutrally explain the story so both lawyers fight it out!\n"
        )
        verdict_note = (
            "IMPORTANT: Do NOT deliver the final 'this court is adjourned / final verdict' line yourself — the system appends "
            "the locked verdict line right after your last Judge line. Your last Judge line must be 1–2 short everyday-English sentences explaining WHY."
        )

    return (
        "Turn the completed AI Court judgment below into a gripping 7-to-9 line courtroom movie scene.\n\n"
        f"{language_block}\n"
        "SCENE STRUCTURE (follow this exact story arc; 7 to 9 lines total):\n"
        "1. speaker='judge', cue='intro', camera='speaker', emotion='stern', chapter='THE CASE':\n"
        "   - Start with 'Order, order!' FIRST, explain what this case is actually about in simple everyday words "
        "so anyone watching with zero legal knowledge instantly gets it: who the accused is, what allegedly happened, "
        "and what question the Court has to decide. Keep it neutral (don't spoil who wins!) and call on the Prosecutor.\n"
        "2. speaker='prosecutor', cue='normal', camera='speaker', emotion='confident', gesture='point', chapter='PROSECUTION':\n"
        "   - Confident, conversational opening hitting the strongest real point from prosecution_side.\n"
        "3. speaker='defense', cue='interrupt', camera='speaker', emotion='stern', gesture='point', chapter='OBJECTION!':\n"
        "   - Dramatic interruption! Start with 'Objection, Your Honour!' and strike straight at the biggest flaw/gap in defense_side.\n"
        "4. speaker='judge', cue='normal', camera='wide', emotion='thinking', gesture='open', chapter='THE EVIDENCE':\n"
        "   - Steps in and asks one sharp, direct question probing the key evidence or witness gap.\n"
        "5. speaker='prosecutor', cue='normal', camera='speaker', emotion='surprised' or 'confident', gesture='emphasis', chapter='PROSECUTION':\n"
        "   - Pushes back directly using another real detail from the record.\n"
        "6. speaker='defense', cue='normal', camera='speaker', emotion='confident', gesture='point', chapter='DEFENCE':\n"
        "   - Sharp counter-punch on what is missing or unproven.\n"
        "7. speaker='judge', cue='normal', camera='speaker', emotion='neutral', gesture='open', chapter='FINDING':\n"
        "   - Calmly wraps up in 1–2 short plain-English sentences WHY the proof held up or fell short (matching court_reasoning).\n\n"
        "ACCURACY & SAFETY RULES (CRITICAL):\n"
        "- Ground EVERY single fact, person name, amount, and event strictly in CASE DATA below.\n"
        "- NEVER invent new people, places, witnesses, evidence, confessions, numbers, or side stories.\n"
        "- Spoken lines ONLY: no markdown (`**`), no asterisks/brackets (`*bangs gavel*`, `[sighs]`), no narrator text.\n"
        "- Keep EVERY line crisp and speakable: 1 to 2 short sentences (15 to 40 words, under 260 characters).\n"
        f"- {verdict_note}\n\n"
        "Output valid JSON matching this schema:\n"
        "{\"lines\":[{\"speaker\":\"judge|prosecutor|defense\",\"text\":\"...\",\"emotion\":\"neutral|confident|stern|thinking|surprised\",\"gesture\":\"none|point|open|emphasis\",\"camera\":\"wide|speaker\",\"cue\":\"intro|normal|interrupt\",\"chapter\":\"...\"}]}\n\n"
        "CASE DATA (READ-ONLY):\n"
        + json.dumps(facts_payload, ensure_ascii=False)
    )


def _hinglish_dub_prompt(lines: List[ScreenplayLine]) -> str:
    items = [{"id": l.id, "speaker": l.speaker, "text": l.text} for l in lines]
    return (
        "Translate these short English courtroom lines into natural, everyday spoken Hindi mixed with ONLY A LITTLE "
        "easy English (the authentic local Bollywood Hinglish people actually speak daily in India).\n\n"
        "RULES (FOLLOW STRICTLY):\n"
        "- BALANCE: ~80% simple everyday Hindi grammar & verbs ('फैसला करना', 'साबित करना', 'टिक नहीं सकता', 'पकड़ा गया', "
        "'बयान दिया', 'भरोसा करना') + ~20% easy familiar English nouns written cleanly in DEVANAGARI "
        "(like ऑर्डर, कोर्ट, केस, प्रोसिक्यूटर, डिफेंस, ऑब्जेक्शन, योर ऑनर, प्रूफ, विटनेस, स्टेटमेंट, रिपोर्ट, बेल, पुलिस, कैश, डाउट, पॉइंट, क्लाइंट, कन्फेशन, सीरियल नंबर).\n"
        "- NEVER write clunky English verbs/idioms transliterated into Hindi such as: 'बूटस्ट्रैप', 'किक करता है', 'क्रिएट करते', 'बैक्ड', "
        "'सस्टेन', 'डिसाइड', 'स्टैंड कर सकता', 'अलेजेज्ड', 'प्रिजम्पशन', 'फाउंडेशन' — translate those concepts into plain conversational Hindi!\n"
        "- Write ALL sentences AND ALL person/place names in DEVANAGARI script (NEVER write Roman Hindi or half-English words; "
        "keep ONLY short tags like FIR, CCTV, PW-1, PW-30, Section 411, Rs. and digits 0-9 in English).\n"
        "- Always translate `'Objection, Your Honour!'` as `'ऑब्जेक्शन, योर ऑनर!'`.\n"
        "- Keep EVERY negative ('not', 'no', 'never', 'can't', 'without', 'none') 100% accurate — never flip meanings.\n"
        "- Keep facts, numbers, and names faithful to the input lines (never add new facts).\n"
        "- Return actual JSON DATA values ONLY (never JSON Schema, `$defs`, or `properties`). Keep same ids and count.\n"
        "Format: {\"lines\":[{\"id\":0,\"text\":\"ऑर्डर, ऑर्डर! ...\"},{\"id\":1,\"text\":\"योर ऑनर, ...\"}]}\n\n"
        + json.dumps(items, ensure_ascii=False)
    )


def _validate_and_build(
    raw_lines: List[_LLMScreenplayLine],
    req: ScreenplayRequest,
    target_lang: Optional[Literal["en", "hi"]] = None,
) -> Optional[List[ScreenplayLine]]:
    lang_mode = target_lang or req.lang
    if not raw_lines or not (6 <= len(raw_lines) <= 10):
        return None

    built: List[ScreenplayLine] = []
    for idx, item in enumerate(raw_lines):
        speaker = _norm_speaker(item.speaker)
        if speaker is None:
            return None
        text = _strip_stage_directions(item.text)
        if lang_mode == "hi":
            text = _polish_hinglish(text)
            if _deva_ratio(text) < 0.40:
                return None
        if not (10 <= len(text) <= 440):
            return None

        cue = _norm_cue(item.cue)
        if idx == 0:
            cue = "intro"
        elif cue == "verdict":
            cue = "normal"

        camera = _norm_camera(item.camera)
        if camera == "verdict":
            camera = "speaker"

        raw_chap = _clip_text(_strip_stage_directions(item.chapter), 28)
        bad_hi_chap = lang_mode == "hi" and raw_chap and not _DEVANAGARI_RE.search(raw_chap)
        repeated_intro_chap = idx > 1 and raw_chap.upper() in ("THE CASE", "INTRO")
        chapter = _default_chapter(speaker, idx, cue, lang_mode) if (not raw_chap or bad_hi_chap or repeated_intro_chap) else raw_chap
        built.append(
            ScreenplayLine(
                id=idx,
                speaker=speaker,
                text=text,
                emotion=_norm_emotion(item.emotion),
                gesture=_norm_gesture(item.gesture),
                camera=camera,
                gavel=(idx == 0 and speaker == "judge"),
                cue=cue,
                chapter=chapter,
            )
        )

    speakers_seen = {l.speaker for l in built}
    if speakers_seen != {"judge", "prosecutor", "defense"}:
        return None
    if built[0].speaker != "judge" or built[-1].speaker != "judge":
        return None

    # Ensure at least one dramatic interruption cues when defense speaks first
    if not any(l.cue == "interrupt" for l in built):
        first_def = next((l for l in built if l.speaker == "defense"), None)
        if first_def:
            first_def.cue = "interrupt"
            if not first_def.chapter or first_def.chapter in ("DEFENCE", "डिफेंस"):
                first_def.chapter = "ऑब्जेक्शन!" if lang_mode == "hi" else "OBJECTION!"

    built.append(build_locked_verdict_line(req.final_decision, lang_mode, len(built)))
    return built


_SchemaT = TypeVar("_SchemaT", bound=BaseModel)


def _call_replay_llm(
    service: object,
    prompt: str,
    response_schema: Type[_SchemaT],
    system_prompt: str,
) -> _SchemaT:
    """
    Prefer `nvidia/nemotron-3-ultra-550b-a55b` for natural courtroom drama and accurate Devanagari Hinglish
    when NVIDIA NIM is the active provider (falling back to the default configured LLMService).
    Honors unit-test patches on `LLMService.generate_structured`.
    """
    from app.core.llm_provider import LLMConfig, NvidiaLLMClient
    from app.services.llm_service import LLMService

    is_patched = not inspect.isfunction(getattr(LLMService, "generate_structured", None)) or hasattr(
        LLMService.generate_structured, "assert_called"
    )
    if LLMConfig.provider() == "nvidia" and not is_patched:
        model_id = os.getenv("REPLAY_LLM_MODEL", "nvidia/nemotron-3-ultra-550b-a55b").strip()
        if model_id:
            try:
                return NvidiaLLMClient(model=model_id).generate_structured(
                    prompt=prompt,
                    response_schema=response_schema,
                    system_prompt=system_prompt,
                )
            except Exception as exc:  # noqa: BLE001 - fall back to centralized LLMService
                logger.warning("Replay preferred model '%s' failed (%s); falling back to LLMService", model_id, exc)

    return service.generate_structured(  # type: ignore[attr-defined]
        prompt=prompt,
        response_schema=response_schema,
        system_prompt=system_prompt,
    )


@router.post("/screenplay", response_model=ScreenplayResponse)
def generate_screenplay(req: ScreenplayRequest) -> ScreenplayResponse:
    """
    Generate a movie-style courtroom screenplay from an already completed AI Court judgment.
    Read-only and stateless; returns `source='fallback'` on any error so the client can drop
    seamlessly back to its deterministic script.
    """
    fallback = ScreenplayResponse(lang=req.lang, source="fallback", lines=[])
    try:
        from app.core.llm_provider import LLMConfig
        from app.services.llm_service import LLMService

        if LLMConfig.provider() == "mock":
            return fallback

        service = LLMService(agent_name="courtroom_replay_screenplay")
        # For Hindi/Hinglish, generate plain conversational movie English first so legalese is stripped cleanly,
        # unless the provider/mock already returned valid Devanagari Hinglish directly.
        out = _call_replay_llm(
            service,
            prompt=_screenplay_prompt(req, force_lang="en"),
            response_schema=_LLMScreenplay,
            system_prompt=(
                "You are an acclaimed courtroom-drama screenwriter. Turn factual court case records into vivid, "
                "simple, human dialogue while remaining 100% faithful to the facts. Output valid JSON only."
            ),
        )
    except Exception as exc:  # noqa: BLE001 - replay must never break the app
        logger.warning("Replay screenplay generation unavailable, falling back: %s", exc)
        return fallback

    if req.lang == "hi":
        direct_hi = _validate_and_build(out.lines, req, target_lang="hi")
        if direct_hi:
            return ScreenplayResponse(lang="hi", source="llm", lines=direct_hi)

        en_lines = _validate_and_build(out.lines, req, target_lang="en")
        if not en_lines:
            logger.info("Replay screenplay rejected at English movie-draft stage (count=%s)", len(out.lines))
            return fallback

        pre_verdict = en_lines[:-1]
        for attempt in range(2):
            try:
                dubbed = _call_replay_llm(
                    service,
                    prompt=_hinglish_dub_prompt(pre_verdict),
                    response_schema=_LLMLines,
                    system_prompt=(
                        "You are a Bollywood courtroom dialogue writer. Dub English movie lines into natural, everyday "
                        "spoken Hindi with light English words, written cleanly in Devanagari script without changing facts or negations. Output populated data JSON only."
                    ),
                )
                by_id = {l.id: l.text for l in dubbed.lines}
            except Exception as exc:  # noqa: BLE001
                logger.warning("Replay Hinglish dubbing attempt %d failed: %s", attempt + 1, exc)
                continue

            hi_lines: List[ScreenplayLine] = []
            valid_dub = True
            for idx, src in enumerate(pre_verdict):
                hi_text = _polish_hinglish(_strip_stage_directions(by_id.get(src.id, "")))
                if not (10 <= len(hi_text) <= 440) or _deva_ratio(hi_text) < 0.40:
                    logger.info("Replay Hinglish line %s failed validation (attempt=%d, ratio=%.2f)", src.id, attempt + 1, _deva_ratio(hi_text))
                    valid_dub = False
                    break
                hi_lines.append(
                    src.model_copy(
                        update={
                            "text": hi_text,
                            "chapter": _default_chapter(src.speaker, idx, src.cue, "hi"),
                        }
                    )
                )
            if valid_dub and len(hi_lines) == len(pre_verdict):
                hi_lines.append(build_locked_verdict_line(req.final_decision, "hi", len(hi_lines)))
                return ScreenplayResponse(lang="hi", source="llm", lines=hi_lines)
        return fallback

    lines = _validate_and_build(out.lines, req, target_lang="en")
    if not lines:
        logger.info("Replay screenplay rejected by validation (lang=%s, count=%s)", req.lang, len(out.lines))
        return fallback

    return ScreenplayResponse(lang=req.lang, source="llm", lines=lines)
