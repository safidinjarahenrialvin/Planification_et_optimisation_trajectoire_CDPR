"""Mesures reproductibles de stabilité des fronts Pareto entre seeds.

Les objectifs ``time`` et ``energy`` sont minimisés. Ce module mesure la
variabilité observée entre fronts sans transformer automatiquement cette
observation en validation scientifique.
"""
from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

_REQUIRED_COLUMNS = ("time", "energy")
_EPSILON = 1e-12


def _finite_float(value: object, label: str) -> float:
    result = float(value)
    if not np.isfinite(result):
        raise ValueError(f"{label} doit être fini")
    return result


def _objective_summary(values: np.ndarray) -> dict[str, float]:
    return {
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "mean": float(np.mean(values)),
        "std": float(np.std(values, ddof=0)),
    }


def _coefficient_of_variation(values: list[float]) -> float | None:
    array = np.asarray(values, dtype=float)
    mean = float(np.mean(array))
    if abs(mean) <= _EPSILON:
        return None
    return float(np.std(array, ddof=0) / abs(mean))


def _interval_overlap(first: np.ndarray, second: np.ndarray) -> float:
    first_min, first_max = float(np.min(first)), float(np.max(first))
    second_min, second_max = float(np.min(second)), float(np.max(second))
    union = max(first_max, second_max) - min(first_min, second_min)
    if union <= _EPSILON:
        return 1.0
    intersection = max(0.0, min(first_max, second_max) - max(first_min, second_min))
    return float(intersection / union)


def _dominance_fraction(source: np.ndarray, other: np.ndarray) -> float:
    """Fraction des points source faiblement dominés par ``other``."""
    dominated = []
    for point in source:
        no_worse = np.all(other <= point + _EPSILON, axis=1)
        strictly_better = np.any(other < point - _EPSILON, axis=1)
        dominated.append(bool(np.any(no_worse & strictly_better)))
    return float(np.mean(dominated))


def _normalized_distances(
    first: np.ndarray,
    second: np.ndarray,
    scale: np.ndarray,
) -> tuple[float, float]:
    normalized_first = first / scale
    normalized_second = second / scale
    distances = np.linalg.norm(
        normalized_first[:, None, :] - normalized_second[None, :, :], axis=2
    )
    directed_first = np.min(distances, axis=1)
    directed_second = np.min(distances, axis=0)
    hausdorff = max(float(np.max(directed_first)), float(np.max(directed_second)))
    chamfer = float((np.mean(directed_first) + np.mean(directed_second)) / 2.0)
    return hausdorff, chamfer


def _load_front(seed: int, run_dir: Path, campaign_dir: Path) -> dict[str, Any]:
    path = run_dir / "solutions_pareto.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Artefact Pareto manquant pour seed {seed}: {path}")
    frame = pd.read_csv(path)
    missing = [column for column in _REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"{path}: colonnes Pareto manquantes: {', '.join(missing)}")
    values = frame.loc[:, list(_REQUIRED_COLUMNS)].apply(pd.to_numeric, errors="coerce")
    if values.empty or values.isna().any().any():
        raise ValueError(f"{path}: objectifs Pareto vides ou non numériques")
    array = values.to_numpy(dtype=float)
    if not np.isfinite(array).all():
        raise ValueError(f"{path}: objectifs Pareto non finis")
    return {
        "seed": int(seed),
        "run_dir": str(run_dir.relative_to(campaign_dir)),
        "n_solutions": len(array),
        "values": array,
        "time": _objective_summary(array[:, 0]),
        "energy": _objective_summary(array[:, 1]),
    }


def _campaign_runs(campaign_dir: Path) -> list[tuple[int, Path]]:
    manifest_path = campaign_dir / "qualification_manifest.json"
    if manifest_path.is_file():
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        runs = payload.get("runs", [])
        result = []
        for run in runs:
            seed = int(run["seed"])
            run_dir = Path(str(run["run_dir"]))
            if not run_dir.is_absolute():
                run_dir = Path.cwd() / run_dir
            if not run_dir.is_dir():
                candidate = campaign_dir / f"seed_{seed}"
                if candidate.is_dir():
                    run_dir = candidate
            result.append((seed, run_dir))
        if result:
            return result
    return [
        (int(path.name.removeprefix("seed_")), path)
        for path in sorted(campaign_dir.glob("seed_*"))
        if path.is_dir() and path.name.removeprefix("seed_").isdigit()
    ]


def analyze_pareto_stability(campaign_dir: Path) -> dict[str, Any]:
    """Retourne les mesures de stabilité des fronts Pareto d'une campagne."""
    campaign_dir = Path(campaign_dir).resolve()
    runs = _campaign_runs(campaign_dir)
    if len(runs) < 2:
        raise ValueError("Au moins deux seeds sont nécessaires pour analyser la stabilité.")
    fronts = [_load_front(seed, run_dir.resolve(), campaign_dir) for seed, run_dir in runs]
    pooled = np.vstack([front["values"] for front in fronts])
    scale = np.ptp(pooled, axis=0)
    scale[scale <= _EPSILON] = 1.0
    pairwise = []
    for first, second in combinations(fronts, 2):
        hausdorff, chamfer = _normalized_distances(
            first["values"], second["values"], scale
        )
        pairwise.append(
            {
                "seed_a": first["seed"],
                "seed_b": second["seed"],
                "normalized_hausdorff": hausdorff,
                "normalized_chamfer": chamfer,
                "time_interval_overlap": _interval_overlap(
                    first["values"][:, 0], second["values"][:, 0]
                ),
                "energy_interval_overlap": _interval_overlap(
                    first["values"][:, 1], second["values"][:, 1]
                ),
                "fraction_a_dominated_by_b": _dominance_fraction(
                    first["values"], second["values"]
                ),
                "fraction_b_dominated_by_a": _dominance_fraction(
                    second["values"], first["values"]
                ),
            }
        )
    cardinalities = [front["n_solutions"] for front in fronts]
    hausdorff_values = [item["normalized_hausdorff"] for item in pairwise]
    chamfer_values = [item["normalized_chamfer"] for item in pairwise]
    time_overlaps = [item["time_interval_overlap"] for item in pairwise]
    energy_overlaps = [item["energy_interval_overlap"] for item in pairwise]
    result = {
        "schema_version": 1,
        "scientific_status": "NOT_VALIDATED",
        "stability_status": "REVIEW_REQUIRED",
        "objective_definition": {
            "time": "Temps de mouvement à minimiser (s)",
            "energy": "Énergie à minimiser (J)",
            "distance_normalization": "Étendue observée sur tous les fronts de la campagne",
        },
        "seeds": [front["seed"] for front in fronts],
        "fronts": [
            {
                "seed": front["seed"],
                "run_dir": front["run_dir"],
                "n_solutions": front["n_solutions"],
                "time": front["time"],
                "energy": front["energy"],
            }
            for front in fronts
        ],
        "pooled_objective_scale": {
            "time_range_s": float(scale[0]),
            "energy_range_J": float(scale[1]),
        },
        "pairwise": pairwise,
        "aggregates": {
            "n_solutions": {
                "min": int(min(cardinalities)),
                "max": int(max(cardinalities)),
                "mean": float(np.mean(cardinalities)),
                "std": float(np.std(cardinalities, ddof=0)),
                "coefficient_of_variation": _coefficient_of_variation(cardinalities),
            },
            "normalized_hausdorff": {
                "mean": float(np.mean(hausdorff_values)),
                "max": float(np.max(hausdorff_values)),
            },
            "normalized_chamfer": {
                "mean": float(np.mean(chamfer_values)),
                "max": float(np.max(chamfer_values)),
            },
            "time_interval_overlap": {
                "mean": float(np.mean(time_overlaps)),
                "min": float(np.min(time_overlaps)),
            },
            "energy_interval_overlap": {
                "mean": float(np.mean(energy_overlaps)),
                "min": float(np.min(energy_overlaps)),
            },
        },
        "observations": {
            "cardinality_varies": len(set(cardinalities)) > 1,
            "time_envelopes_do_not_all_overlap": min(time_overlaps) <= _EPSILON,
            "energy_envelopes_do_not_all_overlap": min(energy_overlaps) <= _EPSILON,
            "fronts_are_not_identical": any(value > _EPSILON for value in hausdorff_values),
        },
        "interpretation": (
            "Les métriques décrivent la variabilité observée entre seeds. Elles ne "
            "définissent pas à elles seules un seuil d’acceptation scientifique ; "
            "une revue humaine doit fixer les seuils de stabilité et examiner les "
            "trajectoires, les gains et les hypothèses physiques."
        ),
    }
    return result


def write_stability_report(campaign_dir: Path) -> dict[str, Any]:
    """Écrit les rapports JSON et Markdown dans une campagne existante."""
    campaign_dir = Path(campaign_dir)
    report = analyze_pareto_stability(campaign_dir)
    json_path = campaign_dir / "pareto_stability_report.json"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown = _markdown_report(report)
    (campaign_dir / "pareto_stability_report.md").write_text(markdown, encoding="utf-8")
    return report


def _markdown_report(report: dict[str, Any]) -> str:
    aggregate = report["aggregates"]
    lines = [
        "# Analyse de stabilité du front Pareto — campagne nominale 9×9",
        "",
        "**Statut scientifique :** `NOT_VALIDATED`",
        "**Statut de stabilité :** `REVIEW_REQUIRED`",
        "",
        "Cette analyse mesure la variabilité observée entre les seeds. Elle ne fixe "
        "pas automatiquement un seuil d’acceptation scientifique.",
        "",
        "## Résumé par seed",
        "",
        "| Seed | Solutions Pareto | Temps min–max (s) | Énergie min–max (J) |",
        "|---:|---:|---:|---:|",
    ]
    for front in report["fronts"]:
        lines.append(
            f"| {front['seed']} | {front['n_solutions']} | "
            f"{front['time']['min']:.3f}–{front['time']['max']:.3f} | "
            f"{front['energy']['min']:.3f}–{front['energy']['max']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Indicateurs agrégés",
            "",
            f"- Cardinalité Pareto : {aggregate['n_solutions']['min']} à "
            f"{aggregate['n_solutions']['max']} solutions, moyenne "
            f"{aggregate['n_solutions']['mean']:.2f}, CV "
            f"{aggregate['n_solutions']['coefficient_of_variation']:.3f}.",
            f"- Distance de Hausdorff normalisée : moyenne "
            f"{aggregate['normalized_hausdorff']['mean']:.4f}, maximum "
            f"{aggregate['normalized_hausdorff']['max']:.4f}.",
            f"- Distance de Chamfer normalisée : moyenne "
            f"{aggregate['normalized_chamfer']['mean']:.4f}, maximum "
            f"{aggregate['normalized_chamfer']['max']:.4f}.",
            f"- Recouvrement des enveloppes temporelles : moyenne "
            f"{aggregate['time_interval_overlap']['mean']:.3f}, minimum "
            f"{aggregate['time_interval_overlap']['min']:.3f}.",
            f"- Recouvrement des enveloppes énergétiques : moyenne "
            f"{aggregate['energy_interval_overlap']['mean']:.3f}, minimum "
            f"{aggregate['energy_interval_overlap']['min']:.3f}.",
            "",
            "## Interprétation",
            "",
            report["interpretation"],
            "",
            "Les seuils d’acceptation doivent être définis avec l’encadrement "
            "scientifique avant toute clôture de la qualification.",
        ]
    )
    return "\n".join(lines) + "\n"
