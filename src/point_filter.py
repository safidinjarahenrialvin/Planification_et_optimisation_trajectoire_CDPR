"""
BLOC 5 — Filtrage des points (PointFilter)
============================================

Référence : contrat de filtrage des points du pipeline SP2 (BLOC 5).
Portée    : ne conserver que les points mécaniquement atteignables,
            classifier les rejets en Cause A / Cause B, traiter le centre
            comme verrou de démarrage.

Classification des rejets
--------------------------
  Cause A : point hors limites opérationnelles (x,y,z hors bornes Config).
            En pratique, Config R4 garantit déjà l'étendue de la grille,
            donc Cause A = ∅ en nominal. La voie est néanmoins implémentée
            et testée pour couvrir le cas où la logique évoluerait.
  Cause B : point dans les bornes mais infaisable au sens WFW (LP sans
            solution).

Verrou du centre
----------------
  Le point le plus proche de (0, 0) est identifié comme centre. S'il
  n'est pas faisable, une exception `CenterNotFeasibleError` est levée —
  l'exécution du pipeline s'arrête, conformément au §5 BLOC 5
  (« Alerte centre — signal bloquant »).

  Le centre n'est jamais classifié en Cause A/B : il est toujours soit
  retenu (faisable), soit bloquant.

Contrat de sortie
-----------------
  - points_filtres.csv : colonnes identiques à points_generes.csv (§6).
  - points_rejetes_cause_a.csv, points_rejetes_cause_b.csv :
    colonnes identiques + 'cause' ∈ {'A','B'} + 'raison' (texte).
  - point_filter_report.json : résumé + alertes + info centre.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

from src.config import Config
from src.wfw import WFW

logger = logging.getLogger(__name__)


# Colonnes du contrat CSV partagé entre les blocs 4 et 5.
_CSV_COLUMNS = ["id", "x", "y", "z", "ligne", "colonne"]
_REJECT_COLUMNS = [*_CSV_COLUMNS, "cause", "raison"]

# Seuils d'alerte du filtrage. Ils signalent une configuration à examiner,
# mais ne transforment pas automatiquement un rejet mécanique en erreur.
_DEFAULT_REJECT_RATE_THRESHOLD = 0.15
_DEFAULT_CAUSE_A_THRESHOLD = 0.05

# Tolérance pour l'identification du centre (m).
_CENTER_TOL = 1e-9

# Nombre minimum de points pour qu'un tour soit constructible.
# Centre + 3 points minimum : en dessous, aucune optimisation sensée
# n'est possible et la baseline NN peut échouer.
_MIN_POINTS_FOR_TOUR: int = 4

class CenterNotFeasibleError(RuntimeError):
    """Levée si le centre de la grille n'est pas faisable mécaniquement."""

class InsufficientPointsError(RuntimeError):
    """
    Levée quand trop peu de points sont retenus après filtrage pour
    construire un tour visitant le centre et au moins 3 points.
    """


@dataclass(frozen=True)
class FilterResult:
    """Résultat complet du filtrage d'une grille."""
    points_retenus: pd.DataFrame = field(compare=False, default=None)
    points_rejetes_cause_a: pd.DataFrame = field(compare=False, default=None)
    points_rejetes_cause_b: pd.DataFrame = field(compare=False, default=None)
    centre: dict = field(default_factory=dict)
    summary: dict = field(default_factory=dict)
    alerts: List[str] = field(default_factory=list)


class PointFilter:
    """
    Filtre mécanique d'une grille de points (DataFrame ou CSV).

    Utilise WFW.is_feasible comme oracle de faisabilité. Aucun recalcul
    géométrique local : tout passe par BLOC 3.
    """

    def __init__(self, config: Config, wfw: WFW) -> None:
        self.config = config
        self.wfw = wfw

    # ------------------------------------------------------------------
    # Filtrage principal
    # ------------------------------------------------------------------
    def filter(
        self,
        points: pd.DataFrame | Path | str,
        reject_rate_threshold: float = _DEFAULT_REJECT_RATE_THRESHOLD,
        cause_a_threshold: float = _DEFAULT_CAUSE_A_THRESHOLD,
    ) -> FilterResult:
        """
        Filtre les points fournis.

        Paramètres
        ----------
        points : DataFrame ou chemin CSV
            Doit contenir au minimum id, x, y, z, ligne, colonne.
        reject_rate_threshold : float
            Seuil d'alerte sur le taux de rejet total (< 15 % par défaut).
        cause_a_threshold : float
            Seuil d'alerte sur le taux de Cause A (< 5 % par défaut).

        Retour
        ------
        FilterResult
        """
        df = self._load_points(points)

        # 1) Identification du centre
        centre_id = self._find_centre_id(df)
        centre_row = df.loc[df["id"] == centre_id].iloc[0]
        centre_pose = np.array([
            float(centre_row["x"]),
            float(centre_row["y"]),
            float(centre_row["z"]),
        ])

        # 2) Verrou du centre — test en premier
        centre_sol = self.wfw.is_feasible(centre_pose)
        if not centre_sol.feasible:
            raise CenterNotFeasibleError(
                f"Centre {centre_pose.tolist()} infaisable : {centre_sol.message}"
            )
        centre_info = {
            "id": int(centre_id),
            "x": float(centre_row["x"]),
            "y": float(centre_row["y"]),
            "z": float(centre_row["z"]),
            "feasible": True,
            "status": int(centre_sol.status),
        }

        # 3) Boucle sur les autres points
        retenus_rows: List[dict] = []
        cause_a_rows: List[dict] = []
        cause_b_rows: List[dict] = []

        for _, row in df.iterrows():
            if int(row["id"]) == centre_id:
                retenus_rows.append(row.to_dict())
                continue

            pose = np.array([float(row["x"]), float(row["y"]), float(row["z"])])

            # Cause A : hors limites opérationnelles
            if not self._within_limits(pose):
                cause_a_rows.append({
                    **row.to_dict(),
                    "cause": "A",
                    "raison": self._out_of_limits_reason(pose),
                })
                continue

            # Cause B : test WFW
            sol = self.wfw.is_feasible(pose)
            if sol.feasible:
                retenus_rows.append(row.to_dict())
            else:
                cause_b_rows.append({
                    **row.to_dict(),
                    "cause": "B",
                    "raison": sol.message,
                })

        # 4) Assemblage des DataFrames (colonnes figées)
        retenus_df = (
            pd.DataFrame(retenus_rows, columns=_CSV_COLUMNS)
            .sort_values("id")
            .reset_index(drop=True)
        )
        cause_a_df = pd.DataFrame(cause_a_rows, columns=_REJECT_COLUMNS).reset_index(drop=True)
        cause_b_df = pd.DataFrame(cause_b_rows, columns=_REJECT_COLUMNS).reset_index(drop=True)

        # 4bis) Vérification du seuil minimal de points.
        # Un tour nécessite au minimum le centre + 3 points, sinon
        # aucune optimisation ni baseline n'est constructible.
        n_kept = len(retenus_df)
        if n_kept < _MIN_POINTS_FOR_TOUR:
            msg = (
                f"Trop peu de points retenus ({n_kept} < {_MIN_POINTS_FOR_TOUR}). "
                f"Le pipeline ne peut pas continuer car un tour nécessite "
                f"au minimum le centre et 3 points."
            )
            logger.warning(msg)
            raise InsufficientPointsError(msg)

        # 5) Statistiques + alertes
        n_total = len(df)
        n_rejected = len(cause_a_df) + len(cause_b_df)
        reject_rate = n_rejected / n_total if n_total > 0 else 0.0
        cause_a_rate = len(cause_a_df) / n_total if n_total > 0 else 0.0

        alerts: List[str] = []
        if reject_rate >= reject_rate_threshold:
            msg = (
                f"Taux de rejet {reject_rate*100:.1f} % ≥ seuil "
                f"{reject_rate_threshold*100:.0f} %."
            )
            alerts.append(msg)
            logger.warning(msg)
        if cause_a_rate >= cause_a_threshold:
            msg = (
                f"Taux Cause A {cause_a_rate*100:.1f} % ≥ seuil "
                f"{cause_a_threshold*100:.0f} %."
            )
            alerts.append(msg)
            logger.warning(msg)

        summary = {
            "n_total": n_total,
            "n_kept": len(retenus_df),
            "n_rejected_cause_a": len(cause_a_df),
            "n_rejected_cause_b": len(cause_b_df),
            "n_rejected_total": int(n_rejected),
            "reject_rate": float(reject_rate),
            "cause_a_rate": float(cause_a_rate),
            "reject_rate_threshold": float(reject_rate_threshold),
            "cause_a_threshold": float(cause_a_threshold),
        }

        logger.info(
            "PointFilter : %d/%d retenus, %d Cause A, %d Cause B.",
            summary["n_kept"], n_total,
            summary["n_rejected_cause_a"], summary["n_rejected_cause_b"],
        )

        return FilterResult(
            points_retenus=retenus_df,
            points_rejetes_cause_a=cause_a_df,
            points_rejetes_cause_b=cause_b_df,
            centre=centre_info,
            summary=summary,
            alerts=alerts,
        )

    # ------------------------------------------------------------------
    # Sauvegarde
    # ------------------------------------------------------------------
    def save(self, result: FilterResult, output_dir: Path | str) -> dict:
        """
        Écrit 4 fichiers sur disque :
          - points_filtres.csv
          - points_rejetes_cause_a.csv
          - points_rejetes_cause_b.csv
          - point_filter_report.json
        Retourne un dict {clé: Path}.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        csv_filtres = output_dir / "points_filtres.csv"
        csv_cause_a = output_dir / "points_rejetes_cause_a.csv"
        csv_cause_b = output_dir / "points_rejetes_cause_b.csv"
        json_report = output_dir / "point_filter_report.json"

        result.points_retenus.to_csv(csv_filtres, index=False, float_format="%.6f")
        result.points_rejetes_cause_a.to_csv(csv_cause_a, index=False, float_format="%.6f")
        result.points_rejetes_cause_b.to_csv(csv_cause_b, index=False, float_format="%.6f")

        report = {
            "centre": result.centre,
            "summary": result.summary,
            "alerts": result.alerts,
        }
        with json_report.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info("PointFilter : 4 fichiers écrits dans %s", output_dir)
        return {
            "points_filtres": csv_filtres,
            "points_rejetes_cause_a": csv_cause_a,
            "points_rejetes_cause_b": csv_cause_b,
            "report": json_report,
        }

    # ------------------------------------------------------------------
    # Pipeline complet
    # ------------------------------------------------------------------
    def run(
        self,
        points: pd.DataFrame | Path | str,
        output_dir: Path | str = "data/outputs",
    ) -> dict:
        """Filtre + sauvegarde en un seul appel. Retourne les chemins."""
        result = self.filter(points)
        return self.save(result, output_dir)

    # ------------------------------------------------------------------
    # Utilitaires privés
    # ------------------------------------------------------------------
    @staticmethod
    def _load_points(points: pd.DataFrame | Path | str) -> pd.DataFrame:
        if isinstance(points, pd.DataFrame):
            df = points.copy()
        else:
            df = pd.read_csv(Path(points))
        missing = [c for c in _CSV_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(
                f"Colonnes manquantes dans les points : {missing}. "
                f"Attendu : {_CSV_COLUMNS}."
            )
        return df

    @staticmethod
    def _find_centre_id(df: pd.DataFrame) -> int:
        """
        Retourne l'id du point le plus proche de (0, 0). Lève si aucun
        point n'est à moins de _CENTER_TOL du centre.
        """
        dist = np.sqrt(df["x"] ** 2 + df["y"] ** 2)
        idx_min = dist.idxmin()
        if dist.loc[idx_min] > _CENTER_TOL:
            raise ValueError(
                f"Centre (0, 0) absent de la grille : point le plus proche "
                f"à {dist.loc[idx_min]:.4f} m. Config non supportée "
                f"(n_rangs et n_colonnes doivent être impairs)."
            )
        return int(df.loc[idx_min, "id"])

    def _within_limits(self, pose: np.ndarray) -> bool:
        cfg = self.config
        x, y, z = float(pose[0]), float(pose[1]), float(pose[2])
        return (
            cfg.x_min - _CENTER_TOL <= x <= cfg.x_max + _CENTER_TOL
            and cfg.y_min - _CENTER_TOL <= y <= cfg.y_max + _CENTER_TOL
            and cfg.z_min - _CENTER_TOL <= z <= cfg.z_max + _CENTER_TOL
        )

    def _out_of_limits_reason(self, pose: np.ndarray) -> str:
        cfg = self.config
        parts = []
        x, y, z = float(pose[0]), float(pose[1]), float(pose[2])
        if not (cfg.x_min - _CENTER_TOL <= x <= cfg.x_max + _CENTER_TOL):
            parts.append(f"x={x:.3f} ∉ [{cfg.x_min}, {cfg.x_max}]")
        if not (cfg.y_min - _CENTER_TOL <= y <= cfg.y_max + _CENTER_TOL):
            parts.append(f"y={y:.3f} ∉ [{cfg.y_min}, {cfg.y_max}]")
        if not (cfg.z_min - _CENTER_TOL <= z <= cfg.z_max + _CENTER_TOL):
            parts.append(f"z={z:.3f} ∉ [{cfg.z_min}, {cfg.z_max}]")
        return "; ".join(parts) if parts else "hors limites (raison inconnue)"
