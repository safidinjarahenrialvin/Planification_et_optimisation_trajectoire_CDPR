"""
BLOC 9 — Profils de vitesse (TrajectoryProfiler)
==================================================

Référence : contrat de profilage des trajectoires du pipeline SP2 (BLOC 9).
Portée    : générer le profil LSPB (position + vitesse) de chaque
            trajectoire produite par BLOC 8, segment par segment.

Formule LSPB
------------
  Paramètres : distance d, direction unitaire u = (p_j − p_i)/d,
               v_max, a_max.

  Distance pour atteindre v_max : d_acc = v_max² / (2·a_max)
  Si d ≥ 2·d_acc → profil trapézoïdal :
      t_acc   = v_max / a_max
      t_cruise= (d − 2·d_acc) / v_max
      T_total = 2·t_acc + t_cruise
      s(t) et v(t) : voir _lspb_position / _lspb_speed
  Sinon → profil triangulaire :
      v_p     = √(d·a_max)
      t_acc   = v_p / a_max
      T_total = 2·t_acc

  Cas dégénéré d = 0 → T_total = 0, p(t) = p_i, v(t) = 0.

Échantillonnage
---------------
  - dt cible = 0.1 s (10 Hz)
  - Nombre de samples par segment = max(min_samples, ⌈T_seg/dt⌉ + 1)
  - Bornes t=0 et t=T_seg incluses → v = 0 testable exactement

Contrat CSV (§6, étendu)
------------------------
  Colonnes de base §6 : t, x, y, z, vx, vy, vz
  Extension documentée : kind, segment_id (préfixés) pour permettre le
  filtrage par trajectoire et par segment dans BLOC 10.

  Fichier : data/outputs/profiles.csv (unique, tous kinds confondus)
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from src.config import Config

logger = logging.getLogger(__name__)

_CSV_COLUMNS = [
    "kind", "segment_id", "t", "x", "y", "z", "vx", "vy", "vz",
]

# Nombre minimum de samples par segment — garantit que même un segment
# très court a au moins un point d'accélération et un de décélération.
_MIN_SAMPLES_PER_SEGMENT = 5

# dt cible par défaut (s).
_DEFAULT_DT = 0.1


@dataclass(frozen=True)
class _Segment:
    """Segment entre deux waypoints — structure interne au profiler."""
    p_i: np.ndarray
    p_j: np.ndarray
    d: float
    T: float


class TrajectoryProfiler:
    """
    Génère les profils LSPB à partir des waypoints de BLOC 8.

    N'effectue aucun calcul géométrique sur les câbles : travaille
    uniquement sur les positions cartésiennes des waypoints.
    """

    def __init__(
        self,
        config: Config,
        dt: float = _DEFAULT_DT,
        min_samples_per_segment: int = _MIN_SAMPLES_PER_SEGMENT,
    ) -> None:
        if dt <= 0.0:
            raise ValueError(f"dt doit être > 0, reçu {dt}.")
        if min_samples_per_segment < 2:
            raise ValueError(
                f"min_samples_per_segment doit être ≥ 2, "
                f"reçu {min_samples_per_segment}."
            )
        self.config = config
        self.dt = float(dt)
        self.min_samples = int(min_samples_per_segment)

    # ------------------------------------------------------------------
    # Formule LSPB — helpers
    # ------------------------------------------------------------------
    def _lspb_time(self, d: float) -> float:
        """Durée totale LSPB sur une distance d."""
        if d <= 0.0:
            return 0.0
        v_max = self.config.v_max
        a_max = self.config.a_max
        d_acc = v_max * v_max / (2.0 * a_max)
        if d >= 2.0 * d_acc:
            return 2.0 * v_max / a_max + (d - 2.0 * d_acc) / v_max
        return 2.0 * math.sqrt(d / a_max)

    def _lspb_position(self, d: float, t: float, T: float) -> float:
        """Position curviligne s(t) ∈ [0, d]."""
        if d <= 0.0 or T <= 0.0:
            return 0.0
        v_max = self.config.v_max
        a_max = self.config.a_max
        d_acc = v_max * v_max / (2.0 * a_max)
        if d >= 2.0 * d_acc:
            t_acc = v_max / a_max
            t_cruise = T - 2.0 * t_acc
            if t < t_acc:
                return 0.5 * a_max * t * t
            if t < t_acc + t_cruise:
                return d_acc + v_max * (t - t_acc)
            t_rem = T - t
            return d - 0.5 * a_max * t_rem * t_rem
        # Triangulaire
        v_p = math.sqrt(d * a_max)
        t_acc_eff = v_p / a_max
        if t < t_acc_eff:
            return 0.5 * a_max * t * t
        t_rem = T - t
        return d - 0.5 * a_max * t_rem * t_rem

    def _lspb_speed(self, d: float, t: float, T: float) -> float:
        """Vitesse scalaire v(t) ≥ 0."""
        if d <= 0.0 or T <= 0.0:
            return 0.0
        v_max = self.config.v_max
        a_max = self.config.a_max
        d_acc = v_max * v_max / (2.0 * a_max)
        if d >= 2.0 * d_acc:
            t_acc = v_max / a_max
            t_cruise = T - 2.0 * t_acc
            if t < t_acc:
                return a_max * t
            if t < t_acc + t_cruise:
                return v_max
            t_rem = T - t
            return max(0.0, a_max * t_rem)
        v_p = math.sqrt(d * a_max)
        t_acc_eff = v_p / a_max
        if t < t_acc_eff:
            return a_max * t
        t_rem = T - t
        # max(0.0, ...) : garantit une vitesse non négative malgré les
        # erreurs d'arrondi flottant quand t ≈ T (fin de segment).
        return max(0.0, a_max * t_rem)

    # ------------------------------------------------------------------
    # Construction des segments
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_waypoints(traj_df: pd.DataFrame) -> np.ndarray:
        """Retourne les positions (M, 3) triées par rank."""
        if "rank" not in traj_df.columns:
            raise ValueError("La trajectoire doit avoir une colonne 'rank'.")
        df = traj_df.sort_values("rank").reset_index(drop=True)
        return df[["x", "y", "z"]].to_numpy(dtype=float)

    def _build_segments(self, waypoints: np.ndarray) -> List[_Segment]:
        segments: List[_Segment] = []
        for k in range(len(waypoints) - 1):
            p_i = waypoints[k]
            p_j = waypoints[k + 1]
            d = float(np.linalg.norm(p_j - p_i))
            T = self._lspb_time(d)
            segments.append(_Segment(p_i=p_i, p_j=p_j, d=d, T=T))
        return segments

    # ------------------------------------------------------------------
    # Profil d'une trajectoire
    # ------------------------------------------------------------------
    def profile_trajectory(
        self,
        kind: str,
        traj_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Génère le DataFrame long du profil pour une trajectoire donnée.

        Paramètres
        ----------
        kind : str
            Étiquette de la trajectoire (time_opt, energy_opt, compromise).
        traj_df : DataFrame
            Doit contenir les colonnes x, y, z, rank.

        Retour
        ------
        DataFrame avec colonnes [_CSV_COLUMNS].
        """
        waypoints = self._extract_waypoints(traj_df)
        segments = self._build_segments(waypoints)

        rows: List[Dict[str, float]] = []
        t_offset = 0.0

        for seg_id, seg in enumerate(segments):
            # Cas dégénéré : segment de longueur nulle → un seul sample.
            if seg.d < 1e-12:
                n_samples = 1
            else:
                n_samples = max(
                    self.min_samples,
                    math.ceil(seg.T / self.dt) + 1,
                )
            t_local = np.linspace(0.0, seg.T, n_samples)

            if seg.d > 1e-12:
                u = (seg.p_j - seg.p_i) / seg.d
            else:
                u = np.zeros(3)

            # Skip the first sample of segments > 0 : il duplique le
            # dernier sample du segment précédent (même waypoint, même t).
            # Ceci garantit un temps global STRICTEMENT croissant et un
            # seul enregistrement par waypoint visité.
            start_k = 0 if seg_id == 0 else 1

            for t_l in t_local[start_k:]:
                s = self._lspb_position(seg.d, float(t_l), seg.T)
                v = self._lspb_speed(seg.d, float(t_l), seg.T)
                p = seg.p_i + s * u
                v_vec = v * u
                rows.append({
                    "kind": kind,
                    "segment_id": seg_id,
                    "t": t_offset + float(t_l),
                    "x": float(p[0]), "y": float(p[1]), "z": float(p[2]),
                    "vx": float(v_vec[0]),
                    "vy": float(v_vec[1]),
                    "vz": float(v_vec[2]),
                })

            t_offset += seg.T

        df = pd.DataFrame(rows, columns=_CSV_COLUMNS)
        logger.info(
            "Profil '%s' : %d segments, %d samples, T_total = %.3f s.",
            kind, len(segments), len(df), t_offset,
        )
        return df

    # ------------------------------------------------------------------
    # Pipeline complet
    # ------------------------------------------------------------------
    def run_and_save(
        self,
        trajectories: pd.DataFrame | Path | str,
        output_dir: Path | str = "data/outputs",
    ) -> Dict[str, Path]:
        """
        Génère et sauvegarde les profils pour les 3 kinds présents dans
        le fichier trajectories.csv de BLOC 8.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if not isinstance(trajectories, pd.DataFrame):
            trajectories = pd.read_csv(Path(trajectories))

        required = {"kind", "rank", "x", "y", "z"}
        missing = required - set(trajectories.columns)
        if missing:
            raise ValueError(
                f"trajectories : colonnes manquantes {sorted(missing)}."
            )

        all_frames: List[pd.DataFrame] = []
        per_kind_paths: Dict[str, Path] = {}

        for kind, sub in trajectories.groupby("kind", sort=False):
            prof = self.profile_trajectory(str(kind), sub)
            all_frames.append(prof)
            # Un fichier par kind — plus pratique pour BLOC 10
            path = output_dir / f"profiles_{kind}.csv"
            prof.to_csv(path, index=False, float_format="%.6f")
            per_kind_paths[str(kind)] = path

        combined = pd.concat(all_frames, ignore_index=True)
        combined_path = output_dir / "profiles.csv"
        combined.to_csv(combined_path, index=False, float_format="%.6f")

        logger.info(
            "TrajectoryProfiler : %d fichiers + profiles.csv écrits dans %s",
            len(per_kind_paths), output_dir,
        )
        result: Dict[str, Path] = {"profiles": combined_path}
        result.update({f"profiles_{k}": v for k, v in per_kind_paths.items()})
        return result
