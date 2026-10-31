"""État minimal partagé entre les pages Streamlit."""
from __future__ import annotations

from typing import Final

import streamlit as st

SESSION_DEFAULTS: Final = {
    "current_run_id": None,
    "current_output_dir": None,
    "run_handle": None,
    "run_status": None,
    "last_validation_status": None,
    "configuration_submitted": False,
    "run_progress": 0.0,
    "run_step": None,
    "run_error": None,
    "parameter_preview": None,
    "parameter_preview_signature": None,
    "selected_strategy": "compromise",
    "demo_mode": False,
}


def initialize_session_state() -> None:
    """Initialise les clés sans déclencher de calcul scientifique."""
    for key, default in SESSION_DEFAULTS.items():
        st.session_state.setdefault(key, default)
