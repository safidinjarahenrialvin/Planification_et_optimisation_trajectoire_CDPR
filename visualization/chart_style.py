"""Tokens et conventions communes aux figures scientifiques."""
from __future__ import annotations

import plotly.graph_objects as go

CHART_FONT = "Inter, Arial, sans-serif"
CHART_TEXT = "#0F172A"
CHART_MUTED = "#475569"
CHART_GRID = "#E2E8F0"
CHART_SURFACE = "#FFFFFF"

STRATEGY_COLORS = {
    "baseline_zigzag": "#5F7182",
    "baseline_nn": "#5F7182",
    "time_opt": "#1769AA",
    "energy_opt": "#2E7D32",
    "compromise": "#8E44AD",
}

POINT_COLORS = {
    "generated": "#64748B",
    "retained": "#16827A",
    "rejected": "#C2413B",
    "warning": "#B45309",
}


def apply_chart_layout(
    figure: go.Figure,
    *,
    height: int,
    legend_title: str | None = None,
    margin: dict[str, int] | None = None,
) -> go.Figure:
    """Applique la présentation commune sans modifier les données de la figure."""
    figure.update_layout(
        template="plotly_white",
        height=height,
        font={"family": CHART_FONT, "color": CHART_TEXT},
        paper_bgcolor=CHART_SURFACE,
        plot_bgcolor=CHART_SURFACE,
        hovermode="closest",
        margin=margin or {"l": 70, "r": 30, "t": 75, "b": 65},
        legend_title=legend_title,
    )
    figure.update_xaxes(
        showline=True,
        linecolor=CHART_GRID,
        gridcolor=CHART_GRID,
        zerolinecolor=CHART_GRID,
    )
    figure.update_yaxes(
        showline=True,
        linecolor=CHART_GRID,
        gridcolor=CHART_GRID,
        zerolinecolor=CHART_GRID,
    )
    return figure


def strategy_color(kind: object) -> str:
    """Retourne une couleur stable pour une stratégie ou une baseline."""
    return STRATEGY_COLORS.get(str(kind), "#2F6F9F")


# Évite qu’un import de type soit nécessaire dans les modules de visualisation.
__all__: tuple[str, ...] = (
    "CHART_GRID",
    "CHART_MUTED",
    "CHART_SURFACE",
    "CHART_TEXT",
    "POINT_COLORS",
    "STRATEGY_COLORS",
    "apply_chart_layout",
    "strategy_color",
)
