"""
Visualisation 3D multi-volumes du WFW/WCW
==========================================

Référence : extension de visualisation 3D du calcul WFW/WCW.
Portée    : produire une figure 3D combinant, dans un même repère :
              - le bâti (ancrages aux 8 coins, arêtes en gris)
              - la nacelle (plateforme mobile et ses 8 attaches)
              - les 8 câbles reliant ancrages et attaches
                            - volumes WCW et WFW en surfaces semi-transparentes, calculés
                                avec les limites de tension de Config

Nesting
-------
Le calcul commence par le WCW, cas le plus permissif, puis réutilise son
masque de faisabilité pour le WFW. Cela réduit les appels LP tout en gardant
les deux volumes cohérents avec la Config active.

T_max choisi
------------
Les deux volumes utilisent le même T_max que Config. Le WCW met T_min à zéro,
le WFW conserve Config.T_min.

Bornes d'échantillonnage
------------------------
Par défaut : enveloppe complète des ancrages (±1.25 m XY, Z ∈ [0, 1.00]).
Indépendantes de Config.x_min/x_max (qui restent à ±0.75 m pour la
production). Surchargeables via le constructeur.

Méthode de rendu
----------------
Les volumes sont rendus par `scipy.spatial.ConvexHull` (enveloppe
convexe des points faisables) + `Poly3DCollection` (faces semi-
transparentes). Approximation : le WFW réel n'est pas convexe, mais
il l'est presque sur cette géométrie. Alternative : scatter fallback
si ConvexHull échoue (points coplanaires, dégénérés, etc.).
"""
from __future__ import annotations

import logging
import time as time_module
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import numpy as np

from src.config import Config
from src.robot_model import RobotModel
from src.wfw import WFW

logger = logging.getLogger(__name__)


# Résolutions par défaut — compromis lisibilité / temps de calcul.
_DEFAULT_N_XY = 25
_DEFAULT_N_Z = 15

# Styles des deux volumes affichés.
# WFW : workspace opérationnel (T_min, T_max de Config) — couleur verte
# WCW : enveloppe relâchée (T_min = 0, T_max de Config) — bleu clair
_VOLUME_STYLES: Dict[str, Dict] = {
    "wcw": {"color": "#90caf9", "alpha": 0.15,
            "label": "WCW ($T_{{min}}=0$)"},
    "wfw": {"color": "#2e7d32", "alpha": 0.45,
            "label": "WFW ($T_{{{tmin}}}$–${{{tmax}}}$ N)"},
}


# ===========================================================================
# Data structures
# ===========================================================================
@dataclass(frozen=True)
class WFWVolume:
    """Volume échantillonné pour une valeur de T_min donnée."""
    t_min: float = 0.0
    t_max: float = 0.0
    x: np.ndarray = field(compare=False, default=None)
    y: np.ndarray = field(compare=False, default=None)
    z: np.ndarray = field(compare=False, default=None)
    feasible: np.ndarray = field(compare=False, default=None)
    n_lp_calls: int = 0
    duration_s: float = 0.0

    @property
    def feasible_ratio(self) -> float:
        if self.feasible is None or self.feasible.size == 0:
            return 0.0
        return float(self.feasible.sum()) / float(self.feasible.size)

    @property
    def n_feasible(self) -> int:
        return int(self.feasible.sum()) if self.feasible is not None else 0

    @property
    def n_total(self) -> int:
        return int(self.feasible.size) if self.feasible is not None else 0


# ===========================================================================
# Viewer
# ===========================================================================
class WFW3DViewer:
    """
    Générateur de la figure multi-volumes. Utilise l'API publique de
    WFW (BLOC 3) sans la modifier.
    """

    def __init__(
        self,
        robot: RobotModel,
        config: Config,
        x_bounds: Optional[Tuple[float, float]] = None,
        y_bounds: Optional[Tuple[float, float]] = None,
        z_bounds: Optional[Tuple[float, float]] = None,
        n_xy: int = _DEFAULT_N_XY,
        n_z: int = _DEFAULT_N_Z,
    ) -> None:
        self.robot = robot
        self.config = config

        # Bornes d'échantillonnage : par défaut, enveloppe des ancrages.
        A = config.ancrages_A
        self.x_bounds = x_bounds or (float(A[0, :].min()), float(A[0, :].max()))
        self.y_bounds = y_bounds or (float(A[1, :].min()), float(A[1, :].max()))
        self.z_bounds = z_bounds or (float(A[2, :].min()), float(A[2, :].max()))

        if n_xy < 4:
            raise ValueError(f"n_xy doit être ≥ 4, reçu {n_xy}.")
        if n_z < 3:
            raise ValueError(f"n_z doit être ≥ 3, reçu {n_z}.")
        self.n_xy = int(n_xy)
        self.n_z = int(n_z)

    # ----------------------------------------------------------------------
    # Calcul
    # ----------------------------------------------------------------------
    def compute_volume(
        self,
        t_min: float,
        t_max: float,
        restrict_to_mask: Optional[np.ndarray] = None,
    ) -> WFWVolume:
        """
        Échantillonne la grille et teste WFW.is_feasible sur chaque point.

        Paramètres
        ----------
        t_min : float
            Borne basse de tension (N). Utiliser 0.0 pour le WCW.
        t_max : float
            Borne haute de tension (N). Obligatoire — utiliser
            `config.T_max` pour un volume cohérent avec le pipeline.
        restrict_to_mask : ndarray booléen, optionnel
            Masque de restriction. Si fourni, seuls les points où le
            masque est True sont testés — économise des appels LP.

        Note : t_max est désormais obligatoire (plus de fallback CLI).
        Cela garantit que tout volume calculé utilise une borne haute
        explicite, traçable et cohérente avec Config.
        """
        cfg_t = replace(self.config, T_min=float(t_min), T_max=float(t_max))
        wfw = WFW(self.robot, cfg_t)

        x = np.linspace(self.x_bounds[0], self.x_bounds[1], self.n_xy)
        y = np.linspace(self.y_bounds[0], self.y_bounds[1], self.n_xy)
        z = np.linspace(self.z_bounds[0], self.z_bounds[1], self.n_z)

        feasible = np.zeros((self.n_xy, self.n_xy, self.n_z), dtype=bool)
        n_calls = 0
        t0 = time_module.perf_counter()

        for k in range(self.n_z):
            for i in range(self.n_xy):
                for j in range(self.n_xy):
                    if restrict_to_mask is not None and not restrict_to_mask[i, j, k]:
                        continue
                    p = np.array([x[i], y[j], z[k]], dtype=float)
                    feasible[i, j, k] = wfw.is_feasible(p).feasible
                    n_calls += 1

        return WFWVolume(
            t_min=float(t_min), t_max=t_max,
            x=x, y=y, z=z, feasible=feasible,
            n_lp_calls=n_calls,
            duration_s=time_module.perf_counter() - t0,
        )

    def compute_workspace_volumes(self) -> Dict[str, WFWVolume]:
        """
        Calcule les 2 volumes du workspace courant (D-CONFIG-14) :
          - 'wcw' : T_min = 0, T_max de Config (enveloppe maximale)
          - 'wfw' : T_min, T_max de Config (workspace opérationnel)

        Ordre de calcul : WCW d'abord (le plus permissif), puis WFW
        restreint au masque WCW. Économise ~50 % des appels LP.

        Utilise uniquement les paramètres de Config — aucune valeur
        CLI ne peut diverger du pipeline.
        """
        t_max = float(self.config.T_max)
        t_min_wfw = float(self.config.T_min)

        logger.info(
            "=== Calcul du WCW (T ∈ [0, %.1f] N) ===", t_max,
        )
        vol_wcw = self.compute_volume(t_min=0.0, t_max=t_max)
        logger.info(
            "  WCW : %5d/%5d faisables (%.2f %%) — %.1f s",
            vol_wcw.n_feasible, vol_wcw.n_total,
            100.0 * vol_wcw.feasible_ratio, vol_wcw.duration_s,
        )

        logger.info(
            "=== Calcul du WFW (T ∈ [%.2f, %.1f] N) ===",
            t_min_wfw, t_max,
        )
        vol_wfw = self.compute_volume(
            t_min=t_min_wfw, t_max=t_max,
            restrict_to_mask=vol_wcw.feasible,
        )
        logger.info(
            "  WFW : %5d/%5d faisables (%.2f %%) — %.1f s",
            vol_wfw.n_feasible, vol_wfw.n_total,
            100.0 * vol_wfw.feasible_ratio, vol_wfw.duration_s,
        )

        return {"wcw": vol_wcw, "wfw": vol_wfw}

    # ----------------------------------------------------------------------
    # Dessin — éléments fixes
    # ----------------------------------------------------------------------
    def _draw_frame(self, ax) -> None:
        """12 arêtes du parallélépipède des ancrages."""
        A = self.config.ancrages_A
        # Indices dans l'ordre de ANCRAGES_A_M
        idx_pairs = [
            # Face haute
            (0, 1), (1, 3), (3, 2), (2, 0),
            # Face basse
            (4, 5), (5, 7), (7, 6), (6, 4),
            # Verticales
            (0, 4), (1, 5), (3, 7), (2, 6),
        ]
        for i, j in idx_pairs:
            ax.plot(
                [A[0, i], A[0, j]],
                [A[1, i], A[1, j]],
                [A[2, i], A[2, j]],
                color="#424242", linewidth=1.8, alpha=0.9,
            )

    def _draw_platform(self, ax, p_center: np.ndarray) -> None:
        """Nacelle (plateforme mobile) — pavé semi-transparent."""
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection

        b = self.config.attaches_B
        xm, xM = float(b[0, :].min()), float(b[0, :].max())
        ym, yM = float(b[1, :].min()), float(b[1, :].max())
        zm, zM = float(b[2, :].min()), float(b[2, :].max())
        px, py, pz = p_center

        corners = [
            (px + xm, py + ym, pz + zm), (px + xM, py + ym, pz + zm),
            (px + xM, py + yM, pz + zm), (px + xm, py + yM, pz + zm),
            (px + xm, py + ym, pz + zM), (px + xM, py + ym, pz + zM),
            (px + xM, py + yM, pz + zM), (px + xm, py + yM, pz + zM),
        ]
        faces = [
            [corners[0], corners[1], corners[2], corners[3]],
            [corners[4], corners[5], corners[6], corners[7]],
            [corners[0], corners[1], corners[5], corners[4]],
            [corners[1], corners[2], corners[6], corners[5]],
            [corners[2], corners[3], corners[7], corners[6]],
            [corners[3], corners[0], corners[4], corners[7]],
        ]
        coll = Poly3DCollection(
            faces, alpha=0.40, facecolor="#1565c0",
            edgecolor="#0d47a1", linewidths=0.8,
        )
        ax.add_collection3d(coll)

    def _platform_label(self) -> str:
        """
        Retourne une étiquette lisible de la taille de plateforme
        (ex. "300×240×50 mm").
        """
        b = self.config.attaches_B
        # b a la forme (3, 8) : ligne 0 = X, ligne 1 = Y, ligne 2 = Z
        # Les demi-étendues sont extraites via min/max sur les 8 colonnes.
        w_mm = round((b[0, :].max() - b[0, :].min()) * 1000)
        h_mm = round((b[1, :].max() - b[1, :].min()) * 1000)
        t_mm = round((b[2, :].max() - b[2, :].min()) * 1000)
        return f"{w_mm}×{h_mm}×{t_mm} mm"

    def _draw_cables(self, ax, p_center: np.ndarray) -> None:
        """8 câbles + marqueurs ancrages/attaches."""
        A = self.config.ancrages_A
        B = self.robot.attach_positions(p_center)
        for i in range(8):
            ax.plot(
                [A[0, i], B[0, i]],
                [A[1, i], B[1, i]],
                [A[2, i], B[2, i]],
                color="#37474f", linewidth=1.0, alpha=0.75,
            )
        ax.scatter(
            A[0, :], A[1, :], A[2, :],
            s=45, c="#212121", marker="s",
            edgecolors="white", linewidths=0.6,
            label="Ancrages", zorder=10,
        )
        ax.scatter(
            B[0, :], B[1, :], B[2, :],
            s=45, c="#0d47a1", marker="o",
            edgecolors="white", linewidths=0.6,
            label="Attaches", zorder=10,
        )

    # ----------------------------------------------------------------------
    # Dessin — volumes
    # ----------------------------------------------------------------------
    def _draw_volume_hull(
        self,
        ax,
        volume: WFWVolume,
        color: str,
        alpha: float,
        label: str,
    ) -> None:
        """Enveloppe convexe d'un volume, semi-transparente."""
        from scipy.spatial import ConvexHull, QhullError
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection

        idx = np.argwhere(volume.feasible)
        if idx.size == 0:
            logger.warning("Volume T_min=%.1f : aucun point faisable.", volume.t_min)
            return
        pts = np.column_stack([
            volume.x[idx[:, 0]],
            volume.y[idx[:, 1]],
            volume.z[idx[:, 2]],
        ])

        # Cap sur le nombre de points pour le hull (perf).
        if len(pts) > 5000:
            rng = np.random.default_rng(42)
            sel = rng.choice(len(pts), size=5000, replace=False)
            pts = pts[sel]

        if len(pts) < 4:
            ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2],
                       s=10, c=color, alpha=alpha, label=label)
            return

        try:
            hull = ConvexHull(pts)
        except QhullError as exc:
            logger.warning(
                "Volume T_min=%.1f : ConvexHull a échoué (%s). Fallback scatter.",
                volume.t_min, exc,
            )
            ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2],
                       s=8, c=color, alpha=alpha, label=label)
            return

        faces = [pts[s, :] for s in hull.simplices]
        coll = Poly3DCollection(
            faces, alpha=alpha, facecolor=color,
            edgecolor=color, linewidths=0.25,
        )
        ax.add_collection3d(coll)
        # Proxy pour la légende
        ax.scatter([], [], [], c=color, alpha=alpha, s=80, label=label)

    def _draw_workspaces(self, ax, volumes: Dict[str, WFWVolume]) -> None:
        """
        Dessine les 2 volumes : WCW (fond) puis WFW (avant).
        L'ordre WCW → WFW garantit que le WFW reste visible.
        """
        for key in ("wcw", "wfw"):
            if key not in volumes:
                continue
            vol = volumes[key]
            style = _VOLUME_STYLES[key].copy()
            # Interpolation du label WFW avec les vraies tensions
            if key == "wfw":
                style["label"] = style["label"].format(
                    tmin=f"{self.config.T_min:g}",
                    tmax=f"{self.config.T_max:g}",
                )
            pct = 100.0 * vol.feasible_ratio
            label = f"{style['label']} — {pct:.1f} %"
            self._draw_volume_hull(
                ax, vol,
                color=style["color"],
                alpha=style["alpha"],
                label=label,
            )

    # ----------------------------------------------------------------------
    # Entrée principale
    # ----------------------------------------------------------------------
    def plot_workspace(
        self,
        output_path: Union[Path, str],
        view_elev: float = 22.0,
        view_azim: float = -60.0,
    ) -> Dict[str, WFWVolume]:
        """
        Calcule les volumes imbriqués et produit la figure combinée.
        Retourne le dict {T_min: WFWVolume} pour analyse ultérieure.
        """
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

        volumes = self.compute_workspace_volumes()

        fig = plt.figure(figsize=(13, 10))
        ax = fig.add_subplot(111, projection="3d")

        p_center = np.array([0.0, 0.0, self.config.z_absolu_r0], dtype=float)

        # Ordre de dessin : cadre, nacelle, câbles, puis volumes
        self._draw_frame(ax)
        self._draw_platform(ax, p_center)
        self._draw_cables(ax, p_center)
        self._draw_workspaces(ax, volumes)

        # Bornes d'affichage : enveloppe des ancrages
        ax.set_xlim(self.x_bounds[0], self.x_bounds[1])
        ax.set_ylim(self.y_bounds[0], self.y_bounds[1])
        ax.set_zlim(self.z_bounds[0], self.z_bounds[1])

        ax.set_xlabel("x [m]", fontsize=11)
        ax.set_ylabel("y [m]", fontsize=11)
        ax.set_zlabel("z [m]", fontsize=11)
        ax.grid(True, alpha=0.3)

        # Ratio visuel basé sur les dimensions physiques
        ax.set_box_aspect((
            self.x_bounds[1] - self.x_bounds[0],
            self.y_bounds[1] - self.y_bounds[0],
            self.z_bounds[1] - self.z_bounds[0],
        ))
        ax.view_init(elev=view_elev, azim=view_azim)

        total_lp = sum(v.n_lp_calls for v in volumes.values())
        total_s = sum(v.duration_s for v in volumes.values())
        ax.set_title(
            f"Espace de travail — robot 8 câbles suspendu\n"
            f"Plateforme {self._platform_label()} — "
            f"T ∈ [{self.config.T_min:g}, {self.config.T_max:g}] N — "
            f"grille {self.n_xy}×{self.n_xy}×{self.n_z} "
            f"({total_lp} LP en {total_s:.1f} s)",
            fontsize=12, pad=14,
        )

        # Légende : on la place à l'extérieur pour qu'elle ne recouvre
        # pas la figure.
        ax.legend(
            loc="upper left", bbox_to_anchor=(1.02, 1.0),
            fontsize=10, framealpha=0.95,
        )

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info("Figure WFW 3D combinée écrite : %s", output_path)
        return volumes
