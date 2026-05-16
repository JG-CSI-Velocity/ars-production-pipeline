"""Tests for shared.branch_mapping (#129 follow-up)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

# Make ars_analysis importable from 00-Scripts (matches run.py wiring)
_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS_DIR))
import types

if "ars_analysis" not in sys.modules:
    _pkg = types.ModuleType("ars_analysis")
    _pkg.__path__ = [str(_SCRIPTS_DIR)]
    sys.modules["ars_analysis"] = _pkg

from ars_analysis.shared.branch_mapping import (  # noqa: E402
    apply_branch_names,
    load_branch_map,
    map_branch_id,
)


class TestLoadBranchMap:
    def test_no_client_id_returns_empty(self):
        assert load_branch_map(None) == {}
        assert load_branch_map("") == {}
        assert load_branch_map("   ") == {}

    def test_returns_mapping_from_inline_config(self):
        config = {
            "1776": {
                "ClientName": "CoastHills",
                "BranchMapping": {"10": "Base", "20": "Lompoc"},
            },
        }
        m = load_branch_map("1776", clients_config=config)
        assert m == {"10": "Base", "20": "Lompoc"}

    def test_client_id_coerced_to_string(self):
        config = {"1776": {"BranchMapping": {"1": "Main"}}}
        # Int client_id should still look up by string key.
        m = load_branch_map(1776, clients_config=config)
        assert m == {"1": "Main"}

    def test_missing_client_returns_empty(self):
        config = {"1776": {"BranchMapping": {"1": "Main"}}}
        assert load_branch_map("9999", clients_config=config) == {}

    def test_client_without_branch_mapping_returns_empty(self):
        config = {"1776": {"ClientName": "CoastHills"}}
        assert load_branch_map("1776", clients_config=config) == {}

    def test_lowercase_field_name_accepted(self):
        # Some legacy entries may carry the snake_case form.
        config = {"1776": {"branch_mapping": {"1": "Main"}}}
        assert load_branch_map("1776", clients_config=config) == {"1": "Main"}

    def test_strings_get_stripped(self):
        config = {"1776": {"BranchMapping": {" 10 ": "  Base  "}}}
        assert load_branch_map("1776", clients_config=config) == {"10": "Base"}

    def test_empty_or_invalid_config_returns_empty(self):
        assert load_branch_map("1776", clients_config={}) == {}
        assert load_branch_map("1776", clients_config={"1776": "not a dict"}) == {}
        # Unknown client ID against a valid config returns empty too.
        assert load_branch_map("DOES_NOT_EXIST", clients_config={"1776": {"BranchMapping": {"1": "x"}}}) == {}


class TestMapBranchId:
    def setup_method(self):
        self.mapping = {"1": "Main Office", "2": "Downtown", "10": "Base"}

    def test_direct_hit(self):
        assert map_branch_id("1", self.mapping) == "Main Office"

    def test_float_string_strips_to_int(self):
        # ODD often emits branch IDs as "1.0"; should still resolve.
        assert map_branch_id("1.0", self.mapping) == "Main Office"
        assert map_branch_id("10.0", self.mapping) == "Base"

    def test_unmapped_passes_through(self):
        assert map_branch_id("99", self.mapping) == "99"
        assert map_branch_id("99.0", self.mapping) == "99.0"

    def test_int_input_works(self):
        assert map_branch_id(1, self.mapping) == "Main Office"
        assert map_branch_id(10, self.mapping) == "Base"

    def test_none_or_blank_returns_empty(self):
        assert map_branch_id(None, self.mapping) == ""
        assert map_branch_id("", self.mapping) == ""
        assert map_branch_id("   ", self.mapping) == ""

    def test_whitespace_stripped(self):
        assert map_branch_id(" 1 ", self.mapping) == "Main Office"


class TestApplyBranchNames:
    def test_basic_replacement(self):
        df = pd.DataFrame({"branch": ["1", "2", "99"], "spend": [100, 200, 300]})
        mapping = {"1": "Main", "2": "Downtown"}
        out = apply_branch_names(df, mapping=mapping)
        assert list(out["branch"]) == ["Main", "Downtown", "99"]  # 99 passes through

    def test_default_column_is_branch(self):
        df = pd.DataFrame({"branch": ["1", "2"]})
        apply_branch_names(df, mapping={"1": "Main", "2": "Downtown"})
        assert list(df["branch"]) == ["Main", "Downtown"]

    def test_custom_column(self):
        df = pd.DataFrame({"Branch": ["1", "2"], "x": [10, 20]})
        apply_branch_names(df, column="Branch", mapping={"1": "Main"})
        assert df["Branch"].tolist() == ["Main", "2"]

    def test_missing_column_is_noop(self):
        df = pd.DataFrame({"x": [1, 2]})
        out = apply_branch_names(df, column="branch", mapping={"1": "Main"})
        assert list(out["x"]) == [1, 2]
        assert "branch" not in out.columns

    def test_empty_mapping_is_noop(self):
        df = pd.DataFrame({"branch": ["1", "2"]})
        apply_branch_names(df, mapping={})
        assert list(df["branch"]) == ["1", "2"]

    def test_none_mapping_loads_from_config(self):
        df = pd.DataFrame({"branch": ["1", "2"]})
        config = {"1776": {"BranchMapping": {"1": "Main", "2": "Downtown"}}}
        apply_branch_names(df, client_id="1776", clients_config=config)
        assert list(df["branch"]) == ["Main", "Downtown"]

    def test_handles_floats_and_nulls(self):
        df = pd.DataFrame({"branch": ["1.0", "2.0", None, ""]})
        apply_branch_names(df, mapping={"1": "Main", "2": "Downtown"})
        assert df["branch"].iloc[0] == "Main"
        assert df["branch"].iloc[1] == "Downtown"
        # NaN stays NaN; the function only touches non-null cells.
        assert pd.isna(df["branch"].iloc[2])

    def test_all_null_column_is_noop(self):
        df = pd.DataFrame({"branch": [None, None, None]})
        apply_branch_names(df, mapping={"1": "Main"})
        assert df["branch"].isna().all()


class TestWithRealRepoConfig:
    """Smoke test against the actual 03_Config/clients_config.json."""

    def test_loads_for_a_real_client(self):
        repo_root = Path(__file__).resolve().parents[3]
        cfg = repo_root / "03_Config" / "clients_config.json"
        if not cfg.exists():
            pytest.skip("Repo config not present")
        data = json.loads(cfg.read_text(encoding="utf-8"))
        # Find any client with a BranchMapping
        target = None
        for cid, entry in data.items():
            if isinstance(entry, dict) and entry.get("BranchMapping"):
                target = cid
                break
        if not target:
            pytest.skip("No client in config has a BranchMapping yet")
        m = load_branch_map(target, clients_config=data)
        assert isinstance(m, dict)
        assert m  # must be non-empty since we filtered for it
        # All keys + values are strings
        assert all(isinstance(k, str) for k in m.keys())
        assert all(isinstance(v, str) for v in m.values())
