"""
test_plan_builder.py
--------------------
Run:  python -m pytest tests/test_plan_builder.py -v
(from the project root, with src on the path -- see conftest.py)
"""

import json
from pathlib import Path as pathlib_Path

import pytest

from config.plan_builder import ExperimentPlanBuilder
from config import plan_defaults as defaults
from config import paths
from config.paths import data_path


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

class TestDefaults:
    def test_default_plan_has_expected_top_keys(self):
        plan = defaults.default_plan()
        assert set(plan.keys()) == {
            "batch_id", "wells", "plate_id", "storage", "plate_execution",
            "biologic", "tip_strategy", "liquid_handling", "electrode_fixture",
            "electrochemistry", "cleanup",
        }

    def test_tip_sequence_is_96_tips(self):
        seq = defaults.default_tip_sequence()
        assert len(seq) == 96
        assert seq[0] == "TIP_A1"
        assert seq[-1] == "TIP_L8"

    def test_toplevel_and_group_ca_differ(self):
        # This distinction is deliberate; guard against accidental unification.
        top = defaults.default_toplevel_ca()
        grp = defaults.default_group_well_ca()
        assert top["Voltage_step"] == [1]
        assert grp["Voltage_step"] == [-1]
        assert top["charge_limit"]["count_mode"] == "cathodic_only"
        assert grp["charge_limit"]["count_mode"] == "net"

    def test_factories_return_fresh_objects(self):
        a = defaults.default_storage()
        b = defaults.default_storage()
        a["primary_root"] = "MUTATED"
        assert b["primary_root"] != "MUTATED"


# ---------------------------------------------------------------------------
# Builder: basic setters
# ---------------------------------------------------------------------------

class TestBuilderSetters:
    def test_chaining_returns_self(self):
        b = ExperimentPlanBuilder()
        assert b.batch("B") is b

    def test_batch_plate_wells(self):
        plan = ExperimentPlanBuilder().batch("B").plate("2").wells(["B1", "B2"]).build()
        assert plan["batch_id"] == "B"
        assert plan["plate_id"] == "2"
        assert plan["wells"] == ["B1", "B2"]

    def test_defaults_untouched_when_not_set(self):
        plan = ExperimentPlanBuilder().batch("Z").build()
        # liquid_handling never set, should equal default
        assert plan["liquid_handling"] == defaults.default_liquid_handling()

    def test_build_returns_deep_copy(self):
        b = ExperimentPlanBuilder()
        plan = b.build()
        plan["batch_id"] = "MUTATED"
        assert b.build()["batch_id"] != "MUTATED"

    def test_partial_section_override(self):
        plan = ExperimentPlanBuilder().biologic(address="USB1").build()
        assert plan["biologic"]["address"] == "USB1"
        # other biologic keys stay default
        assert plan["biologic"]["output_dir"] == "biologic_results"

    def test_rows_to_run_shorthand(self):
        plan = ExperimentPlanBuilder().rows_to_run(["C", "D"]).build()
        assert plan["plate_execution"]["rows_to_run"] == ["C", "D"]

    def test_measurement_block_override(self):
        plan = ExperimentPlanBuilder().eis(Final_frequency=10, Points_per_decade=12).build()
        assert plan["electrochemistry"]["eis"]["Final_frequency"] == 10
        assert plan["electrochemistry"]["eis"]["Points_per_decade"] == 12
        # untouched eis key stays default
        assert plan["electrochemistry"]["eis"]["Initial_frequency"] == 100000

    def test_generic_set_escape_hatch(self):
        plan = ExperimentPlanBuilder().set("electrode_fixture.slow_descent.step_mm", 0.25).build()
        assert plan["electrode_fixture"]["slow_descent"]["step_mm"] == 0.25


# ---------------------------------------------------------------------------
# Builder: storage / path normalization
# ---------------------------------------------------------------------------

class TestStorage:
    def test_storage_roots_set(self):
        plan = ExperimentPlanBuilder().storage(
            primary_root="C:/SDL_Data", mirror_roots=["D:/backup"]
        ).build()
        assert plan["storage"]["primary_root"] == "C:/SDL_Data"
        assert plan["storage"]["mirror_roots"] == ["D:/backup"]

    def test_storage_partial_leaves_default(self):
        plan = ExperimentPlanBuilder().storage(primary_root="/Volumes/SDL").build()
        assert plan["storage"]["primary_root"] == "/Volumes/SDL"
        assert plan["storage"]["mirror_roots"] == []  # default untouched


# ---------------------------------------------------------------------------
# Builder: group plans
# ---------------------------------------------------------------------------

class TestGroupPlans:
    def test_add_single_group_plan(self):
        plan = ExperimentPlanBuilder().add_group_plan("B1_to_B4", ["B1", "B2", "B3", "B4"]).build()
        gp = plan["electrochemistry"]["group_plans"]
        assert "B1_to_B4" in gp
        assert set(gp["B1_to_B4"]["per_well"].keys()) == {"B1", "B2", "B3", "B4"}

    def test_group_well_has_ca_and_cv(self):
        plan = ExperimentPlanBuilder().add_group_plan("X", ["X1"]).build()
        well = plan["electrochemistry"]["group_plans"]["X"]["per_well"]["X1"]
        assert "ca" in well and "cv" in well
        assert well["ca"]["Voltage_step"] == [-1]  # group-well default

    def test_per_well_override_is_deep_merged(self):
        plan = (
            ExperimentPlanBuilder()
            .add_group_plan(
                "B1_to_B4",
                ["B1", "B2"],
                per_well_overrides={"B1": {"ca": {"Voltage_step": [-1.2]}}},
            )
            .build()
        )
        wells = plan["electrochemistry"]["group_plans"]["B1_to_B4"]["per_well"]
        assert wells["B1"]["ca"]["Voltage_step"] == [-1.2]      # overridden
        assert wells["B1"]["ca"]["Step_number"] == 1            # default retained
        assert wells["B2"]["ca"]["Voltage_step"] == [-1]        # untouched well

    def test_generate_for_rows(self):
        plan = ExperimentPlanBuilder().add_group_plans_for_rows(["A", "B"], cols=4).build()
        gp = plan["electrochemistry"]["group_plans"]
        assert "A1_to_A4" in gp and "B1_to_B4" in gp
        assert set(gp["A1_to_A4"]["per_well"].keys()) == {"A1", "A2", "A3", "A4"}

    def test_clear_group_plans(self):
        b = ExperimentPlanBuilder().add_group_plan("X", ["X1"])
        b.clear_group_plans()
        assert b.build()["electrochemistry"]["group_plans"] == {}


# ---------------------------------------------------------------------------
# Save / load round trip
# ---------------------------------------------------------------------------

class TestSaveLoad:
    def test_save_and_reload(self, tmp_path):
        out = tmp_path / "experiment_plan.json"
        ExperimentPlanBuilder().batch("Q").save(str(out))
        assert out.is_file()
        reloaded = json.loads(out.read_text())
        assert reloaded["batch_id"] == "Q"

    def test_save_no_overwrite_raises(self, tmp_path):
        out = tmp_path / "experiment_plan.json"
        ExperimentPlanBuilder().save(str(out))
        with pytest.raises(FileExistsError):
            ExperimentPlanBuilder().save(str(out), overwrite=False)

    def test_from_file_then_modify(self, tmp_path):
        out = tmp_path / "plan.json"
        ExperimentPlanBuilder().batch("A").plate("1").save(str(out))
        plan = ExperimentPlanBuilder.from_file(str(out)).plate("99").build()
        assert plan["plate_id"] == "99"
        assert plan["batch_id"] == "A"  # preserved from file


# ---------------------------------------------------------------------------
# Data directory resolution (the one knob that moves)
# ---------------------------------------------------------------------------

class TestDataDir:
    def test_relative_resolves_under_root(self, monkeypatch):
        monkeypatch.setattr(paths, "DATA_DIR", "data")
        expected = (paths.PROJECT_ROOT / "data" / "plan.json").resolve()
        assert data_path("plan.json") == expected

    def test_absolute_data_dir_used_directly(self, monkeypatch):
        monkeypatch.setattr(paths, "DATA_DIR", "/srv/sdl/run_data")
        assert data_path("plan.json") == pathlib_Path("/srv/sdl/run_data/plan.json").resolve()

    def test_override_arg_beats_module_default(self, monkeypatch):
        monkeypatch.setattr(paths, "DATA_DIR", "data")
        assert data_path("plan.json", data_dir="/tmp/x") == pathlib_Path("/tmp/x/plan.json").resolve()

    def test_absolute_name_passthrough(self, tmp_path):
        p = tmp_path / "plan.json"
        assert data_path(str(p)) == p.resolve()

    def test_save_respects_data_dir_override(self, tmp_path):
        target = tmp_path / "elsewhere"
        written = ExperimentPlanBuilder().batch("K").save("plan.json", data_dir=str(target))
        assert written == (target / "plan.json").resolve()
        assert written.is_file()


# ---------------------------------------------------------------------------
# Fidelity: builder reproduces the uploaded file's structure
# ---------------------------------------------------------------------------

class TestFidelityToUpload:
    """
    Rebuild the uploaded plan from defaults + a few setters and confirm the
    result matches the original semantically (same keys, same structure).
    The uploaded file is copied into tests/fixtures by conftest if present.
    """

    def test_reproduces_uploaded_structure(self, uploaded_plan):
        if uploaded_plan is None:
            pytest.skip("uploaded experiment_plan.json fixture not available")

        rows = ["A", "B", "C", "D", "E", "F"]
        rebuilt = (
            ExperimentPlanBuilder()
            .batch("A")
            .plate("1")
            .wells(["A1", "A2", "A3", "A4"])
            .add_group_plans_for_rows(rows, cols=4)
            .build()
        )

        # Same top-level keys
        assert set(rebuilt.keys()) == set(uploaded_plan.keys())
        # Same group-plan names
        assert set(rebuilt["electrochemistry"]["group_plans"].keys()) == set(
            uploaded_plan["electrochemistry"]["group_plans"].keys()
        )
        # Spot-check one per-well block matches
        r_well = rebuilt["electrochemistry"]["group_plans"]["A1_to_A4"]["per_well"]["A1"]
        u_well = uploaded_plan["electrochemistry"]["group_plans"]["A1_to_A4"]["per_well"]["A1"]
        assert r_well == u_well
