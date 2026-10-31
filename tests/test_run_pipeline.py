"""Regression tests for the pipeline command-line contract."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_pipeline import (
    _all_outputs_exist,
    _build_parser,
    _check_config_fingerprint,
    _config_fingerprint,
    _resolve_config_and_params,
    _validation_status,
)
from src.config import Config


def test_fast_mode_uses_zero_loss_bounds() -> None:
    args = _build_parser().parse_args(["--fast"])
    params = _resolve_config_and_params(args)
    config = params["config"]

    assert config.x_max == 0.40
    assert config.y_max == 0.24


def test_fast_mode_keeps_explicit_bounds_override() -> None:
    args = _build_parser().parse_args(["--fast", "--xy-bound", "0.20"])
    params = _resolve_config_and_params(args)
    config = params["config"]

    assert config.x_max == 0.20
    assert config.y_max == 0.20


def test_invalid_numeric_parameters_are_rejected() -> None:
    for option in (["--fast", "--K", "0"], ["--fast", "--pop-size", "1"],
                   ["--fast", "--n-gen", "0"]):
        args = _build_parser().parse_args(option)
        with pytest.raises(ValueError):
            _resolve_config_and_params(args)


def test_resume_fingerprint_includes_profile_parameters() -> None:
    base = Config.with_n(3, zero_loss=True)
    changed = Config.with_n(3, zero_loss=True, v_max=0.050, T_stabilisation=3.0)

    assert _config_fingerprint(base, 5, 30, 100, 42) != _config_fingerprint(
        changed, 5, 30, 100, 42,
    )


def test_resume_rejects_missing_fingerprint(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match=r"aucun \.config_hash"):
        _check_config_fingerprint(tmp_path, "hash", resume=True)


def test_resume_does_not_skip_empty_outputs(tmp_path: Path) -> None:
    (tmp_path / "points_generes.csv").touch()
    (tmp_path / "points_generes_report.json").write_text("{}", encoding="utf-8")

    assert not _all_outputs_exist(tmp_path, "4_point_generator")


def test_resume_reads_existing_validation_status(tmp_path: Path) -> None:
    (tmp_path / "validation_report.json").write_text(
        json.dumps({"overall_status": "WARN"}), encoding="utf-8",
    )

    assert _validation_status(tmp_path) == "WARN"
