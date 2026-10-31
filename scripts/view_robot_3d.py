#!/usr/bin/env python3
"""
Script — Viewer 3D interactif du robot à câbles.
==================================================

Génère un fichier HTML autonome avec une visualisation 3D interactive
du robot. Le fichier s'ouvre dans n'importe quel navigateur et se
tourne à la souris.

Usage
-----
    # Vue par défaut (plateforme 300x240, pas de trajectoire)
    python scripts/view_robot_3d.py

    # Avec la trajectoire time_opt en surimpression
    python scripts/view_robot_3d.py --trajectory data/outputs/trajectories.csv \
                                     --kind time_opt

    # Avec la grille de points
    python scripts/view_robot_3d.py --points data/outputs/points_filtres.csv

    # Combinaison
    python scripts/view_robot_3d.py --trajectory data/outputs/trajectories.csv \
                                     --kind compromise \
                                     --points data/outputs/points_filtres.csv
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd  # noqa: E402

from src.config import Config, DEFAULT_PLATFORM              # noqa: E402
from src.robot_3d_viewer import Robot3DViewer  # noqa: E402


logger = logging.getLogger("view_robot_3d")


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)-7s] %(name)-22s | %(message)s",
        datefmt="%H:%M:%S",
    )


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Viewer 3D interactif du robot à câbles.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--platform", type=str, default=DEFAULT_PLATFORM,
                   help=f"Taille de la plateforme. Défaut : "
                        f"{DEFAULT_PLATFORM} (prototype M1). "
                        f"Autres noms : 250x200, 700x560. "
                        f"Ou dimension libre 'WxH' en mm.")
    p.add_argument("--platform-mass", type=float, default=None,
                   help="Masse de la plateforme en grammes (défaut : auto).")
    p.add_argument("--trajectory", type=Path, default=None,
                   help="CSV des waypoints (trajectories.csv).")
    p.add_argument("--kind", type=str, default="time_opt",
                   choices=["time_opt", "energy_opt", "compromise"],
                   help="Quelle trajectoire afficher (défaut : time_opt).")
    p.add_argument("--points", type=Path, default=None,
                   help="CSV des points de vue (points_filtres.csv).")
    p.add_argument("--output", type=Path,
                   default=Path("data/outputs/figures/robot_3d.html"),
                   help="Fichier HTML de sortie.")
    p.add_argument("--no-grid", action="store_true",
                   help="Ne pas afficher la grille de points.")
    p.add_argument("--show-trajectory", action="store_true",
                   help="Afficher la trajectoire en ligne (désactivé par "
                        "défaut : seuls les points de vue au sol sont "
                        "affichés).")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--offline-html", action="store_true",
                   help="Embarque Plotly.js dans le HTML (~3 Mo). "
                        "Nécessaire pour usage sans Internet "
                        "(soutenance, archivage). Défaut : CDN (~15 Ko).")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    _setup_logging(args.verbose)

    config = Config.with_n(
        9,
        platform=args.platform,
        platform_mass=(
            args.platform_mass / 1000.0
            if args.platform_mass is not None else None
        ),
    )
    logger.info(
        "Plateforme %s — masse %.1f g.",
        args.platform, config.masse_kg * 1000,
    )

    # Chargement optionnel de la trajectoire
    trajectory_df = None
    if args.trajectory is not None:
        df_all = pd.read_csv(args.trajectory)
        trajectory_df = df_all[df_all["kind"] == args.kind].copy()
        if trajectory_df.empty:
            logger.error(
                "Aucune trajectoire du kind '%s' dans %s.",
                args.kind, args.trajectory,
            )
            return 1
        logger.info(
            "Trajectoire '%s' chargée : %d waypoints.",
            args.kind, len(trajectory_df),
        )

    # Chargement optionnel des points
    points_df = None
    if args.points is not None:
        points_df = pd.read_csv(args.points)
        logger.info("Grille chargée : %d points.", len(points_df))

    # Construction de la figure
    viewer = Robot3DViewer(config)
    fig = viewer.build_figure(
        trajectory_df=trajectory_df,
        points_df=points_df,
        show_grid=not args.no_grid,
        show_trajectory=args.show_trajectory,
    )
    path = viewer.save_html(fig, args.output, offline=args.offline_html)

    logger.info("Fichier HTML prêt. Ouvrir avec un navigateur :")
    logger.info("  xdg-open %s", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
