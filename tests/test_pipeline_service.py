"""Tests du contrat applicatif du service d'orchestration."""
from __future__ import annotations

import json
from threading import Event
from pathlib import Path

import pytest

from services.pipeline_service import (
    PipelineCancelled,
    PipelineOptions,
    PipelineRequest,
    PipelineService,
    PipelineResult,
)
from src.config import Config


def test_pipeline_options_reject_invalid_values() -> None:
    with pytest.raises(ValueError, match=r"K doit être >= 1"):
        PipelineOptions(K=0, pop_size=30, n_gen=100)
    with pytest.raises(ValueError, match=r"pop_size doit être >= 2"):
        PipelineOptions(K=5, pop_size=1, n_gen=100)
    with pytest.raises(ValueError, match=r"n_gen doit être >= 1"):
        PipelineOptions(K=5, pop_size=30, n_gen=0)


def test_pipeline_request_normalizes_output_path(tmp_path: Path) -> None:
    request = PipelineRequest(
        config=Config.with_n(3, zero_loss=True),
        output_dir=str(tmp_path / "run"),
        options=PipelineOptions(K=5, pop_size=30, n_gen=100),
    )

    assert request.output_dir == tmp_path / "run"


def test_pipeline_result_exposes_artifacts_and_legacy_shape(tmp_path: Path) -> None:
    artifact = tmp_path / "validation_report.json"
    artifact.write_text("{}", encoding="utf-8")
    result = PipelineResult(
        output_dir=tmp_path,
        timings={"10_validator": 1.25},
        meta={"validation_status": "WARN", "n_points_generated": 9},
    )

    assert result.validation_status == "WARN"
    assert result.artifacts == [artifact]
    assert result.as_legacy_dict() == {
        "timings": {"10_validator": 1.25},
        "meta": {"validation_status": "WARN", "n_points_generated": 9},
    }


def test_pipeline_cancellation_marks_manifest_and_keeps_run_unloadable(
    tmp_path: Path,
) -> None:
    cancellation = Event()

    def cancel_on_first_generation(step: str, status: str, fraction: float) -> None:
        if step == "7_optimizer" and status.startswith("generation "):
            cancellation.set()

    output_dir = tmp_path / "cancelled-run"
    request = PipelineRequest(
        config=Config.with_n(3, zero_loss=True),
        output_dir=output_dir,
        options=PipelineOptions(K=5, pop_size=20, n_gen=10, seed=42),
        progress_callback=cancel_on_first_generation,
        cancellation_event=cancellation,
    )

    with pytest.raises(PipelineCancelled, match="Annulation demandée"):
        PipelineService().run(request)

    manifest = json.loads((output_dir / "run_manifest.json").read_text())
    assert manifest["status"] == "CANCELLED"
    assert manifest["cancelled_step"] == "7_optimizer"
    assert "solutions_pareto.csv" not in manifest["available_artifacts"]
