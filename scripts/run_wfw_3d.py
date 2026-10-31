#!/usr/bin/env python3
"""
Script — Visualisation 3D du workspace courant (WFW + WCW).
==============================================================

Produit une figure 3D montrant les 2 volumes d'espace de travail
du robot, en utilisant **uniquement les paramètres de Config** :

  - WCW (Wrench Closure Workspace, enveloppe maximale)
        T_min = 0, T_max = Config.T_max
  - WFW (Wrench Feasible Workspace, workspace opérationnel)
        T_min, T_max = Config.T_min, Config.T_max

Aucune valeur de tension n'est configurable via CLI : la figure
reflète **toujours** la configuration active du pipeline.

Usage
-----
    # Figure par défaut, résolution définie par WFW3DViewer
    python scripts/run_wfw_3d.py

    # Aperçu rapide (~10 s)
    python scripts/run_wfw_3d.py --n-xy 12 --n-z 8

    # Haute résolution (~3 min)
    python scripts/run_wfw_3d.py --n-xy 40 --n-z 20

    # Autre plateforme
    python scripts/run_wfw_3d.py --platform 700x560
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.config import DEFAULT_PLATFORM, Config  # noqa: E402
from src.robot_model import RobotModel            # noqa: E402
from src.wfw_3d import (                          # noqa: E402
    _DEFAULT_N_XY,
    _DEFAULT_N_Z,
    WFW3DViewer,
)

logger = logging.getLogger("run_wfw_3d")


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)-7s] %(name)-22s | %(message)s",
        datefmt="%H:%M:%S",
    )


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Visualisation 3D du workspace courant (WFW + WCW).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--n-xy", type=int, default=_DEFAULT_N_XY,
                   help=f"Points par axe XY (défaut : {_DEFAULT_N_XY}).")
    p.add_argument("--n-z", type=int, default=_DEFAULT_N_Z,
                   help=f"Points sur l'axe Z (défaut : {_DEFAULT_N_Z}).")
    p.add_argument("--platform", type=str, default=DEFAULT_PLATFORM,
                   help=f"Taille de la plateforme. Défaut : "
                        f"{DEFAULT_PLATFORM}. Autres noms : 250x200, "
                        f"700x560. Ou dimension libre 'WxH' en mm.")
    p.add_argument("--platform-mass", type=float, default=None,
                   help="Masse de la plateforme en grammes "
                        "(défaut : auto-estimée).")
    p.add_argument("--elev", type=float, default=22.0,
                   help="Élévation de la caméra 3D (défaut : 22°).")
    p.add_argument("--azim", type=float, default=-60.0,
                   help="Azimut de la caméra 3D (défaut : -60°).")
    p.add_argument("--output-dir", type=Path, default=Path("data/outputs"),
                   help="Répertoire de sortie (défaut : data/outputs).")
    p.add_argument("--output-name", type=str,
                   default="workspace_3d.png",
                   help="Nom du fichier PNG "
                        "(défaut : workspace_3d.png).")
    p.add_argument("--verbose", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    _setup_logging(args.verbose)

    # Config utilise strictement les paramètres actifs du pipeline.
    # Aucune valeur de tension n'est modifiable ici — c'est par design
    # pour garantir que la figure reflète toujours la Config courante.
    config = Config.with_n(
        9,
        platform=args.platform,
        platform_mass=(
            args.platform_mass / 1000.0
            if args.platform_mass is not None else None
        ),
    )
    robot = RobotModel(config)

    logger.info(
        "Plateforme %s : masse %.1f g.",
        args.platform, config.masse_kg * 1000,
    )
    logger.info(
        "Workspace à visualiser : WFW T ∈ [%.2f, %.2f] N, "
        "WCW T ∈ [0, %.2f] N.",
        config.T_min, config.T_max, config.T_max,
    )
    logger.info(
        "Échantillonnage : enveloppe des ancrages "
        "(±%.2f m XY, Z ∈ [%.2f, %.2f] m)",
        config.ancrages_A[0, :].max(),
        config.ancrages_A[2, :].min(),
        config.ancrages_A[2, :].max(),
    )

    viewer = WFW3DViewer(robot, config, n_xy=args.n_xy, n_z=args.n_z)

    # Suffixe conditionnel du nom de fichier (D-CONFIG-13)
    out_name = args.output_name
    stem = Path(out_name).stem
    suffix = Path(out_name).suffix
    if args.platform != DEFAULT_PLATFORM and args.platform not in stem:
        out_name = f"{stem}_{args.platform}{suffix}"

    t0 = time.perf_counter()
    volumes = viewer.plot_workspace(
        output_path=args.output_dir / "figures" / out_name,
        view_elev=args.elev,
        view_azim=args.azim,
    )
    dt = time.perf_counter() - t0

    logger.info("Terminé en %.1f s.", dt)
    for key in ("wcw", "wfw"):
        v = volumes[key]
        logger.info(
            "  %s : %5d/%5d faisables (%.2f %%)",
            key.upper(), v.n_feasible, v.n_total,
            100.0 * v.feasible_ratio,
        )
    logger.info("Figure : %s", args.output_dir / "figures" / out_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
