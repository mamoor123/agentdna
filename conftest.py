"""Pytest configuration — add SDK source to path, configure test env."""
import os
import sys
from pathlib import Path

# Set test env vars BEFORE any registry imports
os.environ["AGENTDNA_AUTH_DISABLED"] = "1"
os.environ["AGENTDNA_RATE_LIMIT_DISABLED"] = "1"

sdk_path = Path(__file__).parent / "src" / "sdk" / "python"
if str(sdk_path) not in sys.path:
    sys.path.insert(0, str(sdk_path))
