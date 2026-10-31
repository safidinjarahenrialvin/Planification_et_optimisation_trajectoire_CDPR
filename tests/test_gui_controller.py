"""Tests unitaires du contrôleur entre GUI et services scientifiques."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.controller import (
    GuiRunParameters,
    RunHandle,
    RunStatus,
    build_config,
    create_run_directory,
    run_from_gui,
)
from services.pipeline_service import PipelineCancelled, PipelineResult
from services.result_service import ResultService


def test_build_config_uses_the_central_config_rules() -> None:
    parameters = GuiRunParameters(
        n=3,
        platform="300x240",
        zero_loss=True,
        K=5,
        pop_size=30,
        n_gen=100,
        seed=42,
    )
    config = build_config(parameters)

    assert config.N == 9
    assert config.z_absolu_r0 == pytest.approx(0.45)


def test_build_config_propagates_explicit_r0_altitude() -> None:
    parameters = GuiRunParameters(
        n=3,
        platform="300x240",
        zero_loss=True,
        K=5,
        pop_size=30,
        n_gen=100,
        seed=42,
        z_absolu_r0_override=0.55,
    )

    assert build_config(parameters).z_absolu_r0 == pytest.approx(0.55)


def test_build_config_propagates_cli_geometry_and_mass_overrides() -> None:
    parameters = GuiRunParameters(
        n=5,
        platform="400x300",
        zero_loss=False,
        K=7,
        pop_size=120,
        n_gen=350,
        seed=9,
        platform_mass_kg=0.5,
        x_bound=0.20,
        y_bound=0.30,
    )

    config = build_config(parameters)

    assert config.masse_kg == pytest.approx(0.5)
    assert config.x_min == pytest.approx(-0.20)
    assert config.x_max == pytest.approx(0.20)
    assert config.y_min == pytest.approx(-0.30)
    assert config.y_max == pytest.approx(0.30)
    assert config.esp_x == pytest.approx(0.10)
    assert config.esp_y == pytest.approx(0.15)


def test_build_config_rejects_r0_altitude_outside_configured_bounds() -> None:
    parameters = GuiRunParameters(
        n=3,
        platform="300x240",
        zero_loss=True,
        K=5,
        pop_size=30,
        n_gen=100,
        seed=42,
        z_absolu_r0_override=0.95,
    )

    with pytest.raises(ValueError, match=r"\[R6\]"):
        build_config(parameters)


def test_create_run_directory_is_unique_and_isolated(tmp_path: Path) -> None:
    first_id, first_path = create_run_directory(tmp_path / "runs")
    second_id, second_path = create_run_directory(tmp_path / "runs")

    assert first_id != second_id
    assert first_path != second_path
    assert first_path.is_dir()
    assert second_path.is_dir()
    assert first_path.parent == second_path.parent == tmp_path / "runs"


def test_run_handle_rejects_double_start(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args, **kwargs):
        raise AssertionError("worker de test")

    monkeypatch.setattr("app.controller.run_from_gui", fake_run)
    handle = RunHandle()
    parameters = GuiRunParameters(3, "300x240", True, 5, 30, 100, 42)
    handle.start(parameters, Path("/tmp/runs"))
    with pytest.raises(RuntimeError, match="déjà été démarré"):
        handle.start(parameters, Path("/tmp/runs"))
    assert handle.wait(timeout=2)
    assert handle.snapshot().status is RunStatus.FAILED


def test_run_handle_captures_completed_result(monkeypatch: pytest.MonkeyPatch) -> None:
    result = PipelineResult(
        output_dir=Path("/tmp/completed-run"),
        timings={},
        meta={"validation_status": "PASS"},
    )

    def fake_run(*args, **kwargs):
        kwargs["progress_callback"]("7_optimizer", "generation 1/2", 0.5)
        return "run-completed", result

    monkeypatch.setattr("app.controller.run_from_gui", fake_run)
    handle = RunHandle()
    handle.start(GuiRunParameters(3, "300x240", True, 5, 30, 100, 42), Path("/tmp/runs"))
    assert handle.wait(timeout=2)
    snapshot = handle.snapshot()
    assert snapshot.status is RunStatus.COMPLETED
    assert snapshot.run_id == "run-completed"
    assert snapshot.progress == 1.0
    assert snapshot.result is result
    assert not handle.cancel()


def test_run_handle_maps_pipeline_cancellation(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args, **kwargs):
        raise PipelineCancelled("annulation de test")

    monkeypatch.setattr("app.controller.run_from_gui", fake_run)
    handle = RunHandle()
    handle.start(GuiRunParameters(3, "300x240", True, 5, 30, 100, 42), Path("/tmp/runs"))
    assert handle.wait(timeout=2)
    snapshot = handle.snapshot()
    assert snapshot.status is RunStatus.CANCELLED
    assert snapshot.error == "annulation de test"


def test_run_handle_can_cancel_before_worker_enters_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(*args, **kwargs):
        assert kwargs["cancellation_event"].is_set()
        raise PipelineCancelled("annulation immédiate")

    monkeypatch.setattr("app.controller.run_from_gui", fake_run)
    handle = RunHandle()
    parameters = GuiRunParameters(3, "300x240", True, 5, 30, 100, 42)
    assert handle.cancel()
    handle.start(parameters, Path("/tmp/runs"))

    assert handle.wait(timeout=2)
    snapshot = handle.snapshot()
    assert snapshot.status is RunStatus.CANCELLED
    assert snapshot.error == "annulation immédiate"


def test_run_handle_records_failure_before_manifest_creation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fail_before_pipeline(*args, **kwargs):
        raise ValueError("configuration invalide avant création du manifeste")

    monkeypatch.setattr("app.controller.run_from_gui", fail_before_pipeline)
    handle = RunHandle()
    handle.start(
        GuiRunParameters(3, "300x240", True, 5, 30, 100, 42),
        tmp_path / "runs",
    )

    assert handle.wait(timeout=2)
    snapshot = handle.snapshot()
    assert snapshot.status is RunStatus.FAILED
    assert "avant création" in (snapshot.error or "")
    assert not (tmp_path / "runs").exists()


def test_run_from_gui_creates_reloadable_complete_run(tmp_path: Path) -> None:
    progress_events: list[tuple[str, str, float]] = []

    run_id, result = run_from_gui(
        GuiRunParameters(
            n=3,
            platform="300x240",
            zero_loss=True,
            K=5,
            pop_size=30,
            n_gen=100,
            seed=42,
            z_absolu_r0_override=0.45,
        ),
        root=tmp_path / "runs",
        progress_callback=lambda step, status, fraction: progress_events.append(
            (step, status, fraction)
        ),
    )

    assert run_id.startswith("run_")
    assert result.output_dir == tmp_path / "runs" / run_id
    assert result.validation_status == "PASS"
    assert result.meta["run_status"] == "COMPLETED"
    assert result.meta["n_points_filtered"] == 9
    assert progress_events[0][0] == "4_point_generator"
    assert progress_events[-1] == ("11_comparator", "done", 1.0)
    optimizer_events = [
        event for event in progress_events
        if event[0] == "7_optimizer" and event[1].startswith("generation ")
    ]
    assert len(optimizer_events) == 100
    assert optimizer_events[0][2] == pytest.approx(0.01)
    assert optimizer_events[-1][2] == pytest.approx(1.0)

    results = ResultService.load(result.output_dir)
    assert results.validation_status == "PASS"
    assert len(results.points_filtered) == 9
    assert results.comparison_diagnostic["optimal_beats_baseline"] is True
    manifest = json.loads((result.output_dir / "run_manifest.json").read_text())
    assert manifest["status"] == "COMPLETED"
    assert manifest["completed_steps"][-1] == "11_comparator"
    config_snapshot = json.loads((result.output_dir / "config.json").read_text())
    assert config_snapshot["scientific"]["domains"]["agronomy_vision"][
        "z_absolu_r0_override"
    ] == pytest.approx(0.45)
    assert config_snapshot["scientific"]["derived"]["z_absolu_r0_m"] == pytest.approx(
        0.45
    )
    assert results.points_generated["z"].to_numpy() == pytest.approx([0.45] * 9)
