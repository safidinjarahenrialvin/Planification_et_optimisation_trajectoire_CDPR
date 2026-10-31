"""Tests des exports reproductibles d’un run."""
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
import json

import pytest

from services.export_service import ExportService
from services.result_service import ResultService


def test_read_artifact_rejects_path_escape(run_fixture: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ExportService.read_artifact(run_fixture, "../config.py")


def test_markdown_report_contains_run_metrics(run_fixture: Path) -> None:
    results = ResultService.load(run_fixture)
    report = ExportService.markdown_report("run-test", results)
    assert "# Rapport jury — Tandem SP2 — `run-test`" in report
    assert "## 1. Conclusion exécutive" in report
    assert "## 3. Couverture et diagnostic WFW/FOV" in report
    assert "9" in report
    assert "Statut des contrôles automatiques" in report
    assert "validation scientifique humaine ou expérimentale" in report
    assert "| Trajectoire temps optimal |" in report
    assert "| Trajectoire énergie optimale |" in report


def test_summary_json_is_compact_and_tracks_selected_trajectory(run_fixture: Path) -> None:
    results = ResultService.load(run_fixture)
    payload = ExportService.summary_payload(
        "run-test", results, selected_kind="energy_opt"
    )
    summary = json.loads(
        ExportService.summary_json("run-test", results, selected_kind="energy_opt")
    )

    assert payload == summary
    assert summary["schema_version"] == 1
    assert summary["run"]["id"] == "run-test"
    assert summary["coverage"]["points_generated"] == 9
    assert summary["validation"]["status"] == results.validation_status
    assert summary["pareto"]["raw_solutions"] == len(results.pareto)
    assert summary["baseline"]["label"] == "Baseline : zigzag"
    assert summary["gains"]["time_metric"] == "time_motion_s"
    assert summary["trajectory_selected"]["kind"] == "energy_opt"
    assert "comparison" not in summary
    assert ExportService.summary_json("run-test", results, selected_kind="energy_opt") == (
        ExportService.summary_json("run-test", results, selected_kind="energy_opt")
    )


def test_targeted_exports_are_limited_to_the_selected_strategy(run_fixture: Path) -> None:
    results = ResultService.load(run_fixture)

    trajectory = ExportService.selected_trajectory_csv(results, "energy_opt").decode("utf-8")
    profile = ExportService.selected_profile_csv(results, "energy_opt").decode("utf-8")
    comparison = ExportService.selected_comparison_csv(results, "energy_opt").decode("utf-8")
    validation = json.loads(ExportService.validation_json(results))

    assert set(line.split(",")[0] for line in trajectory.splitlines()[1:]) == {"energy_opt"}
    assert set(line.split(",")[0] for line in profile.splitlines()[1:]) == {"energy_opt"}
    assert "energy_opt" in comparison
    assert validation["overall_status"] == results.validation_status

    with pytest.raises(ValueError, match="stratégie inconnue"):
        ExportService.selected_trajectory_csv(results, "unknown")


def test_jury_report_contains_real_comparison_table(run_fixture: Path) -> None:
    results = ResultService.load(run_fixture)
    report = ExportService.jury_markdown_report("run-test", results)

    assert "| Stratégie | Temps de mouvement (s)" in report
    assert "Gain temps de mouvement (%)" in report
    assert "Temps total (s)" in report
    assert "Transitions infaisables" in report
    assert "Baseline des gains" in report
    assert "Stratégies optimisées incluses dans les gains" in report
    assert "Gain temps de mouvement maximal" in report
    assert "Gain énergie maximal" in report
    assert "(baseline - strategy) / baseline" in report
    assert "Baseline : zigzag" in report
    assert "Distribution des coûts sur les transitions faisables" in report
    assert "Médiane" in report


def test_legacy_baseline_fallback_is_explicit_in_jury_export(
    legacy_baseline_run_fixture: Path,
) -> None:
    results = ResultService.load(legacy_baseline_run_fixture)
    report = ExportService.jury_markdown_report("legacy-run", results)
    fallback_label = "Baseline de repli historique : plus proche voisin"

    assert fallback_label in report
    assert f"Baseline des gains : `{fallback_label}`" in report
    with ZipFile(BytesIO(ExportService.zip_run(legacy_baseline_run_fixture))) as zip_file:
        comparison_csv = zip_file.read(
            f"{legacy_baseline_run_fixture.name}/comparison.csv"
        ).decode("utf-8")
    assert "baseline_nn" in comparison_csv


def test_zip_run_contains_config_and_scientific_tables(run_fixture: Path) -> None:
    archive = ExportService.zip_run(run_fixture)
    with ZipFile(BytesIO(archive)) as zip_file:
        names = set(zip_file.namelist())
    assert f"{run_fixture.name}/config.json" in names
    assert f"{run_fixture.name}/trajectories.csv" in names
    assert f"{run_fixture.name}/figures/pareto_front.png" in names


@pytest.mark.parametrize("status", ["RUNNING", "FAILED", "CANCELLED"])
def test_zip_run_rejects_non_completed_manifest(run_fixture: Path, status: str) -> None:
    (run_fixture / "run_manifest.json").write_text(
        json.dumps({"status": status}), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="seul COMPLETED est exportable"):
        ExportService.zip_run(run_fixture)


def test_zip_run_excludes_temporary_files(run_fixture: Path) -> None:
    temporary = run_fixture / "config.json.tmp"
    temporary.write_text("temporary", encoding="utf-8")

    archive = ExportService.zip_run(run_fixture)
    with ZipFile(BytesIO(archive)) as zip_file:
        assert f"{run_fixture.name}/config.json.tmp" not in zip_file.namelist()


def test_available_files_filters_extensions(run_fixture: Path) -> None:
    files = ExportService.available_files(run_fixture, (".json",))
    assert files
    assert all(path.suffix == ".json" for path in files)
