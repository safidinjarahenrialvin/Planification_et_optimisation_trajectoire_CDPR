"""
Tests unitaires — BLOC 1 (RobotModel)
======================================

Référence : contrat géométrique du modèle robot SP2 (BLOC 1).
Note : la seule différence avec la v3.0 concerne T6, dont les valeurs
       numériques sont recalculées pour la nouvelle géométrie (plateforme
       700×560 mm, masse 0.417 kg, bornes [1, 58] N).
"""
from __future__ import annotations

import numpy as np
import pytest

from src.config import Config
from src.robot_model import RobotModel


@pytest.fixture
def cfg() -> Config:
    return Config()


@pytest.fixture
def model(cfg: Config) -> RobotModel:
    return RobotModel(cfg)


@pytest.fixture
def p_center(cfg: Config) -> np.ndarray:
    """Point central de référence : (0, 0, z_absolu(R0))."""
    return np.array([0.0, 0.0, cfg.z_absolu_r0])


# --- T1 : formes ---------------------------------------------------
def test_shapes(model: RobotModel, p_center: np.ndarray) -> None:
    out = model.evaluate(p_center)
    assert out["U"].shape == (8, 3)
    assert out["L"].shape == (8,)
    assert out["W"].shape == (6, 8)
    assert out["B"].shape == (3, 8)


def test_finiteness(model: RobotModel, p_center: np.ndarray) -> None:
    out = model.evaluate(p_center)
    assert np.all(np.isfinite(out["U"]))
    assert np.all(np.isfinite(out["L"]))
    assert np.all(np.isfinite(out["W"]))


# --- T2 : unité et positivité ---------------------------------------
def test_unit_norm(model: RobotModel, p_center: np.ndarray) -> None:
    U = model.cable_vectors(p_center)
    norms = np.linalg.norm(U, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-12)


def test_lengths_positive(model: RobotModel, p_center: np.ndarray) -> None:
    L = model.cable_lengths(p_center)
    assert np.all(L > 0.1)


# --- T3 : symétrie de W au centre ------------------------------------
def test_W_symmetry_structure(model: RobotModel, p_center: np.ndarray) -> None:
    W = model.structure_matrix(p_center)

    U_z_top = W[2, 0:4]
    U_z_bot = W[2, 4:8]
    assert np.allclose(U_z_top, U_z_top[0], atol=1e-12)
    assert np.allclose(U_z_bot, U_z_bot[0], atol=1e-12)
    assert U_z_top[0] > 0
    assert U_z_bot[0] < 0

    assert abs(W[0, 0:4].sum()) < 1e-12
    assert abs(W[1, 0:4].sum()) < 1e-12
    assert abs(W[0, 4:8].sum()) < 1e-12
    assert abs(W[1, 4:8].sum()) < 1e-12

    assert abs(W[3, :].sum()) < 1e-12
    assert abs(W[4, :].sum()) < 1e-12


# --- T4 : rang 6 ----------------------------------------------------
def test_W_rank_6_at_center(model: RobotModel, p_center: np.ndarray) -> None:
    W = model.structure_matrix(p_center)
    rank = np.linalg.matrix_rank(W, tol=1e-9)
    assert rank == 6, f"W doit être de rang 6, rang obtenu : {rank}"


# --- T5 : convention de signe ----------------------------------------
def test_alternative_formulation_is_negative(
    model: RobotModel, p_center: np.ndarray
) -> None:
    B = model.attach_positions(p_center)
    A = model.A

    v_A = B - A
    L_A = np.linalg.norm(v_A, axis=0)
    U_A = (v_A / L_A).T
    moments_A = np.cross(B.T, U_A)
    W_A = np.vstack([U_A.T, moments_A.T])

    W_B = model.structure_matrix(p_center)
    assert np.allclose(W_A, -W_B, atol=1e-12)


# --- T6 : équilibre statique au centre --------------------------------
def test_central_equilibrium_self_consistent(
    cfg: Config, model: RobotModel, p_center: np.ndarray
) -> None:
    """
    Vérifie l'existence de la famille de solutions symétriques T ∈ [1, 58]^8
    satisfaisant l'équilibre statique au point central.

    Paramètres v3.1 : plateforme 700×560 mm, masse 0.417 kg,
    T_min=1.0 N, T_max=58.0 N.
    """
    W = model.structure_matrix(p_center)
    g = 9.81
    mg = cfg.masse_kg * g

    K_top = W[2, 0:4].sum()
    K_bot = W[2, 4:8].sum()

    assert K_top > 0
    assert K_bot < 0

    # Cas 1 : T_bot = T_min
    T_bot = cfg.T_min
    T_top = (mg - K_bot * T_bot) / K_top
    assert cfg.T_min <= T_top <= cfg.T_max
    # Vérification de l'équilibre (dynamique, plateforme-agnostique)
    T = np.zeros(8)
    T[0:4] = T_top
    T[4:8] = T_bot
    F_ext = np.array([0.0, 0.0, -mg, 0.0, 0.0, 0.0])
    assert np.allclose(W @ T + F_ext, 0.0, atol=1e-9)

    # Vérification finale : résidu d'équilibre nul pour T symétrique
    T = np.zeros(8)
    T[0:4] = T_top
    T[4:8] = T_bot
    F_ext = np.array([0.0, 0.0, -mg, 0.0, 0.0, 0.0])
    residual = W @ T + F_ext
    assert np.allclose(residual, 0.0, atol=1e-9)


# --- T7 : impression diagnostique (n'échoue jamais) ------------------
def test_print_W_at_center(
    model: RobotModel, p_center: np.ndarray, capsys: pytest.CaptureFixture
) -> None:
    W = model.structure_matrix(p_center)
    with capsys.disabled():
        print("\n=== W au point central (0, 0, 0.45) — v3.1 ===")
        print("      " + "  ".join(f"c{k+1:>6d}" for k in range(8)))
        labels = ["U_x", "U_y", "U_z", "M_x", "M_y", "M_z"]
        for i, lbl in enumerate(labels):
            row = "  ".join(f"{W[i, j]:+.4f}" for j in range(8))
            print(f"{lbl:>3s}   {row}")
        print("=" * 46)
