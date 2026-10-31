"""Figures interactives des résultats d’optimisation."""
from __future__ import annotations

import plotly.graph_objects as go
import pandas as pd

from visualization.chart_style import apply_chart_layout


_MAX_PARETO_RENDER = 2000


def build_pareto_figure(pareto: pd.DataFrame) -> go.Figure:
    """Construit une présentation lisible du front temps-énergie."""
    required = {"time", "energy", "solution_id"}
    missing = required - set(pareto.columns)
    if missing:
        raise ValueError(f"Colonnes Pareto manquantes : {sorted(missing)}")

    sampled = len(pareto) > _MAX_PARETO_RENDER
    if sampled:
        indices = pd.Series(range(len(pareto))).sample(
            n=_MAX_PARETO_RENDER, random_state=0
        ).sort_values()
        pareto = pareto.iloc[indices.to_numpy()]
    pareto = pareto.sort_values("time").reset_index(drop=True)
    min_time_index = pareto["time"].idxmin()
    min_energy_index = pareto["energy"].idxmin()
    labels = pd.Series("", index=pareto.index, dtype="string")
    labels.loc[min_time_index] = "Min. temps"
    labels.loc[min_energy_index] = (
        labels.loc[min_energy_index] + " · " if labels.loc[min_energy_index] else ""
    ) + "Min. énergie"
    figure = go.Figure(
        data=[
            go.Scatter(
                x=pareto["time"],
                y=pareto["energy"],
                mode="lines+markers+text",
                text=labels,
                textposition="top center",
                customdata=pareto[["solution_id", "time", "energy"]],
                hovertemplate=(
                    "solution=%{customdata[0]}<br>"
                    "temps de mouvement=%{customdata[1]:.3f} s<br>"
                    "énergie=%{customdata[2]:.3f} J<extra></extra>"
                ),
                line={"color": "#1769AA", "width": 2.5},
                marker={
                    "size": 10,
                    "color": pareto["energy"],
                    "colorscale": "Viridis",
                    "showscale": True,
                    "colorbar": {"title": "Énergie (J)"},
                },
            )
        ]
    )
    figure.update_layout(
        title=(
            "Front de Pareto : compromis temps / énergie"
            + (" : affichage échantillonné" if sampled else "")
        ),
        xaxis_title="Temps de mouvement (s)",
        yaxis_title="Énergie (J)",
    )
    apply_chart_layout(figure, height=480, legend_title="Solutions")
    figure.add_annotation(
        x=0.5,
        y=1.08,
        xref="paper",
        yref="paper",
        text="Chaque point est une solution non dominée ; la ligne montre le compromis",
        showarrow=False,
        font={"size": 12, "color": "#52606d"},
    )
    return figure
