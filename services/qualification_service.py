"""Campagnes reproductibles de qualification scientifique du pipeline SP2.

Ce module orchestre plusieurs runs indépendants sans modifier les algorithmes
scientifiques. Chaque seed possède son propre répertoire et la campagne
produit un manifeste ainsi qu'un résumé exploitable par un humain ou un outil.
"""
from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from services.configuration_service import ConfigurationService
from services.pareto_stability import write_stability_report
from services.pipeline_service import PipelineOptions, PipelineRequest, PipelineService
from src.config import Config


@dataclass(frozen=True)
class QualificationSpec:
    """Paramètres gelés d'une campagne de qualification."""

    n: int = 9
    platform: str = "300x240"
    zero_loss: bool = True
    K: int = 10
    pop_size: int = 500
    n_gen: int = 1500
    seeds: tuple[int, ...] = (42, 43, 44)

    def __post_init__(self) -> None:
        if self.n < 3 or self.n % 2 == 0:
            raise ValueError("n doit être impair et supérieur ou égal à 3.")
        if self.K < 1 or self.pop_size < 2 or self.n_gen < 1:
            raise ValueError("K, pop_size et n_gen doivent être strictement valides.")
        if not self.seeds:
            raise ValueError("La campagne doit contenir au moins une seed.")
        if len(set(self.seeds)) != len(self.seeds):
            raise ValueError("Les seeds doivent être uniques.")


@dataclass(frozen=True)
class QualificationRecord:
    """Résultat résumé d'un run de campagne."""

    seed: int
    run_dir: str
    status: str
    validation_status: str
    n_points_generated: int | None = None
    n_points_filtered: int | None = None
    n_pareto_solutions: int | None = None
    optimal_beats_baseline: bool | None = None
    min_time_gain_pct: float | None = None
    min_energy_gain_pct: float | None = None
    error: str | None = None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _record_from_run(seed: int, run_dir: Path, result_meta: dict[str, Any]) -> QualificationRecord:
    manifest = _read_json(run_dir / "run_manifest.json")
    diagnostic = _read_json(run_dir / "comparison_diagnostic.json")
    status = str(manifest.get("status", result_meta.get("run_status", "UNKNOWN")))
    validation_status = str(
        manifest.get("validation_status", result_meta.get("validation_status", "UNKNOWN"))
    )
    return QualificationRecord(
        seed=seed,
        run_dir=str(run_dir),
        status=status,
        validation_status=validation_status,
        n_points_generated=_optional_int(result_meta.get("n_points_generated")),
        n_points_filtered=_optional_int(result_meta.get("n_points_filtered")),
        n_pareto_solutions=_optional_int(result_meta.get("n_pareto_solutions")),
        optimal_beats_baseline=_optional_bool(diagnostic.get("optimal_beats_baseline")),
        min_time_gain_pct=_optional_float(diagnostic.get("min_time_gain_pct")),
        min_energy_gain_pct=_optional_float(diagnostic.get("min_energy_gain_pct")),
        error=str(manifest["error"]) if manifest.get("error") else None,
    )


def _optional_int(value: Any) -> int | None:
    return int(value) if value is not None else None


def _optional_float(value: Any) -> float | None:
    return float(value) if value is not None else None


def _optional_bool(value: Any) -> bool | None:
    return bool(value) if value is not None else None


def write_records_csv(path: Path, records: Iterable[QualificationRecord]) -> None:
    """Écrit un résumé tabulaire stable de la campagne."""
    rows = [asdict(record) for record in records]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(QualificationRecord.__dataclass_fields__))
        writer.writeheader()
        writer.writerows(rows)


def run_qualification(spec: QualificationSpec, output_dir: Path) -> list[QualificationRecord]:
    """Exécute une campagne séquentielle et conserve chaque run séparément."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    config = Config.with_n(spec.n, platform=spec.platform, zero_loss=spec.zero_loss)
    records: list[QualificationRecord] = []
    _write_json(
        output_dir / "qualification_manifest.json",
        {
            "schema_version": 1,
            "status": "RUNNING",
            "scientific_status": "NOT_VALIDATED",
            "specification": asdict(spec),
            "configuration_fingerprint_basis": ConfigurationService.serialize_config(config),
            "runs": [],
        },
    )

    for seed in spec.seeds:
        run_dir = output_dir / f"seed_{seed}"
        run_dir.mkdir(parents=True, exist_ok=False)
        try:
            effective = ConfigurationService.validate(
                config,
                K=spec.K,
                pop_size=spec.pop_size,
                n_gen=spec.n_gen,
                seed=seed,
            )
            result = PipelineService().run(
                PipelineRequest(
                    config=effective.config,
                    output_dir=run_dir,
                    options=PipelineOptions(
                        K=effective.K,
                        pop_size=effective.pop_size,
                        n_gen=effective.n_gen,
                        seed=effective.seed,
                    ),
                )
            )
            record = _record_from_run(seed, run_dir, result.meta)
        except Exception as exc:  # campagne : conserver les échecs pour diagnostic
            record = _record_from_run(seed, run_dir, {})
            if record.status == "UNKNOWN":
                record = QualificationRecord(
                    seed=seed,
                    run_dir=str(run_dir),
                    status="FAILED",
                    validation_status="UNKNOWN",
                    error=str(exc),
                )
        records.append(record)
        _write_json(
            output_dir / "qualification_manifest.json",
            {
                "schema_version": 1,
                "status": "RUNNING",
                "scientific_status": "NOT_VALIDATED",
                "specification": asdict(spec),
                "configuration_fingerprint_basis": ConfigurationService.serialize_config(config),
                "runs": [asdict(item) for item in records],
            },
        )

    write_records_csv(output_dir / "qualification_summary.csv", records)
    _write_json(
        output_dir / "qualification_manifest.json",
        {
            "schema_version": 1,
            "status": "COMPLETED",
            "scientific_status": "NOT_VALIDATED",
            "specification": asdict(spec),
            "configuration_fingerprint_basis": ConfigurationService.serialize_config(config),
            "runs": [asdict(item) for item in records],
        },
    )
    if all(
        record.status == "COMPLETED"
        and (Path(record.run_dir) / "solutions_pareto.csv").is_file()
        for record in records
    ):
        write_stability_report(output_dir)
    return records
