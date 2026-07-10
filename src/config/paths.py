"""
paths.py
--------
Data-directory resolution.

The code locates itself: this file is src/config/paths.py, so the project root
is a fixed offset up the tree, no discovery needed. The one thing that actually
moves between development and deployment is the data directory, so that is the
single settable knob here.
"""

from __future__ import annotations

import os
from pathlib import Path

# Project root = two levels up from src/config/paths.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# The data directory. Relative values resolve under PROJECT_ROOT; absolute
# values are used as-is. Defaults to "<root>/data" for development. Override for
# deployment either by setting the RINGOAI_DATA_DIR env var, or by reassigning
# paths.DATA_DIR in code.
DATA_DIR: str = os.environ.get("RINGOAI_DATA_DIR", "data")


def data_path(name: str, data_dir: str | os.PathLike | None = None) -> Path:
    """
    Absolute path to `name` inside the data directory.

    An absolute `name` is returned unchanged. Otherwise `name` is placed inside
    `data_dir` (falling back to the module DATA_DIR); a relative data dir is
    resolved under PROJECT_ROOT.
    """
    p = Path(name)
    if p.is_absolute():
        return p.resolve()

    d = Path(data_dir if data_dir is not None else DATA_DIR).expanduser()
    if not d.is_absolute():
        d = PROJECT_ROOT / d
    return (d / p).resolve()
