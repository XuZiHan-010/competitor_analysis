import os
import sys
from pathlib import Path

os.environ["MOCK_LLM"] = "true"
os.environ["DATABASE_URL"] = ""
os.environ["REDIS_URL"] = ""

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
