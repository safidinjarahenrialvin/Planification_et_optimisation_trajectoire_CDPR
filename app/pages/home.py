"""Accueil de présentation scientifique de Tandem SP2."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.state import initialize_session_state  # noqa: E402
from app.demo import render_demo_guide  # noqa: E402
from app.layout import render_metric_grid  # noqa: E402
from services.result_service import ResultLoadError, ResultService  # noqa: E402
from services.presentation_service import build_jury_script  # noqa: E402
from visualization.pareto_plots import build_pareto_figure  # noqa: E402

initialize_session_state()
render_demo_guide("Synthèse")


def _load_presentation_results():
    """Retourne les résultats affichables et leur origine explicite."""
    output_dir = st.session_state.current_output_dir
    run_id = st.session_state.current_run_id
    if output_dir and run_id:
        try:
            return ResultService.load(Path(output_dir)), f"Source active : `{run_id}`"
        except ResultLoadError as exc:
            st.warning(f"Le run courant n’est pas lisible : {exc}")
    return None, None


st.markdown(
    '<span class="small-kicker">Projet Tandem SP2</span>',
    unsafe_allow_html=True,
)
st.title("Planification et optimisation des trajectoires d’un robot à câbles")
st.write(
    "Cette plateforme transforme une grille de points en trajectoires analysées, "
    "en vérifiant leur couverture et le compromis entre temps de mouvement et énergie."
)

render_metric_grid(
    [
        ("Source", "Chargée" if st.session_state.current_run_id else "Aucune"),
        (
            "Configuration",
            "Prête" if st.session_state.configuration_submitted else "À préparer",
        ),
    ]
)

results, origin = _load_presentation_results()
if results is None:
    st.subheader("Aucune source de résultats chargée")
    st.info(
        "L’interface est volontairement vide au démarrage. Lancez une exécution dans "
        "Paramètres pour produire le premier résultat de la session."
    )
    source_entries = [
        (f"Run : {path.name}", path)
        for path in ResultService.discover_loadable_runs(Path("data/runs"))
    ]
    source_entries.extend(
        (f"Snapshot : {path.name}", path)
        for path in ResultService.discover_snapshots(Path("data/snapshots"))
    )
    source_labels = [label for label, _ in source_entries]
    incomplete_count = len(ResultService.incomplete_runs(Path("data/runs")))
    if incomplete_count:
        st.caption(
            f"{incomplete_count} dossier(s) local(aux) incomplet(s) non proposé(s) au chargement."
        )
    selected_label = st.selectbox(
        "Source à afficher",
        ["Aucune source :", *source_labels],
        index=0,
    )
    if selected_label != "Aucune source :":
        selected_path = source_entries[source_labels.index(selected_label)][1]
        if st.button("Charger cette source", type="primary"):
            try:
                loaded = ResultService.load(selected_path)
            except ResultLoadError as exc:
                st.error(
                    "Cette source ne peut pas être chargée. Vérifiez que le dossier "
                    "contient tous les artefacts du run."
                )
                with st.expander("Détail technique", expanded=False):
                    st.code(str(exc))
            else:
                st.session_state.current_run_id = selected_path.name
                st.session_state.current_output_dir = str(selected_path)
                st.session_state.last_validation_status = loaded.validation_status
                st.session_state.demo_mode = False
                st.rerun()
    st.page_link("pages/parameters.py", label="Configurer et lancer un run")
    st.caption(
        "Les résultats produits par le terminal peuvent être copiés dans "
        "`data/runs/<nom_du_run>` puis chargés depuis cette page."
    )
else:
    st.caption(origin)
    if st.button("Rafraîchir la source"):
        st.session_state.current_run_id = None
        st.session_state.current_output_dir = None
        st.session_state.last_validation_status = None
        st.session_state.run_handle = None
        st.session_state.run_status = None
        st.session_state.run_progress = 0.0
        st.session_state.run_step = None
        st.session_state.run_error = None
        st.session_state.demo_mode = False
        st.session_state.selected_strategy = "compromise"
        st.rerun()
    point_stats = results.point_statistics()
    diagnostic = results.comparison_diagnostic
    pareto_stats = results.pareto_statistics()
    gain_stats = results.gain_statistics()

    st.markdown("### Résumé")
    render_metric_grid(
        [
            ("Points retenus", f"{point_stats['count']} / {len(results.points_generated)}"),
            ("Compromis Pareto distincts", pareto_stats["distinct_count"]),
            ("Gain temps de mouvement minimal", f"{gain_stats['min_time_gain_pct']:.2f} %"),
            ("Gain énergie minimal", f"{gain_stats['min_energy_gain_pct']:.2f} %"),
            (
                "Comparaison à la baseline",
                "Meilleure" if diagnostic["optimal_beats_baseline"] else "À analyser",
            ),
        ]
    )

    st.plotly_chart(
        build_pareto_figure(results.pareto),
        width="stretch",
        key="home_pareto",
    )

    st.markdown("### Conclusion")
    st.info(
        "La comparaison met en évidence un compromis entre temps de mouvement "
        "et énergie. La stratégie retenue dépend de la priorité de l’étude."
    )

    if st.session_state.demo_mode:
        with st.expander("Script oral généré depuis ce run", expanded=False):
            st.markdown(build_jury_script(st.session_state.current_run_id, results))
