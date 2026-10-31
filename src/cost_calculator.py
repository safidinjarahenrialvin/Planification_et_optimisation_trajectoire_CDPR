"""
BLOC 6 — Calculatrice de coûts (CostCalculator)
=================================================

Référence : contrat de calcul des coûts du pipeline SP2 (BLOC 6).
Portée    : construire la matrice (N' × N') des coûts temps/énergie entre
            chaque paire de points retenus par BLOC 5 (le centre inclus).

Cœur technique
--------------
  - Temps    : profil LSPB analytique (trapézoïdal ou triangulaire).
  - Énergie  : intégration quasi-statique sur K sous-pas par segment,
               avec résolution d'un QP à norme minimale par sous-pas.

QP à norme minimale par sous-pas
---------------------------------
  min  ½ ‖T‖²
  s.c. W(p)·T = rhs          (rhs = (0, 0, m·g, 0, 0, 0))
       T_min ≤ T ≤ T_max

Stratégie à deux étages :
  1) Fast path : T* = Wᵀ(WWᵀ)⁻¹·rhs  (pseudo-inverse non bornée)
     → si T* ∈ [T_min, T_max], on retourne directement.
  2) Slow path : SLSQP borné, warm-starté par T* ou par le milieu des bornes.
     → si SLSQP échoue, la sous-pose est marquée infaisable.

Le fast path évite SLSQP lorsque la solution non bornée respecte déjà les
limites. Les poses qui ne satisfont pas ces limites passent au solveur SLSQP,
avec vérification indépendante du résidu et des bornes.

Symétrie
--------
Le profil LSPB est symétrique en distance, donc time(i,j) = time(j,i) à la
machine près. L'énergie est symétrique par construction physique (même
travail dans les deux sens à la non-régénération près — hypothèse de travail).
La symétrie est contrôlée par les tests et par le validateur.

Terme stabilisation
-------------------
Séparé de la matrice : BLOC 8 l'ajoute au temps total (N' × T_stab).
Fourni ici via la méthode stabilization_term() pour centraliser la logique.

Format CSV (§6)
---------------
  i, j, distance, time, energy, feasible
  - i, j        : id des points filtrés (ints)
  - distance    : ||p_j − p_i||₂ (m)
  - time        : durée du mouvement LSPB (s)
  - energy      : travail moteur cumulé sur le segment (J)
  - feasible    : 1 si les deux extrémités sont faisables, sinon 0
"""
from __future__ import annotations

import logging
import time as time_module
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from src.config import Config
from src.robot_model import RobotModel

logger = logging.getLogger(__name__)

_G: float = 9.81

# Colonnes figées du CSV de sortie (§6).
_CSV_COLUMNS = ["i", "j", "distance", "time", "energy", "feasible"]

# Nombre de sous-pas par segment (compromis précision/temps de calcul).
_DEFAULT_K = 10

# Tolérance SLSQP.
_SLSQP_FTOL = 1e-10
_SLSQP_MAXITER = 200


class CostCalculator:
    """
    Construit la matrice de coûts (N' × N') pour une liste de points filtrés.
    """

    def __init__(self, config: Config, robot: RobotModel) -> None:
        self.config = config
        self.robot = robot
        self._mg = config.masse_kg * _G
        self._rhs = np.array([0.0, 0.0, self._mg, 0.0, 0.0, 0.0], dtype=float)

    # ------------------------------------------------------------------
    # Temps LSPB
    # ------------------------------------------------------------------
    def lspb_time(self, distance: float) -> float:
        """
        Durée du mouvement LSPB sur une distance donnée.

        Profil trapézoïdal si d ≥ v_max²/a_max, triangulaire sinon.
        Cas dégénéré d=0 → 0 s.
        """
        if distance <= 0.0:
            return 0.0
        v_max = self.config.v_max
        a_max = self.config.a_max
        d_acc = v_max * v_max / (2.0 * a_max)   # distance pour atteindre v_max
        d_full = 2.0 * d_acc                     # aller + freinage
        if distance >= d_full:
            t_acc = v_max / a_max
            t_cruise = (distance - d_full) / v_max
            return 2.0 * t_acc + t_cruise
        # Profil triangulaire : pic de vitesse v_p tel que d = v_p²/a_max
        v_p = np.sqrt(distance * a_max)
        return 2.0 * v_p / a_max

    # ------------------------------------------------------------------
    # QP à norme minimale par sous-pas
    # ------------------------------------------------------------------
    def _solve_tension(
        self,
        W: np.ndarray,
        T0: np.ndarray | None = None,
    ) -> Tuple[np.ndarray | None, bool]:
        """
        Résout min ½‖T‖² s.c. W·T = rhs, T_min ≤ T ≤ T_max.

        Retour
        ------
        (T, success) : tensions (8,) ou None, et booléen.
        """
        T_min = self.config.T_min
        T_max = self.config.T_max

        # --- Fast path : pseudo-inverse ---
        try:
            WtW_inv = np.linalg.inv(W @ W.T)
            T_pinv = W.T @ (WtW_inv @ self._rhs)
            if np.all(T_pinv >= T_min - 1e-12) and np.all(T_pinv <= T_max + 1e-12):
                return T_pinv, True
        except np.linalg.LinAlgError:
            pass

        # --- Slow path : SLSQP borné ---
        if T0 is None:
            T0 = np.full(8, 0.5 * (T_min + T_max))

        res = minimize(
            fun=lambda T: 0.5 * float(T @ T),
            x0=T0,
            jac=lambda T: T,
            method="SLSQP",
            constraints=[{
                "type": "eq",
                "fun": lambda T: W @ T - self._rhs,
                "jac": lambda T: W,
            }],
            bounds=[(T_min, T_max)] * 8,
            options={"ftol": _SLSQP_FTOL, "maxiter": _SLSQP_MAXITER, "disp": False},
        )

        # Vérification indépendante : SLSQP peut retourner success=True
        # avec un résidu d'équilibre non négligeable. On vérifie :
        #   1. l'équilibre W·T = rhs (résidu < 1e-6)
        #   2. les bornes T_min/T_max (marge 1e-6)
        if res.success and res.x is not None:
            T = np.asarray(res.x, dtype=float)
            residual = float(np.linalg.norm(W @ T - self._rhs))
            in_bounds = (
                np.all(T >= T_min - 1e-6) and np.all(T <= T_max + 1e-6)
            )
            if residual < 1e-6 and in_bounds:
                return T, True

        # --- Fallback : retenter depuis le milieu des bornes ---
        # Si le warm-start T0 est un mauvais point (souvent parce qu'il
        # vient d'un sous-pas infaisable), on retente depuis le centre
        # du polytope.
        T_mid = np.full(8, 0.5 * (T_min + T_max))
        if T0 is None or not np.allclose(T0, T_mid):
            res2 = minimize(
                fun=lambda T: 0.5 * float(T @ T),
                x0=T_mid,
                jac=lambda T: T,
                method="SLSQP",
                constraints=[{
                    "type": "eq",
                    "fun": lambda T: W @ T - self._rhs,
                    "jac": lambda T: W,
                }],
                bounds=[(T_min, T_max)] * 8,
                options={"ftol": _SLSQP_FTOL, "maxiter": _SLSQP_MAXITER, "disp": False},
            )
            if res2.success and res2.x is not None:
                T2 = np.asarray(res2.x, dtype=float)
                residual2 = float(np.linalg.norm(W @ T2 - self._rhs))
                in_bounds2 = (
                    np.all(T2 >= T_min - 1e-6) and np.all(T2 <= T_max + 1e-6)
                )
                if residual2 < 1e-6 and in_bounds2:
                    return T2, True

        return None, False

    # ------------------------------------------------------------------
    # Énergie d'un segment
    # ------------------------------------------------------------------

    def _segment_energy(
        self,
        p_i: np.ndarray,
        p_j: np.ndarray,
        K: int,
    ) -> Tuple[float, bool]:
        """
        Énergie cumulée sur un segment en K sous-pas quasi-statiques.

        Évaluation de T AU POINT MILIEU de chaque sous-segment.

        Cette convention est essentielle pour la SYMÉTRIE du résultat :
        - Sens i→j, sous-segment k   → point milieu p_i + ((k+0.5)/K)·Δ
        - Sens j→i, sous-segment k   → point milieu p_j + ((k+0.5)/K)·(−Δ)
                                     = p_i + ((K−k−0.5)/K)·Δ
        Ces deux points coïncident avec le point milieu du sous-segment
        K−1−k dans le sens i→j. Les |dL| correspondants sont identiques.
        Donc E_ij ≡ E_ji à la précision SLSQP près (< 1e-6 J), conforme
        au critère §7 (|E_ij − E_ji| < 1e-3 J).

        Si T était évalué au point DÉPART (k/K), l'asymétrie
        E_ij = Σ T(p_k)·|dL_k|  vs  E_ji = Σ T(p_{k+1})·|dL_k|
        introduirait un écart systématique de l'ordre de 1 % (~0.08 J
        sur 6 J), incompatibe avec le seuil §7.
        """
        # Poses aux bornes des sous-segments (K+1 points)
        alphas = np.linspace(0.0, 1.0, K + 1)
        poses = np.array([p_i + a * (p_j - p_i) for a in alphas])  # (K+1, 3)

        # Longueurs et variations le long du segment
        L_all = np.array([self.robot.cable_lengths(p) for p in poses])
        dL_all = np.diff(L_all, axis=0)  # (K, 8)

        # Poses aux points MILIEUX des sous-segments (K points)
        alphas_mid = (np.arange(K) + 0.5) / K
        poses_mid = np.array([p_i + a * (p_j - p_i) for a in alphas_mid])

        energy = 0.0
        T_prev: np.ndarray | None = None
        for k in range(K):
            W = self.robot.structure_matrix(poses_mid[k])
            T_k, ok = self._solve_tension(W, T0=T_prev)
            if not ok or T_k is None:
                return float("nan"), False
            energy += float(np.sum(T_k * np.abs(dL_all[k])))
            T_prev = T_k

        return energy, True

    # ------------------------------------------------------------------
    # Coût d'une paire
    # ------------------------------------------------------------------
    def _pair_cost(
        self,
        id_i: int,
        p_i: np.ndarray,
        id_j: int,
        p_j: np.ndarray,
        K: int,
    ) -> dict:
        """Calcule les 6 colonnes du CSV pour une paire (i, j)."""
        distance = float(np.linalg.norm(p_j - p_i))
        t_motion = self.lspb_time(distance)

        if id_i == id_j:
            # Paire triviale i==j
            return {
                "i": int(id_i), "j": int(id_j),
                "distance": 0.0, "time": 0.0, "energy": 0.0, "feasible": 1,
            }

        energy, ok = self._segment_energy(p_i, p_j, K)
        return {
            "i": int(id_i),
            "j": int(id_j),
            "distance": distance,
            "time": t_motion,
            "energy": energy if ok else float("nan"),
            "feasible": 1 if ok else 0,
        }

    # ------------------------------------------------------------------
    # Construction de la matrice
    # ------------------------------------------------------------------
    def build_matrix(
        self,
        points: pd.DataFrame | Path | str,
        K: int = _DEFAULT_K,
        verbose: bool = True,
    ) -> pd.DataFrame:
        """
        Construit la matrice complète (N' × N') des coûts.

        Paramètres
        ----------
        points : DataFrame ou chemin CSV (colonnes id, x, y, z, ...).
        K      : nombre de sous-pas par segment.
        verbose: log de progression.

        Retour
        ------
        DataFrame avec colonnes i, j, distance, time, energy, feasible.
        """
        df = self._load_points(points)
        n = len(df)
        ids = df["id"].to_numpy(dtype=int)
        xyz = df[["x", "y", "z"]].to_numpy(dtype=float)

        rows = []
        t_start = time_module.perf_counter()
        for a in range(n):
            for b in range(n):
                row = self._pair_cost(ids[a], xyz[a], ids[b], xyz[b], K)
                rows.append(row)
            if verbose and (a + 1) % 10 == 0:
                dt = time_module.perf_counter() - t_start
                logger.info(
                    "CostCalculator : %d/%d lignes traitées (%.1f s écoulées)",
                    a + 1, n, dt,
                )

        matrix = pd.DataFrame(rows, columns=_CSV_COLUMNS)
        # Les colonnes id restent en int
        matrix["i"] = matrix["i"].astype(int)
        matrix["j"] = matrix["j"].astype(int)
        matrix["feasible"] = matrix["feasible"].astype(int)
        return matrix

    # ------------------------------------------------------------------
    # Terme stabilisation
    # ------------------------------------------------------------------
    def stabilization_term(self, n_points: int) -> float:
        """
        Temps total de stabilisation = N' × T_stabilisation (s).
        Consommé par BLOC 8, pas par la matrice elle-même.
        """
        return float(n_points) * float(self.config.T_stabilisation)

    # ------------------------------------------------------------------
    # Sauvegarde
    # ------------------------------------------------------------------
    def save(self, matrix: pd.DataFrame, path: Path | str) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        matrix.to_csv(path, index=False, float_format="%.6e")
        logger.info("Matrice de coûts écrite : %s (%d entrées)", path, len(matrix))
        return path

    # ------------------------------------------------------------------
    # Pipeline complet
    # ------------------------------------------------------------------
    def run(
        self,
        points: pd.DataFrame | Path | str,
        output_dir: Path | str = "data/outputs",
        K: int = _DEFAULT_K,
    ) -> dict:
        """
        Construit la matrice, la sauvegarde, et retourne un dict de chemins
        + métadonnées (dont le terme stabilisation).
        """
        output_dir = Path(output_dir)
        matrix = self.build_matrix(points, K=K)
        csv_path = self.save(matrix, output_dir / "cost_matrix.csv")

        n_points = int(matrix["i"].nunique())
        stab_time = self.stabilization_term(n_points)

        return {
            "csv": csv_path,
            "n_points": n_points,
            "stabilization_time_s": stab_time,
            "n_feasible_pairs": int(matrix["feasible"].sum()),
            "n_infeasible_pairs": int(len(matrix) - matrix["feasible"].sum()),
        }

    # ------------------------------------------------------------------
    # Utilitaires privés
    # ------------------------------------------------------------------
    @staticmethod
    def _load_points(points: pd.DataFrame | Path | str) -> pd.DataFrame:
        if isinstance(points, pd.DataFrame):
            df = points.copy()
        else:
            df = pd.read_csv(Path(points))
        required = ["id", "x", "y", "z"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Colonnes manquantes : {missing}. Attendu : {required}.")
        return df
