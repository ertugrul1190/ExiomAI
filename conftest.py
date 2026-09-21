import os
import sys
from pathlib import Path

# Keep the application modules importable no matter where
# pytest is started from.
sys.path.insert(0, str(Path(__file__).parent))

# The provider client is constructed at import time. Tests
# never make a real call, but a key must exist.
os.environ.setdefault("OPENAI_API_KEY", "test-key-not-used")
