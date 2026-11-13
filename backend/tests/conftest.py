"""
Pytest configuration for AI Court of India.
Ensures both workspace root and backend directory are in sys.path.
"""

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent

for p in [ROOT, BACKEND]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
