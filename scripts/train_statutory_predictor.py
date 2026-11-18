"""
Statutory & Companion-Section Predictor Pipeline (v2 - High Recall & Balanced)
Trained on 10,000+ Supreme Court Decisions (overthelex/indian-court-decisions)
"""

import os
import re
import sys
import time
import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.multiclass import OneVsRestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, f1_score, precision_score, recall_score
from sklearn.preprocessing import MultiLabelBinarizer

# Priority Statutory Targets in Indian Law
TARGET_SECTIONS = [
    # Violent Offences
    "IPC_302", "IPC_304", "IPC_304B", "IPC_307", "IPC_323", "IPC_324", "IPC_325", "IPC_326", "IPC_376",
    # Theft & Stolen Property (Core Companions)
    "IPC_379", "IPC_380", "IPC_392", "IPC_395", "IPC_397", "IPC_411", "IPC_412", "IPC_420", "IPC_467", "IPC_468", "IPC_471",
    # Group & Common Intention
    "IPC_34", "IPC_120B", "IPC_147", "IPC_148", "IPC_149", "IPC_201", "IPC_506",
    # Evidence Act Doctrines
    "IEA_27", "IEA_102", "IEA_106", "IEA_114", "IEA_32",
    # Procedural Safeguards
    "CRPC_100", "CRPC_154", "CRPC_161", "CRPC_164", "CRPC_313", "CRPC_439", "CRPC_482",
    # Special Statutes
    "ARMS_25", "ARMS_27", "ARMS_39", "NDPS_8", "NDPS_20", "NDPS_21", "RPUP_3"
]

SECTION_PATTERNS = {
    "IPC_302": [r"\b(?:section|sec\.?|s\.)\s*302\b", r"\b302\s*(?:ipc|indian penal code)\b", r"\bmurder\b"],
    "IPC_304": [r"\b(?:section|sec\.?|s\.)\s*304\s*part\b", r"\bculpable\s+homicide\s+not\s+amounting\s+to\s+murder\b"],
    "IPC_304B": [r"\b(?:section|sec\.?|s\.)\s*304\s*b\b", r"\bdowry\s+death\b"],
    "IPC_307": [r"\b(?:section|sec\.?|s\.)\s*307\b", r"\battempt\s+to\s+murder\b"],
    "IPC_323": [r"\b(?:section|sec\.?|s\.)\s*323\b", r"\bvoluntarily\s+causing\s+hurt\b"],
    "IPC_324": [r"\b(?:section|sec\.?|s\.)\s*324\b", r"\bdangerous\s+weapon\b"],
    "IPC_325": [r"\b(?:section|sec\.?|s\.)\s*325\b", r"\bgrievous\s+hurt\b"],
    "IPC_326": [r"\b(?:section|sec\.?|s\.)\s*326\b"],
    "IPC_376": [r"\b(?:section|sec\.?|s\.)\s*376\b", r"\brape\b"],
    "IPC_379": [r"\b(?:section|sec\.?|s\.)\s*379\b", r"\btheft\b", r"\bstolen\b"],
    "IPC_380": [r"\b(?:section|sec\.?|s\.)\s*380\b", r"\btheft\s+in\s+dwelling\s+house\b"],
    "IPC_392": [r"\b(?:section|sec\.?|s\.)\s*392\b", r"\brobbery\b"],
    "IPC_395": [r"\b(?:section|sec\.?|s\.)\s*395\b", r"\bdacoity\b"],
    "IPC_397": [r"\b(?:section|sec\.?|s\.)\s*397\b"],
    "IPC_411": [r"\b(?:section|sec\.?|s\.)\s*411\b", r"\breceiving\s+stolen\s+property\b", r"\bstolen\s+property\b", r"\bscrap\s+godown\b"],
    "IPC_412": [r"\b(?:section|sec\.?|s\.)\s*412\b"],
    "IPC_420": [r"\b(?:section|sec\.?|s\.)\s*420\b", r"\bcheating\b", r"\bdishonestly\s+inducing\b"],
    "IPC_467": [r"\b(?:section|sec\.?|s\.)\s*467\b", r"\bforgery\s+of\s+valuable\s+security\b"],
    "IPC_468": [r"\b(?:section|sec\.?|s\.)\s*468\b", r"\bforgery\s+for\s+purpose\s+of\s+cheating\b"],
    "IPC_471": [r"\b(?:section|sec\.?|s\.)\s*471\b", r"\busing\s+as\s+genuine\b"],
    "IPC_34": [r"\b(?:section|sec\.?|s\.)\s*34\b", r"\bcommon\s+intention\b", r"\br/w\s*34\b"],
    "IPC_120B": [r"\b(?:section|sec\.?|s\.)\s*120\s*b\b", r"\bcriminal\s+conspiracy\b"],
    "IPC_147": [r"\b(?:section|sec\.?|s\.)\s*147\b", r"\brioting\b"],
    "IPC_148": [r"\b(?:section|sec\.?|s\.)\s*148\b", r"\brioting,\s+armed\b"],
    "IPC_149": [r"\b(?:section|sec\.?|s\.)\s*149\b", r"\bunlawful\s+assembly\b", r"\br/w\s*149\b"],
    "IPC_201": [r"\b(?:section|sec\.?|s\.)\s*201\b", r"\bcausing\s+disappearance\s+of\s+evidence\b"],
    "IPC_506": [r"\b(?:section|sec\.?|s\.)\s*506\b", r"\bcriminal\s+intimidation\b"],
    "IEA_27": [r"\b(?:section|sec\.?|s\.)\s*27\s*(?:of\s+the\s+)?(?:indian\s+)?evidence\s*act\b", r"\bdisclosure\s+statement\b", r"\brecovery\s+under\s+section\s+27\b", r"\bpolice\s+custody\s+recovery\b"],
    "IEA_102": [r"\b(?:section|sec\.?|s\.)\s*102\s*(?:of\s+the\s+)?(?:indian\s+)?evidence\s*act\b", r"\bburden\s+of\s+proof\b", r"\bburden\s+of\s+the\s+prosecution\b"],
    "IEA_106": [r"\b(?:section|sec\.?|s\.)\s*106\s*(?:of\s+the\s+)?(?:indian\s+)?evidence\s*act\b", r"\bespecially\s+within\s+the\s+knowledge\b"],
    "IEA_114": [r"\b(?:section|sec\.?|s\.)\s*114\s*(?:of\s+the\s+)?(?:indian\s+)?evidence\s*act\b", r"\bpresumption\s+of\s+fact\b", r"\bpresumption\s+under\s+section\s+114\b"],
    "IEA_32": [r"\b(?:section|sec\.?|s\.)\s*32\s*(?:of\s+the\s+)?(?:indian\s+)?evidence\s*act\b", r"\bdying\s+declaration\b"],
    "CRPC_100": [r"\b(?:section|sec\.?|s\.)\s*100\s*(?:of\s+the\s+)?(?:cr\.?p\.?c|code\s+of\s+criminal\s+procedure)\b", r"\bindependent\s+witness\b.*?\b(?:search|recovery|seizure)\b"],
    "CRPC_154": [r"\b(?:section|sec\.?|s\.)\s*154\s*(?:of\s+the\s+)?(?:cr\.?p\.?c|code\s+of\s+criminal\s+procedure)\b", r"\bfirst\s+information\s+report\b"],
    "CRPC_161": [r"\b(?:section|sec\.?|s\.)\s*161\s*(?:of\s+the\s+)?(?:cr\.?p\.?c|code\s+of\s+criminal\s+procedure)\b", r"\bstatement\s+under\s+section\s+161\b"],
    "CRPC_164": [r"\b(?:section|sec\.?|s\.)\s*164\s*(?:of\s+the\s+)?(?:cr\.?p\.?c|code\s+of\s+criminal\s+procedure)\b", r"\bconfession\s+under\s+section\s+164\b"],
    "CRPC_313": [r"\b(?:section|sec\.?|s\.)\s*313\s*(?:of\s+the\s+)?(?:cr\.?p\.?c|code\s+of\s+criminal\s+procedure)\b", r"\bexamination\s+of\s+the\s+accused\b"],
    "CRPC_439": [r"\b(?:section|sec\.?|s\.)\s*439\s*(?:of\s+the\s+)?(?:cr\.?p\.?c|code\s+of\s+criminal\s+procedure)\b", r"\bapplication\s+for\s+bail\b"],
    "CRPC_482": [r"\b(?:section|sec\.?|s\.)\s*482\s*(?:of\s+the\s+)?(?:cr\.?p\.?c|code\s+of\s+criminal\s+procedure)\b", r"\binherent\s+powers\s+to\s+quash\b"],
    "ARMS_25": [r"\bsection\s*25\b.*?\barms\s*act\b", r"\barms\s*act\b.*?\bsection\s*25\b", r"\bcountry\s+made\s+pistol\b", r"\bfirearm\b", r"\bcartridge\b"],
    "ARMS_27": [r"\bsection\s*27\b.*?\barms\s*act\b", r"\buse\s+of\s+unlicensed\s+firearm\b"],
    "ARMS_39": [r"\bsection\s*39\b.*?\barms\s*act\b", r"\bsanction\s+under\s+the\s+arms\s+act\b", r"\bdistrict\s+magistrate\s+sanction\b"],
    "NDPS_8": [r"\bsection\s*8\b.*?\bndps\b", r"\bndps\b.*?\bsection\s*8\b"],
    "NDPS_20": [r"\bsection\s*20\b.*?\bndps\b", r"\bganja\b", r"\bcharas\b", r"\bcannabis\b"],
    "NDPS_21": [r"\bsection\s*21\b.*?\bndps\b", r"\bheroin\b", r"\bsmack\b", r"\bpsychotropic\b"],
    "RPUP_3": [r"\bsection\s*3\b.*?\brp\s*\(?up\)?\b", r"\brailway\s+property\s+\(unlawful\s+possession\)\b", r"\brailway\s+stores\b", r"\brailway\s+angle\s+plate\b"]
}

COMPILED_PATTERNS = {
    sec: [re.compile(p, re.IGNORECASE) for p in patterns]
    for sec, patterns in SECTION_PATTERNS.items()
}

# Companion Rules (Domain Legal Knowledge for Indian Criminal Law)
COMPANION_EXPANSION = {
    "IPC_411": ["IPC_379", "IEA_114", "CRPC_100"],
    "IPC_412": ["IPC_395", "IEA_114"],
    "IPC_302": ["IPC_34", "IEA_27", "IEA_102"],
    "IPC_307": ["IPC_34", "IPC_324"],
    "ARMS_25": ["ARMS_39", "CRPC_100"],
    "RPUP_3": ["IPC_379", "IEA_114", "CRPC_100"],
    "IPC_420": ["IPC_120B", "IPC_468", "IPC_471"]
}

def extract_labels_from_text(text: str) -> list[str]:
    """Scan text for statutory presence."""
    labels = []
    # Search upper 15,000 characters
    search_window = text[:15000]
    for sec, pat_list in COMPILED_PATTERNS.items():
        for pat in pat_list:
            if pat.search(search_window):
                labels.append(sec)
                break
    return labels

def extract_facts_feature(text: str) -> str:
    """Extract factual opening / narrative before legal citations overwhelm."""
    lines = [line.strip() for line in text.split("\n") if len(line.strip()) > 30]
    if len(lines) >= 3:
        body = " ".join(lines[1:20])
    else:
        body = text[:3500]
    return re.sub(r"\s+", " ", body).strip()

def build_companion_predictor():
    print("=" * 60)
    print("Statutory & Companion-Section Predictor Pipeline (v2)")
    print("=" * 60)

    # 1. Load Parquet Slices (10,009 judgments)
    cache_dir = r"C:\Users\Aryan Naikar\.cache\huggingface\hub\datasets--overthelex--indian-court-decisions\snapshots\30e604222ae94c9881dd42626b2cd07294cf1e56\supreme_court"
    val_path = os.path.join(cache_dir, "validation.parquet")
    test_path = os.path.join(cache_dir, "test.parquet")

    dfs = []
    if os.path.exists(val_path):
        dfs.append(pd.read_parquet(val_path))
    if os.path.exists(test_path):
        dfs.append(pd.read_parquet(test_path))

    df = pd.concat(dfs, ignore_index=True)
    print(f"Total Supreme Court judgments loaded: {len(df)}")

    # 2. Extract X and Y
    t0 = time.time()
    records_x = []
    records_y = []

    for idx, row in df.iterrows():
        text = row.get("full_text", "")
        if not text or len(text) < 500:
            continue
        labels = extract_labels_from_text(text)
        if labels:
            facts = extract_facts_feature(text)
            # Expand with domain companion rules
            expanded = set(labels)
            for l in labels:
                if l in COMPANION_EXPANSION:
                    for comp in COMPANION_EXPANSION[l]:
                        expanded.add(comp)
            records_x.append(facts)
            records_y.append(list(expanded))

    print(f"Extracted {len(records_x)} labeled case texts in {time.time()-t0:.2f}s!")

    # Check label frequency
    from collections import Counter
    all_labels = [lbl for sublist in records_y for lbl in sublist]
    counts = Counter(all_labels)
    print("\nTop detected statutes:")
    for lbl, count in counts.most_common(20):
        print(f"  - {lbl:12s}: {count} cases")

    active_classes = [c for c, cnt in counts.items() if cnt >= 5]
    print(f"\nActive statutory classes: {len(active_classes)}")

    mlb = MultiLabelBinarizer(classes=sorted(active_classes))
    Y = mlb.fit_transform(records_y)
    X = records_x

    X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.15, random_state=42)
    print(f"Training set: {len(X_train)} | Test set: {len(X_test)}")

    # 3. Model Pipeline: TF-IDF + LogisticRegression with class_weight='balanced'
    print("\nTraining TF-IDF + OneVsRest LogisticRegression (class_weight='balanced')...")
    t_train = time.time()

    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=25000,
            sublinear_tf=True,
            min_df=2,
            stop_words='english'
        )),
        ('clf', OneVsRestClassifier(LogisticRegression(
            class_weight='balanced',
            C=2.0,
            max_iter=1000,
            random_state=42
        )))
    ])

    pipeline.fit(X_train, Y_train)
    print(f"Training completed in {time.time()-t_train:.2f}s!")

    # 4. Evaluation
    # For balanced multi-label, we can predict using probability threshold (e.g. 0.35)
    def predict_with_threshold(pipe, texts, threshold=0.35, top_k=7):
        probs = pipe.predict_proba(texts)
        results = []
        for row in probs:
            # Get indices where prob >= threshold
            indices = np.where(row >= threshold)[0]
            if len(indices) == 0:
                # Fallback to top-3 highest
                indices = np.argsort(row)[-3:]
            elif len(indices) > top_k:
                # Sort and keep top_k
                top_sorted = indices[np.argsort(row[indices])][::-1]
                indices = top_sorted[:top_k]
            results.append(indices)
        return results

    test_indices = predict_with_threshold(pipeline, X_test, threshold=0.35)
    Y_pred_bin = np.zeros_like(Y_test)
    for i, idxs in enumerate(test_indices):
        Y_pred_bin[i, idxs] = 1

    micro_f1 = f1_score(Y_test, Y_pred_bin, average='micro', zero_division=0)
    macro_f1 = f1_score(Y_test, Y_pred_bin, average='macro', zero_division=0)
    precision = precision_score(Y_test, Y_pred_bin, average='micro', zero_division=0)
    recall = recall_score(Y_test, Y_pred_bin, average='micro', zero_division=0)

    print("\nModel Evaluation (Threshold = 0.35):")
    print(f"  • Micro F1 Score:  {micro_f1 * 100:.2f}%")
    print(f"  • Macro F1 Score:  {macro_f1 * 100:.2f}%")
    print(f"  • Precision:       {precision * 100:.2f}%")
    print(f"  • Recall:          {recall * 100:.2f}%")

    # 5. Verification on Benchmark Cases
    print("\n" + "=" * 60)
    print("Verification on AI Court Benchmark Cases:")
    print("=" * 60)

    benchmark_cases = {
        "Shabuddin Murder & Arms Case": (
            "The deceased was murdered in broad daylight by multiple assailants using sharp cutting weapons "
            "and country made pistol. The accused were apprehended and on their disclosure statement under police custody, "
            "the weapon and blood stained clothes were recovered. Charges framed for murder and unlicensed firearm."
        ),
        "Jharkhand Railway Theft Case": (
            "The railway protection force searched the scrap godown of the accused and recovered railway track iron plates. "
            "The accused failed to produce receipt or lawful permit for possession of stolen railway material. "
            "Search conducted without joining independent local witnesses."
        ),
        "Cheating & Forgery Bank Loan Case": (
            "The accused impersonated as company director, fabricated loan application and forged board resolutions "
            "dishonestly inducing the bank to disburse loan of Rs. 2 crores."
        )
    }

    class PredictorWrapper:
        def __init__(self, pipe, binarizer, threshold=0.30):
            self.pipe = pipe
            self.binarizer = binarizer
            self.classes_ = binarizer.classes_
            self.threshold = threshold

        def predict(self, text: str, top_k: int = 6):
            probs = self.pipe.predict_proba([text])[0]
            ranked = np.argsort(probs)[::-1]
            results = []
            for idx in ranked:
                if probs[idx] >= self.threshold or len(results) < 3:
                    if len(results) < top_k:
                        results.append({
                            "section": self.classes_[idx],
                            "probability": round(float(probs[idx]), 3)
                        })
            return results

    wrapper = PredictorWrapper(pipeline, mlb, threshold=0.30)

    for name, text in benchmark_cases.items():
        preds = wrapper.predict(text)
        print(f"\nCase: {name}")
        for p in preds:
            print(f"  -> {p['section']:12s} (confidence: {p['probability']*100:.1f}%)")

    # 6. Save Bundle
    output_dir = r"c:\Users\Aryan Naikar\OneDrive\Desktop\vs\AI-Court-of-India\backend\data\models"
    model_path = os.path.join(output_dir, "statutory_section_predictor.joblib")
    
    saved_bundle = {
        "pipeline": pipeline,
        "mlb": mlb,
        "classes": list(mlb.classes_),
        "threshold": 0.30,
        "version": "2.0.0",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    joblib.dump(saved_bundle, model_path)
    file_size_mb = os.path.getsize(model_path) / (1024 * 1024)
    print(f"\n[Saved] Model successfully exported to:\n  {model_path} ({file_size_mb:.2f} MB)")

if __name__ == "__main__":
    build_companion_predictor()
