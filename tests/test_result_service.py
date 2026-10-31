"""Tests de lecture et d’analyse des résultats d’un run."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from shutil import copytree

import pytest
import pandas as pd

from services.result_service import ResultLoadError, ResultService
from visualization.pareto_plots import build_pareto_figure
from visualization.summary_plots import (
    build_absolute_comparison_figure,
    build_comparison_figure,
)
from visualization.cost_plots import (
    build_cost_distribution_figure,
    build_cost_heatmap,
)
from visualization.wfw_plots import build_wfw_coverage_figure
from visualization.trajectory_plots import (
    build_profile_figure,
    build_trajectory_xy_figure,
)
from visualization.run_comparison_plots import (
    build_run_gain_figure,
    build_run_kpi_figure,
)
from visualization.labels import baseline_kind, baseline_label, kind_label


REFERENCE = Path(__file__).parents[1] / "tests" / "fixtures" / "reference_run"


def test_result_service_loads_reference_run() -> None:
    results = ResultService.load(REFERENCE)

    assert results.validation_status == "PASS"
    assert len(results.points_filtered) == 9
    assert len(results.pareto) == 16
    assert len(results.cost_matrix) == 81
    assert results.point_filter_report["summary"]["reject_rate"] == 0.0
    assert results.point_statistics()["count"] == 9
    assert results.trajectory_statistics()["best_time_kind"] == "time_opt"
    assert results.trajectory_statistics()["best_time_motion_kind"] == "time_opt"
    assert results.trajectory_statistics()["best_time_total_kind"] == "time_opt"
    assert results.trajectory_statistics()["best_energy_kind"] == "energy_opt"
    assert results.trajectory_statistics()["min_time_total_s"] == pytest.approx(95.199475)
    assert results.points_rejected.empty
    assert len(results.baseline_trajectory) == 10
    assert results.baseline_trajectory["kind"].eq("baseline_zigzag").all()


def test_trajectory_time_rankings_keep_motion_and_total_distinct() -> None:
    results = ResultService.load(REFERENCE)
    summary = results.trajectory_summary.copy()
    # La stabilisation peut différer du temps de déplacement : le contrat
    # doit exposer cette différence au lieu de l'effacer dans « plus rapide ».
    summary.loc[summary["kind"] == "time_opt", "total_time_stab_s"] = 100.0
    summary["total_time_s"] = summary["total_time_motion_s"] + summary["total_time_stab_s"]
    ranked = replace(results, trajectory_summary=summary).trajectory_statistics()

    assert ranked["best_time_motion_kind"] == "time_opt"
    assert ranked["best_time_total_kind"] != ranked["best_time_motion_kind"]


def test_wfw_coverage_figure_uses_real_point_statuses() -> None:
    results = ResultService.load(REFERENCE)
    figure = build_wfw_coverage_figure(
        results.points_generated,
        results.points_filtered,
        results.points_rejected,
    )

    assert len(figure.data) == 2
    assert figure.layout.xaxis.title.text == "X (m)"
    assert figure.layout.yaxis.title.text == "Y (m)"


def test_wfw_coverage_figure_supports_explicit_point_views() -> None:
    results = ResultService.load(REFERENCE)

    retained = build_wfw_coverage_figure(
        results.points_generated,
        results.points_filtered,
        results.points_rejected,
        view="retained",
    )
    rejected = build_wfw_coverage_figure(
        results.points_generated,
        results.points_filtered,
        results.points_rejected,
        view="rejected",
    )

    assert [trace.name for trace in retained.data] == ["Points retenus"]
    assert len(rejected.data) == 0
    assert "points rejetés" in rejected.layout.title.text
    with pytest.raises(ValueError, match="Vue WFW inconnue"):
        build_wfw_coverage_figure(
            results.points_generated,
            results.points_filtered,
            results.points_rejected,
            view="invalid",
        )


def test_result_service_loads_explicit_test_fixture() -> None:
    results = ResultService.load(REFERENCE)

    assert results.output_dir.name == "reference_run"
    assert results.comparison_diagnostic["optimal_beats_baseline"] is True
    assert results.comparison["gain_time_vs_baseline_pct"].max() > 20


def test_pareto_and_gain_statistics_explain_aggregated_kpis() -> None:
    results = ResultService.load(REFERENCE)
    assert results.pareto_statistics() == {
        "raw_count": 16,
        "distinct_count": 4,
        "duplicate_count": 12,
    }
    stats = results.gain_statistics()
    assert stats["baseline_kind"] == "baseline_zigzag"
    assert stats["baseline_time_motion_s"] == pytest.approx(98.232286)
    assert stats["baseline_energy_J"] == pytest.approx(197.98825)
    assert stats["strategy_count"] == 3
    assert stats["time_metric"] == "time_motion_s"
    assert stats["energy_metric"] == "energy_J"
    assert stats["min_time_gain_pct"] == pytest.approx(6.1535888516327475)
    assert stats["min_time_gain_kind"] == "energy_opt"
    assert stats["max_time_gain_pct"] == pytest.approx(21.41130157553291)
    assert stats["max_time_gain_kind"] == "time_opt"
    assert stats["min_energy_gain_pct"] == pytest.approx(12.831856435924854)
    assert stats["min_energy_gain_kind"] == "time_opt"
    assert stats["max_energy_gain_pct"] == pytest.approx(14.027942567298812)
    assert stats["max_energy_gain_kind"] == "energy_opt"
    assert "baseline" in stats["time_formula"]


def test_result_service_reports_missing_artifact(tmp_path: Path) -> None:
    with pytest.raises(ResultLoadError, match=r"Répertoire de run introuvable"):
        ResultService.load(tmp_path / "missing")


def test_result_service_reports_incomplete_run(tmp_path: Path) -> None:
    tmp_path.mkdir(exist_ok=True)
    with pytest.raises(ResultLoadError, match=r"Artefact CSV manquant"):
        ResultService.load(tmp_path)


def test_result_service_reports_missing_columns(tmp_path: Path) -> None:
    run = tmp_path / "run"
    copytree(REFERENCE, run)
    comparison = pd.read_csv(run / "comparison.csv").drop(columns=["energy_J"])
    comparison.to_csv(run / "comparison.csv", index=False)

    with pytest.raises(ResultLoadError, match=r"comparison\.csv.*energy_J"):
        ResultService.load(run)


def test_result_service_reports_non_finite_values(tmp_path: Path) -> None:
    run = tmp_path / "run"
    copytree(REFERENCE, run)
    comparison = pd.read_csv(run / "comparison.csv")
    comparison.loc[0, "energy_J"] = float("nan")
    comparison.to_csv(run / "comparison.csv", index=False)

    with pytest.raises(ResultLoadError, match=r"valeurs non numériques.*energy_J"):
        ResultService.load(run)


def test_result_service_coerces_numeric_strings_and_accepts_empty_optional_rejections(
    tmp_path: Path,
) -> None:
    run = tmp_path / "run"
    copytree(REFERENCE, run)
    comparison = pd.read_csv(run / "comparison.csv")
    comparison["n_waypoints"] = comparison["n_waypoints"].astype(str)
    comparison["energy_J"] = comparison["energy_J"].map(lambda value: f"{value:.6f}")
    comparison.to_csv(run / "comparison.csv", index=False)
    (run / "points_rejetes_cause_a.csv").write_text(
        "id,x,y,z,ligne,colonne,cause,raison\n", encoding="utf-8"
    )

    results = ResultService.load(run)

    assert results.comparison["n_waypoints"].dtype.kind in "iu"
    assert results.comparison["energy_J"].dtype.kind == "f"
    assert results.points_rejected.empty


def test_result_service_rejects_fractional_integer_and_invalid_optional_csv(
    tmp_path: Path,
) -> None:
    run = tmp_path / "run"
    copytree(REFERENCE, run)
    comparison = pd.read_csv(run / "comparison.csv")
    comparison["n_waypoints"] = comparison["n_waypoints"].astype(object)
    comparison.loc[0, "n_waypoints"] = 10.5
    comparison.to_csv(run / "comparison.csv", index=False)
    with pytest.raises(ResultLoadError, match=r"valeurs entières attendues.*n_waypoints"):
        ResultService.load(run)

    copytree(REFERENCE, run, dirs_exist_ok=True)
    (run / "baseline_zigzag.csv").write_text("kind,rank\nbaseline_zigzag,0\n", encoding="utf-8")
    with pytest.raises(ResultLoadError, match=r"baseline_zigzag\.csv.*colonnes manquantes"):
        ResultService.load(run)


def test_result_service_reports_inconsistent_strategy_kinds(tmp_path: Path) -> None:
    run = tmp_path / "run"
    copytree(REFERENCE, run)
    comparison = pd.read_csv(run / "comparison.csv")
    comparison.loc[comparison["kind"] == "time_opt", "kind"] = "unknown_strategy"
    comparison.to_csv(run / "comparison.csv", index=False)

    with pytest.raises(ResultLoadError, match=r"unknown_strategy"):
        ResultService.load(run)


def test_result_service_rejects_non_contiguous_trajectory_ranks(tmp_path: Path) -> None:
    run = tmp_path / "run"
    copytree(REFERENCE, run)
    trajectories = pd.read_csv(run / "trajectories.csv")
    trajectories.loc[
        (trajectories["kind"] == "time_opt") & (trajectories["rank"] == 1), "rank"
    ] = 99
    trajectories.to_csv(run / "trajectories.csv", index=False)

    with pytest.raises(ResultLoadError, match=r"rangs non contigus.*time_opt"):
        ResultService.load(run)


def test_result_service_rejects_trajectory_summary_waypoint_mismatch(tmp_path: Path) -> None:
    run = tmp_path / "run"
    copytree(REFERENCE, run)
    summary = pd.read_csv(run / "trajectories_summary.csv")
    summary.loc[summary["kind"] == "compromise", "n_waypoints"] = 999
    summary.to_csv(run / "trajectories_summary.csv", index=False)

    with pytest.raises(ResultLoadError, match=r"n_waypoints incohérent pour 'compromise'"):
        ResultService.load(run)


def test_result_service_rejects_missing_baseline(tmp_path: Path) -> None:
    run = tmp_path / "run"
    copytree(REFERENCE, run)
    comparison = pd.read_csv(run / "comparison.csv")
    comparison.loc[comparison["kind"].str.startswith("baseline_"), "kind"] = "reference"
    comparison.to_csv(run / "comparison.csv", index=False)

    with pytest.raises(ResultLoadError, match=r"exactement une baseline, trouvé 0"):
        ResultService.load(run)


def test_result_service_rejects_multiple_baselines(tmp_path: Path) -> None:
    run = tmp_path / "run"
    copytree(REFERENCE, run)
    comparison = pd.read_csv(run / "comparison.csv")
    comparison.loc[comparison.index[-1], "kind"] = "baseline_nn"
    comparison.to_csv(run / "comparison.csv", index=False)

    with pytest.raises(ResultLoadError, match=r"exactement une baseline, trouvé 2"):
        ResultService.load(run)


def test_result_service_rejects_missing_strategy_profile(tmp_path: Path) -> None:
    run = tmp_path / "run"
    copytree(REFERENCE, run)
    profiles = pd.read_csv(run / "profiles.csv")
    profiles = profiles[profiles["kind"] != "compromise"]
    profiles.to_csv(run / "profiles.csv", index=False)

    with pytest.raises(ResultLoadError, match=r"profiles\.csv.*différentes"):
        ResultService.load(run)


@pytest.mark.parametrize(
    ("filename", "mutate", "message"),
    [
        (
            "validation_report.json",
            lambda value: value.pop("checks"),
            r"validation_report\.json.*checks doit être une liste non vide",
        ),
        (
            "validation_report.json",
            lambda value: value["checks"][0].update(status=[]),
            r"validation_report\.json.*checks\[0\] doit contenir",
        ),
        (
            "comparison_diagnostic.json",
            lambda value: value.update(per_trajectory=[]),
            r"comparison_diagnostic\.json.*per_trajectory invalide",
        ),
        (
            "comparison_diagnostic.json",
            lambda value: value.update(min_time_gain_pct=10**400),
            r"comparison_diagnostic\.json.*min_time_gain_pct doit être un nombre fini",
        ),
        (
            "hypotheses_report.json",
            lambda value: value.pop("hypotheses"),
            r"hypotheses_report\.json.*liste d’hypothèses",
        ),
        (
            "points_generes_report.json",
            lambda value: value.update(fov_footprint=[]),
            r"points_generes_report\.json.*empreinte FOV",
        ),
        (
            "point_filter_report.json",
            lambda value: value.pop("summary"),
            r"point_filter_report\.json.*summary et alerts",
        ),
    ],
)
def test_result_service_rejects_invalid_json_artifact_shapes(
    tmp_path: Path,
    filename: str,
    mutate,
    message: str,
) -> None:
    run = tmp_path / "run"
    copytree(REFERENCE, run)
    report_path = run / filename
    report = json.loads(report_path.read_text(encoding="utf-8"))
    mutate(report)
    report_path.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(ResultLoadError, match=message):
        ResultService.load(run)


def test_result_service_reports_divergent_configuration_fingerprint(tmp_path: Path) -> None:
    run = tmp_path / "run"
    copytree(REFERENCE, run)
    (run / ".config_hash").write_text("0000000000000000", encoding="utf-8")

    with pytest.raises(ResultLoadError, match=r"config\.json et \.config_hash divergent"):
        ResultService.load(run)


def test_result_service_rejects_failed_manifest_and_discovery_excludes_it(
    tmp_path: Path,
) -> None:
    runs = tmp_path / "runs"
    run = runs / "failed"
    copytree(REFERENCE, run)
    (run / "run_manifest.json").write_text(
        '{"status": "FAILED", "failed_step": "7_optimizer", '
        '"error": "front Pareto invalide"}',
        encoding="utf-8",
    )

    with pytest.raises(ResultLoadError, match=r"statut 'FAILED'.*7_optimizer"):
        ResultService.load(run)
    assert ResultService.discover_loadable_runs(runs) == []
    assert ResultService.incomplete_runs(runs) == [run]


def test_diagnose_run_exposes_failure_and_artifact_inventory(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    run = runs / "failed"
    copytree(REFERENCE, run)
    (run / "run_manifest.json").write_text(
        '{"status": "FAILED", "failed_step": "7_optimizer", '
        '"error": "front Pareto invalide"}',
        encoding="utf-8",
    )
    (run / "comparison.csv").unlink()

    diagnostic = ResultService.diagnose_run(run)

    assert diagnostic["loadable"] is False
    assert diagnostic["manifest_status"] == "FAILED"
    assert diagnostic["failed_step"] == "7_optimizer"
    assert diagnostic["manifest_error"] == "front Pareto invalide"
    assert "comparison.csv" in diagnostic["missing_artifacts"]
    assert "run_manifest.json" in diagnostic["available_artifacts"]
    assert "non chargeable" in diagnostic["error"]


def test_result_service_diagnoses_cancelled_manifest(tmp_path: Path) -> None:
    run = tmp_path / "cancelled"
    copytree(REFERENCE, run)
    (run / "run_manifest.json").write_text(
        '{"status": "CANCELLED", "cancelled_step": "7_optimizer", '
        '"error": "Annulation demandée après la génération 1/10"}',
        encoding="utf-8",
    )

    diagnostic = ResultService.diagnose_run(run)

    assert diagnostic["loadable"] is False
    assert diagnostic["manifest_status"] == "CANCELLED"
    assert diagnostic["cancelled_step"] == "7_optimizer"
    assert "statut 'CANCELLED'" in diagnostic["error"]


def test_result_service_rejects_manifest_with_non_object_root(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    run = runs / "malformed"
    copytree(REFERENCE, run)
    (run / "run_manifest.json").write_text("[]", encoding="utf-8")

    with pytest.raises(ResultLoadError, match=r"run_manifest\.json doit être un objet"):
        ResultService.load(run)
    assert ResultService.discover_loadable_runs(runs) == []
    assert ResultService.incomplete_runs(runs) == [run]


def test_discovery_excludes_incomplete_sources(tmp_path: Path) -> None:
    snapshots = tmp_path / "snapshots"
    snapshots.mkdir()
    copytree(REFERENCE, snapshots / "complete")
    (snapshots / "complete" / "run_manifest.json").write_text(
        '{"schema_version": 1, "status": "COMPLETED"}',
        encoding="utf-8",
    )
    symlinked = snapshots / "symlinked-manifest"
    copytree(REFERENCE, symlinked)
    external_manifest = tmp_path / "external-manifest.json"
    external_manifest.write_text(
        '{"schema_version": 1, "status": "COMPLETED"}',
        encoding="utf-8",
    )
    (symlinked / "run_manifest.json").symlink_to(external_manifest)
    (snapshots / "incomplete").mkdir()
    (snapshots / "incomplete" / "validation_report.json").write_text("{}")

    discovered = ResultService.discover_snapshots(snapshots)

    assert [path.name for path in discovered] == ["complete"]


def test_pareto_figure_is_interactive_and_has_expected_axes() -> None:
    results = ResultService.load(REFERENCE)
    figure = build_pareto_figure(results.pareto)

    assert len(figure.data) == 1
    assert len(figure.data[0].x) == 16
    assert figure.layout.xaxis.title.text == "Temps de mouvement (s)"
    assert figure.layout.yaxis.title.text == "Énergie (J)"
    assert "lines" in figure.data[0].mode
    assert "compromis" in figure.layout.title.text
    assert figure.layout.annotations


def test_large_pareto_figure_is_bounded_for_display() -> None:
    pareto = pd.DataFrame({
        "solution_id": range(2501),
        "time": range(2501),
        "energy": range(2501, 0, -1),
    })

    figure = build_pareto_figure(pareto)

    assert len(figure.data[0].x) == 2000
    assert "échantillonné" in figure.layout.title.text


def test_comparison_figure_uses_real_gain_columns() -> None:
    results = ResultService.load(REFERENCE)
    figure = build_comparison_figure(results.comparison)

    assert len(figure.data) == 3
    assert figure.layout.yaxis.title.text == "Gain relatif (%)"
    assert max(figure.data[0].y) > 20
    assert figure.data[2].name == "Niveau de la baseline : 0 %"
    assert set(figure.data[2].y) == {0}


def test_absolute_comparison_figure_keeps_baseline_as_reference() -> None:
    results = ResultService.load(REFERENCE)
    figure = build_absolute_comparison_figure(results.comparison)

    assert len(figure.data) == 4
    assert len(figure.data[0].x) == 4
    assert "Baseline : zigzag" in figure.layout.title.text
    assert figure.layout.xaxis.title.text == "Trajectoire"
    assert figure.layout.xaxis2.title.text == "Trajectoire"
    assert figure.layout.yaxis.title.text == "Temps de mouvement (s)"
    assert figure.layout.yaxis2.title.text == "Énergie (J)"
    assert {trace.name for trace in figure.data[2:]} == {
        "Baseline", "Stratégies optimisées"
    }


def test_baseline_labels_follow_the_actual_kind() -> None:
    official = "Baseline : zigzag"
    fallback = "Baseline de repli historique : plus proche voisin"
    assert baseline_label(["baseline_zigzag", "time_opt"]) == official
    assert baseline_label(["baseline_nn", "time_opt"]) == fallback
    assert baseline_kind(["baseline_nn", "baseline_zigzag"]) == "baseline_zigzag"
    assert kind_label("baseline_zigzag") == official
    assert kind_label("baseline_nn") == fallback
    comparison = pd.DataFrame([
        {
            "kind": "baseline_nn",
            "time_motion_s": 10.0,
            "energy_J": 20.0,
        },
        {
            "kind": "time_opt",
            "time_motion_s": 8.0,
            "energy_J": 18.0,
        },
    ])
    figure = build_absolute_comparison_figure(comparison)
    assert fallback in figure.layout.title.text
    assert fallback in figure.data[0].x


def test_legacy_baseline_nn_run_remains_loadable_and_explicit(
    legacy_baseline_run_fixture: Path,
) -> None:
    results = ResultService.load(legacy_baseline_run_fixture)

    assert results.comparison_diagnostic["baseline_kind"] == "baseline_nn"
    assert results.baseline_trajectory["kind"].eq("baseline_nn").all()
    assert results.gain_statistics()["baseline_kind"] == "baseline_nn"
    summary = ResultService.summarize("legacy", results)
    assert summary.baseline_kind == "baseline_nn"


def test_trajectory_figures_use_real_profile_and_waypoint_data() -> None:
    results = ResultService.load(REFERENCE)
    trajectory_figure = build_trajectory_xy_figure(results.trajectories)
    profile_figure = build_profile_figure(results.profiles, "compromise")

    assert len(trajectory_figure.data) == 3
    selected_figure = build_trajectory_xy_figure(results.trajectories, "energy_opt")
    assert len(selected_figure.data) == 1
    assert "Trajectoire énergie optimale" in selected_figure.layout.title.text
    combined = pd.concat(
        [results.baseline_trajectory, results.trajectories.query("kind == 'energy_opt'")],
        ignore_index=True,
    )
    combined_figure = build_trajectory_xy_figure(combined)
    assert {trace.name for trace in combined_figure.data} == {
        "Baseline : zigzag", "Trajectoire énergie optimale"
    }
    assert len(profile_figure.data) == 4
    assert profile_figure.layout.yaxis.title.text == "Vitesse (m/s)"


def test_cost_heatmaps_use_real_transition_matrix() -> None:
    results = ResultService.load(REFERENCE)
    figure = build_cost_heatmap(results.cost_matrix, "time")

    assert len(figure.data) == 1
    assert figure.data[0].z.shape == (9, 9)
    assert figure.layout.xaxis.title.text == "Point d’arrivée j"


def test_cost_statistics_exclude_self_loops_and_summarize_feasible_edges() -> None:
    results = ResultService.load(REFERENCE)
    matrix = results.cost_matrix.copy()
    self_loops = matrix["i"] == matrix["j"]
    first_edge = matrix.index[~self_loops][0]
    matrix.loc[first_edge, "feasible"] = 0

    summary = replace(results, cost_matrix=matrix).cost_statistics()

    assert summary["point_count"] == 9
    assert summary["transition_count"] == 72
    assert summary["feasible_count"] == 71
    assert summary["infeasible_count"] == 1
    assert summary["feasibility_rate"] == pytest.approx(71 / 72)
    assert summary["metrics"]["time"]["count"] == 71
    assert summary["metrics"]["time"]["min"] > 0
    assert summary["metrics"]["time"]["q1"] <= summary["metrics"]["time"]["median"]


def test_cost_distribution_figure_separates_units_and_uses_feasible_edges() -> None:
    results = ResultService.load(REFERENCE)
    figure = build_cost_distribution_figure(results.cost_matrix)

    boxes = [trace for trace in figure.data if trace.type == "box"]
    means = [trace for trace in figure.data if trace.name == "Moyenne"]
    assert len(boxes) == 3
    assert len(means) == 3
    assert all(len(trace.y) == 72 for trace in boxes)
    assert all(trace.marker.symbol == "diamond" for trace in means)
    assert figure.layout.yaxis.title.text == "m"
    assert figure.layout.yaxis2.title.text == "s"
    assert figure.layout.yaxis3.title.text == "J"
    assert "transition faisable" in figure.layout.title.text


def test_large_cost_heatmap_is_bounded_for_display() -> None:
    values = [
        {"i": i, "j": j, "time": float(i + j), "energy": 1.0, "feasible": 1}
        for i in range(201)
        for j in range(201)
    ]
    figure = build_cost_heatmap(pd.DataFrame(values), "time")

    assert figure.data[0].z.shape == (150, 150)
    assert "échantillonné" in figure.layout.title.text


def test_run_summary_is_comparable_and_figures_keep_separate_units() -> None:
    results = ResultService.load(REFERENCE)
    summary = ResultService.summarize("reference", results, is_reference=True)
    kpi = build_run_kpi_figure([summary])
    gains = build_run_gain_figure([summary])

    assert summary.coverage_rate == 1.0
    assert summary.pareto_count == 16
    assert summary.pareto_distinct_count == 4
    assert summary.is_reference is True
    assert summary.baseline_kind == "baseline_zigzag"
    assert len(kpi.data) == 2
    assert len(gains.data) == 3
    assert gains.data[2].name == "Niveau des baselines : 0 %"
    assert kpi.data[0].customdata[0] == "Baseline : zigzag"
    assert "Baseline : %{customdata}" in gains.data[0].hovertemplate
