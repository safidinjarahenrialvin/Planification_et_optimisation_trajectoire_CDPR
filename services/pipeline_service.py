"""Service d'orchestration du pipeline scientifique Tandem SP2.

Ce module ne dépend d'aucune interface utilisateur. Il reprend l'ordre
scientifique des BLOCs 4 à 11 et fournit un contrat typé réutilisable par la
CLI, les tests et la future GUI.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Callable, Dict, List, Tuple

import pandas as pd

from src.comparator import Comparator
from src.config import Config
from src.cost_calculator import CostCalculator
from src.extractor import TrajectoryExtractor
from src.optimizer import Optimizer
from src.point_filter import PointFilter
from src.point_generator import PointGenerator
from src.profiler import TrajectoryProfiler
from src.robot_model import RobotModel
from src.validator import Validator
from src.wfw import WFW
from services.configuration_service import ConfigurationService

logger = logging.getLogger("pipeline_service")


class PipelineCancelled(RuntimeError):
    """Indique qu’un run a été arrêté entre deux étapes sûres."""


@dataclass(frozen=True)
class PipelineOptions:
    """Paramètres d'exécution indépendants de l'interface utilisateur."""

    K: int
    pop_size: int
    n_gen: int
    seed: int = 42
    resume: bool = False

    def __post_init__(self) -> None:
        if self.K < 1:
            raise ValueError(f"K doit être >= 1, reçu {self.K}.")
        if self.pop_size < 2:
            raise ValueError(
                f"pop_size doit être >= 2, reçu {self.pop_size}."
            )
        if self.n_gen < 1:
            raise ValueError(f"n_gen doit être >= 1, reçu {self.n_gen}.")


@dataclass(frozen=True)
class PipelineRequest:
    """Demande complète d'exécution du pipeline."""

    config: Config
    output_dir: Path
    options: PipelineOptions
    progress_callback: Callable[[str, str, float], None] | None = None
    cancellation_event: Event | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_dir", Path(self.output_dir))


@dataclass(frozen=True)
class PipelineResult:
    """Résultat structuré d'une exécution du pipeline."""

    output_dir: Path
    timings: Dict[str, float]
    meta: Dict[str, object]

    @property
    def validation_status(self) -> str:
        return str(self.meta.get("validation_status", "(skipped)"))

    @property
    def artifacts(self) -> List[Path]:
        if not self.output_dir.exists():
            return []
        return sorted(path for path in self.output_dir.rglob("*") if path.is_file())

    def as_legacy_dict(self) -> Dict[str, object]:
        """Retourne le format historique utilisé par l'ancien CLI."""
        return {"timings": self.timings, "meta": self.meta}


# Fichiers attendus par étape — sert au mode --resume.
_STEP_OUTPUTS: Dict[str, List[str]] = {
    "4_point_generator": ["points_generes.csv", "points_generes_report.json"],
    "5_point_filter": [
        "points_filtres.csv",
        "points_rejetes_cause_a.csv",
        "points_rejetes_cause_b.csv",
        "point_filter_report.json",
    ],
    "6_cost_calculator": ["cost_matrix.csv"],
    "7_optimizer": ["solutions_pareto.csv", "solutions_orders.csv"],
    "8_extractor": ["trajectories.csv", "trajectories_summary.csv"],
    "9_profiler": [
        "profiles.csv",
        "profiles_time_opt.csv",
        "profiles_energy_opt.csv",
        "profiles_compromise.csv",
    ],
    "10_validator": [
        "validation_report.json",
        "hypotheses_report.json",
        "hypotheses_report.md",
        "figures/wfw_slice.png",
        "figures/pareto_front.png",
        "figures/trajectories_3d_time_opt.png",
        "figures/trajectories_3d_energy_opt.png",
        "figures/trajectories_3d_compromise.png",
        "figures/profiles.png",
    ],
    "11_comparator": [
        "baseline_zigzag.csv",
        "comparison.csv",
        "figures/comparison.png",
        "comparison_diagnostic.json",
        "figures/trajectories_comparison_grid.png",
    ],
}


def _config_fingerprint(
    config: Config, K: int, pop_size: int, n_gen: int, seed: int,
) -> str:
    """Calcule l'empreinte stable utilisée par le mode ``resume``."""
    return ConfigurationService.fingerprint(config, K, pop_size, n_gen, seed)


def _check_config_fingerprint(
    output_dir: Path, fingerprint: str, resume: bool,
) -> None:
    """Vérifie que ``resume`` ne mélange pas deux configurations."""
    hash_path = output_dir / ".config_hash"
    if not resume:
        hash_path.write_text(fingerprint, encoding="utf-8")
        return
    if not hash_path.exists():
        raise RuntimeError(
            f"Reprise refusée : aucun .config_hash trouvé dans {output_dir}. "
            "Les sorties existantes peuvent provenir d'une autre configuration. "
            "Supprimer les sorties ou relancer sans --resume."
        )
    stored = hash_path.read_text(encoding="utf-8").strip()
    if stored != fingerprint:
        raise RuntimeError(
            f"Configuration différente du dernier run (--resume refusé).\n"
            f"  Hash attendu : {stored}\n"
            f"  Hash actuel  : {fingerprint}\n"
            "  → Supprimer data/outputs/* ou retirer --resume pour "
            "régénérer tous les artefacts."
        )


def _all_outputs_exist(output_dir: Path, step: str) -> bool:
    return all(
        (path := output_dir / filename).is_file() and path.stat().st_size > 0
        for filename in _STEP_OUTPUTS[step]
    )


_RUN_MANIFEST = "run_manifest.json"


def _manifest_artifacts(output_dir: Path) -> list[str]:
    return sorted(
        str(path.relative_to(output_dir))
        for path in output_dir.rglob("*")
        if path.is_file() and path.name != _RUN_MANIFEST
    )


def _write_run_manifest(
    output_dir: Path,
    *,
    status: str,
    completed_steps: list[str],
    fingerprint: str,
    failed_step: str | None = None,
    cancelled_step: str | None = None,
    error: str | None = None,
    validation_status: str | None = None,
) -> None:
    """Écrit l’état d’un run pour empêcher l’exposition d’artefacts partiels."""
    payload: Dict[str, object] = {
        "schema_version": 1,
        "status": status,
        "fingerprint": fingerprint,
        "completed_steps": completed_steps,
        "available_artifacts": _manifest_artifacts(output_dir),
    }
    if failed_step is not None:
        payload["failed_step"] = failed_step
    if cancelled_step is not None:
        payload["cancelled_step"] = cancelled_step
    if error is not None:
        payload["error"] = error
    if validation_status is not None:
        payload["validation_status"] = validation_status
    path = output_dir / _RUN_MANIFEST
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _validation_status(output_dir: Path) -> str:
    with (output_dir / "validation_report.json").open(encoding="utf-8") as stream:
        return str(json.load(stream)["overall_status"])


def _fast_warn_is_expected(output_dir: Path) -> bool:
    with (output_dir / "validation_report.json").open(encoding="utf-8") as stream:
        report = json.load(stream)
    checks = report.get("checks", [])
    return (
        report.get("overall_status") == "WARN"
        and not any(check.get("status") == "FAIL" for check in checks)
        and {
            check.get("name") for check in checks if check.get("status") == "WARN"
        } == {"solutions_pareto"}
    )


def _fmt_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f} s"
    minutes, remainder = divmod(seconds, 60)
    return f"{int(minutes)} min {remainder:.1f} s"


def _run_step(
    step_name: str,
    output_dir: Path,
    resume: bool,
    fn: Callable[[], object],
    progress_callback: Callable[[str, str, float], None] | None = None,
) -> Tuple[object, float]:
    manifest_path = output_dir / _RUN_MANIFEST

    def update_manifest(
        status: str,
        *,
        completed_step: str | None = None,
        failed_step: str | None = None,
        cancelled_step: str | None = None,
        error: str | None = None,
    ) -> None:
        if not manifest_path.is_file():
            return
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            completed_steps = list(manifest.get("completed_steps", []))
            fingerprint = str(manifest.get("fingerprint", ""))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return
        if completed_step is not None and completed_step not in completed_steps:
            completed_steps.append(completed_step)
        _write_run_manifest(
            output_dir,
            status=status,
            completed_steps=completed_steps,
            fingerprint=fingerprint,
            failed_step=failed_step,
            cancelled_step=cancelled_step,
            error=error,
        )

    if resume and _all_outputs_exist(output_dir, step_name):
        logger.info("[SKIP] %s — sorties déjà présentes.", step_name)
        update_manifest("RUNNING", completed_step=step_name)
        if progress_callback is not None:
            progress_callback(step_name, "skipped", 1.0)
        return None, 0.0
    logger.info("[START] %s", step_name)
    update_manifest("RUNNING")
    if progress_callback is not None:
        progress_callback(step_name, "running", 0.0)
    started = time.perf_counter()
    try:
        result = fn()
    except PipelineCancelled as exc:
        duration = time.perf_counter() - started
        update_manifest(
            "CANCELLED",
            cancelled_step=step_name,
            error=str(exc),
        )
        logger.warning(
            "[CANCEL] %s après %s : %s",
            step_name,
            _fmt_duration(duration),
            exc,
        )
        raise
    except Exception as exc:
        duration = time.perf_counter() - started
        update_manifest("FAILED", failed_step=step_name, error=str(exc))
        logger.error(
            "[FAIL ] %s après %s : %s",
            step_name,
            _fmt_duration(duration),
            exc,
        )
        raise
    duration = time.perf_counter() - started
    update_manifest("RUNNING", completed_step=step_name)
    logger.info("[DONE ] %s en %s", step_name, _fmt_duration(duration))
    if progress_callback is not None:
        progress_callback(step_name, "done", 1.0)
    return result, duration


class PipelineService:
    """Orchestre une exécution scientifique complète, sans dépendance GUI."""

    def run(self, request: PipelineRequest) -> PipelineResult:
        config = request.config
        output_dir = request.output_dir
        options = request.options
        progress_callback = request.progress_callback
        cancellation_event = request.cancellation_event
        output_dir.mkdir(parents=True, exist_ok=True)
        figures_dir = output_dir / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)

        effective = ConfigurationService.validate(
            config,
            K=options.K,
            pop_size=options.pop_size,
            n_gen=options.n_gen,
            seed=options.seed,
        )
        _check_config_fingerprint(output_dir, effective.fingerprint, options.resume)
        ConfigurationService.write_snapshot(output_dir, effective)
        _write_run_manifest(
            output_dir,
            status="RUNNING",
            completed_steps=[],
            fingerprint=effective.fingerprint,
        )

        timings: Dict[str, float] = {}
        meta: Dict[str, object] = {}
        robot = RobotModel(config)
        wfw = WFW(robot, config)
        logger.info(
            "z_absolu_r0 = %.3f m%s",
            config.z_absolu_r0,
            " (override)" if config.z_absolu_r0_override is not None else "",
        )

        def step4() -> pd.DataFrame:
            generator = PointGenerator(config)
            generator.run(output_dir=output_dir)
            return generator.generate()

        df_points, duration = _run_step(
            "4_point_generator", output_dir, options.resume, step4,
            progress_callback,
        )
        timings["4_point_generator"] = duration
        if df_points is None:
            df_points = pd.read_csv(output_dir / "points_generes.csv")
        meta["n_points_generated"] = len(df_points)

        def step5() -> pd.DataFrame:
            point_filter = PointFilter(config, wfw)
            info = point_filter.run(df_points, output_dir=output_dir)
            return pd.read_csv(info["points_filtres"])

        df_filtered, duration = _run_step(
            "5_point_filter", output_dir, options.resume, step5,
            progress_callback,
        )
        timings["5_point_filter"] = duration
        if df_filtered is None:
            df_filtered = pd.read_csv(output_dir / "points_filtres.csv")
        meta["n_points_filtered"] = len(df_filtered)

        def step6() -> pd.DataFrame:
            calculator = CostCalculator(config, robot)
            calculator.run(df_filtered, output_dir=output_dir, K=options.K)
            costs = pd.read_csv(output_dir / "cost_matrix.csv")
            infeasible = int((costs["feasible"] == 0).sum())
            rate = infeasible / len(costs) if len(costs) else 0.0
            logger.info(
                "Matrice de coûts : %d paires infaisables (%.1f %%).",
                infeasible,
                rate * 100,
            )
            return costs

        df_costs, duration = _run_step(
            "6_cost_calculator", output_dir, options.resume, step6,
            progress_callback,
        )
        timings["6_cost_calculator"] = duration
        if df_costs is None:
            df_costs = pd.read_csv(output_dir / "cost_matrix.csv")
        meta["n_cost_entries"] = len(df_costs)
        meta["n_infeasible_pairs"] = int((df_costs["feasible"] == 0).sum())

        def step7() -> pd.DataFrame:
            optimizer = Optimizer(config, df_filtered, df_costs)

            def update_optimizer_progress(generation: int, total: int) -> None:
                if cancellation_event is not None and cancellation_event.is_set():
                    raise PipelineCancelled(
                        f"Annulation demandée après la génération {generation}/{total}."
                    )
                if progress_callback is not None:
                    progress_callback(
                        "7_optimizer",
                        f"generation {generation}/{total}",
                        min(1.0, generation / total),
                    )

            optimizer.run_and_save(
                output_dir=output_dir,
                pop_size=options.pop_size,
                n_gen=options.n_gen,
                seed=options.seed,
                progress_callback=(
                    update_optimizer_progress
                    if progress_callback is not None or cancellation_event is not None
                    else None
                ),
            )
            return pd.read_csv(output_dir / "solutions_pareto.csv")

        df_solutions, duration = _run_step(
            "7_optimizer", output_dir, options.resume, step7,
            progress_callback,
        )
        timings["7_optimizer"] = duration
        if df_solutions is None:
            df_solutions = pd.read_csv(output_dir / "solutions_pareto.csv")
        meta["n_pareto_solutions"] = len(df_solutions)

        def step8() -> Dict[str, Path]:
            extractor = TrajectoryExtractor(
                config, df_filtered, df_costs, df_solutions,
            )
            return extractor.run_and_save(output_dir=output_dir)

        _, duration = _run_step(
            "8_extractor", output_dir, options.resume, step8,
            progress_callback,
        )
        timings["8_extractor"] = duration

        def step9() -> Dict[str, Path]:
            trajectories = pd.read_csv(output_dir / "trajectories.csv")
            profiler = TrajectoryProfiler(
                config, dt=0.1, min_samples_per_segment=5,
            )
            return profiler.run_and_save(trajectories, output_dir=output_dir)

        _, duration = _run_step(
            "9_profiler", output_dir, options.resume, step9,
            progress_callback,
        )
        timings["9_profiler"] = duration

        def step10() -> Dict[str, object]:
            validator = Validator(
                config,
                robot,
                wfw,
                output_dir=output_dir,
                figures_dir=figures_dir,
            )
            return validator.run_all()

        result10, duration = _run_step(
            "10_validator", output_dir, options.resume, step10,
            progress_callback,
        )
        timings["10_validator"] = duration
        if result10 is not None:
            meta["validation_status"] = result10["validation"]["overall_status"]
        else:
            meta["validation_status"] = _validation_status(output_dir)

        def step11() -> Dict[str, Path]:
            points = pd.read_csv(output_dir / "points_filtres.csv")
            costs = pd.read_csv(output_dir / "cost_matrix.csv")
            summary = pd.read_csv(output_dir / "trajectories_summary.csv")
            trajectories = pd.read_csv(output_dir / "trajectories.csv")
            comparator = Comparator(config, points, costs, summary, trajectories)
            return comparator.run_and_save(output_dir=output_dir)

        _, duration = _run_step(
            "11_comparator", output_dir, options.resume, step11,
            progress_callback,
        )
        timings["11_comparator"] = duration

        diagnostic_path = output_dir / "comparison_diagnostic.json"
        if diagnostic_path.exists():
            with diagnostic_path.open(encoding="utf-8") as stream:
                diagnostic = json.load(stream)
            meta["optimal_beats_baseline"] = diagnostic["optimal_beats_baseline"]
            meta["min_time_gain_pct"] = diagnostic["min_time_gain_pct"]
            meta["min_energy_gain_pct"] = diagnostic["min_energy_gain_pct"]

        meta["run_status"] = "COMPLETED"
        _write_run_manifest(
            output_dir,
            status="COMPLETED",
            completed_steps=list(_STEP_OUTPUTS),
            fingerprint=effective.fingerprint,
            validation_status=str(meta.get("validation_status", "UNKNOWN")),
        )
        return PipelineResult(output_dir=output_dir, timings=timings, meta=meta)


def run_pipeline(
    config: Config,
    output_dir: Path,
    K: int,
    pop_size: int,
    n_gen: int,
    seed: int,
    resume: bool,
) -> Dict[str, object]:
    """Compatibilité temporaire avec l’ancienne fonction publique."""
    request = PipelineRequest(
        config=config,
        output_dir=output_dir,
        options=PipelineOptions(
            K=K,
            pop_size=pop_size,
            n_gen=n_gen,
            seed=seed,
            resume=resume,
        ),
    )
    return PipelineService().run(request).as_legacy_dict()
