"""Historique compact et comparaison traçable des exécutions SP2."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.demo import render_demo_guide  # noqa: E402
from app.layout import render_table_context  # noqa: E402
from app.state import initialize_session_state  # noqa: E402
from services.result_service import ResultLoadError, ResultService, RunSummary  # noqa: E402
from visualization.labels import baseline_label  # noqa: E402
from visualization.run_comparison_plots import (  # noqa: E402
    build_run_gain_figure,
    build_run_kpi_figure,
)

initialize_session_state()
render_demo_guide("Historique")

st.title("Historique")
st.caption("Sélectionnez un run, puis comparez uniquement des configurations identifiées.")

source_paths = ResultService.discover_loadable_runs(Path("data/runs"))
if not st.session_state.current_output_dir:
    st.info("Aucune source n’est actuellement chargée.")

if source_paths:
    source_labels = [f"Run : {path.name}" for path in source_paths]
    selected_source = st.selectbox(
        "Source à charger",
        ["Ne pas modifier :", *source_labels],
        key="history_source_selector",
    )
    if selected_source != "Ne pas modifier :" and st.button(
        "Charger la source", type="primary", key="load_history_source"
    ):
        selected_path = source_paths[source_labels.index(selected_source)]
        try:
            loaded = ResultService.load(selected_path)
        except ResultLoadError as exc:
            st.error(f"Cette source ne peut pas être chargée : {exc}")
        else:
            st.session_state.current_run_id = selected_path.name
            st.session_state.current_output_dir = str(selected_path)
            st.session_state.last_validation_status = loaded.validation_status
            st.session_state.demo_mode = False
            st.success(f"Source chargée : {selected_path.name}")
            st.rerun()
else:
    st.warning("Aucun run complet et chargeable n’est disponible.")

entries: dict[str, tuple[RunSummary, object]] = {}
for run_path in source_paths:
    try:
        run_results = ResultService.load(run_path)
    except ResultLoadError:
        continue
    summary = ResultService.summarize(run_path.name, run_results)
    entries[summary.run_id] = (summary, run_results)

invalid_diagnostics = [
    ResultService.diagnose_run(path)
    for path in ResultService.incomplete_runs(Path("data/runs"))
]
if invalid_diagnostics:
    with st.expander("Runs incomplets exclus", expanded=False):
        st.caption("Ces dossiers sont conservés pour diagnostic et exclus des comparaisons.")
        diagnostic_rows = [
            {
                "Run": item["run_id"],
                "Statut": item["manifest_status"],
                "Étape": item["failed_step"] or "—",
                "Erreur": item["error"] or item["manifest_error"] or "—",
                "Artefacts manquants": ", ".join(item["missing_artifacts"]) or "—",
            }
            for item in invalid_diagnostics
        ]
        st.dataframe(diagnostic_rows, width="stretch", hide_index=True)

if not entries:
    st.warning("Aucun run comparable n’est disponible.")
else:
    summaries = [entry[0] for entry in entries.values()]
    st.subheader("Runs disponibles")
    rows = [
        {
            "Run": summary.run_id,
            "Statut": summary.status,
            "Baseline": baseline_label([summary.baseline_kind]),
            "Couverture": f"{summary.coverage_rate:.1%}",
            "Pareto": summary.pareto_distinct_count,
            "Meilleur temps (s)": summary.best_time_motion_s,
            "Meilleure énergie (J)": summary.best_energy_J,
            "Gain temps (%)": summary.min_time_gain_pct,
            "Gain énergie (%)": summary.min_energy_gain_pct,
        }
        for summary in summaries
    ]
    render_table_context("statut, couverture et meilleures performances par run.")
    st.dataframe(
        rows,
        width="stretch",
        hide_index=True,
        column_config={
            "Meilleur temps (s)": st.column_config.NumberColumn(format="%.2f"),
            "Meilleure énergie (J)": st.column_config.NumberColumn(format="%.2f"),
            "Gain temps (%)": st.column_config.NumberColumn(format="%.2f"),
            "Gain énergie (%)": st.column_config.NumberColumn(format="%.2f"),
        },
    )

    with st.expander("Évolution entre les runs", expanded=False):
        st.plotly_chart(build_run_kpi_figure(summaries), width="stretch")
        st.plotly_chart(build_run_gain_figure(summaries), width="stretch")

    if len(entries) >= 2:
        with st.expander("Comparer deux runs", expanded=False):
            run_ids = list(entries)
            left, right = st.columns(2)
            with left:
                run_a = st.selectbox("Run A", run_ids, index=0, key="history_run_a")
            with right:
                run_b = st.selectbox(
                    "Run B", run_ids, index=min(1, len(run_ids) - 1), key="history_run_b"
                )
            summary_a = entries[run_a][0]
            summary_b = entries[run_b][0]
            if summary_a.baseline_kind != summary_b.baseline_kind:
                st.warning(
                    "Baselines différentes : les gains relatifs ne sont pas directement "
                    "comparables."
                )
            elif summary_a.fingerprint == summary_b.fingerprint:
                st.success("Même empreinte de configuration : comparaison algorithmique possible.")
            else:
                st.warning("Empreintes différentes : interpréter la comparaison avec prudence.")
            diff_rows = [
                {
                    "Indicateur": "Baseline",
                    "Run A": baseline_label([summary_a.baseline_kind]),
                    "Run B": baseline_label([summary_b.baseline_kind]),
                },
                {
                    "Indicateur": "Statut",
                    "Run A": summary_a.status,
                    "Run B": summary_b.status,
                },
                {
                    "Indicateur": "Couverture",
                    "Run A": f"{summary_a.coverage_rate:.1%}",
                    "Run B": f"{summary_b.coverage_rate:.1%}",
                },
                {
                    "Indicateur": "Meilleur temps (s)",
                    "Run A": summary_a.best_time_motion_s,
                    "Run B": summary_b.best_time_motion_s,
                },
                {
                    "Indicateur": "Meilleure énergie (J)",
                    "Run A": summary_a.best_energy_J,
                    "Run B": summary_b.best_energy_J,
                },
            ]
            st.dataframe(diff_rows, width="stretch", hide_index=True)
    else:
        st.info("Un second run est nécessaire pour activer la comparaison.")
