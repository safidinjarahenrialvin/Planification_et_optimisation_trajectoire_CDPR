"""
Tests unitaires — BLOC 0 (Config v3.2)
========================================
Référence : contrat de configuration SP2 et variantes legacy.
Défauts : 9×9, esp 0.20 m, bornes ±0.80 m, Z_max 0.86, NSGA 500/1500.
"""
from __future__ import annotations
import logging

import numpy as np
import pytest
from dataclasses import FrozenInstanceError

from src.config import Config

# --- T1 : construction par défaut -------------------------------------
def test_default_config_constructs() -> None:
    assert Config() is not None


# --- T2 : propriétés dérivées de la configuration par défaut ---------
def test_derived_properties_match_v3_2() -> None:
    cfg = Config()
    assert cfg.N == 81                                     # 9 × 9
    assert cfg.z_absolu_sol == pytest.approx(0.65)
    assert cfg.z_absolu_r0 == pytest.approx(0.45)


# --- T3 : immuabilité -------------------------------------------------
def test_config_is_frozen() -> None:
    cfg = Config()
    with pytest.raises(FrozenInstanceError):
        cfg.masse_kg = 1.0  # type: ignore[misc]


# --- T4 : R1 ----------------------------------------------------------
def test_R1_ok() -> None:
    Config(T_min=1.0, T_max=58.0)


def test_R1_fail_equal() -> None:
    with pytest.raises(ValueError, match=r"\[R1\]"):
        Config(T_min=10.0, T_max=10.0)


def test_R1_fail_inverted() -> None:
    with pytest.raises(ValueError, match=r"\[R1\]"):
        Config(T_min=58.0, T_max=1.0)


# --- T5 : R2 ----------------------------------------------------------
def test_R2_ok() -> None:
    Config(x_min=-0.80, x_max=0.80, y_min=-0.80, y_max=0.80)


def test_R2_fail_x_too_large() -> None:
    with pytest.raises(ValueError, match=r"\[R2\]"):
        Config(x_min=-0.80, x_max=1.50, y_min=-0.80, y_max=0.80)


def test_R2_fail_y_too_small() -> None:
    with pytest.raises(ValueError, match=r"\[R2\]"):
        Config(x_min=-0.80, x_max=0.80, y_min=-1.50, y_max=0.80)


# --- T6 : R3 ----------------------------------------------------------
def test_R3_fail_zero_rangs() -> None:
    with pytest.raises(ValueError, match=r"\[R3\]"):
        Config(n_rangs=0, n_colonnes=9)


def test_R3_fail_negative_colonnes() -> None:
    with pytest.raises(ValueError, match=r"\[R3\]"):
        Config(n_rangs=9, n_colonnes=-1)


# --- T7 : R4 ----------------------------------------------------------
def test_R4_ok_default() -> None:
    """Cas nominal v3.2 : 9×9 @ 0.20 m → ±0.80 m = limite exacte."""
    Config(n_rangs=9, n_colonnes=9, esp_x=0.20, esp_y=0.20,
           x_min=-0.80, x_max=0.80, y_min=-0.80, y_max=0.80)


def test_R4_fail_grid_too_wide() -> None:
    """11×11 @ 0.20 m → ±1.00 m > ±0.80 m : doit échouer."""
    with pytest.raises(ValueError, match=r"\[R4\]"):
        Config(n_rangs=11, n_colonnes=11, esp_x=0.20, esp_y=0.20,
               x_min=-0.80, x_max=0.80, y_min=-0.80, y_max=0.80)


# --- T8 : R5 ----------------------------------------------------------
def test_R5_fail() -> None:
    with pytest.raises(ValueError, match=r"\[R5\]"):
        Config(orientation_plateforme="mobile")


# --- T9 : R6 ----------------------------------------------------------
def test_R6_fail_plants_too_tall() -> None:
    with pytest.raises(ValueError, match=r"\[R6\]"):
        Config(hauteur_plants=0.80, z_vol=0.30, offset_r0_sol=0.20,
               z_min=0.00, z_max=0.86)


# --- T10 : R7 ---------------------------------------------------------
def test_R7_fail_not_tuple() -> None:
    with pytest.raises(ValueError, match=r"\[R7\]"):
        Config(fov_camera=[62.2, 48.8])  # type: ignore[arg-type]


# --- T11 : N paramétrique --------------------------------------------
@pytest.mark.parametrize(
    "n, expected_N, expected_esp",
    [
        (3, 9, 0.80),
        (5, 25, 0.40),
        (7, 49, 0.80 / 3.0),
        (9, 81, 0.20),
        (11, 121, 0.16),
    ],
)
def test_with_n_derives_grid(n: int, expected_N: int, expected_esp: float) -> None:
    cfg = Config.with_n(n)
    assert cfg.N == expected_N
    assert cfg.esp_x == pytest.approx(expected_esp)
    assert cfg.esp_y == pytest.approx(expected_esp)
    assert cfg.x_min == pytest.approx(-0.80)
    assert cfg.x_max == pytest.approx(+0.80)
    assert cfg.z_max == pytest.approx(0.86)


@pytest.mark.parametrize(
    "n, expected_pop, expected_gen",
    [
        (3, 30, 100),
        (5, 100, 300),
        (7, 200, 500),
        (9, 500, 1500),
        (11, 800, 2000),
    ],
)
def test_with_n_derives_nsga(n: int, expected_pop: int, expected_gen: int) -> None:
    cfg = Config.with_n(n)
    assert cfg.nsga_pop_size == expected_pop
    assert cfg.nsga_n_gen == expected_gen


def test_with_n_rejects_even() -> None:
    with pytest.raises(ValueError, match="impair"):
        Config.with_n(8)


def test_with_n_rejects_small() -> None:
    with pytest.raises(ValueError, match="impair"):
        Config.with_n(1)


def test_with_n_accepts_overrides() -> None:
    cfg = Config.with_n(9, nsga_pop_size=999, T_max=100.0)
    assert cfg.nsga_pop_size == 999
    assert cfg.T_max == 100.0
    assert cfg.N == 81


# --- T12 : z override --------------------------------------------------
def test_z_override_default_none() -> None:
    cfg = Config()
    assert cfg.z_absolu_r0_override is None
    assert cfg.z_absolu_r0 == pytest.approx(0.45)


def test_z_override_effective() -> None:
    cfg = Config(z_absolu_r0_override=0.60)
    assert cfg.z_absolu_r0 == pytest.approx(0.60)


def test_z_override_out_of_bounds_raises() -> None:
    with pytest.raises(ValueError, match=r"\[R6\]"):
        Config(z_absolu_r0_override=0.95)


def test_z_override_at_bounds_ok() -> None:
    cfg_lo = Config(z_absolu_r0_override=0.00)
    cfg_hi = Config(z_absolu_r0_override=0.86)
    assert cfg_lo.z_absolu_r0 == pytest.approx(0.00)
    assert cfg_hi.z_absolu_r0 == pytest.approx(0.86)


# --- T13 : journal ---------------------------------------------------
def test_log_hypotheses_emits_all(caplog: pytest.LogCaptureFixture) -> None:
    cfg = Config()
    with caplog.at_level(logging.INFO, logger="src.config"):
        cfg.log_hypotheses()
    full_log = "\n".join(rec.message for rec in caplog.records)
    for code in ("B1", "B2", "B3", "B4", "B5"):
        assert code in full_log


# --- T14 : legacy v3.0 et v3.1 ---------------------------------------
def test_legacy_v3_0_preserved() -> None:
    legacy = Config.legacy_v3_0()
    assert legacy.N == 81                                # 9×9
    assert legacy.esp_x == pytest.approx(0.25)
    assert legacy.x_max == pytest.approx(1.00)
    assert legacy.T_max == pytest.approx(4.395)
    assert legacy.masse_kg == pytest.approx(0.385)


def test_legacy_v3_1_preserved() -> None:
    legacy = Config.legacy_v3_1()
    assert legacy.N == 49                                # 7×7
    assert legacy.esp_x == pytest.approx(0.25)
    assert legacy.x_max == pytest.approx(0.75)
    assert legacy.T_max == pytest.approx(58.0)
    assert legacy.masse_kg == pytest.approx(0.417)


def test_v3_2_differs_from_legacy() -> None:
    v3_2 = Config()
    v3_1 = Config.legacy_v3_1()
    assert v3_2.N != v3_1.N                              # 81 vs 49
    assert v3_2.esp_x != v3_1.esp_x                      # 0.20 vs 0.25
    assert v3_2.x_max != v3_1.x_max                      # 0.80 vs 0.75


# --- T15 : mode zero_loss ----------------------------------------------
def test_with_n_zero_loss_bounds() -> None:
    """
    Le mode zero-loss sur 700x560 resserre les bornes à ±0.545 m.
    Note : depuis D-CONFIG-12, zero_loss dépend de la plateforme. Ce
    test cible explicitement la plateforme historique 700x560.
    """
    cfg = Config.with_n(9, platform="700x560", zero_loss=True)
    assert cfg.x_min == pytest.approx(-0.545)
    assert cfg.x_max == pytest.approx(+0.545)
    assert cfg.y_min == pytest.approx(-0.545)
    assert cfg.y_max == pytest.approx(+0.545)
    assert cfg.N == 81
    # Espacement dérivé : 2 × 0.545 / 8 = 0.13625
    assert cfg.esp_x == pytest.approx(0.13625)


@pytest.mark.parametrize("n", [3, 5, 7, 9, 11])
def test_with_n_zero_loss_esp(n: int) -> None:
    """
    Vérifie l'espacement dérivé pour plusieurs n en mode zero_loss sur
    la plateforme historique 700x560 (bornes ±0.545 m).
    """
    cfg = Config.with_n(n, platform="700x560", zero_loss=True)
    expected_esp = 2.0 * 0.545 / (n - 1)
    assert cfg.esp_x == pytest.approx(expected_esp)


def test_with_n_zero_loss_r4_valid() -> None:
    """La Config zero_loss sur 700x560 doit passer R4 (étendue ⊆ limites)."""
    cfg = Config.with_n(9, platform="700x560", zero_loss=True)
    # Étendue = (9-1)/2 × 0.13625 = 0.545 = limite → OK
    half = (cfg.n_colonnes - 1) / 2.0 * cfg.esp_x
    assert half == pytest.approx(0.545)
    assert half <= max(abs(cfg.x_min), abs(cfg.x_max)) + 1e-9


def test_with_n_default_is_not_zero_loss() -> None:
    """Vérifie que zero_loss=False par défaut (rétrocompatibilité)."""
    cfg_default = Config.with_n(9)
    cfg_explicit = Config.with_n(9, zero_loss=False)
    assert cfg_default.x_max == cfg_explicit.x_max == pytest.approx(0.80)


# --- T16 : override manuel des bornes X/Y ------------------------------
def test_with_n_xy_bound_symmetric() -> None:
    """--xy-bound définit les deux axes en même temps."""
    cfg = Config.with_n(9, xy_bound=0.30)
    assert cfg.x_min == pytest.approx(-0.30)
    assert cfg.x_max == pytest.approx(+0.30)
    assert cfg.y_min == pytest.approx(-0.30)
    assert cfg.y_max == pytest.approx(+0.30)
    # Espacement dérivé : 2 × 0.30 / 8 = 0.075
    assert cfg.esp_x == pytest.approx(0.075)
    assert cfg.esp_y == pytest.approx(0.075)


def test_with_n_x_y_bound_asymmetric() -> None:
    """--x-bound et --y-bound permettent une zone rectangulaire."""
    cfg = Config.with_n(9, x_bound=0.20, y_bound=0.40)
    assert cfg.x_max == pytest.approx(+0.20)
    assert cfg.y_max == pytest.approx(+0.40)
    # Espacements différents par axe
    assert cfg.esp_x == pytest.approx(2 * 0.20 / 8)   # 0.05
    assert cfg.esp_y == pytest.approx(2 * 0.40 / 8)   # 0.10


def test_with_n_x_bound_only() -> None:
    """--x-bound seul : Y prend la même valeur."""
    cfg = Config.with_n(9, x_bound=0.50)
    assert cfg.x_max == pytest.approx(+0.50)
    assert cfg.y_max == pytest.approx(+0.50)  # Y suit X par défaut
    assert cfg.esp_x == cfg.esp_y


def test_with_n_y_bound_only() -> None:
    """--y-bound seul : X prend la même valeur."""
    cfg = Config.with_n(9, y_bound=0.60)
    assert cfg.x_max == pytest.approx(+0.60)
    assert cfg.y_max == pytest.approx(+0.60)
    assert cfg.esp_x == cfg.esp_y


def test_with_n_x_y_override_xy_bound() -> None:
    """--x-bound et --y-bound priment sur --xy-bound."""
    cfg = Config.with_n(9, xy_bound=0.50, x_bound=0.20, y_bound=0.30)
    assert cfg.x_max == pytest.approx(+0.20)
    assert cfg.y_max == pytest.approx(+0.30)


def test_with_n_bound_too_small_raises() -> None:
    """Une borne ≤ 0 doit lever."""
    with pytest.raises(ValueError, match="positives"):
        Config.with_n(9, xy_bound=0.0)
    with pytest.raises(ValueError, match="positives"):
        Config.with_n(9, x_bound=-0.10)


def test_with_n_bound_above_anchors_raises() -> None:
    """Une borne > 1.25 m doit être refusée par R2."""
    with pytest.raises(ValueError, match=r"\[R2\]"):
        Config.with_n(9, xy_bound=1.50)


@pytest.mark.parametrize("bound", [0.10, 0.20, 0.30, 0.50])
def test_with_n_custom_bounds_r4_valid(bound: float) -> None:
    """Pour toute borne custom, R4 doit être satisfaite par construction."""
    cfg = Config.with_n(9, xy_bound=bound)
    half = (cfg.n_colonnes - 1) / 2.0 * cfg.esp_x
    assert half == pytest.approx(bound, abs=1e-9)

# --- T17 : tailles de plateforme ---------------------------------------
def test_platform_default_is_300x240() -> None:
    """Défaut v3.5 : plateforme 300×240 → demi-étendues (±0.150, ±0.120)."""
    cfg = Config.with_n(9)
    assert cfg.attaches_B[0, 0] == pytest.approx(-0.150)
    assert cfg.attaches_B[1, 0] == pytest.approx(+0.120)
    # Masse auto-estimée pour 300x240 ≈ 384 g
    assert cfg.masse_kg == pytest.approx(0.384, abs=2e-3)


def test_platform_560x560() -> None:
    """Carré compact : demi-étendues (±0.280, ±0.280)."""
    cfg = Config.with_n(9, platform="560x560")
    # Vérifier les 4 coins (colonnes 0-3 sont le niveau z = +0.025)
    assert cfg.attaches_B[0, 0] == pytest.approx(-0.280)
    assert cfg.attaches_B[0, 1] == pytest.approx(+0.280)
    assert cfg.attaches_B[1, 0] == pytest.approx(+0.280)
    assert cfg.attaches_B[1, 1] == pytest.approx(+0.280)
    # Masse recalculée
    assert cfg.masse_kg < 0.417


def test_platform_630x630() -> None:
    """Carré aire-équivalent : demi-étendues (±0.315, ±0.315)."""
    cfg = Config.with_n(9, platform="630x630")
    assert cfg.attaches_B[0, 0] == pytest.approx(-0.315)
    assert cfg.attaches_B[1, 0] == pytest.approx(+0.315)
    # Masse proche du rectangle (même aire)
    assert cfg.masse_kg == pytest.approx(0.417, abs=5e-3)


def test_platform_invalid_raises() -> None:
    """Chaîne non reconnue → ValueError."""
    with pytest.raises(ValueError, match="invalide"):
        Config.with_n(9, platform="not_a_size")
    with pytest.raises(ValueError, match="invalide"):
        Config.with_n(9, platform="400")   # pas de séparateur
    with pytest.raises(ValueError, match="positives"):
        Config.with_n(9, platform="0x300")  # dimension nulle


@pytest.mark.parametrize("platform", ["700x560", "560x560", "630x630"])
def test_platform_attaches_shape(platform: str) -> None:
    """Vérifie que la matrice attaches_B est toujours (3, 8)."""
    cfg = Config.with_n(9, platform=platform)
    assert cfg.attaches_B.shape == (3, 8)


def test_platform_mass_recalculated() -> None:
    """La masse auto-estimée varie selon les dimensions."""
    cfg_rect = Config.with_n(9, platform="700x560")
    cfg_sq = Config.with_n(9, platform="560x560")
    cfg_eq = Config.with_n(9, platform="630x630")
    assert cfg_sq.masse_kg < cfg_rect.masse_kg
    assert cfg_eq.masse_kg == pytest.approx(cfg_rect.masse_kg, abs=5e-3)


# --- T18 : plateforme — dimension libre et masse custom ----------------
@pytest.mark.parametrize(
    "spec, expected_half_x, expected_half_y",
    [
        ("400x300", 0.200, 0.150),
        ("300X200", 0.150, 0.100),
        ("600×500", 0.300, 0.250),
        ("1000x1000", 0.500, 0.500),
    ],
)
def test_platform_custom_size_string(
    spec: str, expected_half_x: float, expected_half_y: float,
) -> None:
    """Les formats WxH, WXH, W×H en mm sont acceptés."""
    cfg = Config.with_n(9, platform=spec)
    assert cfg.attaches_B[0, 0] == pytest.approx(-expected_half_x)
    assert cfg.attaches_B[1, 0] == pytest.approx(+expected_half_y)


def test_platform_custom_size_param() -> None:
    """platform_size (en m) prend la priorité sur platform (nom)."""
    cfg = Config.with_n(9, platform="560x560", platform_size=(0.20, 0.15))
    assert cfg.attaches_B[0, 0] == pytest.approx(-0.20)
    assert cfg.attaches_B[1, 0] == pytest.approx(+0.15)


def test_platform_custom_size_zero_raises() -> None:
    """platform_size ≤ 0 doit lever."""
    with pytest.raises(ValueError, match="strictement positif"):
        Config.with_n(9, platform_size=(0.0, 0.20))
    with pytest.raises(ValueError, match="strictement positif"):
        Config.with_n(9, platform_size=(0.20, -0.10))


def test_platform_custom_mass() -> None:
    """platform_mass (kg) écrase l'estimation automatique."""
    cfg = Config.with_n(9, platform="560x560", platform_mass=0.500)
    assert cfg.masse_kg == pytest.approx(0.500)


def test_platform_custom_mass_zero_raises() -> None:
    with pytest.raises(ValueError, match="strictement positif"):
        Config.with_n(9, platform_mass=0.0)
    with pytest.raises(ValueError, match="strictement positif"):
        Config.with_n(9, platform_mass=-0.1)


def test_platform_custom_mass_priority() -> None:
    """platform_mass > auto-estimation."""
    cfg_auto = Config.with_n(9, platform="560x560")
    cfg_custom = Config.with_n(9, platform="560x560", platform_mass=0.500)
    assert cfg_auto.masse_kg != cfg_custom.masse_kg
    assert cfg_custom.masse_kg == pytest.approx(0.500)


def test_platform_named_aliases_work() -> None:
    """Tous les noms canoniques restent accessibles."""
    for name, (hx, hy) in {
        "300x240": (0.150, 0.120),
        "250x200": (0.125, 0.100),
        "700x560": (0.350, 0.280),
        "560x560": (0.280, 0.280),
        "630x630": (0.315, 0.315),
    }.items():
        cfg = Config.with_n(9, platform=name)
        assert cfg.attaches_B[0, 0] == pytest.approx(-hx)
        assert cfg.attaches_B[1, 0] == pytest.approx(+hy)


# --- T19 : garde-fou singularité plateforme carrée ---------------------
def test_square_platform_warns(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Une plateforme carrée émet un WARNING sur la singularité W."""
    import logging
    with caplog.at_level(logging.WARNING, logger="src.config"):
        Config.with_n(9, platform="560x560")
    assert any(
        "carrée" in rec.message and "singulière" in rec.message
        for rec in caplog.records
    )


def test_rectangular_platform_no_warn(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Une plateforme rectangulaire n'émet aucun WARNING."""
    import logging
    with caplog.at_level(logging.WARNING, logger="src.config"):
        Config.with_n(9, platform="700x560")
    assert not any(
        "carrée" in rec.message and "singulière" in rec.message
        for rec in caplog.records
    )


def test_named_aliases_still_work_but_warn_if_square() -> None:
    """Les noms connus restent acceptés pour compatibilité tests."""
    # Rectangle : pas de warning attendu
    cfg_rect = Config.with_n(9, platform="700x560")
    assert cfg_rect.attaches_B[0, 0] == pytest.approx(-0.350)
    # Carré : accepté mais signalé (le warning est testé ci-dessus)
    cfg_sq = Config.with_n(9, platform="630x630")
    assert cfg_sq.attaches_B[0, 0] == pytest.approx(-0.315)


def test_default_platform_is_small() -> None:
    """Le défaut doit être la petite plateforme M1 (300×240)."""
    cfg = Config.with_n(9)
    # Vérification directe contre la constante du module
    from src.config import _PLATFORM_MAP
    assert _PLATFORM_MAP["300x240"] == (0.150, 0.120)
    # Vérification via attaches_B
    assert abs(cfg.attaches_B[0, 0]) == pytest.approx(0.150)
    assert abs(cfg.attaches_B[1, 0]) == pytest.approx(0.120)

# --- T20 : zero_loss par plateforme ----------------------------------
def test_zero_loss_per_platform_300x240() -> None:
    """zero_loss sur 300x240 utilise les bornes calibrées (0.40, 0.24)."""
    cfg = Config.with_n(9, platform="300x240", zero_loss=True)
    assert cfg.x_max == pytest.approx(+0.400)
    assert cfg.y_max == pytest.approx(+0.240)
    # Espacements dérivés par axe
    assert cfg.esp_x == pytest.approx(2 * 0.400 / 8)
    assert cfg.esp_y == pytest.approx(2 * 0.240 / 8)


def test_zero_loss_per_platform_700x560_unchanged() -> None:
    """zero_loss sur 700x560 reste à l'ancienne valeur 0.545."""
    cfg = Config.with_n(9, platform="700x560", zero_loss=True)
    assert cfg.x_max == pytest.approx(+0.545)
    assert cfg.y_max == pytest.approx(+0.545)


def test_zero_loss_per_platform_250x200() -> None:
    cfg = Config.with_n(9, platform="250x200", zero_loss=True)
    assert cfg.x_max == pytest.approx(+0.280)
    assert cfg.y_max == pytest.approx(+0.280)


def test_zero_loss_per_platform_200x160() -> None:
    cfg = Config.with_n(9, platform="200x160", zero_loss=True)
    assert cfg.x_max == pytest.approx(+0.090)
    assert cfg.y_max == pytest.approx(+0.090)


def test_zero_loss_unknown_platform_falls_back(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Plateforme absente de la table → warning + fallback 0.545."""
    import logging
    with caplog.at_level(logging.WARNING, logger="src.config"):
        cfg = Config.with_n(9, platform="450x360", zero_loss=True)
    assert cfg.x_max == pytest.approx(+0.545)
    assert any(
        "absente de _ZERO_LOSS_BY_PLATFORM" in rec.message
        for rec in caplog.records
    )


def test_zero_loss_override_takes_priority() -> None:
    """--x-bound/--y-bound écrasent zero_loss."""
    cfg = Config.with_n(
        9, platform="300x240", zero_loss=True,
        x_bound=0.20, y_bound=0.15,
    )
    assert cfg.x_max == pytest.approx(+0.20)
    assert cfg.y_max == pytest.approx(+0.15)


def test_zero_loss_xy_bound_takes_priority() -> None:
    """--xy-bound écrase zero_loss."""
    cfg = Config.with_n(
        9, platform="300x240", zero_loss=True, xy_bound=0.25,
    )
    assert cfg.x_max == pytest.approx(+0.25)
    assert cfg.y_max == pytest.approx(+0.25)


# --- T21 : cohérence DEFAULT_PLATFORM (D-CONFIG-13) --------------------
def test_default_platform_constant_exists() -> None:
    """DEFAULT_PLATFORM doit être défini et référencé dans _PLATFORM_MAP."""
    from src.config import DEFAULT_PLATFORM, _PLATFORM_MAP
    assert isinstance(DEFAULT_PLATFORM, str)
    assert DEFAULT_PLATFORM in _PLATFORM_MAP


def test_default_platform_matches_with_n_default() -> None:
    """
    Config.with_n() sans argument `platform` doit utiliser DEFAULT_PLATFORM.
    Garantit la cohérence entre la constante publique et le comportement
    réel du constructeur.
    """
    from src.config import DEFAULT_PLATFORM, _PLATFORM_MAP
    cfg = Config.with_n(9)
    hx, hy = _PLATFORM_MAP[DEFAULT_PLATFORM]
    assert abs(cfg.attaches_B[0, 0]) == pytest.approx(hx)
    assert abs(cfg.attaches_B[1, 0]) == pytest.approx(hy)


def test_default_platform_is_reachable_by_name() -> None:
    """Config.with_n(platform=DEFAULT_PLATFORM) doit donner la même config."""
    from src.config import DEFAULT_PLATFORM
    cfg_default = Config.with_n(9)
    cfg_explicit = Config.with_n(9, platform=DEFAULT_PLATFORM)
    assert cfg_default.attaches_B.shape == cfg_explicit.attaches_B.shape
    assert (cfg_default.attaches_B == cfg_explicit.attaches_B).all()
    assert cfg_default.masse_kg == pytest.approx(cfg_explicit.masse_kg)

# --- T22 : cohérence Config() vs with_n(9) ----------------------------
def test_default_config_matches_with_n_9() -> None:
    """
    Config() et Config.with_n(9) doivent produire le même robot.

    Empêche la dérive silencieuse entre les défauts du dataclass et la
    factory `with_n` — piège identifié lors de la revue du 2026-09-17.
    """
    cfg_default = Config()
    cfg_with_n = Config.with_n(9)

    # Attaches identiques
    assert np.allclose(cfg_default.attaches_B, cfg_with_n.attaches_B)

    # Masse identique
    assert cfg_default.masse_kg == pytest.approx(cfg_with_n.masse_kg)

    # Limites et grille
    assert cfg_default.n_rangs == cfg_with_n.n_rangs
    assert cfg_default.n_colonnes == cfg_with_n.n_colonnes
    assert cfg_default.esp_x == pytest.approx(cfg_with_n.esp_x)
    assert cfg_default.esp_y == pytest.approx(cfg_with_n.esp_y)
    assert cfg_default.x_max == pytest.approx(cfg_with_n.x_max)
    assert cfg_default.y_max == pytest.approx(cfg_with_n.y_max)


# --- T23 : règle R8 — cinématique strictement positive ----------------
def test_R8_fail_zero_v_max() -> None:
    """v_max = 0 doit être refusé par R8."""
    with pytest.raises(ValueError, match=r"\[R8\]"):
        Config(v_max=0.0)


def test_R8_fail_negative_v_max() -> None:
    with pytest.raises(ValueError, match=r"\[R8\]"):
        Config(v_max=-0.01)


def test_R8_fail_zero_a_max() -> None:
    """a_max = 0 doit être refusé par R8 (division par zéro en LSPB)."""
    with pytest.raises(ValueError, match=r"\[R8\]"):
        Config(a_max=0.0)


def test_R8_fail_negative_a_max() -> None:
    with pytest.raises(ValueError, match=r"\[R8\]"):
        Config(a_max=-0.01)


def test_R8_ok_default() -> None:
    """Les valeurs par défaut (v_max=0.045, a_max=0.03) passent R8."""
    cfg = Config()
    assert cfg.v_max > 0
    assert cfg.a_max > 0
