"""
plan_builder.py
---------------
A fluent builder for experiment_plan.json.

The whole point: start from a complete, valid default plan and change only the
handful of fields that vary per run. A typical run reads as a short chain:

    from config.plan_builder import ExperimentPlanBuilder

    path = (
        ExperimentPlanBuilder()
        .batch("B")
        .plate("2")
        .wells(["B1", "B2", "B3", "B4"])
        .rows_to_run(["B"])
        .storage(primary_root="/Volumes/SDL_Data")   # macOS root, say
        .channel_well_map({"B1": 1, "B2": 2, "B3": 3, "B4": 4})
        .add_group_plan("B1_to_B4", ["B1", "B2", "B3", "B4"])
        .save("experiment_plan.json")                # cross-OS path resolution
    )

Everything not mentioned stays at its default from plan_defaults.py.

Group plans are the bulky, repetitive part of the file. Rather than hand-write
~200 lines per row, `add_group_plan` / `add_group_plans_for_rows` generate the
per-well ca/cv blocks from defaults, with optional per-well overrides.

Path handling is delegated to paths.py so the same code reads and writes the
config correctly on macOS and Windows even if the folder layout changes.
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

from . import plan_defaults as defaults
from .paths import data_path


class ExperimentPlanBuilder:
    """
    Build an experiment plan by mutating a deep copy of the defaults.

    All setters return `self` for chaining. `build()` returns a deep copy of the
    accumulated plan; `save()` writes it to disk with OS-independent path
    resolution. `from_file()` loads an existing plan so you can tweak and resave.
    """

    def __init__(self, base: dict[str, Any] | None = None) -> None:
        # Deep copy so the caller's dict (or the defaults) is never mutated.
        self._plan: dict[str, Any] = deepcopy(base) if base is not None else defaults.default_plan()

    # ------------------------------------------------------------------
    # Construction from an existing plan
    # ------------------------------------------------------------------

    @classmethod
    def from_file(
        cls,
        name: str,
        data_dir: str | os.PathLike | None = None,
    ) -> "ExperimentPlanBuilder":
        """
        Load an existing plan JSON and return a builder wrapping it, so you can
        change a few fields and save again.

        `data_dir` overrides where the file is read from; if omitted, the
        RINGOAI_DATA_DIR env var then the DATA_DIR default apply (see paths.py).
        """
        path = data_path(name, data_dir=data_dir)
        if not path.is_file():
            raise FileNotFoundError(f"Config file not found: '{path}'")
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return cls(base=data)

    # ------------------------------------------------------------------
    # Top-level per-run knobs
    # ------------------------------------------------------------------

    def batch(self, batch_id: str) -> "ExperimentPlanBuilder":
        self._plan["batch_id"] = batch_id
        return self

    def plate(self, plate_id: str) -> "ExperimentPlanBuilder":
        self._plan["plate_id"] = plate_id
        return self

    def wells(self, wells: list[str]) -> "ExperimentPlanBuilder":
        self._plan["wells"] = list(wells)
        return self

    def active_sequence(self, sequence: str) -> "ExperimentPlanBuilder":
        self._plan["electrochemistry"]["active_sequence"] = sequence
        return self

    def run_mode(self, mode: str) -> "ExperimentPlanBuilder":
        self._plan["electrochemistry"]["electrochem_run_mode"] = mode
        return self

    def channel_well_map(self, mapping: dict[str, int]) -> "ExperimentPlanBuilder":
        self._plan["electrochemistry"]["channel_well_map"] = dict(mapping)
        return self

    # ------------------------------------------------------------------
    # Section setters (only override the keys you pass; rest stay default)
    # ------------------------------------------------------------------

    def storage(
        self,
        primary_root: str | None = None,
        mirror_roots: list[str] | None = None,
    ) -> "ExperimentPlanBuilder":
        """
        Set instrument storage roots. These are the instrument PC's paths, so
        they are stored as-is (json.dump handles any backslash escaping).
        """
        if primary_root is not None:
            self._plan["storage"]["primary_root"] = primary_root
        if mirror_roots is not None:
            self._plan["storage"]["mirror_roots"] = list(mirror_roots)
        return self

    def plate_execution(
        self,
        enabled: bool | None = None,
        rows_to_run: list[str] | None = None,
        stop_after_rows: int | None = None,
    ) -> "ExperimentPlanBuilder":
        self._update_section(
            "plate_execution",
            enabled=enabled,
            rows_to_run=rows_to_run,
            stop_after_rows=stop_after_rows,
        )
        return self

    def rows_to_run(self, rows: list[str]) -> "ExperimentPlanBuilder":
        """Shorthand for the single most commonly changed plate_execution field."""
        self._plan["plate_execution"]["rows_to_run"] = list(rows)
        return self

    def biologic(
        self,
        address: str | None = None,
        binary_path: str | None = None,
        output_dir: str | None = None,
    ) -> "ExperimentPlanBuilder":
        self._update_section(
            "biologic",
            address=address,
            binary_path=binary_path,
            output_dir=output_dir,
        )
        return self

    def tip_strategy(
        self,
        start_tip: str | None = None,
        tip_sequence: list[str] | None = None,
        drop_tip_after_fill: bool | None = None,
        get_new_tip_for_cleanup: bool | None = None,
    ) -> "ExperimentPlanBuilder":
        self._update_section(
            "tip_strategy",
            start_tip=start_tip,
            tip_sequence=tip_sequence,
            drop_tip_after_fill=drop_tip_after_fill,
            get_new_tip_for_cleanup=get_new_tip_for_cleanup,
        )
        return self

    def liquid_handling(self, **overrides: Any) -> "ExperimentPlanBuilder":
        self._update_section("liquid_handling", **overrides)
        return self

    def electrode_fixture(self, **overrides: Any) -> "ExperimentPlanBuilder":
        self._update_section("electrode_fixture", **overrides)
        return self

    def cleanup(self, **overrides: Any) -> "ExperimentPlanBuilder":
        self._update_section("cleanup", **overrides)
        return self

    # ------------------------------------------------------------------
    # Measurement-block setters (top-level cv / ca / eis)
    # ------------------------------------------------------------------

    def cv(self, **overrides: Any) -> "ExperimentPlanBuilder":
        self._update_nested(["electrochemistry", "cv"], overrides)
        return self

    def ca(self, **overrides: Any) -> "ExperimentPlanBuilder":
        self._update_nested(["electrochemistry", "ca"], overrides)
        return self

    def eis(self, **overrides: Any) -> "ExperimentPlanBuilder":
        self._update_nested(["electrochemistry", "eis"], overrides)
        return self

    # ------------------------------------------------------------------
    # Group plans (the bulky repetitive section) - generated from defaults
    # ------------------------------------------------------------------

    def add_group_plan(
        self,
        name: str,
        wells: Iterable[str],
        per_well_overrides: dict[str, dict[str, Any]] | None = None,
    ) -> "ExperimentPlanBuilder":
        """
        Add one group plan whose per-well entries default to the standard
        group-well ca/cv blocks. Override specific wells as needed.

        Parameters
        ----------
        name : str
            Group-plan key, e.g. "B1_to_B4".
        wells : iterable of str
            Well ids to populate, e.g. ["B1", "B2", "B3", "B4"].
        per_well_overrides : dict[well_id, partial_dict] | None
            Deep-merged onto that well's default. For example
            {"B1": {"ca": {"Voltage_step": [-1.2]}}} changes only that value
            and leaves the rest of B1 (and all other wells) at defaults.
        """
        per_well_overrides = per_well_overrides or {}
        per_well: dict[str, Any] = {}
        for well in wells:
            entry = defaults.default_group_well()
            if well in per_well_overrides:
                self._deep_merge(entry, per_well_overrides[well])
            per_well[well] = entry

        self._plan["electrochemistry"]["group_plans"][name] = {"per_well": per_well}
        return self

    def add_group_plans_for_rows(
        self,
        rows: Iterable[str],
        cols: int = 4,
        name_template: str = "{row}1_to_{row}{cols}",
    ) -> "ExperimentPlanBuilder":
        """
        Convenience: generate one group plan per row. For row "B" with cols=4
        this creates group "B1_to_B4" over wells B1..B4, all at defaults.
        """
        for row in rows:
            wells = [f"{row}{i}" for i in range(1, cols + 1)]
            name = name_template.format(row=row, cols=cols)
            self.add_group_plan(name, wells)
        return self

    def clear_group_plans(self) -> "ExperimentPlanBuilder":
        self._plan["electrochemistry"]["group_plans"] = {}
        return self

    # ------------------------------------------------------------------
    # Generic escape hatch
    # ------------------------------------------------------------------

    def set(self, key_path: str, value: Any, sep: str = ".") -> "ExperimentPlanBuilder":
        """
        Set any value by dotted path, creating intermediate dicts as needed.
        Escape hatch for fields without a dedicated setter, e.g.
        .set("electrode_fixture.slow_descent.step_mm", 0.25)
        """
        keys = key_path.split(sep)
        node = self._plan
        for k in keys[:-1]:
            node = node.setdefault(k, {})
            if not isinstance(node, dict):
                raise TypeError(f"'{key_path}': '{k}' is not a dict.")
        node[keys[-1]] = value
        return self

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def build(self) -> dict[str, Any]:
        """Return a deep copy of the accumulated plan."""
        return deepcopy(self._plan)

    def save(
        self,
        name: str = "experiment_plan.json",
        data_dir: str | os.PathLike | None = None,
        indent: int = 2,
        overwrite: bool = True,
    ) -> Path:
        """
        Write the plan to disk.

        Parameters
        ----------
        name : str
            Filename or absolute path.
        data_dir : path-like or None
            Where to write. If None, resolution falls back to the
            RINGOAI_DATA_DIR env var, then the DATA_DIR default in paths.py.
            Ignored if `name` is absolute.
        indent : int
            JSON indent.
        overwrite : bool
            If False and the file exists, raise FileExistsError.

        Returns
        -------
        Path
            The path written.
        """
        path = data_path(name, data_dir=data_dir)
        if not overwrite and path.exists():
            raise FileExistsError(f"Refusing to overwrite existing file: '{path}'")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self._plan, fh, indent=indent)
        return path

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _update_section(self, section: str, **overrides: Any) -> None:
        """Set only the keys whose value is not None, in a top-level section."""
        target = self._plan[section]
        for key, value in overrides.items():
            if value is not None:
                target[key] = value

    def _update_nested(self, path: list[str], overrides: dict[str, Any]) -> None:
        """Overwrite keys in a nested dict located at `path`."""
        node = self._plan
        for k in path:
            node = node[k]
        for key, value in overrides.items():
            node[key] = value

    def _deep_merge(self, base: dict[str, Any], updates: dict[str, Any]) -> None:
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
