"""Figures synchronisées des trajectoires et profils issus des artefacts."""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import pandas as pd

from visualization.labels import kind_label
from visualization.chart_style import apply_chart_layout, strategy_color


_MAX_TRAJECTORY_RENDER = 2500
_MAX_PROFILE_RENDER = 5000


def _sample_frame(frame: pd.DataFrame, limit: int) -> pd.DataFrame:
    if len(frame) <= limit:
        return frame
    indices = np.linspace(0, len(frame) - 1, limit, dtype=int)
    return frame.iloc[np.unique(indices)]


def build_trajectory_xy_figure(
    trajectories: pd.DataFrame, kind: str | None = None
) -> go.Figure:
    """Trace les trajectoires XY réelles, éventuellement pour une stratégie."""
    required = {"kind", "rank", "x", "y"}
    missing = required - set(trajectories.columns)
    if missing:
        raise ValueError(f"Colonnes trajectoires manquantes : {sorted(missing)}")

    if kind is not None:
        trajectories = trajectories.loc[trajectories["kind"] == kind]
        if trajectories.empty:
            raise ValueError(f"Trajectoire introuvable pour la stratégie {kind!r}")

    figure = go.Figure()
    for strategy, frame in trajectories.groupby("kind", sort=True):
        frame = _sample_frame(frame.sort_values("rank"), _MAX_TRAJECTORY_RENDER)
        figure.add_trace(
            go.Scatter(
                x=frame["x"],
                y=frame["y"],
                mode="lines+markers",
                name=kind_label(strategy),
                line={"color": strategy_color(strategy), "width": 3},
                marker={"color": strategy_color(strategy)},
                customdata=frame[["rank"]],
                hovertemplate="rang=%{customdata[0]}<br>x=%{x:.3f} m<br>"
                "y=%{y:.3f} m<extra></extra>",
            )
        )
    title = (
        f"Trajectoire dans le plan XY : {kind_label(kind)}"
        if kind is not None
        else "Trajectoires dans le plan XY"
    )
    figure.update_layout(title=title, xaxis_title="X (m)", yaxis_title="Y (m)")
    apply_chart_layout(figure, height=480, legend_title="Stratégie")
    figure.update_yaxes(scaleanchor="x")
    return figure


def build_profile_figure(profiles: pd.DataFrame, kind: str) -> go.Figure:
    """Trace les composantes et la norme de vitesse d’une stratégie."""
    required = {"kind", "t", "vx", "vy", "vz"}
    missing = required - set(profiles.columns)
    if missing:
        raise ValueError(f"Colonnes profils manquantes : {sorted(missing)}")

    frame = _sample_frame(
        profiles.loc[profiles["kind"] == kind].sort_values("t").copy(),
        _MAX_PROFILE_RENDER,
    )
    if frame.empty:
        raise ValueError(f"Profil introuvable pour la stratégie {kind!r}")
    frame["speed_norm"] = np.sqrt(frame["vx"] ** 2 + frame["vy"] ** 2 + frame["vz"] ** 2)
    figure = go.Figure()
    for column, label, color in (
        ("vx", "Vitesse X", "#1565c0"),
        ("vy", "Vitesse Y", "#2e7d32"),
        ("vz", "Vitesse Z", "#ef6c00"),
        ("speed_norm", "Norme vitesse", "#6a1b9a"),
    ):
        figure.add_trace(
            go.Scatter(
                x=frame["t"],
                y=frame[column],
                mode="lines",
                name=label,
                line={"color": color, "width": 3 if column == "speed_norm" else 1.5},
            )
        )
    figure.update_layout(
        title=f"Profil cinématique : {kind_label(kind)}",
        xaxis_title="Temps (s)",
        yaxis_title="Vitesse (m/s)",
    )
    apply_chart_layout(figure, height=430, legend_title="Composante")
    return figure
