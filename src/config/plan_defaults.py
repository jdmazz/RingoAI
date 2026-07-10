"""
plan_defaults.py
----------------
Single source of truth for every default value in an experiment plan.

Design intent
-------------
Each section is a *factory function* returning a brand-new dict, never a shared
module-level dict. That guarantees two builders can never accidentally mutate
each other's state, and it keeps every default visible in one obvious place so
"change a default" means "edit one function here."

Note the deliberate distinction between:
  * `default_toplevel_ca()`  -> Voltage_step [1],  count_mode "cathodic_only"
  * `default_group_well_ca()`-> Voltage_step [-1], count_mode "net"
These matched the uploaded plan and are intentionally NOT unified.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Standard 96-tip sequence (A1..L8), generated rather than hand-listed.
# ---------------------------------------------------------------------------

def default_tip_sequence() -> list[str]:
    """TIP_A1 .. TIP_L8 (12 columns A-L, 8 rows 1-8)."""
    cols = "ABCDEFGHIJKL"
    return [f"TIP_{c}{r}" for c in cols for r in range(1, 9)]


# ---------------------------------------------------------------------------
# Top-level measurement blocks
# ---------------------------------------------------------------------------

def default_toplevel_cv() -> dict[str, Any]:
    return {
        "enabled": True,
        "vs_initial": [False, False, False],
        "Voltage_step": [-0.2, 0.9, -0.2],
        "Scan_Rate": [0.1, 0.1, 0.1],
        "Scan_number": 1,
        "Record_every_dE": 0.001,
        "N_Cycles": 0,
        "Begin_measuring_I": 0.0,
        "End_measuring_I": 1.0,
    }


def default_toplevel_ca() -> dict[str, Any]:
    return {
        "enabled": True,
        "vs_initial": [False],
        "Voltage_step": [1],
        "Duration_step": [1.0],
        "Step_number": 1,
        "Record_every_dT": 0.001,
        "Record_every_dI": 0.001,
        "N_Cycles": 1000000,
        "charge_limit": {
            "mode": "per_channel_stop",
            "target_charge_C": 0.003,
            "count_mode": "cathodic_only",
            "safety_max_time_s": 600,
        },
    }


def default_eis() -> dict[str, Any]:
    return {
        "enabled": True,
        "vs_initial": False,
        "Initial_Voltage_step": 0.0,
        "Duration_step": 1.0,
        "Record_every_dT": 0.1,
        "Record_every_dI": 0.001,
        "Initial_frequency": 100000,
        "Final_frequency": 1,
        "sweep": False,
        "Amplitude_Voltage": 0.01,
        "Points_per_decade": 8,
        "Frequency_number": 60,
        "Average_N_times": 1,
        "Correction": False,
        "Wait_for_steady": 0.1,
    }


def default_randomization() -> dict[str, Any]:
    return {
        "ca": {
            "enabled": True,
            "mode": "bounded",
            "seed": 12345,
            "bounds": {
                "voltage_on": {"min": -1.3, "max": -1.1},
                "voltage_off": {"min": -0.1, "max": -0.1},
                "t_on_s": {"min": 0.02, "max": 0.05},
                "t_off_s": {"min": 0.1, "max": 0.3},
            },
            "safety": {
                "min_voltage_v": -2.0,
                "max_voltage_v": 0.5,
                "max_total_time_s": 600.0,
                "max_cycles": 200,
            },
        }
    }


# ---------------------------------------------------------------------------
# Per-well blocks used inside group_plans (distinct from top-level!)
# ---------------------------------------------------------------------------

def default_group_well_ca() -> dict[str, Any]:
    return {
        "enabled": True,
        "vs_initial": [False],
        "Voltage_step": [-1],
        "Duration_step": [1.0],
        "Step_number": 1,
        "Record_every_dT": 0.001,
        "Record_every_dI": 0.001,
        "N_Cycles": 1000000,
        "charge_limit": {
            "mode": "per_channel_stop",
            "target_charge_C": 0.003,
            "count_mode": "net",
            "safety_max_time_s": 600,
        },
    }


def default_group_well_cv() -> dict[str, Any]:
    return {
        "enabled": True,
        "vs_initial": [False, False, False],
        "Voltage_step": [-0.2, 0.9, -0.2],
        "Scan_Rate": [0.1, 0.1, 0.1],
        "Scan_number": 1,
        "Record_every_dE": 0.001,
        "N_Cycles": 0,
        "Begin_measuring_I": 0.0,
        "End_measuring_I": 1.0,
    }


def default_group_well() -> dict[str, Any]:
    """One per-well entry: a ca block and a cv block."""
    return {"ca": default_group_well_ca(), "cv": default_group_well_cv()}


# ---------------------------------------------------------------------------
# Non-electrochemistry sections
# ---------------------------------------------------------------------------

def default_storage() -> dict[str, Any]:
    return {"primary_root": "C:/SDL_Data", "mirror_roots": []}


def default_plate_execution() -> dict[str, Any]:
    return {"enabled": True, "rows_to_run": ["B"], "stop_after_rows": None}


def default_biologic() -> dict[str, Any]:
    return {
        "address": "USB0",
        "binary_path": "C:/EC-Lab Development Package/lib",
        "output_dir": "biologic_results",
    }


def default_tip_strategy() -> dict[str, Any]:
    return {
        "start_tip": "TIP_A1",
        "tip_sequence": default_tip_sequence(),
        "drop_tip_after_fill": False,
        "get_new_tip_for_cleanup": False,
    }


def default_liquid_handling() -> dict[str, Any]:
    return {
        "precursor_source": "PRECURSOR_1",
        "fill_volume_ul_per_well": 5000,
        "aspirate_extra_ul": 0,
        "waste_location": "WASTE",
        "rinse_location": "RINSE_1",
        "trash_location": "TRASH",
    }


def default_electrode_fixture() -> dict[str, Any]:
    return {
        "position_name": "ELECTRODE_BATCH_A",
        "lower_into_test_position": True,
        "test_depth_z": 105.0,
        "test_depth_a": 218,
        "raise_after_test": True,
        "slow_descent": {
            "enabled": True,
            "approach_offset_z_mm": 20.0,
            "step_mm": 0.5,
            "dwell_s": 0.35,
        },
    }


def default_cleanup() -> dict[str, Any]:
    return {"remove_used_solution": True, "rinse_after_batch": False}


def default_channel_well_map() -> dict[str, int]:
    return {"A1": 1, "A2": 2, "A3": 3, "A4": 4}


# ---------------------------------------------------------------------------
# The complete default plan
# ---------------------------------------------------------------------------

def default_plan() -> dict[str, Any]:
    """
    A full experiment plan populated entirely with defaults. This mirrors the
    uploaded experiment_plan.json with an empty group_plans map (add group
    plans explicitly via the builder so nothing is generated you did not ask
    for).
    """
    return {
        "batch_id": "A",
        "wells": ["A1", "A2", "A3", "A4"],
        "plate_id": "1",
        "storage": default_storage(),
        "plate_execution": default_plate_execution(),
        "biologic": default_biologic(),
        "tip_strategy": default_tip_strategy(),
        "liquid_handling": default_liquid_handling(),
        "electrode_fixture": default_electrode_fixture(),
        "electrochemistry": {
            "active_sequence": "eis_ca_eis",
            "channel_well_map": default_channel_well_map(),
            "cv": default_toplevel_cv(),
            "ca": default_toplevel_ca(),
            "eis": default_eis(),
            "randomization": default_randomization(),
            "group_plans": {},
            "electrochem_run_mode": "sequential",
        },
        "cleanup": default_cleanup(),
    }
