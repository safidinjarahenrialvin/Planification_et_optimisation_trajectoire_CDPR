"""
BLOC 3 — WFW (Wrench-Feasible Workspace)
==========================================

Référence : contrat de faisabilité mécanique du pipeline SP2 (BLOC 3).
Portée    : tester, pour une pose p, l'existence d'une distribution de
            tensions T ∈ [T_min, T_max]^8 satisfaisant l'équilibre statique.

Formulation LP (Option A — faisabilité pure)
---------------------------------------------
    min  0ᵀ · T
    s.c. W(p)·T = −F_ext          (6 égalités)
         T_min ≤ T_i ≤ T_max      (16 bornes)

où F_ext = (0, 0, −m·g, 0, 0, 0), donc RHS = −F_ext = (0, 0, +m·g, 0, 0, 0).
Résolu par scipy.optimize.linprog (méthode HiGHS, déterministe et rapide).

Le LP retourne faisable / infaisable, et si faisable une solution T
quelconque dans le polytope (pas nécessairement la solution symétrique —
le polytope est de dimension 2 au centre, donc famille de solutions).

Le bloc accepte n'importe quel ensemble de poses fourni par le générateur
ou par un appelant. Le filtrage et la validation réutilisent le même oracle
LP afin d'éviter deux définitions concurrentes de la faisabilité.

Limites connues
----------------
- Le LP fournit une décision de faisabilité et une distribution de tensions,
    mais pas une marge de robustesse par rapport aux bornes.
- La constante de gravité G = 9.81 m/s² est fixée au niveau module.
  Elle n'apparaît pas dans Config (§2.5) et n'est pas paramétrable.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linprog

from src.config import Config
from src.robot_model import RobotModel

logger = logging.getLogger(__name__)

# Gravité terrestre — constante de travail (non paramétrable dans Config).
_G: float = 9.81

# Résidu maximal toléré pour valider une solution LP comme propre (m).
_RESIDUAL_TOL: float = 1e-6


@dataclass(frozen=True)
class WFWSolution:
    """Résultat d'un test WFW à une pose donnée."""
    feasible: bool
    tensions: np.ndarray | None  # (8,) si feasible, sinon None
    residual: float                 # ‖W(p)·T − rhs‖₂, NaN si infeasible
    status: int                     # code HiGHS (0 = optimal, 2 = infeasible…)
    message: str


class WFW:
    """
    Test de faisabilité en efforts pour un CDPR 8 câbles 6-DOF statique.

    Utilisé par BLOC 5 (filtrage des points) et BLOC 10 (validation,
    rapport de couverture, figure du mémoire).
    """

    def __init__(self, robot: RobotModel, config: Config) -> None:
        self.robot = robot
        self.config = config
        # RHS pré-calculé : −F_ext = (0, 0, +m·g, 0, 0, 0)
        mg = config.masse_kg * _G
        self._rhs = np.array([0.0, 0.0, mg, 0.0, 0.0, 0.0], dtype=float)
        # Bornes uniformes sur les 8 tensions
        self._bounds = [(config.T_min, config.T_max)] * 8

    # ------------------------------------------------------------------
    # Test LP d'une pose unique
    # ------------------------------------------------------------------
    def is_feasible(self, p: np.ndarray) -> WFWSolution:
        """
        Teste l'existence d'une distribution de tensions admissible à la
        pose p ∈ ℝ³ (dans R0).

        Test préalable : rang de W. Si la matrice de structure est
        singulière (rang < 6), le robot ne peut pas contrôler les 6 DOF.
        Aucune distribution de tensions ne peut y remédier — c'est une
        propriété géométrique. Détecté en particulier pour les plateformes
        dont le polygone d'attaches est homothétique à celui des ancrages
        (D-CONFIG-09).

        Retour
        ------
        WFWSolution — objet gelé avec champs :
            feasible : bool
            tensions : (8,) ou None
            residual : ‖W·T − rhs‖₂ si faisable, NaN sinon
            status   : code retour HiGHS (ou -1 si W singulière)
            message  : message retour HiGHS ou diagnostic de singularité
        """
        W = self.robot.structure_matrix(p)

        # --- Test de rang préalable (garde-fou D-CONFIG-09) ---
        rank = int(np.linalg.matrix_rank(W))
        if rank < 6:
            return WFWSolution(
                feasible=False,
                tensions=None,
                residual=float("nan"),
                status=-1,
                message=(
                    f"Matrice W singulière (rang {rank} < 6). Le robot "
                    f"ne peut pas contrôler les 6 DOF à cette pose. "
                    f"Vérifier la géométrie de la plateforme (ratio "
                    f"d'aspect ~1 → singularité structurelle)."
                ),
            )

        # c = 0 : LP de faisabilité pure (tout point faisable est optimal).
        c = np.zeros(8)
        res = linprog(
            c,
            A_eq=W,
            b_eq=self._rhs,
            bounds=self._bounds,
            method="highs",
        )

        # Cas nominal : HiGHS a trouvé une solution.
        if res.status == 0 and res.x is not None:
            T = np.asarray(res.x, dtype=float)
            residual = float(np.linalg.norm(W @ T - self._rhs))
            if residual <= _RESIDUAL_TOL:
                return WFWSolution(
                    feasible=True,
                    tensions=T,
                    residual=residual,
                    status=0,
                    message=str(res.message),
                )
            # Statut 0 mais résidu suspect : on signale et rétrograde.
            logger.warning(
                "LP status=0 mais résidu %.2e > tol à p=%s", residual, p,
            )
            return WFWSolution(
                feasible=False,
                tensions=None,
                residual=residual,
                status=int(res.status),
                message=f"résidu {residual:.2e} > {_RESIDUAL_TOL:.2e}",
            )

        # Statut 2 (infaisable) : comportement attendu hors WFW.
        return WFWSolution(
            feasible=False,
            tensions=None,
            residual=float("nan"),
            status=int(res.status),
            message=str(res.message),
        )

    # ------------------------------------------------------------------
    # Test d'une grille complète
    # ------------------------------------------------------------------
    def check_grid(
        self,
        points: np.ndarray | pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Teste la faisabilité d'un ensemble de N poses.

        Paramètres
        ----------
        points : ndarray (N, 3) ou DataFrame avec colonnes x, y, z.

        Retour
        ------
        DataFrame avec colonnes :
            id, x, y, z, feasible, status, residual, message
        """
        xyz = self._coerce_points(points)
        rows = []
        for i, p in enumerate(xyz):
            sol = self.is_feasible(p)
            rows.append({
                "id": int(i),
                "x": float(p[0]),
                "y": float(p[1]),
                "z": float(p[2]),
                "feasible": bool(sol.feasible),
                "status": int(sol.status),
                "residual": sol.residual if sol.feasible else float("nan"),
                "message": sol.message,
            })
        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Résumé de couverture — utilisé par BLOC 5 et BLOC 10
    # ------------------------------------------------------------------
    @staticmethod
    def coverage_summary(report: pd.DataFrame) -> dict:
        """
        Résume un rapport de couverture.

        Retour
        ------
        dict avec clés :
            n_total, n_feasible, n_rejected, reject_rate
        """
        n_total = len(report)
        n_feasible = int(report["feasible"].sum())
        n_rejected = n_total - n_feasible
        rate = (n_rejected / n_total) if n_total > 0 else float("nan")
        return {
            "n_total": n_total,
            "n_feasible": n_feasible,
            "n_rejected": n_rejected,
            "reject_rate": rate,
        }

    # ------------------------------------------------------------------
    # Figure WFW (coupe 2D) — pour BLOC 10 et le mémoire
    # ------------------------------------------------------------------
    def plot_wfw_slice(
        self,
        output_path: Path,
        z: float | None = None,
        resolution: int = 60,
        overlay_points: np.ndarray | None = None,
    ) -> Path:
        """
        Trace la carte de faisabilité WFW en coupe horizontale à z donné.

        Paramètres
        ----------
        output_path : Path
            Chemin du PNG de sortie.
        z : float, optionnel
            Altitude de la coupe dans R0. Défaut : z_absolu_r0.
        resolution : int
            Nombre de points par axe (grille resolution × resolution).
        overlay_points : ndarray (N, 3), optionnel
            Points à superposer (ex. les 81 points de B4). Marqués en
            vert si faisables, rouge sinon.

        Retour
        ------
        Le Path du fichier écrit.
        """
        import matplotlib.pyplot as plt
        from matplotlib.colors import ListedColormap

        if z is None:
            z = self.config.z_absolu_r0

        xs = np.linspace(self.config.x_min, self.config.x_max, resolution)
        ys = np.linspace(self.config.y_min, self.config.y_max, resolution)
        XX, YY = np.meshgrid(xs, ys)
        feas = np.zeros_like(XX, dtype=float)

        # Boucle LP — 81 à 3600 appels selon resolution, HiGHS reste rapide.
        for i in range(resolution):
            for j in range(resolution):
                p = np.array([XX[i, j], YY[i, j], z])
                feas[i, j] = 1.0 if self.is_feasible(p).feasible else 0.0

        fig, ax = plt.subplots(figsize=(8, 7))
        cmap = ListedColormap(["#ffcdd2", "#c8e6c9"])  # rouge clair / vert clair
        ax.pcolormesh(XX, YY, feas, cmap=cmap, shading="auto", vmin=0, vmax=1)

        # Superposition éventuelle de points (grille B4, etc.)
        if overlay_points is not None:
            xyz = self._coerce_points(overlay_points)
            for p in xyz:
                color = "green" if self.is_feasible(p).feasible else "red"
                ax.plot(
                    p[0], p[1], "o",
                    color=color, markersize=5,
                    markeredgecolor="black", markeredgewidth=0.6,
                )

        ax.set_xlabel("x (m)")
        ax.set_ylabel("y (m)")
        ax.set_title(f"WFW — coupe à z = {z:.3f} m dans R0")
        ax.set_aspect("equal")
        ax.grid(True, alpha=0.3)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info("Figure WFW écrite : %s", output_path)
        return output_path

    # ------------------------------------------------------------------
    # Utilitaire interne
    # ------------------------------------------------------------------
    @staticmethod
    def _coerce_points(points) -> np.ndarray:
        """Normalise ndarray/DataFrame vers un ndarray (N, 3) float."""
        if isinstance(points, pd.DataFrame):
            for col in ("x", "y", "z"):
                if col not in points.columns:
                    raise ValueError(
                        f"DataFrame doit contenir une colonne '{col}'."
                    )
            xyz = points[["x", "y", "z"]].to_numpy(dtype=float)
        else:
            xyz = np.asarray(points, dtype=float)
        if xyz.ndim != 2 or xyz.shape[1] != 3:
            raise ValueError(
                f"points doit être de shape (N, 3), reçu {xyz.shape}."
            )
        return xyz
