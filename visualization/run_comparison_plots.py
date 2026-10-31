"""Figures de comparaison multi-runs."""
from __future__ import annotations

from typing import Sequence

from plotly.subplots import make_subplots
import plotly.graph_objects as go

from services.result_service import RunSummary
from visualization.labels import kind_label


def build_run_kpi_figure(summaries: Sequence[RunSummary]) -> go.Figure:
    """Compare les temps et énergies absolus avec des axes séparés."""
    if not summaries:
        raise ValueError("Au moins un run est nécessaire")
    labels = [summary.run_id for summary in summaries]
    baseline_labels = [kind_label(summary.baseline_kind) for summary in summaries]
    figure = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Meilleur temps de mouvement", "Meilleure énergie"),
    )
    figure.add_trace(
        go.Bar(
            x=labels,
            y=[summary.best_time_motion_s for summary in summaries],
            name="Temps de mouvement",
            marker_color="#1769aa",
            customdata=baseline_labels,
            hovertemplate=(
                "%{x}<br>Baseline : %{customdata}<br>"
                "Temps : %{y:.2f} s<extra></extra>"
            ),
        ),
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Bar(
            x=labels,
            y=[summary.best_energy_J for summary in summaries],
            name="Énergie",
            marker_color="#2e7d32",
            customdata=baseline_labels,
            hovertemplate=(
                "%{x}<br>Baseline : %{customdata}<br>"
                "Énergie : %{y:.2f} J<extra></extra>"
            ),
        ),
        row=1,
        col=2,
    )
    figure.update_yaxes(title_text="Temps de mouvement (s)", row=1, col=1)
    figure.update_yaxes(title_text="Énergie (J)", row=1, col=2)
    figure.update_layout(
        title="Comparaison des performances absolues",
        template="plotly_white",
        height=430,
        showlegend=False,
    )
    return figure


def build_run_gain_figure(summaries: Sequence[RunSummary]) -> go.Figure:
    """Compare les gains relatifs de chaque run contre sa baseline."""
    if not summaries:
        raise ValueError("Au moins un run est nécessaire")
    labels = [summary.run_id for summary in summaries]
    figure = go.Figure(
        data=[
            go.Bar(
                name="Gain temps de mouvement",
                x=labels,
                y=[summary.min_time_gain_pct for summary in summaries],
                marker_color="#1565c0",
                customdata=[kind_label(summary.baseline_kind) for summary in summaries],
                hovertemplate=(
                    "%{x}<br>Baseline : %{customdata}<br>"
                    "Gain temps : %{y:.2f} %<extra></extra>"
                ),
            ),
            go.Bar(
                name="Gain énergie",
                x=labels,
                y=[summary.min_energy_gain_pct for summary in summaries],
                marker_color="#2e7d32",
                customdata=[kind_label(summary.baseline_kind) for summary in summaries],
                hovertemplate=(
                    "%{x}<br>Baseline : %{customdata}<br>"
                    "Gain énergie : %{y:.2f} %<extra></extra>"
                ),
            ),
        ]
    )
    figure.update_layout(
        title="Gains relatifs contre la baseline de chaque run",
        xaxis_title="Run",
        yaxis_title="Gain (%)",
        barmode="group",
        template="plotly_white",
        height=430,
    )
    figure.add_trace(
        go.Scatter(
            name="Niveau des baselines : 0 %",
            x=labels,
            y=[0] * len(labels),
            mode="lines",
            line={"color": "#263238", "width": 1.5, "dash": "dash"},
            hovertemplate="Référence de la baseline de ce run : 0 %<extra></extra>",
        )
    )
    return figure
