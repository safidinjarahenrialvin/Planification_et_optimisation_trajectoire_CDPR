#!/usr/bin/env python3
"""
Adaptateur CLI du pipeline scientifique SP2.

L'orchestration est implémentée dans ``services.pipeline_service`` afin d'être
réutilisable par la CLI, les tests et la future interface graphique.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Assure que le script est exécutable depuis n'importe quel cwd.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.config import Config, DEFAULT_PLATFORM  # noqa: E402
from src.optimizer import DegenerateFrontError  # noqa: E402
from src.point_filter import InsufficientPointsError  # noqa: E402
from services import pipeline_service as _pipeline_service  # noqa: E402
from services.pipeline_service import (  # noqa: E402
    PipelineCancelled,
    PipelineRequest,
    PipelineOptions,
    PipelineService,
    _fmt_duration,
)

# Alias publics historiques conservés pour les tests et appelants existants.
_STEP_OUTPUTS = _pipeline_service._STEP_OUTPUTS
_all_outputs_exist = _pipeline_service._all_outputs_exist
_check_config_fingerprint = _pipeline_service._check_config_fingerprint
_config_fingerprint = _pipeline_service._config_fingerprint
_fast_warn_is_expected = _pipeline_service._fast_warn_is_expected
_validation_status = _pipeline_service._validation_status
run_pipeline = _pipeline_service.run_pipeline

logger = logging.getLogger("run_pipeline")


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)-7s] %(name)-22s | %(message)s",
        datefmt="%H:%M:%S",
    )


# ===========================================================================
# Rapport final
# ===========================================================================
def _print_final_report(
    output_dir: Path,
    timings: Dict[str, float],
    meta: Dict[str, object],
) -> None:
    print()
    print("=" * 72)
    print("PIPELINE SP2 — RAPPORT FINAL")
    print("=" * 72)
    print()
    print(f"Répertoire de sortie : {output_dir.resolve()}")
    print()
    print("Timings par étape :")
    total = 0.0
    for step, duration in timings.items():
        if duration > 0.0:
            print(f"  {step:25s} {_fmt_duration(duration):>12s}")
            total += duration
        else:
            print(f"  {step:25s} {'(skipped)':>12s}")
    print(f"  {'TOTAL':25s} {_fmt_duration(total):>12s}")
    print()
    print("Métriques clés :")
    for key, value in meta.items():
        print(f"  {key:25s} {value}")
    print()
    print("Fichiers produits :")
    for path in sorted(output_dir.rglob("*")):
        if path.is_file():
            relative = path.relative_to(output_dir)
            size = path.stat().st_size
            print(f"  {relative!s:50s} {size:>10,} octets")
    print()
    print("=" * 72)


# ===========================================================================
# Configuration CLI
# ===========================================================================
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pipeline complet SP2 (BLOC 4 → BLOC 11).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Mode rapide : grille 3×3 avec bornes zero-loss, K=5, "
        "pop_size=30, n_gen=100 (défaut : off)",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=None,
        help="Taille de la grille n×n (défaut : 9 → N=81). Impair ≥ 3.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/outputs"),
        help="Répertoire de sortie (défaut : data/outputs).",
    )
    parser.add_argument(
        "--K",
        type=int,
        default=None,
        help="Sous-pas BLOC 6 (défaut : 10 ; --fast : 5).",
    )
    parser.add_argument(
        "--pop-size",
        type=int,
        default=None,
        help="Population NSGA-II (défaut : table Config selon n).",
    )
    parser.add_argument(
        "--n-gen",
        type=int,
        default=None,
        help="Générations NSGA-II (défaut : table Config selon n).",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Graine NSGA-II (défaut : 42).",
    )
    parser.add_argument(
        "--z-absolu",
        type=float,
        default=None,
        help="Override de z_absolu_r0 en m.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip les étapes dont les sorties existent déjà.",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Active les logs DEBUG.",
    )
    parser.add_argument(
        "--zero-loss",
        action="store_true",
        help="Active les bornes resserrées selon la plateforme.",
    )
    parser.add_argument(
        "--platform",
        type=str,
        default=DEFAULT_PLATFORM,
        help=f"Taille de la plateforme mobile. Défaut : {DEFAULT_PLATFORM}.",
    )
    parser.add_argument(
        "--platform-mass",
        type=float,
        default=None,
        help="Masse de la plateforme en grammes.",
    )
    parser.add_argument(
        "--xy-bound",
        type=float,
        default=None,
        help="Override symétrique des bornes X et Y en m.",
    )
    parser.add_argument(
        "--x-bound", type=float, default=None, help="Override de la borne X en m.",
    )
    parser.add_argument(
        "--y-bound", type=float, default=None, help="Override de la borne Y en m.",
    )
    return parser


def _resolve_config_and_params(args: argparse.Namespace) -> Dict[str, object]:
    """Résout la Config et les paramètres à partir de la CLI."""
    z_override: Optional[float] = getattr(args, "z_absolu", None)
    common = {
        "xy_bound": args.xy_bound,
        "x_bound": args.x_bound,
        "y_bound": args.y_bound,
        "platform": args.platform,
        "platform_mass": (
            args.platform_mass / 1000.0
            if args.platform_mass is not None else None
        ),
        "z_absolu_r0_override": z_override,
    }

    if args.fast:
        config = Config.with_n(3, zero_loss=True, **common)
        K = args.K if args.K is not None else 5
        logger.info(
            "Mode FAST : grille 3×3 (N=%d), esp=%.3f m, K=%d.",
            config.N, config.esp_x, K,
        )
    else:
        n = args.n if args.n is not None else 9
        config = Config.with_n(n, zero_loss=args.zero_loss, **common)
        K = args.K if args.K is not None else 10
        if args.x_bound is not None or args.y_bound is not None:
            mode_str = "custom-asym"
        elif args.xy_bound is not None:
            mode_str = "custom-sym"
        elif args.zero_loss:
            mode_str = "ZERO-LOSS"
        else:
            mode_str = "standard"
        logger.info(
            "Mode FULL (%s) : grille %d×%d (N=%d), esp=(%.4f, %.4f) m, "
            "plateforme %s (masse %.1f g), K=%d.",
            mode_str,
            config.n_rangs,
            config.n_colonnes,
            config.N,
            config.esp_x,
            config.esp_y,
            args.platform,
            config.masse_kg * 1000,
            K,
        )

    pop_size = args.pop_size if args.pop_size is not None else config.nsga_pop_size
    n_gen = args.n_gen if args.n_gen is not None else config.nsga_n_gen
    options = PipelineOptions(
        K=K, pop_size=pop_size, n_gen=n_gen, seed=args.seed, resume=args.resume,
    )
    logger.info(
        "NSGA-II : pop_size=%d, n_gen=%d, seed=%d.",
        options.pop_size,
        options.n_gen,
        options.seed,
    )
    if z_override is not None:
        logger.warning(
            "[OVERRIDE] z_absolu_r0 forcé à %.3f m.", config.z_absolu_r0,
        )
    return {
        "config": config,
        "options": options,
        # Clés conservées pour les appelants/tests de la version historique.
        "K": options.K,
        "pop_size": options.pop_size,
        "n_gen": options.n_gen,
        "seed": options.seed,
    }


def main(argv: List[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)

    try:
        params = _resolve_config_and_params(args)
        request = PipelineRequest(
            config=params["config"],
            output_dir=args.output_dir,
            options=params["options"],
        )
        result = PipelineService().run(request)
    except InsufficientPointsError as exc:
        logger.error("Configuration inviable — %s", exc)
        logger.error(
            "Le pipeline s'arrête car trop peu de points sont exploitables. "
            "Essayez : --zero-loss, --xy-bound 0.30, ou --platform 700x560."
        )
        return 3
    except DegenerateFrontError as exc:
        logger.error("Front NSGA-II dégénéré — %s", exc)
        logger.error(
            "Aucun tour faisable. Vérifier que la grille filtrée admet "
            "un chemin hamiltonien (points connectés entre eux)."
        )
        return 4
    except PipelineCancelled as exc:
        logger.warning("Pipeline annulé proprement — %s", exc)
        return 2
    except Exception as exc:
        logger.error("Pipeline interrompu : %s", exc)
        return 1

    _print_final_report(args.output_dir, result.timings, result.meta)
    status = result.validation_status
    if status == "PASS":
        return 0
    if args.fast and status == "WARN" and _fast_warn_is_expected(args.output_dir):
        logger.info("Smoke test FAST terminé avec WARN Pareto attendu : code 0.")
        return 0
    logger.warning("Validation status : %s", status)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
