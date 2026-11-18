"""
Model #2 Trainer: Evidentiary Defect & Doctrinal-Trigger Classifier
Dataset: 10,009 Supreme Court of India Decisions (overthelex/indian-court-decisions)
         + curated Indian Criminal Jurisprudence domain anchors
Architecture: TF-IDF (1-2 grams) + OneVsRestClassifier(LogisticRegression)
Output: backend/data/models/evidentiary_defect_classifier.joblib
"""

from __future__ import annotations

import os
import re
import time
from collections import Counter
import joblib
import numpy as np
import pandas as pd
from huggingface_hub import hf_hub_download
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MultiLabelBinarizer

DEFECT_PATTERNS: dict[str, list[str]] = {
    "NO_INDEPENDENT_PANCH_WITNESS": [
        r"\b(?:no|without|absence of|failed to join|non-examination of)\s+(?:any\s+)?independent\s+(?:public\s+|local\s+)?(?:witness|panch)",
        r"\bpanch\s+witness(?:es)?\s+turned\s+hostile\b",
        r"\bonly\s+police\s+witness(?:es)?\b",
    ],
    "GENERIC_UNIDENTIFIED_PROPERTY": [
        r"\b(?:no|without|lacking)\s+(?:serial\s+number|distinctive\s+mark|identification\s+mark|ownership\s+proof)",
        r"\b(?:unnumbered|unmarked)\s+(?:cash|currency|scrap|iron|articles|property)\b",
        r"\bidentity\s+of\s+(?:the\s+)?stolen\s+property\s+(?:not|never)\s+established\b",
    ],
    "NO_PRIOR_TIP_DOCK_ID": [
        r"\b(?:no|without|absence of)\s+(?:prior\s+)?(?:test\s+identification\s+parade|t\.?i\.?p\.?)\b",
        r"\bdock\s+identification\s+for\s+the\s+first\s+time\b",
    ],
    "CO_ACCUSED_CONFESSION_ONLY": [
        r"\bconfession(?:al)?\s+(?:statement\s+)?of\s+co-?accused\b",
        r"\bimplicated\s+(?:solely|only)\s+on\s+(?:the\s+)?basis\s+of\s+co-?accused\b",
        r"\bsection\s+30\s*(?:of\s+the\s+)?(?:indian\s+)?evidence\s+act\b",
    ],
    "OPEN_OR_JOINT_ACCESS_RECOVERY": [
        r"\brecover(?:ed|y)\s+from\s+(?:an\s+)?open\s+place\b",
        r"\baccessible\s+to\s+(?:all|general\s+public|others)\b",
        r"\bexclusive\s+(?:and\s+conscious\s+)?possession\s+not\s+(?:proved|established)\b",
    ],
    "MISSING_STATUTORY_SANCTION_OR_FSL": [
        r"\b(?:no|without|absence of|missing)\s+(?:valid\s+|previous\s+)?sanction\b",
        r"\bsection\s+39\s*(?:of\s+the\s+)?arms\s+act\b",
        r"\b(?:no|without|missing)\s+(?:fsl|forensic|ballistic|armourer)\s+report\b",
    ],
    "MISSING_ELECTRONIC_CERTIFICATE": [
        r"\b(?:65\s*b|section\s+63\s+bsa)\s+certificate\b",
        r"\belectronic\s+record.*?(?:inadmissible|without\s+certificate)\b",
    ],
    "UNEXPLAINED_DELAY_OR_CHAIN_GAP": [
        r"\b(?:unexplained|inordinate)\s+delay\s+in\s+(?:lodging\s+)?(?:the\s+)?f\.?i\.?r\b",
        r"\bchain\s+of\s+custody.*?(?:broken|doubtful|not\s+established)\b",
        r"\bmalkhana\s+register\s+not\s+produced\b",
    ],
}

COMPILED_DEFECTS = {
    code: [re.compile(pat, re.IGNORECASE) for pat in pats]
    for code, pats in DEFECT_PATTERNS.items()
}

# Curated Indian criminal jurisprudence domain anchor samples covering all 8 defect classes
CURATED_ANCHORS: list[tuple[str, list[str]]] = [
    (
        "Seizure memo prepared in a busy locality without joining independent public witnesses; only police personnel signed panchnama.",
        ["NO_INDEPENDENT_PANCH_WITNESS"],
    ),
    (
        "Search and seizure conducted at the scrap godown without any independent local resident present; panch witnesses turned hostile during trial.",
        ["NO_INDEPENDENT_PANCH_WITNESS"],
    ),
    (
        "Recovery of currency notes without serial numbers or distinctive identifying marks; ownership and identity of stolen property not established.",
        ["GENERIC_UNIDENTIFIED_PROPERTY"],
    ),
    (
        "Recovered common scrap iron pieces lacked railway identification stamping or expert comparison; no article test identification held.",
        ["GENERIC_UNIDENTIFIED_PROPERTY"],
    ),
    (
        "Witness identified the accused for the first time in the dock during trial with absence of prior Test Identification Parade (TIP).",
        ["NO_PRIOR_TIP_DOCK_ID"],
    ),
    (
        "No TIP conducted after arrest despite unknown assailants seen briefly at night; dock identification after two years is unreliable.",
        ["NO_PRIOR_TIP_DOCK_ID"],
    ),
    (
        "Accused implicated solely on the basis of confessional statement of co-accused recorded in police custody with zero independent recovery.",
        ["CO_ACCUSED_CONFESSION_ONLY"],
    ),
    (
        "Under Section 30 of the Indian Evidence Act, confession of co-accused cannot be substantive evidence without independent corroboration.",
        ["CO_ACCUSED_CONFESSION_ONLY"],
    ),
    (
        "Weapon alleged to be recovered under Section 27 disclosure from an open field accessible to general public; exclusive conscious possession not proved.",
        ["OPEN_OR_JOINT_ACCESS_RECOVERY"],
    ),
    (
        "Stolen articles seized from a jointly occupied ancestral room accessible to all family members; exclusive possession not established.",
        ["OPEN_OR_JOINT_ACCESS_RECOVERY"],
    ),
    (
        "Prosecution under Section 25 Arms Act launched without previous sanction of District Magistrate under Section 39 Arms Act and without ballistic FSL report.",
        ["MISSING_STATUTORY_SANCTION_OR_FSL"],
    ),
    (
        "Missing armourer or forensic laboratory report testing whether the seized country made pistol was in working condition.",
        ["MISSING_STATUTORY_SANCTION_OR_FSL"],
    ),
    (
        "Call detail records and CCTV electronic record tendered in evidence without mandatory certificate under Section 65B IEA / Section 63 BSA.",
        ["MISSING_ELECTRONIC_CERTIFICATE"],
    ),
    (
        "Digital video footage produced as secondary electronic record inadmissible for want of Section 65B(4) certificate.",
        ["MISSING_ELECTRONIC_CERTIFICATE"],
    ),
    (
        "Inordinate unexplained delay in lodging the FIR and sending special report to Magistrate; malkhana register not produced and chain of custody broken.",
        ["UNEXPLAINED_DELAY_OR_CHAIN_GAP"],
    ),
    (
        "Contraband samples remained unsealed for days and malkhana entry was missing, casting serious doubt on chain of custody.",
        ["UNEXPLAINED_DELAY_OR_CHAIN_GAP"],
    ),
    # Multi-defect real theft/recovery combinations
    (
        "Unmarked currency notes cash recovered without independent panch witness; no prior TIP held before dock identification.",
        ["GENERIC_UNIDENTIFIED_PROPERTY", "NO_INDEPENDENT_PANCH_WITNESS", "NO_PRIOR_TIP_DOCK_ID"],
    ),
    (
        "Police searched shop without independent public witnesses; co-accused named solely in custody confession; unsealed property missing malkhana link.",
        ["NO_INDEPENDENT_PANCH_WITNESS", "CO_ACCUSED_CONFESSION_ONLY", "UNEXPLAINED_DELAY_OR_CHAIN_GAP"],
    ),
    (
        "Recovered pistol from open bush accessible to all without independent witness, no Section 39 Arms Act sanction and no FSL report.",
        ["OPEN_OR_JOINT_ACCESS_RECOVERY", "NO_INDEPENDENT_PANCH_WITNESS", "MISSING_STATUTORY_SANCTION_OR_FSL"],
    ),
    (
        "Delay in lodging FIR; CDR electronic records lacked 65B certificate; recovered cash unnumbered without ownership proof.",
        ["UNEXPLAINED_DELAY_OR_CHAIN_GAP", "MISSING_ELECTRONIC_CERTIFICATE", "GENERIC_UNIDENTIFIED_PROPERTY"],
    ),
]


def extract_matching_windows(text: str) -> tuple[str, list[str]] | None:
    """Scan judgment upper window and return matching context + detected defect classes."""
    window = text[:12000]
    labels: list[str] = []
    match_spans: list[tuple[int, int]] = []

    for code, pat_list in COMPILED_DEFECTS.items():
        for pat in pat_list:
            m = pat.search(window)
            if m:
                labels.append(code)
                match_spans.append((max(0, m.start() - 250), min(len(window), m.end() + 250)))
                break

    if not labels:
        return None

    snippets = [re.sub(r"\s+", " ", window[s:e]).strip() for s, e in match_spans[:3]]
    combined = " ".join(snippets)
    return combined, sorted(set(labels))


def main() -> None:
    print("=" * 64)
    print("Model #2: Evidentiary Defect & Doctrinal-Trigger Classifier")
    print("=" * 64)

    cache_dir = (
        r"C:\Users\Aryan Naikar\.cache\huggingface\hub\datasets--overthelex--indian-court-decisions"
        r"\snapshots\30e604222ae94c9881dd42626b2cd07294cf1e56\supreme_court"
    )
    dfs = []
    for fname in ("validation.parquet", "test.parquet"):
        fpath = os.path.join(cache_dir, fname)
        if not os.path.exists(fpath):
            fpath = hf_hub_download(
                repo_id="overthelex/indian-court-decisions",
                filename=f"supreme_court/{fname}",
                repo_type="dataset",
            )
        dfs.append(pd.read_parquet(fpath))

    df = pd.concat(dfs, ignore_index=True)
    print(f"Loaded Supreme Court judgments: {len(df)}")

    t0 = time.time()
    records_x: list[str] = []
    records_y: list[list[str]] = []

    for text in df["full_text"].dropna():
        if len(text) < 400:
            continue
        res = extract_matching_windows(text)
        if res is not None:
            snippet, lbls = res
            records_x.append(snippet)
            records_y.append(lbls)

    print(f"Extracted {len(records_x)} SC defect passages in {time.time() - t0:.2f}s")

    # Add curated domain anchors (4x weight so rare defects have clear separator boundaries)
    for _ in range(4):
        for txt, lbls in CURATED_ANCHORS:
            records_x.append(txt)
            records_y.append(lbls)

    counts = Counter(lbl for sub in records_y for lbl in sub)
    print("\nDefect class support across dataset + anchors:")
    for code in sorted(DEFECT_PATTERNS.keys()):
        print(f"  - {code:34s}: {counts[code]} samples")

    classes = sorted(DEFECT_PATTERNS.keys())
    mlb = MultiLabelBinarizer(classes=classes)
    Y = mlb.fit_transform(records_y)

    X_train, X_test, Y_train, Y_test = train_test_split(
        records_x, Y, test_size=0.2, random_state=42
    )
    print(f"\nTraining samples: {len(X_train)} | Test samples: {len(X_test)}")

    t_fit = time.time()
    pipeline = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                ngram_range=(1, 2),
                max_features=20000,
                sublinear_tf=True,
                stop_words="english",
            ),
        ),
        (
            "clf",
            OneVsRestClassifier(
                LogisticRegression(
                    class_weight="balanced",
                    C=2.0,
                    max_iter=500,
                    solver="liblinear",
                    random_state=42,
                ),
                n_jobs=1,
            ),
        ),
    ])
    pipeline.fit(X_train, Y_train)
    print(f"Training completed in {time.time() - t_fit:.2f}s")

    probs = pipeline.predict_proba(X_test)
    Y_pred = (probs >= 0.35).astype(int)
    micro_f1 = f1_score(Y_test, Y_pred, average="micro", zero_division=0)
    macro_f1 = f1_score(Y_test, Y_pred, average="macro", zero_division=0)
    prec = precision_score(Y_test, Y_pred, average="micro", zero_division=0)
    rec = recall_score(Y_test, Y_pred, average="micro", zero_division=0)
    print(
        f"\nTest Evaluation (@0.35): Micro-F1={micro_f1*100:.2f}% | "
        f"Macro-F1={macro_f1*100:.2f}% | Precision={prec*100:.2f}% | Recall={rec*100:.2f}%"
    )

    out_dir = r"c:\Users\Aryan Naikar\OneDrive\Desktop\vs\AI-Court-of-India\backend\data\models"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "evidentiary_defect_classifier.joblib")
    joblib.dump(
        {
            "pipeline": pipeline,
            "mlb": mlb,
            "classes": list(mlb.classes_),
            "threshold": 0.35,
            "version": "1.0.0",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        out_path,
    )
    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    print(f"Saved model to: {out_path} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
