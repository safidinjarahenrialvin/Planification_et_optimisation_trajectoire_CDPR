"""Helpers de mise en page partagés entre les pages Streamlit."""
from __future__ import annotations

from collections.abc import Sequence

import streamlit as st


_STATUS_DESCRIPTIONS = {
    "PASS": "les contrôles automatiques sont réussis",
    "WARN": "les contrôles automatiques signalent un point à examiner",
    "FAIL": "les contrôles automatiques signalent un échec",
}

_STATUS_CLASSES = {"PASS": "status-pass", "WARN": "status-warn", "FAIL": "status-fail"}


def status_description(status: object) -> str:
    """Retourne une formulation compréhensible sans dépendre de la couleur."""
    value = str(status).upper()
    return f"{value} : {_STATUS_DESCRIPTIONS.get(value, 'statut non documenté')}"


def render_accessible_status(status: object, detail: str | None = None) -> None:
    """Affiche un statut avec son code et sa signification en toutes lettres."""
    message = status_description(status)
    if detail:
        message = f"{message}. {detail}"
    status_class = _STATUS_CLASSES.get(str(status).upper(), "status-unknown")
    st.markdown(
        f'<p class="status-summary {status_class}" role="status">'
        f"<strong>{message}</strong></p>",
        unsafe_allow_html=True,
    )


def render_table_context(description: str) -> None:
    """Associe une description textuelle immédiatement lisible à un tableau."""
    st.caption(f"Tableau : {description}")


def render_chart_context(description: str) -> None:
    """Expose une description courte pour les personnes ne lisant pas le graphique."""
    st.caption(description)


def render_metric_grid(
    metrics: Sequence[tuple[str, object]],
    *,
    columns_per_row: int = 2,
) -> None:
    """Affiche les métriques en lignes courtes, lisibles dans le panneau principal."""
    if columns_per_row < 1:
        raise ValueError("columns_per_row doit être supérieur ou égal à 1")

    for start in range(0, len(metrics), columns_per_row):
        row = st.columns(columns_per_row)
        for column, (label, value) in zip(
            row,
            metrics[start : start + columns_per_row],
            strict=False,
        ):
            with column:
                st.metric(label, value)
