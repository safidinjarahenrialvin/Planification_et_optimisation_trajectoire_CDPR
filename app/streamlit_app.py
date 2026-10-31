"""Point d’entrée de l’application GUI Tandem SP2."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st  # noqa: E402

from app.state import initialize_session_state  # noqa: E402
from app.theme import apply_theme  # noqa: E402

st.set_page_config(
    page_title="Tandem SP2",
    page_icon="T",
    layout="wide",
    initial_sidebar_state="auto",
)

initialize_session_state()
apply_theme()

pages = [
    st.Page(str(Path(__file__).parent / "pages" / "home.py"), title="Accueil"),
    st.Page(str(Path(__file__).parent / "pages" / "parameters.py"), title="Paramètres"),
    st.Page(str(Path(__file__).parent / "pages" / "results.py"), title="Résultats"),
    st.Page(str(Path(__file__).parent / "pages" / "history.py"), title="Historique"),
]

navigation = st.navigation(pages)
navigation.run()
