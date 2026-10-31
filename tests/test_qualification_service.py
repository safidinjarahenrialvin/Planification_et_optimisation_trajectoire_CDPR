from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.qualification_service import (
    QualificationSpec,
    QualificationRecord,
    run_qualification,
    write_records_csv,
)
from services.pareto_stability import analyze_pareto_stability, write_stability_report


def test_spec_rejects_invalid_or_duplicate_seeds() -> None:
    with pytest.raises(ValueError, match="seeds doivent être uniques"):
        QualificationSpec(seeds=(42, 42))
    with pytest.raises(ValueError, match="impair"):
        QualificationSpec(n=8)


def test_write_records_csv_has_stable_contract(tmp_path: Path) -> None:
    path = tmp_path / "summary.csv"
    write_records_csv(
        path,
        [
            QualificationRecord(
                seed=42,
                run_dir="seed_42",
                status="COMPLETED",
                validation_status="WARN",
                n_pareto_solutions=3,
            )
        ],
    )
    content = path.read_text(encoding="utf-8")
    assert content.splitlines()[0].startswith("seed,run_dir,status,validation_status")
    assert "42,seed_42,COMPLETED,WARN" in content


def test_run_qualification_keeps_each_seed_and_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from services import qualification_service as module

    class FakeResult:
        def __init__(self) -> None:
            self.meta = {
                "run_status": "COMPLETED",
                "validation_status": "PASS",
                "n_points_generated": 81,
                "n_points_filtered": 81,
                "n_pareto_solutions": 12,
            }

    class FakePipeline:
        def run(self, request):
            request.output_dir.joinpath("run_manifest.json").write_text(
                json.dumps({
                    "status": "COMPLETED",
                    "validation_status": "PASS",
                    "completed_steps": [],
                }),
                encoding="utf-8",
            )
            request.output_dir.joinpath("comparison_diagnostic.json").write_text(
                json.dumps({
                    "optimal_beats_baseline": True,
                    "min_time_gain_pct": 4.0,
                    "min_energy_gain_pct": 5.0,
                }),
                encoding="utf-8",
            )
            return FakeResult()

    monkeypatch.setattr(module, "PipelineService", FakePipeline)
    records = run_qualification(
        QualificationSpec(seeds=(42, 43), pop_size=10, n_gen=2),
        tmp_path / "campaign",
    )

    assert [record.seed for record in records] == [42, 43]
    assert all(record.status == "COMPLETED" for record in records)
    assert (tmp_path / "campaign" / "seed_42").is_dir()
    assert (tmp_path / "campaign" / "seed_43").is_dir()
    manifest = json.loads(
        (tmp_path / "campaign" / "qualification_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["status"] == "COMPLETED"
    assert manifest["scientific_status"] == "NOT_VALIDATED"
    assert len(manifest["runs"]) == 2


def test_pareto_stability_reports_cardinality_and_pairwise_distances(
    tmp_path: Path,
) -> None:
    campaign = tmp_path / "campaign"
    fronts = {
        42: [(1.0, 4.0), (2.0, 3.0)],
        43: [(1.5, 3.5), (2.5, 2.5), (3.0, 2.0)],
    }
    for seed, values in fronts.items():
        run = campaign / f"seed_{seed}"
        run.mkdir(parents=True)
        rows = ["solution_id,time,energy,order"]
        rows.extend(
            f"{index},{time},{energy},[]"
            for index, (time, energy) in enumerate(values)
        )
        (run / "solutions_pareto.csv").write_text(
            "\n".join(rows) + "\n", encoding="utf-8"
        )

    report = analyze_pareto_stability(campaign)

    assert report["scientific_status"] == "NOT_VALIDATED"
    assert report["stability_status"] == "REVIEW_REQUIRED"
    assert report["aggregates"]["n_solutions"]["min"] == 2
    assert report["aggregates"]["n_solutions"]["max"] == 3
    assert report["observations"]["cardinality_varies"] is True
    assert len(report["pairwise"]) == 1
    assert report["pairwise"][0]["normalized_hausdorff"] > 0

    write_stability_report(campaign)
    assert (campaign / "pareto_stability_report.json").is_file()
    assert (campaign / "pareto_stability_report.md").is_file()
