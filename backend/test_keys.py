import sys
from pathlib import Path

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import httpx
from dotenv import load_dotenv

env_file = backend_dir.parent / ".env"
load_dotenv(dotenv_path=env_file, override=True)

from app.core.llm_provider import LLMProvider, LLMConfig
from app.services.llm_service import LLMService
from app.agents.live_hearing_agents import LiveProsecutorAgent, LawyerAction

def run_diagnostics():
    key = LLMConfig.openrouter_api_key()
    masked_key = (key[:10] + "..." + key[-4:]) if key else "None"
    model = LLMConfig.openrouter_model()

    print("=" * 64)
    print("           OPENROUTER API KEY DIAGNOSTIC REPORT")
    print("=" * 64)
    print("1. Configuration from .env:")
    print(f"   - Provider      : {LLMConfig.provider()}")
    print(f"   - Active Model  : {model}")
    print(f"   - API Key       : {masked_key}")
    print()

    # Step 2: OpenRouter Authentication
    print("2. OpenRouter Authentication & Account Status:")
    headers = {"Authorization": f"Bearer {key}"}
    try:
        auth_res = httpx.get("https://openrouter.ai/api/v1/auth/key", headers=headers, timeout=8.0)
        if auth_res.status_code == 200:
            data = auth_res.json().get("data", {})
            print("   - API Key Status: VALID & ACTIVE (HTTP 200 OK)")
            print(f"   - Key Label     : {data.get('label')}")
            print(f"   - Free Tier     : {data.get('is_free_tier')}")
            print(f"   - Total Usage   : ${data.get('usage', 0):.6f}")
        else:
            print(f"   - API Key Status: FAILED (HTTP {auth_res.status_code})")
            print(f"   - Response      : {auth_res.text}")
            return
    except Exception as e:
        print(f"   - Network Error : {e}")
        return
    print()

    # Step 3: Direct Text Generation
    print(f"3. Text Generation Test (Model: {model}):")
    try:
        llm = LLMProvider.get()
        reply = llm.generate_text("Reply with exactly: ALL SYSTEMS OPERATIONAL", system_prompt="System check.")
        print(f"   - Provider Class: {type(llm).__name__}")
        print(f"   - Response      : '{reply.strip()}'")
        print("   - Status        : PASSED")
    except Exception as e:
        print(f"   - Status        : FAILED ({e})")
        return
    print()

    # Step 4: Structured Output Generation
    print("4. Structured JSON Schema Test:")
    try:
        struct_res = llm.generate_structured(
            prompt="State one key point on seizure memo Ex.PB.",
            response_schema=LawyerAction,
            system_prompt="You are a courtroom prosecutor."
        )
        print(f"   - Message       : '{struct_res.message}'")
        print(f"   - Next Speaker  : '{struct_res.next_speaker}'")
        print("   - Status        : PASSED")
    except Exception as e:
        print(f"   - Status        : FAILED ({e})")
        return
    print()

    # Step 5: Courtroom Live Agent Test
    print("5. Live Courtroom Agent Test (LiveProsecutorAgent):")
    try:
        pros = LiveProsecutorAgent()
        action = pros.argue(
            case=None,
            prosecution=None,
            transcript=[{
                "role": "judge",
                "content": "Prosecutor, state your position on the recovered country-made pistol Ex.P3."
            }],
            active_issue="Recovery of country-made pistol Ex.P3",
            turn_in_issue=1
        )
        print(f"   - Agent Speech  : '{action.message}'")
        print(f"   - Target Speaker: '{action.next_speaker}'")
        print("   - Status        : PASSED")
    except Exception as e:
        print(f"   - Status        : FAILED ({e})")
        return
    print()

    print("=" * 64)
    print("           RESULT: ALL 5 DIAGNOSTIC CHECKS PASSED")
    print("           YOUR OPENROUTER KEY IS FULLY FUNCTIONAL!")
    print("=" * 64)

if __name__ == "__main__":
    run_diagnostics()
