"""Lecture contrôlée et statistiques des résultats d’un run SP2."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Dict, List

import numpy as np
import pandas as pd


class ResultLoadError(RuntimeError):
    """Indique qu’un run est incomplet ou illisible."""


@dataclass(frozen=True)
class RunSummary:
    """Indicateurs normalisés permettant de comparer plusieurs runs."""

    run_id: str
    output_dir: Path
    status: str
    points_generated: int
    points_kept: int
    coverage_rate: float
    pareto_count: int
    pareto_distinct_count: int
    best_time_s: float | None
    best_time_motion_s: float | None
    best_time_stab_s: float | None
    best_time_total_s: float | None
    best_energy_J: float | None
    min_time_gain_pct: float | None
    min_energy_gain_pct: float | None
    fingerprint: str | None
    baseline_kind: str
    is_reference: bool = False


@dataclass(frozen=True)
class RunResults:
    """Jeu de résultats normalisé prêt à être présenté par la GUI."""

    output_dir: Path
    points_generated: pd.DataFrame
    points_filtered: pd.DataFrame
    pareto: pd.DataFrame
    trajectories: pd.DataFrame
    baseline_trajectory: pd.DataFrame
    trajectory_summary: pd.DataFrame
    profiles: pd.DataFrame
    comparison: pd.DataFrame
    cost_matrix: pd.DataFrame
    validation: Dict[str, Any]
    comparison_diagnostic: Dict[str, Any]
    hypotheses: Dict[str, Any]
    points_generated_report: Dict[str, Any]
    point_filter_report: Dict[str, Any]
    points_rejected: pd.DataFrame

    @property
    def artifacts(self) -> List[Path]:
        return sorted(path for path in self.output_dir.rglob("*") if path.is_file())

    @property
    def validation_status(self) -> str:
        return str(self.validation.get("overall_status", "UNKNOWN"))

    def point_statistics(self) -> Dict[str, Any]:
        points = self.points_filtered
        if points.empty:
            return {"count": 0, "x_min_m": None, "x_max_m": None,
                    "y_min_m": None, "y_max_m": None}
        return {
            "count": len(points),
            "x_min_m": float(points["x"].min()),
            "x_max_m": float(points["x"].max()),
            "y_min_m": float(points["y"].min()),
            "y_max_m": float(points["y"].max()),
        }

    def trajectory_statistics(self) -> Dict[str, Any]:
        """Retourne séparément les classements mouvement et temps total.

        Le contrat de comparaison définit « plus rapide » comme le meilleur
        temps de mouvement. Le temps total reste disponible séparément car il
        ajoute la stabilisation aux waypoints.
        """
        summary = self.trajectory_summary
        if summary.empty:
            return {
                "count": 0,
                "best_time_kind": None,
                "best_time_motion_kind": None,
                "best_time_total_kind": None,
                "best_energy_kind": None,
                "min_time_s": None,
                "min_time_motion_s": None,
                "min_time_stab_s": None,
                "min_time_total_s": None,
            }
        return {
            "count": len(summary),
            # Compatibilité : best_time_kind signifie historiquement
            # « plus rapide » et reste donc fondé sur le temps de mouvement.
            "best_time_kind": str(
                summary.loc[summary["total_time_motion_s"].idxmin(), "kind"]
            ),
            "best_time_motion_kind": str(
                summary.loc[summary["total_time_motion_s"].idxmin(), "kind"]
            ),
            "best_time_total_kind": str(
                summary.loc[summary["total_time_s"].idxmin(), "kind"]
            ),
            "best_energy_kind": str(
                summary.loc[summary["total_energy_J"].idxmin(), "kind"]
            ),
            "min_time_s": float(summary["total_time_s"].min()),
            "min_time_motion_s": float(summary["total_time_motion_s"].min()),
            "min_time_stab_s": float(summary["total_time_stab_s"].min()),
            "min_time_total_s": float(summary["total_time_s"].min()),
            "min_energy_s": float(summary["total_energy_J"].min()),
        }

    def pareto_statistics(self) -> Dict[str, int]:
        """Distingue les solutions brutes des compromis temps-énergie distincts."""
        raw_count = len(self.pareto)
        if raw_count == 0:
            return {"raw_count": 0, "distinct_count": 0, "duplicate_count": 0}
        required = {"time", "energy"}
        missing = required - set(self.pareto.columns)
        if missing:
            raise ValueError(f"Colonnes Pareto manquantes : {sorted(missing)}")
        distinct_count = len(self.pareto.drop_duplicates(subset=["time", "energy"]))
        return {
            "raw_count": raw_count,
            "distinct_count": distinct_count,
            "duplicate_count": raw_count - distinct_count,
        }

    def gain_statistics(self) -> Dict[str, Any]:
        """Retourne des KPI de gains entièrement traçables.

        Les valeurs sont celles de ``comparison_diagnostic.json``. Les minima
        désignent le gain le moins favorable parmi les stratégies optimisées;
        les maxima désignent le gain le plus élevé. La baseline et les
        formules sont exposées pour éviter toute interprétation implicite.
        """
        per_trajectory = self.comparison_diagnostic.get("per_trajectory", {})
        if not per_trajectory:
            return {
                "baseline_kind": self.comparison_diagnostic.get("baseline_kind"),
                "baseline_time_motion_s": self.comparison_diagnostic.get("baseline_time_s"),
                "baseline_energy_J": self.comparison_diagnostic.get("baseline_energy_J"),
                "strategy_count": 0,
                "time_metric": "time_motion_s",
                "energy_metric": "energy_J",
                "time_formula": "(baseline - strategy) / baseline × 100",
                "energy_formula": "(baseline - strategy) / baseline × 100",
                "min_time_gain_pct": None,
                "min_time_gain_kind": None,
                "max_time_gain_pct": None,
                "max_time_gain_kind": None,
                "min_energy_gain_pct": None,
                "min_energy_gain_kind": None,
                "max_energy_gain_pct": None,
                "max_energy_gain_kind": None,
            }
        time_kind = min(
            per_trajectory,
            key=lambda kind: float(per_trajectory[kind]["gain_time_pct"]),
        )
        max_time_kind = max(
            per_trajectory,
            key=lambda kind: float(per_trajectory[kind]["gain_time_pct"]),
        )
        energy_kind = min(
            per_trajectory,
            key=lambda kind: float(per_trajectory[kind]["gain_energy_pct"]),
        )
        max_energy_kind = max(
            per_trajectory,
            key=lambda kind: float(per_trajectory[kind]["gain_energy_pct"]),
        )
        return {
            "baseline_kind": self.comparison_diagnostic.get("baseline_kind"),
            "baseline_time_motion_s": self.comparison_diagnostic.get("baseline_time_s"),
            "baseline_energy_J": self.comparison_diagnostic.get("baseline_energy_J"),
            "strategy_count": len(per_trajectory),
            "time_metric": "time_motion_s",
            "energy_metric": "energy_J",
            "time_formula": "(baseline - strategy) / baseline × 100",
            "energy_formula": "(baseline - strategy) / baseline × 100",
            "min_time_gain_pct": float(per_trajectory[time_kind]["gain_time_pct"]),
            "min_time_gain_kind": str(time_kind),
            "max_time_gain_pct": float(per_trajectory[max_time_kind]["gain_time_pct"]),
            "max_time_gain_kind": str(max_time_kind),
            "min_energy_gain_pct": float(per_trajectory[energy_kind]["gain_energy_pct"]),
            "min_energy_gain_kind": str(energy_kind),
            "max_energy_gain_pct": float(per_trajectory[max_energy_kind]["gain_energy_pct"]),
            "max_energy_gain_kind": str(max_energy_kind),
        }

    def cost_statistics(self) -> Dict[str, Any]:
        """Résume les transitions inter-points et les coûts faisables du run.

        Les boucles i → i sont exclues des taux et des distributions afin de ne pas
        biaiser la faisabilité ni ramener artificiellement les coûts vers zéro.
        """
        matrix = self.cost_matrix
        inter_point = matrix.loc[matrix["i"] != matrix["j"]]
        feasible = inter_point.loc[inter_point["feasible"] > 0]
        n_total = len(inter_point)
        metrics: Dict[str, Any] = {}
        for metric in ("distance", "time", "energy"):
            values = feasible[metric].astype(float)
            if values.empty:
                metrics[metric] = {
                    "count": 0, "mean": None, "median": None, "std": None,
                    "q1": None, "q3": None, "min": None, "max": None,
                }
                continue
            metrics[metric] = {
                "count": int(values.count()),
                "mean": float(values.mean()),
                "median": float(values.median()),
                "std": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
                "q1": float(values.quantile(0.25)),
                "q3": float(values.quantile(0.75)),
                "min": float(values.min()),
                "max": float(values.max()),
            }
        point_ids = pd.concat([matrix["i"], matrix["j"]], ignore_index=True)
        return {
            "point_count": int(point_ids.nunique()),
            "transition_count": n_total,
            "feasible_count": len(feasible),
            "infeasible_count": n_total - len(feasible),
            "feasibility_rate": len(feasible) / n_total if n_total else 0.0,
            "metrics": metrics,
        }


class ResultService:
    """Charge un run complet sans exposer la structure de fichiers à la GUI."""

    _INTEGER = "integer"
    _FLOAT = "float"
    _STRING = "string"
    _CSV_SCHEMAS: ClassVar[Dict[str, Dict[str, Dict[str, str]]]] = {
        "points_generes.csv": {
            "required": {
                "id": _INTEGER, "x": _FLOAT, "y": _FLOAT, "z": _FLOAT,
                "ligne": _INTEGER, "colonne": _INTEGER,
            },
            "allow_empty": False,
        },
        "points_filtres.csv": {
            "required": {
                "id": _INTEGER, "x": _FLOAT, "y": _FLOAT, "z": _FLOAT,
                "ligne": _INTEGER, "colonne": _INTEGER,
            },
            "allow_empty": False,
        },
        "solutions_pareto.csv": {
            "required": {
                "solution_id": _INTEGER, "time": _FLOAT,
                "energy": _FLOAT, "order": _STRING,
            },
            "allow_empty": False,
        },
        "trajectories.csv": {
            "required": {
                "kind": _STRING, "rank": _INTEGER, "point_id": _INTEGER,
                "x": _FLOAT, "y": _FLOAT, "z": _FLOAT,
                "cumulative_time_motion_s": _FLOAT,
                "cumulative_energy_J": _FLOAT,
            },
            "allow_empty": False,
        },
        "trajectories_summary.csv": {
            "required": {
                "kind": _STRING, "order": _STRING, "n_waypoints": _INTEGER,
                "total_time_motion_s": _FLOAT, "total_time_stab_s": _FLOAT,
                "total_time_s": _FLOAT, "total_energy_J": _FLOAT,
            },
            "allow_empty": False,
        },
        "profiles.csv": {
            "required": {
                "kind": _STRING, "segment_id": _INTEGER, "t": _FLOAT,
                "x": _FLOAT, "y": _FLOAT, "z": _FLOAT,
                "vx": _FLOAT, "vy": _FLOAT, "vz": _FLOAT,
            },
            "allow_empty": False,
        },
        "comparison.csv": {
            "required": {
                "kind": _STRING, "time_motion_s": _FLOAT, "energy_J": _FLOAT,
                "distance_m": _FLOAT, "n_waypoints": _INTEGER,
                "gain_time_vs_baseline_pct": _FLOAT,
                "gain_energy_vs_baseline_pct": _FLOAT,
            },
            "allow_empty": False,
        },
        "cost_matrix.csv": {
            "required": {
                "i": _INTEGER, "j": _INTEGER, "distance": _FLOAT,
                "time": _FLOAT, "energy": _FLOAT, "feasible": _INTEGER,
            },
            "allow_empty": False,
        },
    }
    _OPTIONAL_CSV_SCHEMAS: ClassVar[Dict[str, Dict[str, Dict[str, str]]]] = {
        "baseline_zigzag.csv": {
            "required": {
                "kind": _STRING, "rank": _INTEGER, "point_id": _INTEGER,
                "x": _FLOAT, "y": _FLOAT, "z": _FLOAT,
                "cumulative_time_motion_s": _FLOAT,
                "cumulative_energy_J": _FLOAT,
            },
            "allow_empty": False,
        },
        "points_rejetes_cause_a.csv": {
            "required": {
                "id": _INTEGER, "x": _FLOAT, "y": _FLOAT, "z": _FLOAT,
                "ligne": _INTEGER, "colonne": _INTEGER,
                "cause": _STRING, "raison": _STRING,
            },
            "allow_empty": True,
        },
        "points_rejetes_cause_b.csv": {
            "required": {
                "id": _INTEGER, "x": _FLOAT, "y": _FLOAT, "z": _FLOAT,
                "ligne": _INTEGER, "colonne": _INTEGER,
                "cause": _STRING, "raison": _STRING,
            },
            "allow_empty": True,
        },
    }

    _CSV_FILES: ClassVar[Dict[str, str]] = {
        "points_generated": "points_generes.csv",
        "points_filtered": "points_filtres.csv",
        "pareto": "solutions_pareto.csv",
        "trajectories": "trajectories.csv",
        "trajectory_summary": "trajectories_summary.csv",
        "profiles": "profiles.csv",
        "comparison": "comparison.csv",
        "cost_matrix": "cost_matrix.csv",
    }

    @classmethod
    def load(cls, output_dir: Path) -> RunResults:
        output_dir = Path(output_dir)
        if not output_dir.is_dir():
            raise ResultLoadError(f"Répertoire de run introuvable : {output_dir}")
        cls._validate_manifest_status(output_dir)

        tables = {
            key: cls._read_csv(output_dir / filename, filename)
            for key, filename in cls._CSV_FILES.items()
        }
        results = RunResults(
            output_dir=output_dir,
            **tables,
            validation=cls._read_json(output_dir / "validation_report.json"),
            comparison_diagnostic=cls._read_json(
                output_dir / "comparison_diagnostic.json"
            ),
            hypotheses=cls._read_json(output_dir / "hypotheses_report.json"),
            points_generated_report=cls._read_json(
                output_dir / "points_generes_report.json"
            ),
            point_filter_report=cls._read_json(
                output_dir / "point_filter_report.json"
            ),
            baseline_trajectory=cls._read_optional_csv(
                output_dir / "baseline_zigzag.csv", "baseline_zigzag.csv"
            ),
            points_rejected=cls._read_optional_rejected_points(output_dir),
        )
        cls._validate_json_artifact_shapes(results)
        cls._validate_cross_artifact_consistency(results)
        cls._validate_config_fingerprint(output_dir)
        return results

    @classmethod
    def summarize(
        cls,
        run_id: str,
        results: RunResults,
        *,
        is_reference: bool = False,
    ) -> RunSummary:
        """Normalise les KPI d’un run sans recalculer le pipeline."""
        points_generated = len(results.points_generated)
        points_kept = len(results.points_filtered)
        diagnostic = results.comparison_diagnostic
        summary = results.trajectory_statistics()
        fingerprint = None
        config_path = results.output_dir / "config.json"
        if config_path.is_file():
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
                if isinstance(config, dict):
                    value = config.get("fingerprint")
                    fingerprint = str(value) if value is not None else None
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                fingerprint = None
        return RunSummary(
            run_id=run_id,
            output_dir=results.output_dir,
            status=results.validation_status,
            points_generated=points_generated,
            points_kept=points_kept,
            coverage_rate=points_kept / points_generated if points_generated else 0.0,
            pareto_count=len(results.pareto),
            pareto_distinct_count=results.pareto_statistics()["distinct_count"],
            best_time_s=summary.get("min_time_s"),
            best_time_motion_s=summary.get("min_time_motion_s"),
            best_time_stab_s=summary.get("min_time_stab_s"),
            best_time_total_s=summary.get("min_time_total_s"),
            best_energy_J=summary.get("min_energy_s"),
            min_time_gain_pct=diagnostic.get("min_time_gain_pct"),
            min_energy_gain_pct=diagnostic.get("min_energy_gain_pct"),
            fingerprint=fingerprint,
            baseline_kind=str(diagnostic["baseline_kind"]),
            is_reference=is_reference,
        )

    @classmethod
    def discover(cls, root: Path = Path("data/runs")) -> list[Path]:
        """Retourne les dossiers de runs présents, triés du plus récent au plus ancien."""
        root = Path(root)
        if not root.is_dir():
            return []
        return sorted(
            (path for path in root.iterdir() if path.is_dir()),
            key=lambda path: path.name,
            reverse=True,
        )

    @classmethod
    def discover_snapshots(cls, root: Path = Path("data/snapshots")) -> list[Path]:
        """Retourne les snapshots complets disponibles, sans charger de résultat."""
        root = Path(root)
        if not root.is_dir():
            return []
        return sorted(
            (
                path for path in root.iterdir()
                if cls._has_current_snapshot_manifest(path) and cls._is_complete(path)
            ),
            key=lambda path: path.name,
            reverse=True,
        )

    @staticmethod
    def _has_current_snapshot_manifest(path: Path) -> bool:
        """Les snapshots proposés doivent porter le manifeste versionné du pipeline."""
        manifest_path = path / "run_manifest.json"
        if path.is_symlink() or manifest_path.is_symlink() or not manifest_path.is_file():
            return False
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return False
        return (
            isinstance(manifest, dict)
            and type(manifest.get("schema_version")) is int
            and manifest["schema_version"] == 1
            and manifest.get("status") == "COMPLETED"
        )

    @classmethod
    def discover_loadable_runs(cls, root: Path = Path("data/runs")) -> list[Path]:
        """Retourne uniquement les runs locaux rechargeables par ``ResultService``."""
        return [path for path in cls.discover(root) if cls._is_complete(path)]

    @classmethod
    def incomplete_runs(cls, root: Path = Path("data/runs")) -> list[Path]:
        """Retourne les dossiers locaux à diagnostiquer sans les proposer au chargement."""
        return [path for path in cls.discover(root) if not cls._is_complete(path)]

    @classmethod
    def diagnose_run(cls, path: Path) -> Dict[str, Any]:
        """Décrit un run sans le rendre chargeable s’il est invalide.

        Le diagnostic est destiné à l’Historique : un dossier incomplet reste
        visible pour expliquer son exclusion, mais seul ``loadable=True`` peut
        alimenter les comparaisons et les résultats scientifiques.
        """
        path = Path(path)
        required = [
            *cls._CSV_FILES.values(),
            "config.json",
            "validation_report.json",
            "comparison_diagnostic.json",
            "hypotheses_report.json",
            "points_generes_report.json",
            "point_filter_report.json",
        ]
        available = sorted(
            str(file.relative_to(path))
            for file in path.rglob("*")
            if file.is_file()
        ) if path.is_dir() else []
        missing = [name for name in required if not (path / name).is_file()]
        manifest_status = "ABSENT"
        failed_step = None
        cancelled_step = None
        manifest_error = None
        manifest_path = path / "run_manifest.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                manifest = None
                manifest_status = "INVALID"
            if isinstance(manifest, dict):
                manifest_status = str(manifest.get("status", "UNKNOWN"))
                failed_step = manifest.get("failed_step")
                cancelled_step = manifest.get("cancelled_step")
                manifest_error = manifest.get("error")
            elif manifest is not None:
                manifest_status = "INVALID"

        error = None
        loadable = False
        if path.is_dir():
            try:
                cls.load(path)
            except ResultLoadError as exc:
                error = str(exc)
            else:
                loadable = True
        else:
            error = f"Répertoire de run introuvable : {path}"
        return {
            "run_id": path.name,
            "path": path,
            "loadable": loadable,
            "manifest_status": manifest_status,
            "failed_step": failed_step,
            "cancelled_step": cancelled_step,
            "manifest_error": manifest_error,
            "error": error,
            "available_artifacts": available,
            "missing_artifacts": missing,
        }

    @classmethod
    def _is_complete(cls, path: Path) -> bool:
        if not path.is_dir():
            return False
        manifest_path = path / "run_manifest.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                return False
            if not isinstance(manifest, dict):
                return False
            if manifest.get("status") != "COMPLETED":
                return False
        required = [
            *cls._CSV_FILES.values(),
            "config.json",
            "validation_report.json",
            "comparison_diagnostic.json",
            "hypotheses_report.json",
            "points_generes_report.json",
            "point_filter_report.json",
        ]
        return all((path / filename).is_file() for filename in required)

    @staticmethod
    def _validate_manifest_status(output_dir: Path) -> None:
        path = output_dir / "run_manifest.json"
        if not path.is_file():
            return
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ResultLoadError(
                "Manifeste de run illisible : run_manifest.json"
            ) from exc
        if not isinstance(manifest, dict):
            raise ResultLoadError(
                "Manifeste de run invalide : run_manifest.json doit être un objet"
            )
        status = manifest.get("status")
        if status != "COMPLETED":
            failed_step = manifest.get(
                "failed_step", manifest.get("cancelled_step", "inconnue")
            )
            detail = manifest.get("error", "aucun détail fourni")
            raise ResultLoadError(
                f"Run non chargeable : statut {status!r}, étape en cause "
                f"{failed_step!r} ({detail})"
            )

    @staticmethod
    def _read_csv(path: Path, label: str) -> pd.DataFrame:
        if not path.is_file():
            raise ResultLoadError(f"Artefact CSV manquant : {label}")
        try:
            frame = pd.read_csv(path)
        except (OSError, pd.errors.ParserError, UnicodeDecodeError) as exc:
            raise ResultLoadError(f"Artefact CSV illisible : {label} ({exc})") from exc
        schema = ResultService._CSV_SCHEMAS.get(label)
        if schema is None:
            return frame
        if frame.empty and not schema["allow_empty"]:
            raise ResultLoadError(f"Artefact CSV vide : {label}")
        required = schema["required"]
        missing = sorted(set(required) - set(frame.columns))
        if missing:
            raise ResultLoadError(
                f"Artefact CSV incomplet : {label} ; colonnes manquantes : "
                f"{', '.join(missing)}"
            )
        for column, kind in required.items():
            frame[column] = ResultService._coerce_column(frame, column, kind, label)
        return frame

    @staticmethod
    def _coerce_column(
        frame: pd.DataFrame, column: str, kind: str, label: str,
    ) -> pd.Series:
        values = frame[column]
        if kind == ResultService._STRING:
            if values.isna().any():
                raise ResultLoadError(
                    f"Artefact CSV invalide : {label} ; valeurs nulles dans {column}"
                )
            result = values.astype(str).str.strip()
            if result.eq("").any():
                raise ResultLoadError(
                    f"Artefact CSV invalide : {label} ; valeurs vides dans {column}"
                )
            return result
        numeric = pd.to_numeric(values, errors="coerce")
        if numeric.isna().any():
            raise ResultLoadError(
                f"Artefact CSV invalide : {label} ; valeurs non numériques dans {column}"
            )
        if not np.isfinite(numeric.to_numpy(dtype=float)).all():
            raise ResultLoadError(
                f"Artefact CSV invalide : {label} ; valeurs infinies dans {column}"
            )
        if kind == ResultService._INTEGER:
            if not (numeric % 1 == 0).all():
                raise ResultLoadError(
                    f"Artefact CSV invalide : {label} ; valeurs entières attendues "
                    f"dans {column}"
                )
            return numeric.astype("int64")
        return numeric.astype("float64")

    @staticmethod
    def _is_finite_json_number(value: Any) -> bool:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        try:
            return bool(np.isfinite(float(value)))
        except (OverflowError, TypeError, ValueError):
            return False

    @staticmethod
    def _validate_json_artifact_shapes(results: RunResults) -> None:
        """Vérifie le contrat minimal des rapports JSON consommés par les vues."""
        validation = results.validation
        overall_status = validation.get("overall_status")
        if not isinstance(overall_status, str) or overall_status not in {
            "PASS", "WARN", "FAIL",
        }:
            raise ResultLoadError(
                "Artefact JSON invalide : validation_report.json ; "
                "overall_status doit valoir PASS, WARN ou FAIL"
            )
        checks = validation.get("checks")
        summary = validation.get("summary")
        if not isinstance(checks, list) or not checks:
            raise ResultLoadError(
                "Artefact JSON invalide : validation_report.json ; "
                "checks doit être une liste non vide"
            )
        if not isinstance(summary, dict):
            raise ResultLoadError(
                "Artefact JSON invalide : validation_report.json ; summary doit être un objet"
            )
        check_statuses = []
        for index, check in enumerate(checks):
            if (
                not isinstance(check, dict)
                or not isinstance(check.get("name"), str)
                or not check["name"].strip()
                or not isinstance(check.get("status"), str)
                or check["status"] not in {"PASS", "WARN", "FAIL"}
            ):
                raise ResultLoadError(
                    "Artefact JSON invalide : validation_report.json ; "
                    f"checks[{index}] doit contenir name et un status valide"
                )
            check_statuses.append(check["status"])
        expected_counts = {
            "n_pass": check_statuses.count("PASS"),
            "n_warn": check_statuses.count("WARN"),
            "n_fail": check_statuses.count("FAIL"),
            "n_total": len(checks),
        }
        for key, expected in expected_counts.items():
            value = summary.get(key)
            if isinstance(value, bool) or not isinstance(value, int) or value != expected:
                raise ResultLoadError(
                    "Artefact JSON invalide : validation_report.json ; "
                    f"summary.{key} incohérent avec checks"
                )

        diagnostic = results.comparison_diagnostic
        if (
            not isinstance(diagnostic.get("baseline_kind"), str)
            or not diagnostic["baseline_kind"].startswith("baseline_")
            or not isinstance(diagnostic.get("optimal_beats_baseline"), bool)
            or not isinstance(diagnostic.get("per_trajectory"), dict)
        ):
            raise ResultLoadError(
                "Artefact JSON invalide : comparison_diagnostic.json ; "
                "baseline_kind, optimal_beats_baseline ou per_trajectory invalide"
            )
        for key in ("min_time_gain_pct", "min_energy_gain_pct"):
            value = diagnostic.get(key)
            if not ResultService._is_finite_json_number(value):
                raise ResultLoadError(
                    "Artefact JSON invalide : comparison_diagnostic.json ; "
                    f"{key} doit être un nombre fini"
                )
        for kind, gains in diagnostic["per_trajectory"].items():
            if not isinstance(kind, str) or not kind or not isinstance(gains, dict):
                raise ResultLoadError(
                    "Artefact JSON invalide : comparison_diagnostic.json ; "
                    "per_trajectory doit associer chaque stratégie à un objet"
                )
            for key in ("gain_time_pct", "gain_energy_pct"):
                value = gains.get(key)
                if not ResultService._is_finite_json_number(value):
                    raise ResultLoadError(
                        "Artefact JSON invalide : comparison_diagnostic.json ; "
                        f"{kind}.{key} doit être un nombre fini"
                    )

        hypotheses = results.hypotheses
        if (
            not isinstance(hypotheses.get("version"), str)
            or not isinstance(hypotheses.get("hypotheses"), list)
            or not hypotheses["hypotheses"]
            or any(
                not isinstance(item, dict)
                or not all(isinstance(item.get(key), str) and item[key].strip()
                           for key in ("code", "titre", "statut", "source"))
                for item in hypotheses["hypotheses"]
            )
        ):
            raise ResultLoadError(
                "Artefact JSON invalide : hypotheses_report.json ; "
                "version et liste d’hypothèses documentées attendues"
            )

        points_report = results.points_generated_report
        if (
            not isinstance(points_report.get("config_summary"), dict)
            or not isinstance(points_report.get("grid_extent"), dict)
            or not isinstance(points_report.get("fov_footprint"), dict)
            or not isinstance(points_report.get("alerts"), list)
        ):
            raise ResultLoadError(
                "Artefact JSON invalide : points_generes_report.json ; "
                "résumé, étendue, empreinte FOV et alertes attendus"
            )

        filter_report = results.point_filter_report
        if (
            not isinstance(filter_report.get("summary"), dict)
            or not isinstance(filter_report.get("alerts"), list)
        ):
            raise ResultLoadError(
                "Artefact JSON invalide : point_filter_report.json ; "
                "summary et alerts attendus"
            )

    @staticmethod
    def _validate_cross_artifact_consistency(results: RunResults) -> None:
        comparison = results.comparison
        if comparison["kind"].duplicated().any():
            duplicate_kinds = sorted(
                comparison.loc[comparison["kind"].duplicated(keep=False), "kind"].unique()
            )
            raise ResultLoadError(
                "Cohérence inter-artefacts invalide : kinds dupliqués dans "
                f"comparison.csv : {', '.join(duplicate_kinds)}"
            )

        summary_kinds = set(results.trajectory_summary["kind"])
        if results.trajectory_summary["kind"].duplicated().any():
            raise ResultLoadError(
                "Cohérence inter-artefacts invalide : kind dupliqué "
                "dans trajectories_summary.csv"
            )
        comparison_kinds = set(comparison["kind"])
        baseline_kinds = {kind for kind in comparison_kinds if str(kind).startswith("baseline_")}
        if len(baseline_kinds) != 1:
            raise ResultLoadError(
                "Cohérence inter-artefacts invalide : comparison.csv doit contenir "
                f"exactement une baseline, trouvé {len(baseline_kinds)}"
            )
        baseline_kind = next(iter(baseline_kinds))
        if results.comparison_diagnostic["baseline_kind"] != baseline_kind:
            raise ResultLoadError(
                "Cohérence inter-artefacts invalide : baseline_kind de "
                "comparison_diagnostic.json ne correspond pas à comparison.csv"
            )

        comparison_strategy_kinds = comparison_kinds - baseline_kinds
        if comparison_strategy_kinds != summary_kinds:
            missing = sorted(summary_kinds - comparison_strategy_kinds)
            unexpected = sorted(comparison_strategy_kinds - summary_kinds)
            raise ResultLoadError(
                "Cohérence inter-artefacts invalide : stratégies de comparison.csv "
                "et trajectories_summary.csv différentes "
                f"(absentes de comparison : {missing}; absentes du résumé : {unexpected})"
            )
        diagnostic_kinds = set(results.comparison_diagnostic["per_trajectory"])
        if diagnostic_kinds != comparison_strategy_kinds:
            raise ResultLoadError(
                "Cohérence inter-artefacts invalide : per_trajectory de "
                "comparison_diagnostic.json ne correspond pas aux stratégies comparées"
            )

        trajectory_kinds = set(results.trajectories["kind"])
        if trajectory_kinds != summary_kinds:
            missing = sorted(summary_kinds - trajectory_kinds)
            unexpected = sorted(trajectory_kinds - summary_kinds)
            raise ResultLoadError(
                "Cohérence inter-artefacts invalide : stratégies de trajectories.csv "
                "et trajectories_summary.csv différentes "
                f"(absentes des trajectoires : {missing}; absentes du résumé : {unexpected})"
            )
        profile_kinds = set(results.profiles["kind"])
        if profile_kinds != summary_kinds:
            missing = sorted(summary_kinds - profile_kinds)
            unexpected = sorted(profile_kinds - summary_kinds)
            raise ResultLoadError(
                "Cohérence inter-artefacts invalide : stratégies de profiles.csv "
                "et trajectories_summary.csv différentes "
                f"(absentes des profils : {missing}; absentes du résumé : {unexpected})"
            )
        point_ids = set(results.points_filtered["id"])
        trajectory_point_ids = set(results.trajectories["point_id"])
        if not trajectory_point_ids <= point_ids:
            missing = sorted(trajectory_point_ids - point_ids)
            raise ResultLoadError(
                "Cohérence inter-artefacts invalide : trajectories.csv référence des "
                f"points absents de points_filtres.csv : {missing}"
            )
        solution_ids = results.pareto["solution_id"]
        if solution_ids.duplicated().any():
            raise ResultLoadError(
                "Cohérence inter-artefacts invalide : solution_id dupliqués "
                "dans solutions_pareto.csv"
            )

        for kind, group in results.trajectories.groupby("kind", sort=False):
            ranks = group["rank"].sort_values().tolist()
            expected_ranks = list(range(len(ranks)))
            if ranks != expected_ranks:
                raise ResultLoadError(
                    "Cohérence inter-artefacts invalide : rangs non contigus dans "
                    f"trajectories.csv pour {kind!r}"
                )
            summary_row = results.trajectory_summary[
                results.trajectory_summary["kind"] == kind
            ].iloc[0]
            n_waypoints = int(summary_row["n_waypoints"])
            if len(group) != n_waypoints:
                raise ResultLoadError(
                    "Cohérence inter-artefacts invalide : n_waypoints incohérent pour "
                    f"{kind!r} entre trajectories.csv et trajectories_summary.csv"
                )
            last = group.sort_values("rank").iloc[-1]
            for column, summary_column in (
                ("cumulative_time_motion_s", "total_time_motion_s"),
                ("cumulative_energy_J", "total_energy_J"),
            ):
                if not np.isclose(float(last[column]), float(summary_row[summary_column])):
                    raise ResultLoadError(
                        "Cohérence inter-artefacts invalide : cumul final incohérent "
                        f"pour {kind!r} dans {column}"
                    )

        baseline = comparison[comparison["kind"] == baseline_kind].iloc[0]
        if not results.baseline_trajectory.empty:
            baseline_kinds = set(results.baseline_trajectory["kind"])
            if baseline_kinds != {baseline_kind}:
                raise ResultLoadError(
                    "Cohérence inter-artefacts invalide : baseline_zigzag.csv ne "
                    "correspond pas à la baseline de comparison.csv"
                )
            baseline_ranks = results.baseline_trajectory["rank"].sort_values().tolist()
            if baseline_ranks != list(range(len(baseline_ranks))):
                raise ResultLoadError(
                    "Cohérence inter-artefacts invalide : rangs non contigus dans "
                    "baseline_zigzag.csv"
                )
            baseline_points = set(results.baseline_trajectory["point_id"])
            if not baseline_points <= point_ids:
                missing = sorted(baseline_points - point_ids)
                raise ResultLoadError(
                    "Cohérence inter-artefacts invalide : baseline_zigzag.csv référence "
                    f"des points absents de points_filtres.csv : {missing}"
                )
            if len(results.baseline_trajectory) != int(baseline["n_waypoints"]):
                raise ResultLoadError(
                    "Cohérence inter-artefacts invalide : n_waypoints incohérent "
                    "pour la baseline"
                )

    @staticmethod
    def _validate_config_fingerprint(output_dir: Path) -> None:
        config_path = output_dir / "config.json"
        hash_path = output_dir / ".config_hash"
        config = ResultService._read_json(config_path)
        fingerprint = config.get("fingerprint")
        if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{16}", fingerprint):
            raise ResultLoadError(
                "Artefact JSON invalide : config.json ; fingerprint attendu sur "
                "16 caractères hexadécimaux"
            )
        if hash_path.is_file() and hash_path.read_text(encoding="utf-8").strip() != fingerprint:
            raise ResultLoadError(
                "Cohérence inter-artefacts invalide : config.json et .config_hash divergent"
            )

    @classmethod
    def _read_optional_rejected_points(cls, output_dir: Path) -> pd.DataFrame:
        frames = []
        for filename in ("points_rejetes_cause_a.csv", "points_rejetes_cause_b.csv"):
            path = output_dir / filename
            if not path.is_file():
                continue
            frame = cls._read_optional_csv(path, filename)
            if not frame.empty:
                frames.append(frame)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    @classmethod
    def _read_optional_csv(cls, path: Path, label: str) -> pd.DataFrame:
        """Lit un optionnel : absent autorisé, présent mais invalide rejeté."""
        if not path.is_file():
            return pd.DataFrame()
        try:
            frame = pd.read_csv(path)
        except (OSError, pd.errors.ParserError, UnicodeDecodeError) as exc:
            raise ResultLoadError(f"Artefact CSV optionnel illisible : {label}") from exc
        schema = cls._OPTIONAL_CSV_SCHEMAS.get(label)
        if schema is None:
            return frame
        if frame.empty and not schema["allow_empty"]:
            raise ResultLoadError(f"Artefact CSV optionnel vide : {label}")
        missing = sorted(set(schema["required"]) - set(frame.columns))
        if missing:
            raise ResultLoadError(
                f"Artefact CSV optionnel incomplet : {label} ; colonnes manquantes : "
                f"{', '.join(missing)}"
            )
        for column, kind in schema["required"].items():
            frame[column] = cls._coerce_column(frame, column, kind, label)
        return frame

    @staticmethod
    def _read_json(path: Path) -> Dict[str, Any]:
        if not path.is_file():
            raise ResultLoadError(f"Artefact JSON manquant : {path.name}")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ResultLoadError(f"Artefact JSON illisible : {path.name} ({exc})") from exc
        if not isinstance(value, dict):
            raise ResultLoadError(f"Artefact JSON inattendu : {path.name}")
        return value
