"""Page de configuration et d’exécution contrôlée du pipeline SP2."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.controller import (  # noqa: E402
    GuiRunParameters,
    RunHandle,
    RunStatus,
    build_config,
)
from app.state import initialize_session_state  # noqa: E402
from services.configuration_service import ConfigurationService  # noqa: E402
from src.config import Config  # noqa: E402

initialize_session_state()

st.markdown(
    """
    <style>
    /* Le seul bouton primaire de cette page est l'action de lancement. */
    div[data-testid="stButton"] button[kind="primary"] {
        background-color: #0E7490;
        border-color: #0E7490;
        color: #FFFFFF;
        box-shadow: 0 4px 10px rgba(14, 116, 144, 0.20);
    }
    div[data-testid="stButton"] button[kind="primary"]:hover:not(:disabled) {
        background-color: #155E75;
        border-color: #155E75;
        color: #FFFFFF;
        box-shadow: 0 6px 14px rgba(14, 116, 144, 0.28);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

_PROFILES = {
    "Instance courte : 3×3": {
        "n": 3, "pop_size": 30, "n_gen": 100, "duration_seconds": 20,
        "description": "Instance courte destinée à vérifier le parcours complet et les artefacts.",
    },
    "Instance intermédiaire : 5×5": {
        "n": 5, "pop_size": 100, "n_gen": 300, "duration_seconds": 60,
        "description": "Instance intermédiaire pour une démonstration plus représentative.",
    },
    "Intermédiaire : 7×7": {
        "n": 7, "pop_size": 200, "n_gen": 500, "duration_seconds": 150,
        "description": "Instance d’analyse pour explorer une grille plus dense.",
    },
    "Production : 9×9": {
        "n": 9, "pop_size": 500, "n_gen": 1500, "duration_seconds": 300,
        "description": "Configuration nominale pour une analyse plus dense.",
    },
    "Haute résolution : 11×11": {
        "n": 11, "pop_size": 800, "n_gen": 2000, "duration_seconds": 600,
        "description": (
            "Instance exploratoire lourde, à lancer uniquement après validation "
            "du cas nominal."
        ),
    },
}
_PLATFORM_PRESETS = ["300x240", "700x560", "250x200", "200x160"]
_MAX_K = 100
_MAX_POP_SIZE = 2000
_MAX_N_GEN = 5000
_LONG_RUN_SECONDS = 120
_VERY_LONG_RUN_SECONDS = 600


def _estimate_duration_seconds(profile: dict, K: int, pop_size: int, n_gen: int) -> float:
    """Estime le budget à partir d’un profil, sans prétendre prédire le runtime."""
    profile_scale = profile["duration_seconds"]
    optimization_scale = ((pop_size / profile["pop_size"]) * (n_gen / profile["n_gen"])) ** 0.5
    k_scale = (K / 5) ** 0.5
    return profile_scale * optimization_scale * k_scale


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"environ {seconds:.0f} s"
    minutes = seconds / 60
    return f"environ {minutes:.1f} min"


def _build_parameters(
    profile: dict,
    platform: str,
    zero_loss: bool,
    K: int,
    pop_size: int,
    n_gen: int,
    seed: int,
    z_absolu_r0_override: float | None = None,
    platform_mass_kg: float | None = None,
    xy_bound: float | None = None,
    x_bound: float | None = None,
    y_bound: float | None = None,
) -> GuiRunParameters:
    return GuiRunParameters(
        n=int(profile["n"]),
        platform=platform.strip(),
        zero_loss=zero_loss,
        K=int(K),
        pop_size=int(pop_size),
        n_gen=int(n_gen),
        seed=int(seed),
        z_absolu_r0_override=z_absolu_r0_override,
        platform_mass_kg=platform_mass_kg,
        xy_bound=xy_bound,
        x_bound=x_bound,
        y_bound=y_bound,
    )


def _parameter_signature(parameters: GuiRunParameters) -> tuple[object, ...]:
    return (
        parameters.n,
        parameters.platform,
        parameters.zero_loss,
        parameters.K,
        parameters.pop_size,
        parameters.n_gen,
        parameters.seed,
        parameters.z_absolu_r0_override,
        parameters.platform_mass_kg,
        parameters.xy_bound,
        parameters.x_bound,
        parameters.y_bound,
    )


st.title("Paramètres")
st.subheader("Configurer une exécution")
st.caption("Sélectionnez un niveau d’étude, ajustez les paramètres, puis actualisez l’aperçu.")

st.subheader("Choisir le niveau d’étude")
profile_name = st.selectbox(
    "Niveau d’exécution",
    options=list(_PROFILES),
    index=None,
    placeholder="Choisir un profil avant de continuer",
    help="Le profil définit la taille de grille et le budget NSGA-II initial.",
)
profile = _PROFILES.get(profile_name) if profile_name else None
if profile is None:
    st.info(
        "Sélectionnez un niveau d’étude pour afficher les paramètres."
    )
    st.stop()

st.caption(profile["description"])
tab_geometry, tab_bounds, tab_altitude, tab_optimization = st.tabs([
    "Plateforme",
    "Bornes opérationnelles",
    "Altitude R0",
    "Optimisation NSGA-II",
])

with tab_geometry:
    geo_col1, geo_col2 = st.columns(2)
    with geo_col1:
        platform_choice = st.selectbox(
            "Plateforme prédéfinie",
            options=[*_PLATFORM_PRESETS, "Personnalisée"],
            index=0,
            help="Les plateformes connues reprennent les dimensions calibrées du modèle Config.",
        )
    with geo_col2:
        if platform_choice == "Personnalisée":
            platform = st.text_input(
                "Dimensions plateforme (largeur×profondeur, mm)",
                value="400x300",
                help="Format CLI accepté : WxH, par exemple 400x300 ou 600X500.",
            )
        else:
            platform = platform_choice
            st.text_input(
                "Dimensions utilisées (largeur×profondeur, mm)",
                value=platform,
                disabled=True,
            )

    mass_col1, mass_col2 = st.columns([1, 2])
    with mass_col1:
        custom_mass = st.checkbox(
            "Imposer la masse",
            value=False,
            help="Correspond à --platform-mass et remplace l’estimation par dimensions.",
        )
    with mass_col2:
        platform_mass_g = st.number_input(
            "Masse plateforme (g)",
            min_value=0.001,
            value=384.0,
            step=1.0,
            format="%.3f",
            disabled=not custom_mass,
            help="Masse strictement positive. La CLI exprime cette valeur en grammes.",
        )
    platform_mass_kg = float(platform_mass_g) / 1000.0 if custom_mass else None


with tab_bounds:
    bound_mode = st.radio(
        "Mode des bornes X/Y",
        options=[
            "Zero-loss calibré",
            "Bornes standard",
            "Borne symétrique personnalisée",
            "Bornes X/Y personnalisées",
        ],
        horizontal=True,
        index=0,
        help=(
            "Zero-loss correspond à --zero-loss ; les trois autres choix correspondent "
            "aux options --xy-bound, --x-bound et --y-bound."
        ),
    )
    xy_bound = x_bound = y_bound = None
    if bound_mode == "Borne symétrique personnalisée":
        xy_bound = st.number_input(
            "Demi-étendue X = Y (m)",
            min_value=0.001,
            max_value=2.49,
            value=0.400,
            step=0.01,
            format="%.3f",
            help="Correspond à --xy-bound. L’espacement de grille est dérivé automatiquement.",
        )
    elif bound_mode == "Bornes X/Y personnalisées":
        bound_col1, bound_col2 = st.columns(2)
        with bound_col1:
            x_bound = st.number_input(
                "Demi-étendue X (m)",
                min_value=0.001,
                max_value=2.49,
                value=0.400,
                step=0.01,
                format="%.3f",
                help="Correspond à --x-bound.",
            )
        with bound_col2:
            y_bound = st.number_input(
                "Demi-étendue Y (m)",
                min_value=0.001,
                max_value=2.49,
                value=0.240,
                step=0.01,
                format="%.3f",
                help="Correspond à --y-bound.",
            )
    zero_loss = bound_mode == "Zero-loss calibré"

with tab_altitude:
    try:
        altitude_config = Config.with_n(
            int(profile["n"]),
            platform=platform.strip(),
            zero_loss=zero_loss,
            platform_mass=platform_mass_kg,
            xy_bound=xy_bound,
            x_bound=x_bound,
            y_bound=y_bound,
        )
    except (TypeError, ValueError):
        altitude_config = Config.with_n(int(profile["n"]), zero_loss=True)
        st.warning(
            "La plateforme ou les bornes seront validées dans l’aperçu avant tout lancement."
        )

    altitude_mode = st.radio(
        "Mode de calcul de l’altitude de R0",
        options=["Automatique", "Valeur imposée"],
        horizontal=True,
        key="altitude_mode",
        help=(
            "Automatique utilise hauteur des plants + volume de vol − offset R0/sol. "
            "Valeur imposée correspond à --z-absolu."
        ),
    )
    z_absolu_r0_override = None
    z_absolu_r0_value = st.number_input(
        "Altitude absolue de la plateforme R0 (m)",
        min_value=float(altitude_config.z_min),
        max_value=float(altitude_config.z_max),
        value=float(altitude_config.z_absolu_r0),
        step=0.001,
        format="%.3f",
        key="z_absolu_r0_input",
        disabled=altitude_mode == "Automatique",
        help=(
            "En mode automatique, la valeur est calculée. En mode Valeur imposée, "
            f"elle est bornée par z_min={altitude_config.z_min:.3f} m et "
            f"z_max={altitude_config.z_max:.3f} m."
        ),
    )
    if altitude_mode == "Automatique":
        st.caption("Altitude calculée automatiquement à partir du modèle de vol.")
    else:
        z_absolu_r0_override = z_absolu_r0_value
        st.warning(
            "Cette valeur est une hypothèse de configuration ; elle ne valide pas "
            "à elle seule la sécurité mécanique ni la qualité agronomique."
        )


with tab_optimization:
    opt_col1, opt_col2, opt_col3 = st.columns(3)
    with opt_col1:
        K = st.number_input(
            "Sous-pas K",
            min_value=1,
            max_value=_MAX_K,
            value=5,
            step=1,
            help="Correspond à --K.",
        )
    with opt_col2:
        pop_size = st.number_input(
            "Population NSGA-II",
            min_value=2,
            max_value=_MAX_POP_SIZE,
            value=int(profile["pop_size"]),
            step=10,
            help="Correspond à --pop-size.",
        )
    with opt_col3:
        n_gen = st.number_input(
            "Générations NSGA-II",
            min_value=1,
            max_value=_MAX_N_GEN,
            value=int(profile["n_gen"]),
            step=50,
            help="Correspond à --n-gen.",
        )
    seed = st.number_input(
        "Graine reproductible",
        min_value=0,
        max_value=2**31 - 1,
        value=42,
        step=1,
        help="Correspond à --seed.",
    )


current_parameters = _build_parameters(
    profile,
    platform,
    zero_loss,
    int(K),
    int(pop_size),
    int(n_gen),
    int(seed),
    z_absolu_r0_override,
    platform_mass_kg,
    float(xy_bound) if xy_bound is not None else None,
    float(x_bound) if x_bound is not None else None,
    float(y_bound) if y_bound is not None else None,
)
current_signature = _parameter_signature(current_parameters)
preview_is_current = st.session_state.parameter_preview_signature == current_signature

preview_button, launch_button = st.columns(2)
with preview_button:
    refresh_preview = st.button("Actualiser l’aperçu", type="secondary")
with launch_button:
    launch_requested = st.button("Lancer l’exécution sélectionnée", type="primary")

if refresh_preview:
    st.session_state.parameter_preview = current_parameters
    st.session_state.parameter_preview_signature = current_signature
    st.session_state.run_error = None
    preview_is_current = True
    st.success("Aperçu actualisé. Vérifiez-le avant de lancer le calcul.")

if launch_requested:
    st.session_state.configuration_submitted = True
    st.session_state.run_error = None
    st.session_state.run_progress = 0.0
    active_handle = st.session_state.run_handle
    if active_handle is not None and active_handle.is_active():
        st.warning("Une exécution est déjà en cours. Annulez-la avant d’en lancer une autre.")
    elif not preview_is_current:
        st.session_state.run_error = (
            "Actualisez l’aperçu après toute modification avant de lancer le calcul."
        )
        st.error(st.session_state.run_error)
    elif current_parameters.n >= 9 and not st.session_state.get("confirm_long_run", False):
        st.session_state.run_error = (
            "Confirmation obligatoire avant un calcul Production ou Haute résolution."
        )
        st.error(st.session_state.run_error)
    else:
        handle = RunHandle()
        handle.start(current_parameters, Path("data/runs"))
        st.session_state.run_handle = handle
        st.session_state.run_status = RunStatus.RUNNING.value
        st.session_state.run_step = None
        st.info("Exécution démarrée en arrière-plan. Vous pouvez suivre sa progression ci-dessous.")


def _render_run_monitor() -> None:
    """Affiche l’état du worker et rafraîchit uniquement cette zone."""
    handle = st.session_state.run_handle
    if handle is None:
        return
    snapshot = handle.snapshot()
    st.session_state.run_status = snapshot.status.value
    st.session_state.run_progress = snapshot.progress
    st.session_state.run_step = snapshot.step
    if snapshot.status in {RunStatus.PENDING, RunStatus.RUNNING}:
        label = snapshot.step or "Préparation"
        detail = snapshot.step_status or "en attente"
        st.progress(snapshot.progress, text=f"{label} : {detail} ({snapshot.progress:.0%})")
        st.caption(
            "Le suivi se met à jour automatiquement. L’annulation reste disponible "
            "tant que le calcul est en cours."
        )
        if st.button("Annuler l’exécution", type="secondary", key="cancel_run"):
            handle.cancel()
            st.rerun()
    elif snapshot.status is RunStatus.COMPLETED and snapshot.result is not None:
        result = snapshot.result
        st.session_state.run_error = None
        st.progress(1.0, text="Run terminé")
        if st.session_state.current_run_id != snapshot.run_id:
            st.session_state.current_run_id = snapshot.run_id
            st.session_state.current_output_dir = str(result.output_dir)
            st.session_state.last_validation_status = result.validation_status
        st.success(f"Run {snapshot.run_id} terminé. Consultez la page Résultats.")
    elif snapshot.status is RunStatus.CANCELLED:
        st.session_state.run_error = snapshot.error or "annulation demandée"
        st.warning(f"Run annulé proprement : {snapshot.error or 'annulation demandée'}")
        st.caption("Ses artefacts restent exclus des résultats chargeables.")
    elif snapshot.status is RunStatus.FAILED:
        st.session_state.run_error = snapshot.error or "cause inconnue"
        st.error(f"Échec contrôlé du run : {snapshot.error or 'cause inconnue'}")


if hasattr(st, "fragment"):
    _render_run_monitor = st.fragment(run_every="1s")(_render_run_monitor)
_render_run_monitor()

st.divider()
st.subheader("Prévisualisation")
preview_parameters = st.session_state.parameter_preview
if preview_parameters is None or not preview_is_current:
    st.info(
        "L’aperçu est absent ou obsolète. Cliquez sur « Actualiser l’aperçu » "
        "après avoir terminé vos réglages."
    )
else:
    try:
        preview_config = build_config(preview_parameters)
        effective = ConfigurationService.validate(
            preview_config,
            K=preview_parameters.K,
            pop_size=preview_parameters.pop_size,
            n_gen=preview_parameters.n_gen,
            seed=preview_parameters.seed,
        )
        preview = effective.to_dict()
        scientific = preview["scientific"]
        derived = scientific["derived"]
        estimated_seconds = _estimate_duration_seconds(
            profile,
            preview_parameters.K,
            preview_parameters.pop_size,
            preview_parameters.n_gen,
        )
        m1, m2 = st.columns(2)
        with m1:
            st.metric("N points", derived["N"])
        with m2:
            st.metric("Durée indicative", _format_duration(estimated_seconds))
        st.metric("Empreinte", effective.fingerprint)
        altitude_source = (
            "valeur imposée"
            if preview_config.z_absolu_r0_override is not None
            else "calcul automatique"
        )
        m3, m4 = st.columns(2)
        with m3:
            st.metric(
                "Bornes tension",
                f"{preview_config.T_min:.1f} : {preview_config.T_max:.1f} N",
            )
        with m4:
            st.metric(
                "Altitude absolue R0",
                f"{preview_config.z_absolu_r0:.3f} m",
                help=f"Altitude absolue de la plateforme R0 : mode : {altitude_source}.",
            )
        if estimated_seconds >= _VERY_LONG_RUN_SECONDS:
            st.error(
                "Ce réglage est très coûteux selon l’estimation indicative. "
                "Utilisez une machine dédiée et vérifiez le cas nominal avant de lancer."
            )
        elif estimated_seconds >= _LONG_RUN_SECONDS:
            st.warning(
                "Ce réglage peut durer plusieurs minutes. Le run ne démarrera qu’après "
                "confirmation explicite."
            )
        else:
            st.caption(
                "Estimation indicative : elle dépend de la machine et ne remplace pas "
                "une mesure."
            )
        with st.expander("Voir les domaines scientifiques et les unités"):
            st.json({
                "domains": scientific["domains"],
                "derived": scientific["derived"],
                "units": scientific["units"],
            })
    except (TypeError, ValueError) as exc:
        st.error(f"Prévisualisation impossible : {exc}")

if current_parameters.n >= 9:
    st.session_state.confirm_long_run = st.checkbox(
        "Je confirme le lancement d’un calcul long et je conserverai le run produit.",
        value=st.session_state.get("confirm_long_run", False),
    )

if st.session_state.run_error and not launch_requested:
    st.error(f"Dernière erreur : {st.session_state.run_error}")
