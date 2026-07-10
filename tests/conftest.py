"""
conftest.py
-----------
Makes `src` importable as a package root during tests and exposes the uploaded
experiment_plan.json (if present) as a fixture for fidelity checks.
"""

import json
import sys
from pathlib import Path

import pytest

# Put <project_root>/src on sys.path so `import config...` works.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def uploaded_plan():
    """
    Return the parsed uploaded plan if a copy exists at data/experiment_plan.json
    or tests/fixtures/experiment_plan.json; otherwise None (test will skip).
    """
    candidates = [
        PROJECT_ROOT / "data" / "experiment_plan.json",
        PROJECT_ROOT / "tests" / "fixtures" / "experiment_plan.json",
    ]
    for c in candidates:
        if c.is_file():
            return json.loads(c.read_text())
    return None
