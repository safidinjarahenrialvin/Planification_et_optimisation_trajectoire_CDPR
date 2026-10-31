"""Page de consultation et d’analyse du dernier run GUI."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.state import initialize_session_state  # noqa: E402
from app.demo import render_demo_guide  # noqa: E402
from app.layout import (  # noqa: E402
    render_chart_context,
    render_metric_grid,
)
from services.export_service import ExportService  # noqa: E402
from services.result_service import ResultLoadError, ResultService  # noqa: E402
from services.snapshot_service import (  # noqa: E402
    SnapshotCreationError,
    SnapshotService,
)
from visualization.pareto_plots import build_pareto_figure  # noqa: E402
from visualization.robot_3d import (  # noqa: E402
    SceneOptions,
    build_robot_figure,
    load_config_snapshot,
)
from visualization.robot_animation import (  # noqa: E402
    AnimationOptions,
    build_robot_animation_figure,
)
from visualization.trajectory_plots import (  # noqa: E402
    build_profile_figure,
    build_trajectory_xy_figure,
)
from visualization.summary_plots import (  # noqa: E402
    build_absolute_comparison_figure,
    build_comparison_figure,
)
from visualization.wfw_plots import build_wfw_coverage_figure  # noqa: E402
from visualization.labels import baseline_label, kind_label  # noqa: E402

initialize_session_state()
render_demo_guide("Résultats")

st.title("Résultats et analyses")

run_id = st.session_state.current_run_id
output_dir_value = st.session_state.current_output_dir
if st.session_state.get("prepared_zip_run_id") != run_id:
    st.session_state.prepared_zip_run_id = None
    st.session_state.prepared_zip_payload = None

if run_id is None or output_dir_value is None:
    st.warning(
        "Aucun résultat n’est encore chargé. Lancez une exécution dans Paramètres "
        "ou sélectionnez une source depuis l’Accueil."
    )
else:
    output_dir = Path(output_dir_value)
    try:
        results = ResultService.load(output_dir)
    except ResultLoadError as exc:
        st.error(
            "Impossible de charger cette source. Vérifiez que le dossier contient "
            "les artefacts complets du run, puis revenez à l’Accueil pour en choisir "
            "une autre."
        )
        with st.expander("Détail technique", expanded=False):
            st.code(str(exc))
    else:
        st.success(f"Source chargée : {run_id}")
        st.caption(f"Artefacts conservés dans : `{output_dir}`")

        pareto_stats = results.pareto_statistics()
        point_stats = results.point_statistics()

        strategy_options = sorted(results.trajectories["kind"].dropna().unique())
        if st.session_state.selected_strategy not in strategy_options:
            st.session_state.selected_strategy = strategy_options[0]
        selected_kind = st.selectbox(
            "Stratégie affichée dans les vues liées",
            strategy_options,
            key="selected_strategy",
            format_func=kind_label,
        )
        selected_trajectory = results.trajectories[
            results.trajectories["kind"] == selected_kind
        ]
        selected_comparison = results.comparison.loc[
            results.comparison["kind"] == selected_kind
        ].iloc[0]

        tabs = st.tabs(
            [
                "Scène 3D",
                "Trajectoires",
                "Profils cinématiques",
                "Couverture WFW",
                "Pareto",
                "Analyse & comparaison",
                "Validation",
            ]
        )

        with tabs[0]:
            st.subheader("Scène 3D du robot à câbles")
            animate_robot = st.checkbox(
                "Activer l’animation pédagogique",
                value=False,
                help="L’animation illustre le profil temporel réel du run.",
            )
            try:
                scene_config = load_config_snapshot(output_dir / "config.json")
                rejected_frames = []
                for filename in ("points_rejetes_cause_a.csv", "points_rejetes_cause_b.csv"):
                    path = output_dir / filename
                    if path.is_file():
                        frame = pd.read_csv(path)
                        if not frame.empty:
                            rejected_frames.append(frame)
                rejected = (
                    pd.concat(rejected_frames, ignore_index=True)
                    if rejected_frames
                    else None
                )
                layer_columns = st.columns(2)
                with layer_columns[0]:
                    show_structure = st.checkbox("Bâti et ancrages", value=True)
                    show_supports = st.checkbox("Pieds", value=True)
                    show_cables = st.checkbox("Câbles", value=True)
                    show_platform = st.checkbox("Plateforme", value=True)
                    show_points = st.checkbox("Points valides", value=True)
                with layer_columns[1]:
                    show_rejected = st.checkbox("Points rejetés", value=False)
                    show_plants = st.checkbox("Plants simplifiés", value=False)
                    show_center = st.checkbox("Centre", value=False)
                    show_path = st.checkbox("Trajectoire", value=False)
                    show_baseline_path = st.checkbox(
                        baseline_label(results.comparison["kind"]), value=False,
                    )
                trajectory_for_scene = selected_trajectory
                if show_baseline_path and not results.baseline_trajectory.empty:
                    trajectory_for_scene = pd.concat(
                        [results.baseline_trajectory, selected_trajectory], ignore_index=True
                    )
                if animate_robot:
                    profile = results.profiles[results.profiles["kind"] == selected_kind]
                    figure = build_robot_animation_figure(
                        scene_config,
                        profile,
                        points_df=results.points_filtered if show_points else None,
                        options=AnimationOptions(max_frames=120),
                    )
                else:
                    figure = build_robot_figure(
                        scene_config,
                        trajectory_df=trajectory_for_scene,
                        points_df=results.points_filtered,
                        rejected_df=rejected,
                        options=SceneOptions(
                            show_frame=show_structure,
                            show_supports=show_supports,
                            show_cables=show_cables,
                            show_platform=show_platform,
                            show_points=show_points,
                            show_rejected=show_rejected,
                            show_plants=show_plants,
                            show_center=show_center,
                            show_trajectory=show_path,
                        ),
                    )
                st.plotly_chart(figure, width="stretch", key="robot_3d")
            except (OSError, KeyError, TypeError, ValueError) as exc:
                st.error("La scène 3D ne peut pas être affichée pour cette source.")
                with st.expander("Détail technique", expanded=False):
                    st.code(str(exc))

        with tabs[1]:
            st.subheader("Trajectoires")
            st.plotly_chart(
                build_trajectory_xy_figure(selected_trajectory),
                width="stretch",
                key="trajectory_xy",
            )
            if not results.baseline_trajectory.empty:
                st.subheader("Baseline")
                st.plotly_chart(
                    build_trajectory_xy_figure(results.baseline_trajectory),
                    width="stretch",
                    key="baseline_trajectory_xy",
                )

        with tabs[2]:
            st.subheader("Profils cinématiques")
            st.plotly_chart(
                build_profile_figure(results.profiles, selected_kind),
                width="stretch",
                key="selected_profile",
            )
        with tabs[3]:
            st.subheader("Couverture WFW des points étudiés")
            wfw_view_label = st.radio(
                "Afficher",
                options=["Tous les points", "Points retenus", "Points rejetés"],
                horizontal=True,
                key="wfw_view",
            )
            wfw_view = {
                "Tous les points": "all",
                "Points retenus": "retained",
                "Points rejetés": "rejected",
            }[wfw_view_label]
            st.plotly_chart(
                build_wfw_coverage_figure(
                    results.points_generated,
                    results.points_filtered,
                    results.points_rejected,
                    view=wfw_view,
                ),
                width="stretch",
                key="wfw_coverage",
            )
            filter_summary = results.point_filter_report.get("summary", {})
            render_metric_grid(
                [
                    ("Points générés", len(results.points_generated)),
                    ("Points retenus", point_stats["count"]),
                    ("Taux de rejet", f"{filter_summary.get('reject_rate', 0):.1%}"),
                    (
                        "Points rejetés",
                        len(results.points_rejected),
                    ),
                ]
            )

        with tabs[4]:
            st.subheader("Front de Pareto")
            pareto = results.pareto
            time_span = float(pareto["time"].max() - pareto["time"].min())
            energy_span = float(pareto["energy"].max() - pareto["energy"].min())
            render_metric_grid(
                [
                    ("Solutions non dominées", pareto_stats["raw_count"]),
                    ("Compromis distincts", pareto_stats["distinct_count"]),
                    ("Amplitude temps", f"{time_span:.2f} s"),
                    ("Amplitude énergie", f"{energy_span:.2f} J"),
                ]
            )
            st.plotly_chart(build_pareto_figure(results.pareto), width="stretch")

        with tabs[5]:
            st.subheader("Analyse et comparaison avec la baseline")
            render_metric_grid(
                [
                    ("Temps de mouvement", f"{selected_comparison['time_motion_s']:.2f} s"),
                    ("Énergie", f"{selected_comparison['energy_J']:.2f} J"),
                    (
                        "Gain temps vs baseline",
                        f"{selected_comparison['gain_time_vs_baseline_pct']:.2f} %",
                    ),
                    (
                        "Gain énergie vs baseline",
                        f"{selected_comparison['gain_energy_vs_baseline_pct']:.2f} %",
                    ),
                ]
            )
            st.plotly_chart(
                build_absolute_comparison_figure(results.comparison),
                width="stretch",
                key="baseline_absolute_comparison",
            )
            render_chart_context(
                "Gains relatifs de temps et d’énergie par rapport à la baseline, "
                "exprimés en pourcentage."
            )
            st.plotly_chart(
                build_comparison_figure(results.comparison),
                width="stretch",
                key="baseline_comparison",
            )

            with st.expander("Téléchargements ciblés", expanded=False):
                st.caption(
                    "Ces fichiers sont construits à partir des artefacts chargés et "
                    "ne modifient jamais le run source."
                )
                download_columns = st.columns(3)
                with download_columns[0]:
                    st.download_button(
                        "Trajectoire sélectionnée",
                        data=ExportService.selected_trajectory_csv(results, selected_kind),
                        file_name=f"trajectoire_{selected_kind}.csv",
                        mime="text/csv",
                        key="download_selected_trajectory",
                    )
                    st.download_button(
                        "Profil cinématique",
                        data=ExportService.selected_profile_csv(results, selected_kind),
                        file_name=f"profil_{selected_kind}.csv",
                        mime="text/csv",
                        key="download_selected_profile",
                    )
                with download_columns[1]:
                    st.download_button(
                        "Comparaison baseline",
                        data=ExportService.selected_comparison_csv(results, selected_kind),
                        file_name=f"comparaison_{selected_kind}.csv",
                        mime="text/csv",
                        key="download_selected_comparison",
                    )
                    st.download_button(
                        "Rapport de validation",
                        data=ExportService.validation_json(results),
                        file_name="validation_report.json",
                        mime="application/json",
                        key="download_validation_report",
                    )
                with download_columns[2]:
                    pareto_path = Path("figures/pareto_front.png")
                    artifact_paths = {
                        path.relative_to(output_dir) for path in results.artifacts
                    }
                    if pareto_path in artifact_paths:
                        st.download_button(
                            "Image du front Pareto",
                            data=ExportService.read_artifact(output_dir, pareto_path),
                            file_name="pareto_front.png",
                            mime="image/png",
                            key="download_pareto_image",
                        )
                    else:
                        st.info("Image Pareto indisponible pour ce run.")

        with tabs[6]:
            st.subheader("Validation")
            validation = results.validation
            summary = validation.get("summary", {})
            render_metric_grid(
                [
                    ("PASS", summary.get("n_pass", 0)),
                    ("WARN", summary.get("n_warn", 0)),
                    ("FAIL", summary.get("n_fail", 0)),
                ],
                columns_per_row=3,
            )
            with st.expander("Preuves techniques", expanded=False):
                st.markdown(
                    "Les artefacts détaillés et les statistiques de la matrice des coûts "
                    "restent accessibles ici sans encombrer les vues de décision."
                )
                st.subheader("Artefacts")
                artifacts = sorted(path.relative_to(output_dir) for path in results.artifacts)
                suffix_counts = pd.Series(
                    path.suffix.lower() or "sans extension" for path in artifacts
                )
                render_metric_grid(
                    [
                        ("Artefacts", len(artifacts)),
                        ("CSV", int((suffix_counts == ".csv").sum())),
                        ("JSON", int((suffix_counts == ".json").sum())),
                        ("Figures PNG", int((suffix_counts == ".png").sum())),
                    ]
                )
                st.caption(
                    "Les tableaux détaillés et rapports sont volontairement conservés dans "
                    "les téléchargements ; l’interface affiche uniquement leurs indicateurs."
                )
                st.subheader("Téléchargements")
                st.caption(
                    "Les téléchargements sont des copies des artefacts ; ils ne modifient "
                    "jamais le run source."
                )

                def download_group(label: str, suffixes: tuple[str, ...], key: str) -> None:
                    files = ExportService.available_files(output_dir, suffixes)
                    if not files:
                        st.info(f"Aucun fichier {label} disponible dans ce run.")
                        return
                    selected = st.selectbox(label, files, format_func=str, key=f"select_{key}")
                    st.download_button(
                        f"Télécharger {label.lower()}",
                        data=ExportService.read_artifact(output_dir, selected),
                        file_name=selected.name,
                        mime={".csv": "text/csv", ".json": "application/json",
                              ".png": "image/png", ".md": "text/markdown"}.get(
                                  selected.suffix.lower(), "application/octet-stream"
                              ),
                        key=f"download_{key}",
                    )

                download_group("CSV", (".csv",), "csv")
                download_group("JSON", (".json",), "json")
                download_group("PNG", (".png",), "png")
                st.caption(
                    "Le résumé compact reprend uniquement les indicateurs de la GUI ; "
                    "il est généré à la demande et ne remplace pas les artefacts détaillés."
                )
                st.download_button(
                    "Télécharger le résumé statistique (summary.json)",
                    data=ExportService.summary_json(
                        run_id,
                        results,
                        selected_kind=selected_kind,
                    ),
                    file_name="summary.json",
                    mime="application/json",
                    key="download_summary_json",
                )
                st.download_button(
                    "Télécharger le rapport",
                    data=ExportService.jury_markdown_report(run_id, results).encode("utf-8"),
                    file_name="rapport.md",
                    mime="text/markdown",
                    key="download_report",
                )
                st.caption(
                    "L’archive complète peut être volumineuse. Elle n’est construite "
                    "qu’après votre demande, puis conservée pour ce run dans la session."
                )
                if st.button("Préparer l’archive complète (ZIP)", key="prepare_zip"):
                    with st.spinner("Assemblage des artefacts du run…"):
                        st.session_state.prepared_zip_payload = ExportService.zip_run(output_dir)
                        st.session_state.prepared_zip_run_id = run_id
                    st.success("Archive prête au téléchargement.")
                if (
                    st.session_state.get("prepared_zip_run_id") == run_id
                    and st.session_state.get("prepared_zip_payload") is not None
                ):
                    st.download_button(
                        "Télécharger l’archive ZIP préparée",
                        data=st.session_state.prepared_zip_payload,
                        file_name=f"{run_id}.zip",
                        mime="application/zip",
                        key="download_zip",
                    )
                st.divider()
                st.subheader("Snapshot persistant")
                if SnapshotService.is_local_run_path(output_dir):
                    st.caption(
                        "Copie explicite et non destructive du run terminé vers "
                        "`data/snapshots/`. La création ne modifie pas le run source."
                    )
                    snapshot_name_key = f"snapshot_name_{run_id}"
                    if snapshot_name_key not in st.session_state:
                        st.session_state[snapshot_name_key] = (
                            SnapshotService.suggested_name(run_id)
                        )
                    snapshot_name = st.text_input(
                        "Nom du snapshot",
                        key=snapshot_name_key,
                        help=(
                            "1 à 64 caractères : lettres ASCII, chiffres, point, "
                            "tiret ou tiret bas. Le nom ne doit pas déjà exister."
                        ),
                    )
                    if st.button("Créer le snapshot", key="create_snapshot"):
                        try:
                            snapshot_path = SnapshotService.create_snapshot(
                                output_dir,
                                snapshot_name,
                            )
                        except SnapshotCreationError as exc:
                            st.error(str(exc))
                        else:
                            st.success(
                                f"Snapshot créé et vérifié : `{snapshot_path}`. "
                                "Il sera sélectionnable depuis l’Accueil."
                            )
                else:
                    st.info(
                        "La création est disponible uniquement pour un run local "
                        "sous `data/runs/`, pas depuis une fixture ou un snapshot."
                    )
