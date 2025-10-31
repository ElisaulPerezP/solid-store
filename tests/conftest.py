# tests/conftest.py
# Ensure project root (parent of tests) is on sys.path so `import src...` works.
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)
