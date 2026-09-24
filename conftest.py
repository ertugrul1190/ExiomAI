import os
import sys
from pathlib import Path

# Keep the application modules importable no matter where
# pytest is started from.
sys.path.insert(0, str(Path(__file__).parent))

# The provider client is constructed at import time. Tests
# never make a real call, but a key must exist.
os.environ.setdefault("OPENAI_API_KEY", "test-key-not-used")

# Every test client shares one address, so the app-wide flood
# guard and answer cap would trip across unrelated tests.
# tests/test_security.py installs strict ones where it needs
# them.
os.environ.setdefault("EXIOM_FLOOD_REQUESTS_PER_MINUTE", "1000000")
os.environ.setdefault("EXIOM_MAX_CONCURRENT_ANSWERS", "1000000")

# The usage ledger is a file shared across restarts; tests
# that need one build their own in a temporary directory.
os.environ.setdefault("EXIOM_USAGE_DB", "off")
