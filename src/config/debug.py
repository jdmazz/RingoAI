"""
debug.py
--------
Use for debugging purposes only.
"""

import sys
from pathlib import Path

# Put src/ on the path BEFORE importing config, so this runs as a plain script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import paths
from config.plan_builder import ExperimentPlanBuilder

paths.DATA_DIR = "~/Developer/RingoAI/data"


def main(data_dir: str | None = None) -> Path:
    builder = (
        ExperimentPlanBuilder()
        .batch("DEBUG")
        .plate("0")
        .wells(["A1", "A2", "A3", "A4"])
        .add_group_plan("A1_to_A4", ["A1", "A2", "A3", "A4"])
    )
    out = builder.save("experiment_plan_debug.json", data_dir=data_dir, overwrite=True)
    print("wrote:", out)
    return out


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    main(target)