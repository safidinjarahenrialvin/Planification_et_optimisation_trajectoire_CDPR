"""Figures de synthèse destinées à la présentation scientifique."""
from __future__ import annotations

import plotly.graph_objects as go
import pandas as pd
from plotly.subplots import make_subplots

from visualization.labels import baseline_label, kind_label


def build_comparison_figure(comparison: pd.DataFrame) -> go.Figure:
    """Compare les gains réels de chaque stratégie à la baseline."""
    required = {"kind", "gain_time_vs_baseline_pct", "gain_energy_vs_baseline_pct"}
    missing = required - set(comparison.columns)
    if missing:
        raise ValueError(f"Colonnes comparaison manquantes : {sorted(missing)}")

    frame = comparison.copy()
    frame["label"] = frame["kind"].map(kind_label)
    figure = go.Figure(
        data=[
            go.Bar(
                name="Gain de temps de mouvement",
                x=frame["label"],
                y=frame["gain_time_vs_baseline_pct"],
                marker_color="#1769aa",
                customdata=frame[["kind"]],
                hovertemplate=(
                    "%{x}<br>gain temps de mouvement=%{y:.2f} %<br>"
                    "stratégie=%{customdata[0]}<extra></extra>"
                ),
            ),
            go.Bar(
                name="Gain d’énergie",
                x=frame["label"],
                y=frame["gain_energy_vs_baseline_pct"],
                marker_color="#2e7d32",
                customdata=frame[["kind"]],
                hovertemplate=(
                    "%{x}<br>gain énergie=%{y:.2f} %<br>"
                    "stratégie=%{customdata[0]}<extra></extra>"
                ),
            ),
        ]
    )
    figure.update_layout(
        title="Gains de temps de mouvement et d’énergie par rapport à la baseline",
        xaxis_title="Stratégie",
        yaxis_title="Gain relatif (%)",
        barmode="group",
        template="plotly_white",
        height=430,
        legend_title="Indicateur",
    )
    figure.add_trace(
        go.Scatter(
            name="Niveau de la baseline : 0 %",
            x=frame["label"],
            y=[0] * len(frame),
            mode="lines",
            line={"color": "#263238", "width": 1.5, "dash": "dash"},
            hovertemplate="Référence baseline : 0 %<extra></extra>",
        )
    )
    return figure


def build_absolute_comparison_figure(comparison: pd.DataFrame) -> go.Figure:
    """Compare les valeurs absolues avec des axes séparés par unité."""
    required = {"kind", "time_motion_s", "energy_J"}
    missing = required - set(comparison.columns)
    if missing:
        raise ValueError(f"Colonnes comparaison manquantes : {sorted(missing)}")
    frame = comparison.copy()
    frame["label"] = frame["kind"].map(kind_label)
    colors = [
        "#5f7182" if str(kind).startswith("baseline") else "#2f8f83"
        for kind in frame["kind"]
    ]
    figure = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Temps de mouvement", "Énergie consommée"),
        horizontal_spacing=0.16,
    )
    figure.add_trace(
        go.Bar(
            name="Temps de mouvement",
            x=frame["label"],
            y=frame["time_motion_s"],
            marker_color=colors,
            customdata=frame[["kind", "energy_J"]],
            hovertemplate=(
                "%{x}<br>temps de mouvement=%{y:.2f} s<br>énergie=%{customdata[1]:.2f} J"
                "<extra></extra>"
            ),
            showlegend=False,
        ),
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Bar(
            name="Énergie",
            x=frame["label"],
            y=frame["energy_J"],
            marker_color=colors,
            customdata=frame[["kind", "time_motion_s"]],
            hovertemplate=(
                "%{x}<br>énergie=%{y:.2f} J<br>temps de mouvement=%{customdata[1]:.2f} s"
                "<extra></extra>"
            ),
            showlegend=False,
        ),
        row=1,
        col=2,
    )
    for name, color in (
        ("Baseline", "#5f7182"),
        ("Stratégies optimisées", "#2f8f83"),
    ):
        figure.add_trace(
            go.Scatter(
                name=name,
                x=[None],
                y=[None],
                mode="markers",
                marker={"symbol": "square", "size": 10, "color": color},
                hoverinfo="skip",
            ),
            row=1,
            col=1,
        )
    figure.update_layout(
        title=f"Performances absolues : référence : {baseline_label(frame['kind'])}",
        barmode="group",
        template="plotly_white",
        height=450,
        legend_title="Type de trajectoire",
        legend={"orientation": "h", "y": -0.2, "x": 0.5, "xanchor": "center"},
    )
    figure.update_xaxes(title_text="Trajectoire", row=1, col=1)
    figure.update_xaxes(title_text="Trajectoire", row=1, col=2)
    figure.update_yaxes(title_text="Temps de mouvement (s)", row=1, col=1)
    figure.update_yaxes(title_text="Énergie (J)", row=1, col=2)
    return figure
