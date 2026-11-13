"""
Standalone Real Model Smoke Test for AI Court of India.
Tests live connectivity and real judgment generation with:
1. Ollama (Primary Local Brain)
2. NVIDIA NIM API (Cloud Provider)

Usage:
    python tests/smoke_test_real_llm.py --provider ollama
    python tests/smoke_test_real_llm.py --provider nvidia
    python tests/smoke_test_real_llm.py --provider both
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Setup paths
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for p in [str(ROOT), str(BACKEND)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from app.core.llm_provider import LLMConfig, LLMProvider, NvidiaLLMClient, OllamaLLMClient
from app.graph.workflow import run_court
from tests.phase2.test_case_agent import SAMPLE_CASE_PACKET_TEXT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("smoke_test")


def test_provider_smoke(provider_name: str) -> bool:
    print("\n" + "=" * 60)
    print(f" SMOKE TEST: {provider_name.upper()} PROVIDER")
    print("=" * 60)

    # 1. Health Check
    health = LLMProvider.check_health(provider_name)
    print(f"[*] Health Check Result: {health}")
    if not health.get("available"):
        print(f"[-] FAILED: Provider '{provider_name}' is unavailable: {health.get('error')}")
        return False
    print(f"[+] SUCCESS: Provider '{provider_name}' is connected and available.")

    # 2. Text Generation Test
    client = LLMProvider.get(provider_name)
    prompt = "Summarize the legal standard for proof beyond reasonable doubt under Indian criminal law in 2 sentences."
    print(f"[*] Sending test generation to {provider_name} ({client.model})...")
    try:
        reply = client.generate_text(prompt=prompt, system_prompt="You are a legal scholar.")
        print(f"[+] Received Response ({len(reply)} chars):")
        print(f"    \"{reply.strip()[:180]}...\"")
    except Exception as e:
        print(f"[-] FAILED generation: {e}")
        return False

    # 3. Courtroom Adjudication Test
    print(f"[*] Running AI Court pipeline with real {provider_name.upper()} brain...")
    # Temporarily set environment provider
    os.environ["LLM_PROVIDER"] = provider_name
    LLMProvider.set_provider(provider_name)

    try:
        final_state = run_court(SAMPLE_CASE_PACKET_TEXT)
        assert final_state is not None
        assert final_state.status == "completed"
        judgment = final_state.judgment
        assert judgment is not None
        print(f"[+] AI Court Adjudication Completed Successfully!")
        print(f"    Case ID:        {final_state.case_id}")
        print(f"    Verdict:        {judgment.final_decision}")
        print(f"    Background:     {judgment.case_background[:100]}...")
        print(f"    Issues Framed:  {len(judgment.issues_for_determination)}")
        print(f"    Citations:      {len(judgment.legal_citations)}")
        return True
    except Exception as e:
        print(f"[-] AI Court run encountered exception: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="AI Court of India — Real LLM Smoke Test")
    parser.add_argument(
        "--provider",
        choices=["ollama", "nvidia", "both"],
        default="ollama",
        help="Provider to smoke test (default: ollama)",
    )
    args = parser.parse_args()

    providers = ["ollama", "nvidia"] if args.provider == "both" else [args.provider]
    results = {}

    for prov in providers:
        success = test_provider_smoke(prov)
        results[prov] = "PASSED" if success else "FAILED"

    print("\n" + "=" * 60)
    print(" SMOKE TEST SUMMARY")
    print("=" * 60)
    for prov, status in results.items():
        print(f"  {prov.upper():10} : {status}")

    all_passed = all(s == "PASSED" for s in results.values())
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
