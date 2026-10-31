"""
BLOC 2 — Cinématique (Kinematics)
==================================

Référence : contrat cinématique du pipeline SP2 (BLOC 2).
Portée    : conversions pose ↔ longueurs de câbles, dans les deux sens.

Sens inverse (pose → longueurs) : formule fermée, déterministe.
    L_i = ‖A_i − B_i(p)‖, pour i = 1..8
    Implémenté directement dans RobotModel.cable_lengths(), exposé ici
    comme façade pour respecter la séparation BLOC 1 / BLOC 2.

Sens direct (longueurs → pose) : résolution numérique d'un système
sur-déterminé 8 équations / 3 inconnues.
    min_p ‖L(p) − L_target‖²
    Résolu par scipy.optimize.least_squares (méthode 'trf' par défaut,
    robuste aux résidus non linéaires et aux bornes optionnelles).

Non-unicité possible
--------------------
L'intersection de 8 sphères en 3D admet en général plusieurs solutions.
Autour du centre de la zone d'étude, la solution est localement unique et
le solveur converge vers elle depuis un point de départ proche (centre ou
pose connue). Le paramètre `p0` est exposé à l'appelant pour cette raison.

Test de non-régression (§7 BLOC 2)
-----------------------------------
Le critère spécifié est :  inverse(direct(L)) ≈ L  à 1e-6 m près.
Autrement dit : forward(inverse(L_target)) ≈ L_target — la direction
bien posée. C'est cette composition qui est vérifiée en priorité par les
tests. La direction inverse (p → L → p') est aussi testée, mais seulement
en partant de points proches du centre, où l'unicité locale est garantie.
"""
from __future__ import annotations

from typing import Optional, Tuple
import warnings
import numpy as np
from scipy.optimize import least_squares

from src.robot_model import RobotModel

# Tolérances du solveur (renvoyées au code — §9.2).
_LS_XTOL: float = 1e-12
_LS_FTOL: float = 1e-12
_LS_GTOL: float = 1e-12

# Tolérance de succès sur le résidu final, en mètres.
_RESIDUAL_TOL: float = 1e-6


class Kinematics:
    """
    Façade cinématique au-dessus de RobotModel.

    Nomenclature (D-BLOC2-03)
    -------------------------
    Les noms de méthodes sont EXPLICITES pour éviter la confusion entre
    la convention robotique classique (forward = actionneurs → task)
    et l'usage fait ici :

        pose_to_lengths(p)  →  L    (MGI : pose → longueurs câbles)
        lengths_to_pose(L)  →  p    (MGD : longueurs câbles → pose)

    Les anciens noms `forward` / `inverse` sont conservés comme aliases
    dépréciés — ils émettent un DeprecationWarning. Ils étaient inversés
    par rapport à la convention académique (source de confusion).
    """

    def __init__(self, robot: RobotModel) -> None:
        self.robot = robot

    # ------------------------------------------------------------------
    # Pose → longueurs (formule fermée)
    # ------------------------------------------------------------------
    def pose_to_lengths(self, p: np.ndarray) -> np.ndarray:
        """Longueurs de câble L ∈ ℝ⁸ pour une pose p ∈ ℝ³ donnée."""
        return self.robot.cable_lengths(p)

    # ------------------------------------------------------------------
    # Longueurs → pose (résolution numérique)
    # ------------------------------------------------------------------
    def lengths_to_pose(
        self,
        L_target: np.ndarray,
        p0: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, bool, float]:
        """
        Estime la pose p ∈ ℝ³ réalisant les longueurs L_target ∈ ℝ⁸.

        Résout les huit contraintes de longueur par moindres carrés et retourne
        la pose estimée, un indicateur de convergence et la norme du résidu.
        """
        L_target = np.asarray(L_target, dtype=float)
        if L_target.shape != (8,):
            raise ValueError(
                f"L_target doit être de shape (8,), reçu {L_target.shape}."
            )
        if p0 is None:
            p0 = np.array([0.0, 0.0, self.robot.config.z_absolu_r0])
        p0 = np.asarray(p0, dtype=float)
        if p0.shape != (3,):
            raise ValueError(f"p0 doit être de shape (3,), reçu {p0.shape}.")

        def _residual(p: np.ndarray) -> np.ndarray:
            # Si p est singulier (confondu avec un ancrage),
            # cable_lengths lève ValueError. On renvoie un résidu
            # non-fini pour que least_squares considère cette pose
            # comme non viable et s'en éloigne naturellement, sans
            # crasher (D-BLOC2-04).
            try:
                return self.robot.cable_lengths(p) - L_target
            except ValueError:
                return np.full(8, np.inf)

        result = least_squares(
            _residual,
            p0,
            method="trf",
            xtol=_LS_XTOL,
            ftol=_LS_FTOL,
            gtol=_LS_GTOL,
        )
        residual_norm = float(np.linalg.norm(result.fun))
        success = (
            result.success
            and residual_norm < _RESIDUAL_TOL
            and np.all(np.isfinite(result.x))
        )
        return result.x, success, residual_norm

    # ------------------------------------------------------------------
    # Aliases dépréciés (rétrocompatibilité)
    # ------------------------------------------------------------------
    def forward(self, p: np.ndarray) -> np.ndarray:
        """
        DEPRECATED (D-BLOC2-03) : utiliser `pose_to_lengths(p)`.

        Nom historique — la convention robotique classique réserve
        `forward` à l'opération actionneurs → task, ce qui est l'inverse
        de ce que cette méthode fait.
        """
        warnings.warn(
            "Kinematics.forward() est déprécié — utiliser "
            "pose_to_lengths(). "
            "Le nom `forward` est réservé à la convention robotique "
            "(actionneurs → pose).",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.pose_to_lengths(p)

    def inverse(
        self,
        L_target: np.ndarray,
        p0: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, bool, float]:
        """
        DEPRECATED (D-BLOC2-03) : utiliser `lengths_to_pose(L, p0)`.
        """
        warnings.warn(
            "Kinematics.inverse() est déprécié — utiliser "
            "lengths_to_pose(). "
            "Le nom `inverse` est réservé à la convention robotique "
            "(pose → actionneurs).",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.lengths_to_pose(L_target, p0=p0)

    # ------------------------------------------------------------------
    # Utilitaire de diagnostic
    # ------------------------------------------------------------------
    def round_trip_L(
        self,
        L_target: np.ndarray,
        p0: Optional[np.ndarray] = None,
    ) -> float:
        """Mesure ‖pose_to_lengths(lengths_to_pose(L)) − L‖₂."""
        p, _, _ = self.lengths_to_pose(L_target, p0=p0)
        return float(np.linalg.norm(self.pose_to_lengths(p) - L_target))
