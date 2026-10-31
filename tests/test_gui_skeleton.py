"""Tests de démarrage, navigation et formulaire du GUI."""
from __future__ import annotations

from shutil import copytree
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest
from services.result_service import ResultService
from services.export_service import ExportService
from services.snapshot_service import SnapshotService


APP_PATH = Path(__file__).parents[1] / "app" / "streamlit_app.py"
REFERENCE = Path(__file__).parents[1] / "tests" / "fixtures" / "reference_run"


def test_gui_home_starts_without_running_pipeline() -> None:
    app = AppTest.from_file(str(APP_PATH)).run()

    assert not app.exception
    assert app.title[0].value == (
        "Planification et optimisation des trajectoires d’un robot à câbles"
    )
    assert any("Projet Tandem SP2" in item.value for item in app.markdown)
    assert app.metric[0].label == "Source"
    assert app.metric[0].value == "Aucune"
    assert app.metric[1].value == "À préparer"
    assert not app.session_state.current_run_id


def test_gui_parameters_page_exposes_controlled_form() -> None:
    app = AppTest.from_file(str(APP_PATH)).run()
    app.switch_page("pages/parameters.py").run()

    assert not app.exception
    assert app.title[0].value == "Paramètres"
    assert app.selectbox[0].label == "Niveau d’exécution"
    assert not app.button
    assert not app.session_state.configuration_submitted


def test_gui_parameters_page_exposes_configuration_preview() -> None:
    app = AppTest.from_file(str(APP_PATH)).run()
    app.switch_page("pages/parameters.py").run()

    assert not app.exception
    assert any("Sélectionnez un niveau d’étude" in item.value for item in app.info)


def test_gui_parameters_preview_is_explicit_and_uses_current_settings() -> None:
    app = AppTest.from_file(str(APP_PATH)).run()
    app.switch_page("pages/parameters.py").run()
    app.selectbox[0].set_value("Instance courte : 3×3").run()

    next(button for button in app.button if button.label == "Actualiser l’aperçu").click().run()

    assert not app.exception
    assert any(item.label == "Durée indicative" for item in app.metric)
    assert app.session_state.parameter_preview_signature == (
        3, "300x240", True, 5, 30, 100, 42, None, None, None, None, None,
    )


def test_gui_parameters_previews_and_invalidates_imposed_r0_altitude() -> None:
    app = AppTest.from_file(str(APP_PATH)).run()
    app.switch_page("pages/parameters.py").run()
    app.selectbox[0].set_value("Instance courte : 3×3").run()

    altitude_mode = next(
        radio for radio in app.radio if radio.label == "Mode de calcul de l’altitude de R0"
    )
    assert altitude_mode.value == "Automatique"
    automatic_altitude_input = next(
        item for item in app.number_input
        if item.label == "Altitude absolue de la plateforme R0 (m)"
    )
    assert automatic_altitude_input.disabled is True
    altitude_mode.set_value("Valeur imposée").run()
    altitude_input = next(
        item for item in app.number_input
        if item.label == "Altitude absolue de la plateforme R0 (m)"
    )
    altitude_input.set_value(0.55).run()
    next(button for button in app.button if button.label == "Actualiser l’aperçu").click().run()

    assert not app.exception
    assert app.session_state.parameter_preview.z_absolu_r0_override == 0.55
    assert app.session_state.parameter_preview_signature[7] == 0.55
    assert any(
        metric.label == "Altitude absolue R0"
        and metric.value == "0.550 m"
        for metric in app.metric
    )

    altitude_input = next(
        item for item in app.number_input
        if item.label == "Altitude absolue de la plateforme R0 (m)"
    )
    altitude_input.set_value(0.56).run()
    next(
        button for button in app.button
        if button.label == "Lancer l’exécution sélectionnée"
    ).click().run()

    assert any("Actualisez l’aperçu" in item.value for item in app.error)
    assert app.session_state.current_run_id is None


def test_gui_parameters_blocks_launch_after_preview_becomes_stale() -> None:
    app = AppTest.from_file(str(APP_PATH)).run()
    app.switch_page("pages/parameters.py").run()
    app.selectbox[0].set_value("Instance courte : 3×3").run()
    next(button for button in app.button if button.label == "Actualiser l’aperçu").click().run()

    next(item for item in app.number_input if item.label == "Sous-pas K").set_value(7).run()
    next(
        button for button in app.button
        if button.label == "Lancer l’exécution sélectionnée"
    ).click().run()

    assert any("Actualisez l’aperçu" in item.value for item in app.error)
    assert app.session_state.current_run_id is None


def test_gui_results_page_is_reachable_without_calculation() -> None:
    app = AppTest.from_file(str(APP_PATH)).run()
    app.switch_page("pages/results.py").run()

    assert not app.exception
    assert app.title[0].value == "Résultats et analyses"
    assert app.warning[0].value.startswith("Aucun résultat")


def test_gui_results_page_handles_missing_baseline_without_exception(
    tmp_path: Path,
) -> None:
    run = tmp_path / "missing-baseline"
    copytree(REFERENCE, run)
    comparison = pd.read_csv(run / "comparison.csv")
    comparison.loc[comparison["kind"].str.startswith("baseline_"), "kind"] = "reference"
    comparison.to_csv(run / "comparison.csv", index=False)

    app = AppTest.from_file(str(APP_PATH)).run()
    app.session_state.current_run_id = run.name
    app.session_state.current_output_dir = str(run)
    app.switch_page("pages/results.py").run()

    assert not app.exception
    assert any("Impossible de charger cette source" in item.value for item in app.error)
    assert any(
        "exactement une baseline" in item.value
        for item in app.get("code")
    )


def test_gui_history_page_stays_neutral_without_loaded_source() -> None:
    app = AppTest.from_file(str(APP_PATH)).run()
    app.switch_page("pages/history.py").run()

    assert not app.exception
    assert app.title[0].value == "Historique"


def test_gui_history_has_no_source_by_default() -> None:
    app = AppTest.from_file(str(APP_PATH)).run()
    app.switch_page("pages/history.py").run()
    assert not app.exception
    assert not app.selectbox
    assert any("Aucun run complet" in item.value for item in app.warning)


def test_gui_history_labels_legacy_baseline_as_historical_fallback(
    legacy_baseline_run_fixture: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        ResultService,
        "discover_loadable_runs",
        classmethod(lambda cls, root: [legacy_baseline_run_fixture]),
    )
    app = AppTest.from_file(str(APP_PATH)).run()
    app.switch_page("pages/history.py").run()

    assert not app.exception
    assert len(app.dataframe) >= 1
    history_frame = app.dataframe[0].value
    assert (
        history_frame.iloc[0]["Baseline"]
        == "Baseline de repli historique : plus proche voisin"
    )


def test_gui_history_warns_when_runs_use_different_baselines(
    tmp_path: Path,
    legacy_baseline_run_fixture: Path,
    monkeypatch,
) -> None:
    official_run = tmp_path / "official-run"
    copytree(REFERENCE, official_run)
    monkeypatch.setattr(
        ResultService,
        "discover_loadable_runs",
        classmethod(lambda cls, root: [official_run, legacy_baseline_run_fixture]),
    )
    app = AppTest.from_file(str(APP_PATH)).run()
    app.switch_page("pages/history.py").run()

    assert not app.exception
    assert any(
        "Baselines différentes" in item.value
        for item in app.warning
    )


def test_gui_loaded_run_is_not_marked_as_demo() -> None:
    app = AppTest.from_file(str(APP_PATH)).run()
    app.session_state.current_run_id = REFERENCE.name
    app.session_state.current_output_dir = str(REFERENCE)
    app.switch_page("pages/results.py").run()
    assert not app.exception
    assert app.session_state.demo_mode is False
    assert not any("Mode présentation guidée actif" in item.value for item in app.info)


def test_gui_results_reference_renders_metric_groups() -> None:
    app = AppTest.from_file(str(APP_PATH)).run()
    app.session_state.current_run_id = REFERENCE.name
    app.session_state.current_output_dir = str(REFERENCE)
    app.session_state.last_validation_status = "WARN"
    app.session_state.demo_mode = False
    app.switch_page("pages/results.py").run()

    assert not app.exception
    assert [tab.label for tab in app.tabs] == [
        "Scène 3D",
        "Trajectoires",
        "Profils cinématiques",
        "Couverture WFW",
        "Pareto",
        "Analyse & comparaison",
        "Validation",
    ]
    assert not any(tab.label == "Décision" for tab in app.tabs)
    metric_labels = [metric.label for metric in app.metric]
    assert "Contrôles automatiques" not in metric_labels
    assert "Amélioration vs baseline" not in metric_labels
    assert "Gain temps minimal" not in metric_labels
    assert "Gain énergie minimal" not in metric_labels
    assert "Points retenus" in metric_labels
    assert "Solutions non dominées" in metric_labels
    assert "Artefacts" in metric_labels
    assert any(
        checkbox.label == "Baseline : zigzag"
        for checkbox in app.checkbox
    )
    strategy_select = next(
        selectbox
        for selectbox in app.selectbox
        if selectbox.label == "Stratégie affichée dans les vues liées"
    )
    assert strategy_select.options == [
        "Trajectoire compromis",
        "Trajectoire énergie optimale",
        "Trajectoire temps optimal",
    ]
    assert not any("Mode présentation guidée actif" in item.value for item in app.info)
    assert any(expander.label == "Preuves techniques" for expander in app.expander)
    assert any(expander.label == "Téléchargements ciblés" for expander in app.expander)
    download_labels = [button.label for button in app.download_button]
    assert "Trajectoire sélectionnée" in download_labels
    assert "Comparaison baseline" in download_labels
    assert "Image du front Pareto" in download_labels
    assert "Télécharger le rapport" in download_labels
    assert "Télécharger le rapport jury" not in download_labels
    assert any(
        selectbox.label == "Stratégie affichée dans les vues liées"
        for selectbox in app.selectbox
    )
    assert not any("Couverture & coûts" in item.value for item in app.subheader)
    assert not any(
        "Résultats statistiques de la matrice des transitions" in item.value
        for item in app.subheader
    )
    wfw_filter = next(radio for radio in app.radio if radio.label == "Afficher")
    assert wfw_filter.options == ["Tous les points", "Points retenus", "Points rejetés"]
    assert not any("Résumé des trajectoires" in item.value for item in app.subheader)
    assert not any("aide de présentation" in item.value for item in app.markdown)
    captions = [item.value for item in app.caption]
    assert not any("projection XY de la trajectoire sélectionnée" in value for value in captions)
    assert not any("profil temporel de la stratégie sélectionnée" in value for value in captions)
    assert not any("couverture WFW des points étudiés" in value for value in captions)
    assert not any("solution non dominée" in value for value in captions)
    assert any("Gains relatifs de temps et d’énergie" in value for value in captions)
    assert not any("Ces contrôles décrivent l’état technique" in value for value in captions)
    assert [metric.label for metric in app.metric].count("PASS") == 1
    assert [metric.label for metric in app.metric].count("WARN") == 1
    assert [metric.label for metric in app.metric].count("FAIL") == 1


def test_gui_creates_snapshot_only_after_explicit_request(monkeypatch) -> None:
    calls: list[tuple[Path, str]] = []
    target = Path("data/snapshots/test-created")

    monkeypatch.setattr(
        SnapshotService,
        "is_local_run_path",
        staticmethod(lambda run_dir: True),
    )
    monkeypatch.setattr(
        SnapshotService,
        "create_snapshot",
        staticmethod(
            lambda run_dir, name: (calls.append((run_dir, name)) or target)
        ),
    )
    app = AppTest.from_file(str(APP_PATH)).run()
    app.session_state.current_run_id = REFERENCE.name
    app.session_state.current_output_dir = str(REFERENCE)
    app.switch_page("pages/results.py").run()

    assert not app.exception
    assert calls == []
    assert any(item.label == "Nom du snapshot" for item in app.text_input)
    create_button = next(
        button for button in app.button if button.label == "Créer le snapshot"
    )
    create_button.click().run()

    assert not app.exception
    assert calls == [(REFERENCE, app.session_state[f"snapshot_name_{REFERENCE.name}"])]
    assert any("Snapshot créé et vérifié" in item.value for item in app.success)


def test_gui_home_can_load_a_snapshot_explicitly(
    tmp_path: Path,
    monkeypatch,
) -> None:
    snapshot = tmp_path / "snapshots" / "snapshot-example"
    copytree(REFERENCE, snapshot)
    monkeypatch.setattr(
        ResultService,
        "discover_snapshots",
        classmethod(lambda cls, root: [snapshot]),
    )
    app = AppTest.from_file(str(APP_PATH)).run()
    app.switch_page("pages/home.py").run()
    source_selector = next(
        selectbox for selectbox in app.selectbox
        if selectbox.label == "Source à afficher"
    )

    assert "Snapshot : snapshot-example" in source_selector.options
    source_selector.set_value("Snapshot : snapshot-example").run()
    next(button for button in app.button if button.label == "Charger cette source").click().run()

    assert not app.exception
    assert app.session_state.current_run_id == "snapshot-example"
    assert app.session_state.current_output_dir == str(snapshot)


def test_results_zip_is_built_only_after_explicit_request(monkeypatch) -> None:
    calls: list[Path] = []

    def build_zip(output_dir: Path) -> bytes:
        calls.append(output_dir)
        return b"test-zip"

    monkeypatch.setattr(ExportService, "zip_run", staticmethod(build_zip))
    app = AppTest.from_file(str(APP_PATH)).run()
    app.session_state.current_run_id = REFERENCE.name
    app.session_state.current_output_dir = str(REFERENCE)
    app.switch_page("pages/results.py").run()

    assert not app.exception
    assert calls == []
    prepare = next(
        button
        for button in app.button
        if button.label == "Préparer l’archive complète (ZIP)"
    )
    prepare.click().run()

    assert not app.exception
    assert calls == [REFERENCE]
    assert any(
        button.label == "Télécharger l’archive ZIP préparée"
        for button in app.get("download_button")
    )


def test_gui_results_labels_legacy_baseline_as_historical_fallback(
    legacy_baseline_run_fixture: Path,
) -> None:
    app = AppTest.from_file(str(APP_PATH)).run()
    app.session_state.current_run_id = legacy_baseline_run_fixture.name
    app.session_state.current_output_dir = str(legacy_baseline_run_fixture)
    app.switch_page("pages/results.py").run()

    assert not app.exception
    fallback_label = "Baseline de repli historique : plus proche voisin"
    assert any(checkbox.label == fallback_label for checkbox in app.checkbox)


def test_gui_loaded_source_can_return_to_neutral_state() -> None:
    app = AppTest.from_file(str(APP_PATH)).run()
    app.session_state.current_run_id = REFERENCE.name
    app.session_state.current_output_dir = str(REFERENCE)
    app.switch_page("pages/home.py").run()
    next(button for button in app.button if button.label == "Rafraîchir la source").click().run()

    assert not app.exception
    assert app.session_state.current_run_id is None
    assert app.session_state.current_output_dir is None


def test_trajectory_labels_are_user_facing_and_stable() -> None:
    from visualization.labels import kind_label

    assert kind_label("compromise") == "Trajectoire compromis"
    assert kind_label("time_opt") == "Trajectoire temps optimal"
    assert kind_label("energy_opt") == "Trajectoire énergie optimale"
