"""Pytest configuration — add SDK source to path."""
import sys
from pathlib import Path

sdk_path = Path(__file__).parent / "src" / "sdk" / "python"
if str(sdk_path) not in sys.path:
    sys.path.insert(0, str(sdk_path))
