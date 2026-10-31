"""Éléments d’interface communs au parcours de démonstration jury."""
from __future__ import annotations

import streamlit as st


DEMO_STEPS = (
    ("1", "Synthèse", "pages/home.py", "Lire la conclusion et les KPI."),
    ("2", "Résultats", "pages/results.py", "Vérifier les preuves et contrôles."),
    ("3", "Trajectoire", "Ouvrir Trajectoire, puis activer l’animation."),
    ("4", "Historique", "pages/history.py", "Comparer les runs chargés."),
    ("5", "Rapport", "pages/results.py", "Télécharger le rapport Markdown."),
)


def render_demo_guide(current_step: str) -> None:
    """Affiche une barre de progression non intrusive quand le mode démo est actif."""
    if not st.session_state.get("demo_mode", False):
        return
    st.info(
        "Mode présentation guidée actif : utilisez les étapes ci-dessous pour suivre "
        "un parcours reproductible basé sur le run actuellement chargé."
    )
    for start in range(0, len(DEMO_STEPS), 2):
        columns = st.columns(2)
        for column, (number, title, page, description) in zip(
            columns, DEMO_STEPS[start : start + 2], strict=False
        ):
            with column:
                marker = "●" if title == current_step else "○"
                st.markdown(f"**{marker} {number}. {title}**")
                st.caption(description)
                if title != current_step:
                    st.page_link(page, label=f"Ouvrir {title}")
    if st.button("Quitter le mode démonstration", key=f"exit_demo_{current_step}"):
        st.session_state.demo_mode = False
        st.rerun()
