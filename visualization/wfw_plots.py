"""Figures interactives de couverture WFW à partir des artefacts du run."""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import pandas as pd

from visualization.chart_style import POINT_COLORS, apply_chart_layout

_MAX_POINTS_RENDER = 3000


def _sample(frame: pd.DataFrame, limit: int) -> pd.DataFrame:
    if len(frame) <= limit:
        return frame
    indices = np.linspace(0, len(frame) - 1, limit, dtype=int)
    return frame.iloc[np.unique(indices)]


def build_wfw_coverage_figure(
    points_generated: pd.DataFrame,
    points_filtered: pd.DataFrame,
    points_rejected: pd.DataFrame | None = None,
    view: str = "all",
) -> go.Figure:
    """Construit une projection XY de couverture depuis les CSV du run.

    La figure ne reconstruit pas une frontière WFW continue : elle représente
    uniquement les points réellement générés, retenus et rejetés par le pipeline.
    """
    if view not in {"all", "retained", "rejected"}:
        raise ValueError(f"Vue WFW inconnue : {view!r}")

    required = {"x", "y"}
    for label, frame in (
        ("points générés", points_generated),
        ("points filtrés", points_filtered),
    ):
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"Colonnes manquantes dans {label} : {sorted(missing)}")

    figure = go.Figure()
    if view == "all":
        generated = _sample(points_generated, _MAX_POINTS_RENDER)
        figure.add_trace(
            go.Scatter(
                x=generated["x"],
                y=generated["y"],
                mode="markers",
                name="Points générés",
                marker={
                    "size": 7,
                    "color": POINT_COLORS["generated"],
                    "symbol": "circle-open",
                },
                hovertemplate="Candidat<br>x=%{x:.3f} m<br>y=%{y:.3f} m<extra></extra>",
            )
        )

    if view in {"all", "retained"}:
        retained = _sample(points_filtered, _MAX_POINTS_RENDER)
        figure.add_trace(
            go.Scatter(
                x=retained["x"],
                y=retained["y"],
                mode="markers",
                name="Points retenus",
                marker={"size": 9, "color": POINT_COLORS["retained"], "symbol": "circle"},
                customdata=retained[["id"]] if "id" in retained else None,
                hovertemplate="Retenu<br>id=%{customdata[0]}<br>x=%{x:.3f} m<br>"
                "y=%{y:.3f} m<extra></extra>",
            )
        )

    if (
        view in {"all", "rejected"}
        and points_rejected is not None
        and not points_rejected.empty
        and "cause" in points_rejected.columns
    ):
        rejected = _sample(points_rejected, _MAX_POINTS_RENDER)
        for cause, label, color in (
            ("A", "Rejetés : cause A", POINT_COLORS["warning"]),
            ("B", "Rejetés : cause B", POINT_COLORS["rejected"]),
        ):
            frame = rejected.loc[
                rejected["cause"].astype(str).str.upper().eq(cause)
            ]
            if frame.empty:
                continue
            figure.add_trace(
                go.Scatter(
                    x=frame["x"],
                    y=frame["y"],
                    mode="markers",
                    name=label,
                    marker={"size": 9, "color": color, "symbol": "x"},
                    hovertemplate=(
                        f"{label}<br>x=%{{x:.3f}} m<br>y=%{{y:.3f}} m<extra></extra>"
                    ),
                )
            )

    figure.update_layout(
        title=(
            "Couverture de la grille : projection XY"
            + {
                "all": "",
                "retained": " : points retenus",
                "rejected": " : points rejetés",
            }[view]
        ),
        xaxis_title="X (m)",
        yaxis_title="Y (m)",
    )
    apply_chart_layout(figure, height=500, legend_title="Statut du point")
    figure.update_yaxes(scaleanchor="x")
    return figure
