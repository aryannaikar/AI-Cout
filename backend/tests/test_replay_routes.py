"""Isolated unit tests for the Courtroom Replay API routes (/api/replay/*)."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.replay_routes import (
    _LLMLines,
    _LLMScreenplay,
    _LLMScreenplayLine,
    LocalizedLine,
    build_locked_verdict_line,
)
from app.main import app

client = TestClient(app)


def _sample_request(lang: str = "en", decision: str = "ACQUITTAL") -> dict:
    return {
        "lang": lang,
        "case_title": "Md. Badruddin Ansari Bail Case",
        "case_background": "Police registered an FIR against unknown thieves after a bank wall was broken, though no cash was stolen. Co-accused Subham later named Badruddin.",
        "issues": ["Whether a co-accused statement alone can deny bail."],
        "prosecution_submissions": "Subham named Badruddin in custody and police noted a broken bank wall report.",
        "defense_submissions": "Badruddin is not named in the FIR, nothing was recovered from him, and no independent witness exists.",
        "evidence_assessment": "FIR is against unknown thieves; no stolen property or tools recovered; no independent panch witnesses.",
        "witness_assessment": "Only PW-1 Subham (co-accused) is cited; no civilian eye-witnesses.",
        "issue_summaries": [
            {
                "prosecution": "Relies on Subham's statement and broken wall memo.",
                "defense": "Co-accused custody statement has no corroboration.",
                "evidence": "No physical recovery links accused.",
                "finding": "NOT PROVED",
            }
        ],
        "reasons": "Charges are not proved because no property was recovered and there is no independent witness corroborating the co-accused.",
        "final_decision": decision,
    }


def test_screenplay_validates_strips_directions_and_appends_locked_verdict_en():
    fake_llm_output = _LLMScreenplay(
        lines=[
            _LLMScreenplayLine(
                speaker="Honourable Judge",
                text="*bangs gavel* Order, order! Today's case is simple: someone broke a bank wall, no money went missing, and Badruddin is accused only because another suspect named him.",
                emotion="firm",
                gesture="emphasis",
                camera="speaker",
                cue="intro",
                chapter="THE CASE",
            ),
            _LLMScreenplayLine(
                speaker="judge",
                text="Prosecutor, what do you have to show us?",
                emotion="neutral",
                gesture="open",
                camera="wide",
                cue="intro",
            ),
            _LLMScreenplayLine(
                speaker="Public Prosecutor",
                text="Your Honour, the co-accused Subham clearly named Badruddin, and the broken bank wall report supports our case.",
                emotion="confident",
                gesture="point",
                camera="speaker",
            ),
            _LLMScreenplayLine(
                speaker="Defence Counsel",
                text="[stands up] Objection, Your Honour! The FIR itself says 'unknown thieves' — my client isn't even named, and nothing was recovered from him!",
                emotion="stern",
                gesture="point",
                camera="speaker",
                cue="interrupt",
            ),
            _LLMScreenplayLine(
                speaker="judge",
                text="Hold on. Police prepared that wall report alone — did any independent civilian witness see a recovery or link him to the scene?",
                emotion="curious",
                gesture="open",
                camera="wide",
            ),
            _LLMScreenplayLine(
                speaker="prosecutor",
                text="We also have a police status report pointing to past cases, Your Honour.",
                emotion="defensive",
                gesture="emphasis",
                camera="speaker",
            ),
            _LLMScreenplayLine(
                speaker="defense",
                text="There's no certified conviction record, no stolen cash, no tools, and zero independent witnesses backing that claim.",
                emotion="confident",
                gesture="point",
                camera="speaker",
            ),
            _LLMScreenplayLine(
                speaker="judge",
                text="Alright, I've heard both sides. Without independent witnesses or recovered items, a co-accused's custody statement alone isn't enough.",
                emotion="neutral",
                gesture="open",
                camera="speaker",
            ),
        ]
    )

    with (
        patch("app.core.llm_provider.LLMConfig.provider", return_value="nvidia"),
        patch("app.services.llm_service.LLMService.generate_structured", return_value=fake_llm_output),
    ):
        resp = client.post("/api/replay/screenplay", json=_sample_request("en", "ACQUITTAL"))

    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "llm"
    assert data["lang"] == "en"
    lines = data["lines"]
    assert len(lines) == 9
    assert lines[0]["speaker"] == "judge"
    assert lines[0]["cue"] == "intro"
    assert lines[0]["gavel"] is True
    assert "*bangs gavel*" not in lines[0]["text"]
    assert lines[2]["speaker"] == "prosecutor"
    assert lines[3]["speaker"] == "defense"
    assert lines[3]["cue"] == "interrupt"
    assert "[stands up]" not in lines[3]["text"]
    # Locked final verdict line appended deterministically by server
    assert lines[-1]["speaker"] == "judge"
    assert lines[-1]["cue"] == "verdict"
    assert lines[-1]["camera"] == "verdict"
    assert lines[-1]["gavel"] is True
    assert "acquitted" in lines[-1]["text"].lower()


def test_screenplay_hindi_hinglish_normalization_and_locked_verdict():
    fake_hi_output = _LLMScreenplay(
        lines=[
            _LLMScreenplayLine(
                speaker="judge",
                text="ऑर्डर, ऑर्डर! आज कोर्ट में एक बैंक की दीवार टूटने का केस है — कोई कैश चोरी नहीं हुआ, बस को-अक्यूज़्ड के बयान पर बदरुद्दीन को फँसाया गया है।",
                emotion="stern",
                cue="intro",
                chapter="केस की कहानी",
            ),
            _LLMScreenplayLine(
                speaker="prosecutor",
                text="योर ऑनर, अभियोजन पक्ष का कहना है कि शुभम ने अपने स्टेटमेंट में साफ नाम लिया है और टूटी दीवार की रिपोर्ट भी है।",
                emotion="confident",
            ),
            _LLMScreenplayLine(
                speaker="defense",
                text="ऑब्जेक्शन, योर ऑनर! FIR में 'अननोन चोर' लिखा है, कोई रिकवरी नहीं हुई और कोई इंडिपेंडेंट विटनेस नहीं है!",
                emotion="stern",
                cue="interrupt",
            ),
            _LLMScreenplayLine(
                speaker="judge",
                text="एक मिनट — क्या पुलिस की रिपोर्ट पर किसी इंडिपेंडेंट गवाह के साइन हैं?",
                emotion="thinking",
            ),
            _LLMScreenplayLine(
                speaker="prosecutor",
                text="योर ऑनर, पुलिस स्टेटस रिपोर्ट में पुराने केस का ज़िक्र भी है।",
                emotion="surprised",
            ),
            _LLMScreenplayLine(
                speaker="defense",
                text="कोई पुराना सर्टिफाइड ऑर्डर नहीं है, न कोई सबूत — सिर्फ शक के बेस पर बेल नहीं रोकी जा सकती।",
                emotion="confident",
            ),
            _LLMScreenplayLine(
                speaker="judge",
                text="ठीक है, मैंने दोनों साइड्स सुन ली हैं। बिना किसी ठोस एविडेंस या विटनेस के केस साबित नहीं होता।",
                emotion="neutral",
            ),
        ]
    )

    with (
        patch("app.core.llm_provider.LLMConfig.provider", return_value="nvidia"),
        patch("app.services.llm_service.LLMService.generate_structured", return_value=fake_hi_output),
    ):
        resp = client.post("/api/replay/screenplay", json=_sample_request("hi", "PARTIAL CONVICTION"))

    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "llm"
    assert data["lang"] == "hi"
    lines = data["lines"]
    # Bookish label smoothed into natural Hinglish
    assert "अभियोजन पक्ष" not in lines[1]["text"]
    assert "प्रोसिक्यूशन" in lines[1]["text"]
    # Locked Hinglish verdict appended cleanly
    assert lines[-1] == build_locked_verdict_line("PARTIAL CONVICTION", "hi", len(lines) - 1).model_dump()
    assert "फाइनल डिसीज़न" in lines[-1]["text"]


def test_screenplay_falls_back_gracefully_on_mock_or_error_or_bad_output():
    with patch("app.core.llm_provider.LLMConfig.provider", return_value="mock"):
        r1 = client.post("/api/replay/screenplay", json=_sample_request("en"))
    assert r1.status_code == 200
    assert r1.json() == {"lang": "en", "source": "fallback", "lines": []}

    with (
        patch("app.core.llm_provider.LLMConfig.provider", return_value="nvidia"),
        patch("app.services.llm_service.LLMService.generate_structured", side_effect=RuntimeError("boom")),
    ):
        r2 = client.post("/api/replay/screenplay", json=_sample_request("hi"))
    assert r2.status_code == 200
    assert r2.json() == {"lang": "hi", "source": "fallback", "lines": []}

    # Reject Hindi payload that comes back half-English ("कोर्ट का निष्कर्ष — The prosecution failed...")
    half_english = _LLMScreenplay(
        lines=[
            _LLMScreenplayLine(
                speaker=s,
                text="कोर्ट का निष्कर्ष — The prosecution failed to prove anything under Section 379 IPC and the evidence fails completely.",
            )
            for s in ("judge", "prosecutor", "defense", "judge", "prosecutor", "judge")
        ]
    )
    half_english_dub = _LLMLines(
        lines=[LocalizedLine(id=i, text=l.text) for i, l in enumerate(half_english.lines)]
    )
    with (
        patch("app.core.llm_provider.LLMConfig.provider", return_value="nvidia"),
        patch("app.services.llm_service.LLMService.generate_structured", side_effect=[half_english, half_english_dub, half_english_dub]),
    ):
        r3 = client.post("/api/replay/screenplay", json=_sample_request("hi"))
    assert r3.status_code == 200
    assert r3.json()["source"] == "fallback"


def test_screenplay_two_pass_hinglish_dubbing_works():
    en_draft = _LLMScreenplay(
        lines=[
            _LLMScreenplayLine(speaker="judge", text="Order, order! Someone broke a bank wall, no cash went missing, and Badruddin is accused based on one statement.", cue="intro"),
            _LLMScreenplayLine(speaker="prosecutor", text="Your Honour, Subham directly named Badruddin and we have the broken wall report."),
            _LLMScreenplayLine(speaker="defense", text="Objection, Your Honour! Nothing was found on my client and no independent witness backed this up.", cue="interrupt"),
            _LLMScreenplayLine(speaker="judge", text="Did any civilian witness sign the police report or see anything at all?"),
            _LLMScreenplayLine(speaker="prosecutor", text="We also have a police status report mentioning earlier complaints."),
            _LLMScreenplayLine(speaker="judge", text="Without recovered items or an independent witness, suspicion alone is not enough."),
        ]
    )
    hi_dub = _LLMLines(
        lines=[
            LocalizedLine(id=0, text="ऑर्डर, ऑर्डर! आज का केस बड़ा सीधा है — बैंक की दीवार टूटी, कैश चोरी नहीं हुआ, और सिर्फ एक बयान पर बदरुद्दीन का नाम आया है।"),
            LocalizedLine(id=1, text="थैंक यू योर ऑनर! शुभम ने अपने स्टेटमेंट में सीधे बदरुद्दीन का नाम लिया है, और टूटी दीवार की रिपोर्ट भी है।"),
            LocalizedLine(id=2, text="ऑब्जेक्शन, योर ऑनर! मेरे क्लाइंट से कुछ भी बरामद नहीं हुआ और कोई इंडिपेंडेंट विटनेस भी नहीं है!"),
            LocalizedLine(id=3, text="एक मिनट — क्या किसी आम विटनेस ने पुलिस की रिपोर्ट पर साइन किए हैं?"),
            LocalizedLine(id=4, text="योर ऑनर, पुलिस स्टेटस रिपोर्ट में पुराने केस का ज़िक्र भी है।"),
            LocalizedLine(id=5, text="देखिए, बिना किसी रिकवरी या इंडिपेंडेंट विटनेस के सिर्फ शक काफी नहीं है।"),
        ]
    )

    with (
        patch("app.core.llm_provider.LLMConfig.provider", return_value="nvidia"),
        patch("app.services.llm_service.LLMService.generate_structured", side_effect=[en_draft, hi_dub]),
    ):
        resp = client.post("/api/replay/screenplay", json=_sample_request("hi", "ACQUITTAL"))

    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "llm"
    assert len(data["lines"]) == 7
    assert data["lines"][0]["chapter"] == "केस की कहानी"
    assert data["lines"][2]["cue"] == "interrupt"
    assert data["lines"][2]["chapter"] == "ऑब्जेक्शन!"
    assert data["lines"][-1]["cue"] == "verdict"
    assert "नॉट गिल्टी" in data["lines"][-1]["text"]


def test_localize_endpoint_still_backwards_compatible():
    with patch("app.core.llm_provider.LLMConfig.provider", return_value="mock"):
        r = client.post(
            "/api/replay/localize",
            json={"lang": "hi", "lines": [{"id": 1, "speaker": "judge", "text": "Look at the evidence carefully."}]},
        )
    assert r.status_code == 200
    assert r.json() == {
        "lang": "hi",
        "source": "fallback",
        "lines": [{"id": 1, "text": "Look at the evidence carefully."}],
    }
