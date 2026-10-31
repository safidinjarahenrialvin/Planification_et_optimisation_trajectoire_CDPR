"""Construction réutilisable de la scène 3D du robot à câbles.

Ce module ne lance aucun calcul de pipeline. Il transforme une configuration et
les artefacts déjà produits en figure Plotly, afin que le CLI et Streamlit
partagent exactement la même géométrie d'affichage.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.config import Config
from src.robot_model import RobotModel
from visualization.labels import kind_label

_POINTS_GROUND_OFFSET = 0.05
_COLOR_FRAME = "#37474f"
_COLOR_SUPPORT = "#546e7a"
_COLOR_ANCHOR = "#d32f2f"
_COLOR_CABLE = "#455a64"
_COLOR_PLATFORM = "#1565c0"
_COLOR_TRAJECTORY = "#2ca02c"
_TRAJECTORY_COLORS = {
    "baseline_zigzag": "#5f7182",
    "baseline_nn": "#5f7182",
    "time_opt": "#1769aa",
    "energy_opt": "#2e7d32",
    "compromise": "#8e44ad",
}
_COLOR_POINTS = "#455a64"
_COLOR_REJECTED = "#ef6c00"
_COLOR_PLANTS = "#43a047"
_MAX_RENDER_POINTS = 1500
_MAX_RENDER_TRAJECTORY = 2500


@dataclass(frozen=True)
class SceneOptions:
    """Couches visibles dans la scène 3D."""

    show_frame: bool = True
    show_supports: bool = True
    show_cables: bool = True
    show_platform: bool = True
    show_points: bool = True
    show_rejected: bool = False
    show_plants: bool = False
    show_center: bool = False
    show_trajectory: bool = False


def load_config_snapshot(path: Path) -> Config:
    """Reconstruit la configuration scientifique gelée d'un run."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    scientific = payload["scientific"]
    domains = scientific["domains"]
    values: dict[str, object] = {}
    for domain in domains.values():
        values.update(domain)
    values["fov_camera"] = tuple(values["fov_camera"])
    for key in ("ancrages_A", "attaches_B"):
        values[key] = np.asarray(values[key], dtype=float)
    return Config(**values)


def build_robot_figure(
    config: Config,
    *,
    trajectory_df: Optional[pd.DataFrame] = None,
    points_df: Optional[pd.DataFrame] = None,
    rejected_df: Optional[pd.DataFrame] = None,
    options: SceneOptions | None = None,
) -> go.Figure:
    """Construit une scène 3D sans modifier les données scientifiques."""
    options = options or SceneOptions()
    robot = RobotModel(config)
    figure = go.Figure()
    anchors = robot.A
    center = np.array([0.0, 0.0, config.z_absolu_r0])
    attachments = robot.attach_positions(center)

    if options.show_frame:
        edges = [(0, 1), (1, 3), (3, 2), (2, 0), (4, 5), (5, 7),
                 (7, 6), (6, 4)]
        for index, (i, j) in enumerate(edges):
            _add_segment(
                figure, anchors[:, i], anchors[:, j], _COLOR_FRAME, 4,
                "Bâti" if index == 0 else None,
            )
        vertical = [(0, 4), (1, 5), (3, 7), (2, 6)]
        for index, (i, j) in enumerate(vertical):
            _add_segment(
                figure, anchors[:, i], anchors[:, j], _COLOR_FRAME, 5,
                "Piliers du cadre" if index == 0 else None,
            )
        figure.add_trace(go.Scatter3d(
            x=anchors[0], y=anchors[1], z=anchors[2], mode="markers",
            marker=dict(size=5, color=_COLOR_ANCHOR), name="Ancrages fixes",
            hovertemplate="Ancrage %{text}<extra></extra>",
            text=[str(i + 1) for i in range(8)],
        ))

    if options.show_supports:
        for index in range(4):
            point = anchors[:, index].copy()
            _add_segment(
                figure,
                np.array([point[0], point[1], -config.offset_r0_sol]),
                np.array([point[0], point[1], 0.0]), _COLOR_SUPPORT, 6,
                "Pieds de support" if index == 0 else None, dash="dash",
            )

    if options.show_cables:
        for index in range(8):
            _add_segment(
                figure, anchors[:, index], attachments[:, index], _COLOR_CABLE,
                3, "Câbles" if index == 0 else None,
                hovertemplate=f"Câble {index + 1}<extra></extra>",
            )

    if options.show_platform:
        b = config.attaches_B
        xmin, xmax = float(b[0].min()), float(b[0].max())
        ymin, ymax = float(b[1].min()), float(b[1].max())
        zmin, zmax = float(b[2].min()), float(b[2].max())
        figure.add_trace(go.Mesh3d(
            x=[center[0] + value for value in (xmin, xmax, xmax, xmin,
                                                 xmin, xmax, xmax, xmin)],
            y=[center[1] + value for value in (ymin, ymin, ymax, ymax,
                                                 ymin, ymin, ymax, ymax)],
            z=[center[2] + value for value in (zmin, zmin, zmin, zmin,
                                                 zmax, zmax, zmax, zmax)],
            i=[0, 0, 0, 1, 1, 2, 4, 4, 5, 6, 2, 3],
            j=[1, 2, 3, 5, 6, 3, 5, 7, 6, 7, 6, 7],
            k=[2, 3, 1, 6, 2, 7, 6, 5, 7, 4, 7, 4],
            color=_COLOR_PLATFORM, opacity=0.9, flatshading=True,
            name="Plateforme mobile", hoverinfo="skip",
        ))

    if options.show_points and points_df is not None and not points_df.empty:
        _add_ground_points(
            figure, points_df, "Points de vue", _COLOR_POINTS, config=config,
        )

    if options.show_rejected and rejected_df is not None and not rejected_df.empty:
        _add_ground_points(
            figure, rejected_df, "Points rejetés", _COLOR_REJECTED, config=config,
            symbol="x", opacity=1.0,
        )

    if options.show_plants and points_df is not None and not points_df.empty:
        _add_plants(figure, _sample_frame(points_df, _MAX_RENDER_POINTS), config)

    if options.show_center:
        figure.add_trace(go.Scatter3d(
            x=[0], y=[0], z=[config.z_absolu_r0], mode="markers",
            marker=dict(size=7, color="#8e24aa", symbol="diamond"),
            name="Centre de la plateforme",
        ))

    if options.show_trajectory and trajectory_df is not None and not trajectory_df.empty:
        trajectory_kinds = list(trajectory_df["kind"].dropna().unique())
        for kind, trajectory in trajectory_df.groupby("kind", sort=True):
            trajectory = _sample_frame(
                trajectory.sort_values("rank"), _MAX_RENDER_TRAJECTORY
            )
            color = _TRAJECTORY_COLORS.get(kind, _COLOR_TRAJECTORY)
            if len(trajectory_kinds) == 1 and not str(kind).startswith("baseline"):
                label = "Trajectoire"
            else:
                label = kind_label(kind)
            figure.add_trace(go.Scatter3d(
                x=trajectory["x"], y=trajectory["y"], z=trajectory["z"],
                mode="lines+markers", line=dict(color=color, width=5),
                marker=dict(size=4, color=color),
                name=f"{label} ({len(trajectory)} waypoints)",
                hovertemplate="Rang %{text}<br>x=%{x:.3f} y=%{y:.3f} z=%{z:.3f}"
                              "<extra></extra>",
                text=trajectory["rank"].astype(str),
            ))

    figure.update_layout(
        title="Robot à câbles suspendu : vue 3D interactive",
        scene=dict(
            xaxis=dict(title="X [m]", range=[-1.35, 1.35], backgroundcolor="white"),
            yaxis=dict(title="Y [m]", range=[-1.35, 1.35], backgroundcolor="white"),
            zaxis=dict(title="Z [m]", range=[-0.35, 1.15], backgroundcolor="white"),
            aspectmode="data",
            camera=dict(eye=dict(x=1.8, y=1.8, z=1.2)),
        ),
        legend=dict(x=0.02, y=0.98, bgcolor="rgba(255,255,255,0.85)"),
        margin=dict(l=0, r=0, t=55, b=0), height=760,
    )
    return figure


def _add_segment(
    figure: go.Figure,
    start: np.ndarray,
    end: np.ndarray,
    color: str,
    width: int,
    name: str | None,
    *,
    dash: str = "solid",
    hovertemplate: str | None = None,
) -> None:
    figure.add_trace(go.Scatter3d(
        x=[start[0], end[0]], y=[start[1], end[1]], z=[start[2], end[2]],
        mode="lines", line=dict(color=color, width=width, dash=dash),
        name=name, showlegend=name is not None,
        hovertemplate=hovertemplate or "<extra></extra>",
    ))


def _add_ground_points(
    figure: go.Figure,
    points: pd.DataFrame,
    name: str,
    color: str,
    *,
    config: Config,
    symbol: str = "circle",
    opacity: float = 0.75,
) -> None:
    points = _sample_frame(points, _MAX_RENDER_POINTS)
    figure.add_trace(go.Scatter3d(
        x=points["x"], y=points["y"],
        z=np.full(len(points), -config.offset_r0_sol + _POINTS_GROUND_OFFSET),
        mode="markers",
        marker=dict(size=5, color=color, opacity=opacity, symbol=symbol),
        name=f"{name} ({len(points)})",
        hovertemplate="Point %{text}<br>x=%{x:.3f} y=%{y:.3f}<extra></extra>",
        text=points.get("id", pd.Series(range(len(points)))).astype(str),
    ))


def _sample_frame(frame: pd.DataFrame, limit: int) -> pd.DataFrame:
    """Réduit uniquement le rendu en conservant le premier et le dernier point."""
    if len(frame) <= limit:
        return frame
    indices = np.linspace(0, len(frame) - 1, limit, dtype=int)
    return frame.iloc[np.unique(indices)]


def _add_plants(figure: go.Figure, points: pd.DataFrame, config: Config) -> None:
    """Ajoute des plants légers, sans modèle détaillé coûteux."""
    ground = -config.offset_r0_sol + _POINTS_GROUND_OFFSET
    top = ground + config.hauteur_plants
    x_values: list[float] = []
    y_values: list[float] = []
    z_values: list[float] = []
    for x, y in zip(points["x"], points["y"], strict=True):
        x_values.extend([x, x, None])
        y_values.extend([y, y, None])
        z_values.extend([ground, top, None])
    figure.add_trace(go.Scatter3d(
        x=x_values, y=y_values, z=z_values, mode="lines",
        line=dict(color=_COLOR_PLANTS, width=4), name="Plants : tiges",
        hoverinfo="skip",
    ))
    figure.add_trace(go.Scatter3d(
        x=points["x"], y=points["y"], z=np.full(len(points), top),
        mode="markers", marker=dict(size=5, color=_COLOR_PLANTS, symbol="diamond"),
        name="Plants : cimes", hoverinfo="skip",
    ))
