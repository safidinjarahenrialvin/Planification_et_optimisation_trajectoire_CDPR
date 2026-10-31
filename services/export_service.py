"""Exports contrôlés des artefacts d’un run GUI."""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Iterable

from services.result_service import RunResults
from visualization.labels import baseline_label, kind_label


class ExportService:
    """Prépare des téléchargements sans modifier le répertoire scientifique."""

    @staticmethod
    def read_artifact(output_dir: Path, relative_path: str | Path) -> bytes:
        """Lit un artefact situé dans le run, en refusant les chemins échappés."""
        root = Path(output_dir).resolve()
        path = (root / relative_path).resolve()
        if root not in path.parents or not path.is_file():
            raise FileNotFoundError(f"Artefact introuvable : {relative_path}")
        return path.read_bytes()

    @classmethod
    def zip_run(cls, output_dir: Path) -> bytes:
        """Retourne une archive ZIP déterministe du run, sans écrire sur disque."""
        root = Path(output_dir).resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"Run introuvable : {output_dir}")
        manifest_path = root / "run_manifest.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("Export ZIP refusé : manifeste de run illisible") from exc
            if not isinstance(manifest, dict):
                raise ValueError("Export ZIP refusé : manifeste de run invalide")
            status = manifest.get("status")
            if status != "COMPLETED":
                raise ValueError(
                    f"Export ZIP refusé : le run a le statut {status!r}, "
                    "seul COMPLETED est exportable"
                )
        files = sorted(
            path for path in root.rglob("*")
            if path.is_file() and not path.name.endswith(".tmp")
        )
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                archive.write(path, arcname=Path(root.name) / path.relative_to(root))
        return buffer.getvalue()

    @staticmethod
    def _selected_frame_csv(frame, kind: str, label: str) -> bytes:
        """Sérialise un sous-ensemble identifié sans écrire dans le run source."""
        if "kind" not in frame.columns:
            raise ValueError(f"Export {label} impossible : colonne kind absente")
        selected = frame.loc[frame["kind"] == kind]
        if selected.empty:
            raise ValueError(f"Export {label} impossible : stratégie inconnue {kind!r}")
        return selected.to_csv(index=False).encode("utf-8")

    @classmethod
    def selected_trajectory_csv(cls, results: RunResults, kind: str) -> bytes:
        """Retourne la trajectoire d’une stratégie sélectionnée."""
        return cls._selected_frame_csv(results.trajectories, kind, "trajectoire")

    @classmethod
    def selected_profile_csv(cls, results: RunResults, kind: str) -> bytes:
        """Retourne le profil cinématique d’une stratégie sélectionnée."""
        return cls._selected_frame_csv(results.profiles, kind, "profil")

    @classmethod
    def selected_comparison_csv(cls, results: RunResults, kind: str) -> bytes:
        """Retourne la ligne de comparaison de la stratégie sélectionnée."""
        return cls._selected_frame_csv(results.comparison, kind, "comparaison")

    @staticmethod
    def validation_json(results: RunResults) -> bytes:
        """Sérialise le rapport de contrôles sans modifier l’artefact original."""
        return (
            json.dumps(results.validation, indent=2, ensure_ascii=False, sort_keys=True)
            + "\n"
        ).encode("utf-8")

    @staticmethod
    def summary_payload(
        run_id: str,
        results: RunResults,
        *,
        selected_kind: str | None = None,
    ) -> dict[str, object]:
        """Construit le résumé compact des indicateurs présentés par la GUI."""
        points = results.point_statistics()
        pareto = results.pareto_statistics()
        gains = results.gain_statistics()
        trajectories = results.trajectory_statistics()
        diagnostic = results.comparison_diagnostic
        config = ExportService._optional_json(results.output_dir / "config.json")
        available_kinds = [str(kind) for kind in results.trajectory_summary["kind"]]
        if selected_kind not in available_kinds:
            selected_kind = "compromise" if "compromise" in available_kinds else (
                available_kinds[0] if available_kinds else None
            )
        selected = results.trajectory_summary.loc[
            results.trajectory_summary["kind"] == selected_kind
        ]
        selected_row = selected.iloc[0].to_dict() if not selected.empty else {}
        return {
            "schema_version": 1,
            "run": {
                "id": run_id,
                "source_directory": str(results.output_dir),
                "configuration_fingerprint": config.get("fingerprint"),
            },
            "coverage": {
                "points_generated": len(results.points_generated),
                "points_retained": int(points["count"]),
                "retention_rate": (
                    points["count"] / len(results.points_generated)
                    if len(results.points_generated) else 0.0
                ),
                "x_range_m": [points["x_min_m"], points["x_max_m"]],
                "y_range_m": [points["y_min_m"], points["y_max_m"]],
            },
            "validation": {
                "status": results.validation_status,
                "pass": int(results.validation.get("summary", {}).get("n_pass", 0)),
                "warn": int(results.validation.get("summary", {}).get("n_warn", 0)),
                "fail": int(results.validation.get("summary", {}).get("n_fail", 0)),
            },
            "pareto": {
                "raw_solutions": pareto["raw_count"],
                "distinct_compromises": pareto["distinct_count"],
            },
            "baseline": {
                "kind": diagnostic.get("baseline_kind"),
                "label": baseline_label(results.comparison["kind"]),
                "optimal_beats_baseline": diagnostic.get("optimal_beats_baseline"),
            },
            "gains": {
                "time_metric": gains["time_metric"],
                "energy_metric": gains["energy_metric"],
                "min_time_pct": gains["min_time_gain_pct"],
                "min_energy_pct": gains["min_energy_gain_pct"],
                "max_time_pct": gains["max_time_gain_pct"],
                "max_energy_pct": gains["max_energy_gain_pct"],
            },
            "trajectory_selected": {
                "kind": selected_kind,
                "label": kind_label(selected_kind) if selected_kind else None,
                "time_motion_s": selected_row.get("total_time_motion_s"),
                "time_stabilization_s": selected_row.get("total_time_stab_s"),
                "time_total_s": selected_row.get("total_time_s"),
                "energy_J": selected_row.get("total_energy_J"),
            },
            "trajectory_summary": {
                "count": trajectories["count"],
                "best_time_motion_kind": trajectories["best_time_motion_kind"],
                "best_time_total_kind": trajectories["best_time_total_kind"],
                "best_energy_kind": trajectories["best_energy_kind"],
            },
        }

    @staticmethod
    def summary_json(
        run_id: str,
        results: RunResults,
        *,
        selected_kind: str | None = None,
    ) -> bytes:
        """Sérialise le résumé compact en JSON UTF-8 déterministe."""
        return (
            json.dumps(
                ExportService.summary_payload(
                    run_id, results, selected_kind=selected_kind
                ),
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")

    @staticmethod
    def markdown_report(run_id: str, results: RunResults) -> str:
        """Produit le rapport jury structuré du run."""
        return ExportService.jury_markdown_report(run_id, results)

    @staticmethod
    def jury_markdown_report(run_id: str, results: RunResults) -> str:
        """Produit une synthèse de présentation depuis les artefacts du run."""
        points = results.point_statistics()
        trajectories = results.trajectory_statistics()
        diagnostic = results.comparison_diagnostic
        filter_summary = results.point_filter_report.get("summary", {})
        config = ExportService._optional_json(results.output_dir / "config.json")
        fingerprint = config.get("fingerprint", "non disponible")
        execution = config.get("execution", {})
        checks = results.validation.get("checks", [])
        hypotheses = results.hypotheses.get("hypotheses", [])
        comparison_kinds = results.comparison["kind"]
        reference_label = baseline_label(comparison_kinds)
        pareto_stats = results.pareto_statistics()
        gain_stats = results.gain_statistics()
        cost_stats = results.cost_statistics()
        summary_by_kind = results.trajectory_summary.set_index("kind").to_dict("index")
        retained_rate = (
            points["count"] / len(results.points_generated)
            if len(results.points_generated)
            else 0.0
        )
        verdict = "améliore la baseline" if diagnostic.get("optimal_beats_baseline") else (
            "ne démontre pas encore d’amélioration sur la baseline"
        )
        lines = [
            f"# Rapport jury — Tandem SP2 — `{run_id}`",
            "",
            "> Synthèse générée automatiquement à partir des artefacts scientifiques "
            "> du run. Les valeurs ci-dessous ne sont pas des illustrations manuelles.",
            "",
            "## 1. Conclusion exécutive",
            "",
            f"Le pipeline retient **{points['count']} points sur "
            f"{len(results.points_generated)}** ({retained_rate:.1%}) et "
            f"{verdict}. Le gain minimal mesuré sur le temps de mouvement est de "
            f"**{diagnostic.get('min_time_gain_pct', 0):.2f} %** et "
            f"**{diagnostic.get('min_energy_gain_pct', 0):.2f} % en énergie**.",
            "Les gains temporels comparent `time_motion_s`; le temps total "
            "inclut le temps de stabilisation aux waypoints.",
            "",
            f"Statut des contrôles automatiques : **{results.validation_status}**.",
            "",
            "## 2. Périmètre et configuration",
            "",
            f"- Répertoire source : `{results.output_dir}`",
            f"- Empreinte de configuration : `{fingerprint}`",
            f"- Points générés / retenus : `{len(results.points_generated)} / {points['count']}`",
            f"- Étendue X : `{points['x_min_m']}` à `{points['x_max_m']}` m",
            f"- Étendue Y : `{points['y_min_m']}` à `{points['y_max_m']}` m",
            f"- Points évalués dans la matrice : `{cost_stats['point_count']}`",
            f"- Transitions inter-points : `{cost_stats['transition_count']}`",
            f"- Transitions faisables : `{cost_stats['feasible_count']}` "
            f"({cost_stats['feasibility_rate']:.1%})",
            f"- Paramètres d’exécution : `{json.dumps(execution, ensure_ascii=False)}`",
            "",
            "## 3. Couverture et diagnostic WFW/FOV",
            "",
            f"- Taux de rejet : `{filter_summary.get('reject_rate', 0):.2%}`",
            f"- Rejets Cause A : `{filter_summary.get('n_rejected_cause_a', 0)}`",
            f"- Rejets Cause B : `{filter_summary.get('n_rejected_cause_b', 0)}`",
            f"- Transitions infaisables : `{cost_stats['infeasible_count']}`",
            "",
            "### Distribution des coûts sur les transitions faisables",
            "",
            "Les boucles d’un point vers lui-même sont exclues. Les quartiles décrivent "
            "la dispersion; les coûts ne sont résumés que pour les transitions faisables.",
            "",
            "| Grandeur | n | Moyenne | Écart-type | Médiane | Q1–Q3 | Min–max |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for metric, label, unit in (
            ("distance", "Distance", "m"),
            ("time", "Temps de déplacement", "s"),
            ("energy", "Énergie", "J"),
        ):
            stats = cost_stats["metrics"][metric]
            if stats["count"]:
                lines.append(
                    f"| {label} ({unit}) | {stats['count']} | {stats['mean']:.3f} | "
                    f"{stats['std']:.3f} | {stats['median']:.3f} | "
                    f"{stats['q1']:.3f}–{stats['q3']:.3f} | "
                    f"{stats['min']:.3f}–{stats['max']:.3f} |"
                )
            else:
                lines.append(f"| {label} ({unit}) | 0 | — | — | — | — | — |")
        alerts = results.points_generated_report.get("alerts", [])
        if alerts:
            lines.extend(["", "Alertes FOV :", *[f"- {alert}" for alert in alerts]])
        else:
            lines.extend(["", "Aucune alerte FOV n’a été produite par le pipeline."])
        lines.extend([
            "",
            "## 4. Optimisation et stratégies",
            "",
            f"- Nombre de stratégies analysées : `{trajectories['count']}`",
            f"- Solutions Pareto brutes / compromis distincts : `"
            f"{pareto_stats['raw_count']} / {pareto_stats['distinct_count']}`",
            f"- Meilleur temps de mouvement : `"
            f"{kind_label(trajectories['best_time_motion_kind'])}`",
            f"- Meilleur temps total : `"
            f"{kind_label(trajectories['best_time_total_kind'])}`",
            f"- Meilleure énergie : `{kind_label(trajectories['best_energy_kind'])}`",
            f"- Baseline des gains : `{kind_label(gain_stats['baseline_kind'])}`",
            f"- Baseline temps de mouvement : `{gain_stats['baseline_time_motion_s']:.6f} s`",
            f"- Baseline énergie : `{gain_stats['baseline_energy_J']:.6f} J`",
            f"- Stratégies optimisées incluses dans les gains : `{gain_stats['strategy_count']}`",
            f"- Formule gain temps : `{gain_stats['time_formula']}`",
            f"- Formule gain énergie : `{gain_stats['energy_formula']}`",
            f"- Gain temps de mouvement minimal : `{gain_stats['min_time_gain_pct']:.2f} %` "
            f"({kind_label(gain_stats['min_time_gain_kind'])})",
            f"- Gain temps de mouvement maximal : `{gain_stats['max_time_gain_pct']:.2f} %` "
            f"({kind_label(gain_stats['max_time_gain_kind'])})",
            f"- Gain énergie minimal : `{gain_stats['min_energy_gain_pct']:.2f} %` "
            f"({kind_label(gain_stats['min_energy_gain_kind'])})",
            f"- Gain énergie maximal : `{gain_stats['max_energy_gain_pct']:.2f} %` "
            f"({kind_label(gain_stats['max_energy_gain_kind'])})",
            "",
            "| Stratégie | Temps de mouvement (s) | Énergie (J) | "
            "Gain temps de mouvement (%) | Gain énergie (%) |",
            "|---|---:|---:|---:|---:|",
        ])
        for row in results.comparison.to_dict("records"):
            lines.append(
                f"| {kind_label(row['kind'])} | {row['time_motion_s']:.2f} | "
                f"{row['energy_J']:.2f} | "
                f"{row['gain_time_vs_baseline_pct']:.2f} | "
                f"{row['gain_energy_vs_baseline_pct']:.2f} |"
            )
        lines.extend([
            "",
            "### Décomposition temporelle des trajectoires optimisées",
            "",
            "| Stratégie | Temps de mouvement (s) | Stabilisation (s) | Temps total (s) |",
            "|---|---:|---:|---:|",
        ])
        for kind, row in summary_by_kind.items():
            lines.append(
                f"| {kind_label(kind)} | {row['total_time_motion_s']:.2f} | "
                f"{row['total_time_stab_s']:.2f} | {row['total_time_s']:.2f} |"
            )
        lines.extend([
            "",
            "## 5. Contrôles automatiques et limites",
            "",
            f"- Contrôles PASS : `{results.validation.get('summary', {}).get('n_pass', 0)}`",
            f"- Contrôles WARN : `{results.validation.get('summary', {}).get('n_warn', 0)}`",
            f"- Contrôles FAIL : `{results.validation.get('summary', {}).get('n_fail', 0)}`",
            "",
            "| Contrôle | Statut | Détail |",
            "|---|---|---|",
        ])
        for check in checks:
            lines.append(
                f"| {check.get('name', 'inconnu')} | {check.get('status', 'inconnu')} | "
                f"{check.get('detail', check.get('message', ''))} |"
            )
        lines.extend([
            "",
            "## 6. Hypothèses et limites",
            "",
        ])
        for hypothesis in hypotheses:
            if isinstance(hypothesis, dict):
                lines.append(
                    f"- **{hypothesis.get('code', 'Hypothèse')} — "
                    f"{hypothesis.get('titre', '')}** : "
                    f"{hypothesis.get('statut', 'non précisé')} — "
                    f"{hypothesis.get('valeur', '')}. Source : "
                    f"{hypothesis.get('source', 'non précisée')}"
                )
        lines.extend([
            "",
            f"La référence comparative utilisée est **{reference_label}**.\n\n"
            "Les statuts PASS/WARN/FAIL décrivent les contrôles automatiques du pipeline; "
            "ils ne constituent pas à eux seuls une validation scientifique humaine ou "
            "expérimentale. Le statut WARN doit être interprété avec le détail des contrôles. "
            "Il ne constitue pas automatiquement un échec, notamment dans le mode "
            "court où le front Pareto peut être court.",
            "",
            "## 7. Traçabilité",
            "",
            "Ce rapport est généré par `ExportService` à partir des CSV, JSON et "
            "configurations gelées du run. Les figures interactives de la GUI sont "
            "reproductibles à partir de ces mêmes artefacts.",
            "",
        ])
        return "\n".join(lines)

    @staticmethod
    def _optional_json(path: Path) -> dict:
        if not path.is_file():
            return {}
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}

    @staticmethod
    def available_files(output_dir: Path, suffixes: Iterable[str]) -> list[Path]:
        """Retourne les fichiers disponibles filtrés par extension."""
        allowed = set(suffixes)
        root = Path(output_dir)
        return sorted(
            path.relative_to(root)
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in allowed
        )
