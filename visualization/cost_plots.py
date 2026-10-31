"""Visualisations interactives et résumés statistiques des transitions SP2."""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import pandas as pd
from plotly.subplots import make_subplots


_METRIC_LABELS = {
    "time": ("Temps de déplacement", "Temps (s)"),
    "energy": ("Énergie de déplacement", "Énergie (J)"),
    "distance": ("Distance de déplacement", "Distance (m)"),
    "feasible": ("Faisabilité des transitions", "Faisable (1)"),
}
_COST_METRICS = {
    "distance": ("Distance", "m"),
    "time": ("Temps de déplacement", "s"),
    "energy": ("Énergie", "J"),
}
_MAX_HEATMAP_AXIS = 150


def build_cost_heatmap(cost_matrix: pd.DataFrame, metric: str) -> go.Figure:
    """Construit une heatmap i→j à partir de la matrice de coûts réelle."""
    required = {"i", "j", metric}
    missing = required - set(cost_matrix.columns)
    if missing:
        raise ValueError(f"Colonnes coûts manquantes : {sorted(missing)}")
    if metric not in _METRIC_LABELS:
        raise ValueError(f"Métrique non supportée : {metric}")

    pivot = cost_matrix.pivot(index="i", columns="j", values=metric).sort_index()
    sampled = len(pivot.index) > _MAX_HEATMAP_AXIS or len(pivot.columns) > _MAX_HEATMAP_AXIS
    if sampled:
        row_idx = np.linspace(0, len(pivot.index) - 1, _MAX_HEATMAP_AXIS, dtype=int)
        col_idx = np.linspace(0, len(pivot.columns) - 1, _MAX_HEATMAP_AXIS, dtype=int)
        pivot = pivot.iloc[np.unique(row_idx), np.unique(col_idx)]
    z = pivot.to_numpy(dtype=float)
    if metric != "feasible" and "feasible" in cost_matrix:
        feasible = cost_matrix.pivot(index="i", columns="j", values="feasible")
        if sampled:
            feasible = feasible.iloc[np.unique(row_idx), np.unique(col_idx)]
        z = np.where(feasible.to_numpy(dtype=float) > 0, z, np.nan)
    title, colorbar_title = _METRIC_LABELS[metric]
    if sampled:
        title += " : affichage échantillonné"
    figure = go.Figure(
        data=[
            go.Heatmap(
                z=z,
                x=pivot.columns.tolist(),
                y=pivot.index.tolist(),
                colorscale="Viridis" if metric != "feasible" else [[0, "#d32f2f"], [1, "#2e7d32"]],
                colorbar={"title": colorbar_title},
                hovertemplate="Départ %{y} → arrivée %{x}<br>"
                f"{colorbar_title}=%{{z:.3f}}<extra></extra>",
            )
        ]
    )
    figure.update_layout(
        title=title,
        xaxis_title="Point d’arrivée j",
        yaxis_title="Point de départ i",
        template="plotly_white",
        height=430,
    )
    return figure


def build_cost_distribution_figure(cost_matrix: pd.DataFrame) -> go.Figure:
    """Affiche les distributions des coûts des transitions faisables, hors diagonale."""
    feasible = cost_matrix.loc[
        (cost_matrix["i"] != cost_matrix["j"]) & (cost_matrix["feasible"] > 0)
    ]
    figure = make_subplots(
        rows=1,
        cols=3,
        subplot_titles=tuple(
            f"{label} ({unit})" for label, unit in _COST_METRICS.values()
        ),
        horizontal_spacing=0.12,
    )
    for column, (metric, (label, unit)) in enumerate(_COST_METRICS.items(), start=1):
        figure.add_trace(
            go.Box(
                y=feasible[metric].astype(float),
                x=np.full(len(feasible), label),
                name=label,
                boxmean=False,
                marker_color="#1769aa",
                line_color="#1769aa",
                hovertemplate=(
                    f"{label} : %{{y:.3f}} {unit}<extra></extra>"
                ),
                showlegend=False,
            ),
            row=1,
            col=column,
        )
        if not feasible.empty:
            figure.add_trace(
                go.Scatter(
                    x=[label],
                    y=[float(feasible[metric].mean())],
                    name="Moyenne",
                    mode="markers",
                    marker={"symbol": "diamond", "size": 10, "color": "#b23a48"},
                    hovertemplate=f"Moyenne : %{{y:.3f}} {unit}<extra></extra>",
                    showlegend=column == 1,
                ),
                row=1,
                col=column,
            )
        figure.update_yaxes(title_text=unit, row=1, col=column)
        figure.update_xaxes(showticklabels=False, row=1, col=column)
    figure.update_layout(
        title="Distribution des coûts par transition faisable",
        template="plotly_white",
        height=400,
        boxmode="group",
        margin={"l": 45, "r": 20, "t": 85, "b": 35},
    )
    figure.add_annotation(
        x=0.5,
        y=1.13,
        xref="paper",
        yref="paper",
        text=(
            f"n = {len(feasible)} transitions faisables · "
            "boîte = Q1 : Q3 · trait = médiane · losange = moyenne"
        ),
        showarrow=False,
        font={"size": 12, "color": "#475569"},
    )
    return figure
