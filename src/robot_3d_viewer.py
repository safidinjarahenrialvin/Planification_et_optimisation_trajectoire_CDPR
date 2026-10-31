"""Façade historique du visualiseur 3D.

Le CLI conserve cette classe pour compatibilité. La construction de la scène
est centralisée dans ``visualization.robot_3d`` afin que le CLI et Streamlit
utilisent la même géométrie et les mêmes conventions d'axes.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from src.config import Config
from visualization.robot_3d import SceneOptions, build_robot_figure

logger = logging.getLogger(__name__)


class Robot3DViewer:
    """Adaptateur rétrocompatible pour le visualiseur Plotly historique."""

    def __init__(self, config: Config) -> None:
        self.config = config

    def build_figure(
        self,
        trajectory_df: Optional[pd.DataFrame] = None,
        points_df: Optional[pd.DataFrame] = None,
        show_grid: bool = True,
        show_trajectory: bool = False,
    ):
        """Construit la figure via le composant partagé de visualisation."""
        return build_robot_figure(
            self.config,
            trajectory_df=trajectory_df,
            points_df=points_df,
            options=SceneOptions(
                show_points=show_grid,
                show_trajectory=show_trajectory,
            ),
        )

    def save_html(self, fig, output_path: Path, offline: bool = False) -> Path:
        """Écrit une figure Plotly HTML, comme dans la version historique."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(
            str(output_path),
            include_plotlyjs=True if offline else "cdn",
            full_html=True,
            config={
                "displaylogo": False,
                "scrollZoom": True,
                "showTips": True,
                "toImageButtonOptions": {
                    "format": "png", "height": 1200, "width": 1600,
                },
            },
        )
        logger.info(
            "Viewer 3D écrit : %s (%.2f Mo, mode %s)",
            output_path,
            output_path.stat().st_size / (1024 * 1024),
            "offline" if offline else "CDN",
        )
        return output_path
