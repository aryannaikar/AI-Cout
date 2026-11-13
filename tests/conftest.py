"""
Pytest configuration for AI Court of India.
Ensures both workspace root and backend directory are in sys.path.
"""

import os
import sys
from pathlib import Path

# Ensure fast hermetic testing by default in pytest suite
os.environ["LLM_PROVIDER"] = "mock"

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

for p in [ROOT, BACKEND]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
