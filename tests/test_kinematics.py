"""
Tests unitaires — BLOC 2 (Kinematics)
=======================================

Référence : contrat cinématique SP2 (BLOC 2).

Nomenclature (D-BLOC2-03)
--------------------------
Les méthodes sont nommées explicitement :
  - `pose_to_lengths(p)` : MGI (pose → longueurs)
  - `lengths_to_pose(L)` : MGD (longueurs → pose)

Les aliases historiques `forward` / `inverse` sont testés uniquement
dans `test_forward_alias_deprecated` et `test_inverse_alias_deprecated`.
"""
from __future__ import annotations

import numpy as np
import pytest

from src.config import Config
from src.kinematics import Kinematics
from src.robot_model import RobotModel


@pytest.fixture
def kin() -> Kinematics:
    return Kinematics(RobotModel(Config()))


# ----------------------------------------------------------------------
# T1 — Pose → longueurs : formule fermée
# ----------------------------------------------------------------------
def test_pose_to_lengths_matches_robot_model(kin: Kinematics) -> None:
    """pose_to_lengths(p) doit être strictement égal à cable_lengths(p)."""
    p = np.array([0.1, -0.2, 0.45])
    assert np.array_equal(
        kin.pose_to_lengths(p), kin.robot.cable_lengths(p),
    )


def test_pose_to_lengths_shape(kin: Kinematics) -> None:
    """Sortie de shape (8,)."""
    p = np.array([0.0, 0.0, 0.45])
    L = kin.pose_to_lengths(p)
    assert L.shape == (8,)
    assert np.all(L > 0.0)


# ----------------------------------------------------------------------
# T2 — Critère §7 : round-trip L → p → L
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "p_true",
    [
        (0.00, 0.00, 0.45),   # centre de référence
        (0.50, 0.00, 0.45),   # décalage X
        (0.00, 0.50, 0.45),   # décalage Y
        (0.75, 0.75, 0.45),   # coin grille 9×9
        (-0.75, 0.75, 0.45),  # autre coin
        (0.00, 0.00, 0.20),   # bas de zone (Z_min op.)
        (0.00, 0.00, 0.80),   # haut de zone (Z_max op.)
        (0.50, -0.50, 0.30),  # combinaison XYZ
    ],
)
def test_round_trip_L(kin: Kinematics, p_true: tuple) -> None:
    """
    Test du critère §7 : à partir d'une pose connue, on calcule L_target,
    on inverse, on recalcule L, et on doit retrouver L_target à 1e-6 m.
    """
    p_true = np.array(p_true, dtype=float)
    L_target = kin.pose_to_lengths(p_true)
    residual = kin.round_trip_L(L_target)
    assert residual < 1e-6, (
        f"round-trip L → p → L échoue pour p_true={p_true} : "
        f"résidu={residual:.2e} m"
    )


# ----------------------------------------------------------------------
# T3 — Direction p → L → p (10 poses, proximité centre pour unicité)
# ----------------------------------------------------------------------
def _ten_poses_in_workspace() -> list:
    """10 poses réparties dans l'espace opérationnel, proches du centre."""
    return [
        (0.00,  0.00, 0.45),
        (0.25,  0.25, 0.45),
        (0.25, -0.25, 0.45),
        (-0.25, 0.25, 0.45),
        (-0.25, -0.25, 0.45),
        (0.50,  0.00, 0.45),
        (0.00,  0.50, 0.45),
        (0.00,  0.00, 0.30),
        (0.00,  0.00, 0.60),
        (0.50,  0.50, 0.45),
    ]


def test_lengths_to_pose_recovers_pose(kin: Kinematics) -> None:
    """À partir de L_target calculé en p_true, on doit retrouver p_true."""
    for p_true in _ten_poses_in_workspace():
        p_true_arr = np.array(p_true, dtype=float)
        L_target = kin.pose_to_lengths(p_true_arr)
        p_est, success, res = kin.lengths_to_pose(L_target, p0=p_true_arr)
        assert success, (
            f"lengths_to_pose a échoué pour p_true={p_true}, "
            f"résidu={res:.2e}"
        )
        assert np.linalg.norm(p_est - p_true_arr) < 1e-6, (
            f"lengths_to_pose a convergé vers {p_est} au lieu de "
            f"{p_true_arr} (écart={np.linalg.norm(p_est - p_true_arr):.2e} m)"
        )


def test_lengths_to_pose_from_center_converges(kin: Kinematics) -> None:
    """
    Sensibilité au point de départ : en partant du centre, le solveur doit
    quand même atteindre la bonne solution pour les 10 poses.
    """
    p0 = np.array([0.0, 0.0, 0.45])
    for p_true in _ten_poses_in_workspace():
        p_true_arr = np.array(p_true, dtype=float)
        L_target = kin.pose_to_lengths(p_true_arr)
        p_est, success, res = kin.lengths_to_pose(L_target, p0=p0)
        assert success, (
            f"échec p0=centre pour p_true={p_true}, résidu={res:.2e}"
        )
        assert np.linalg.norm(p_est - p_true_arr) < 1e-6


# ----------------------------------------------------------------------
# T4 — Erreurs d'entrée
# ----------------------------------------------------------------------
def test_lengths_to_pose_rejects_bad_shape(kin: Kinematics) -> None:
    """L_target de shape ≠ (8,) doit être refusé."""
    with pytest.raises(ValueError):
        kin.lengths_to_pose(np.zeros(7))


def test_lengths_to_pose_rejects_bad_p0(kin: Kinematics) -> None:
    """p0 de shape ≠ (3,) doit être refusé."""
    with pytest.raises(ValueError):
        kin.lengths_to_pose(np.ones(8), p0=np.zeros(2))


# ----------------------------------------------------------------------
# T5 — Cohérence avec le W-matrix
# ----------------------------------------------------------------------
def test_lengths_to_pose_yields_same_W(kin: Kinematics) -> None:
    """
    Si deux poses p1, p2 donnent le même L, elles doivent aussi donner
    la même matrice de structure W (à la précision du solveur près).
    """
    p1 = np.array([0.30, -0.20, 0.45])
    L = kin.pose_to_lengths(p1)
    p2, _, _ = kin.lengths_to_pose(L, p0=p1)
    W1 = kin.robot.structure_matrix(p1)
    W2 = kin.robot.structure_matrix(p2)
    assert np.allclose(W1, W2, atol=1e-9)


def test_lengths_to_pose_near_boundary(kin: Kinematics) -> None:
    """Vérifie que les poses proches des limites convergent."""
    for p_true in [(0.75, 0.0, 0.45), (0.0, 0.75, 0.45), (-0.75, -0.75, 0.45)]:
        p_true = np.array(p_true, dtype=float)
        L = kin.pose_to_lengths(p_true)
        p_est, success, _ = kin.lengths_to_pose(L, p0=p_true)
        assert success
        assert np.linalg.norm(p_est - p_true) < 1e-6


# ----------------------------------------------------------------------
# T6 — Aliases dépréciés (D-BLOC2-03)
# ----------------------------------------------------------------------
def test_forward_alias_deprecated(kin: Kinematics) -> None:
    """
    L'alias `forward` émet un DeprecationWarning et délègue à
    `pose_to_lengths`.
    """
    p = np.array([0.1, -0.2, 0.45])
    with pytest.warns(DeprecationWarning, match="pose_to_lengths"):
        L = kin.forward(p)
    assert np.array_equal(L, kin.pose_to_lengths(p))


def test_inverse_alias_deprecated(kin: Kinematics) -> None:
    """
    L'alias `inverse` émet un DeprecationWarning et délègue à
    `lengths_to_pose`.
    """
    p = np.array([0.1, -0.2, 0.45])
    L = kin.pose_to_lengths(p)
    with pytest.warns(DeprecationWarning, match="lengths_to_pose"):
        p_est, _, _ = kin.inverse(L, p0=p)
    assert np.allclose(p_est, p, atol=1e-6)



def test_lengths_to_pose_robust_to_singular_pose(kin: Kinematics) -> None:
    """
    Une cible de longueurs impossible (p0 confondu avec un ancrage)
    ne doit pas faire crasher le solveur — il doit retourner
    success=False au lieu de lever (D-BLOC2-04).
    """
    # Cible incohérente : longueurs = 0 pour un câble, impossible
    L_impossible = np.full(8, 0.001)
    # p0 volontairement très proche d'un ancrage (pose singulière)
    p0_singulier = np.array([-1.249, 1.249, 0.999])
    p_est, success, residual = kin.lengths_to_pose(
        L_impossible, p0=p0_singulier,
    )
    # Le solveur doit retourner success=False sans lever d'exception
    assert not success
    assert residual > 0  # résidu non nul
