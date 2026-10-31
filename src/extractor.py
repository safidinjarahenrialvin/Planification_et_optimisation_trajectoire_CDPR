"""
BLOC 8 — Extraction des trajectoires représentatives (TrajectoryExtractor)
============================================================================

Référence : contrat d'extraction des trajectoires du pipeline SP2 (BLOC 8).
Portée    : sélectionner 3 trajectoires représentatives du front de
            Pareto — temps minimal, énergie minimale, compromis —
            et produire un CSV long des waypoints pour BLOC 9.

Sélection des 3 trajectoires
-----------------------------
  time_opt   : argmin(time)  sur le front
  energy_opt : argmin(energy) sur le front
  compromise : min || (t_norm, e_norm) ||₂ où
                  t_norm = (t − t_min) / (t_max − t_min)
                  e_norm = (e − e_min) / (e_max − e_min)
                avec 0 par convention si range = 0.

Terme stabilisation
-------------------
  Constante = N' × T_stabilisation (spec BLOC 6). Ajoutée UNIQUEMENT
  au résumé final (`total_time_s`), pas aux cumulatives par waypoint
  (qui mesurent le déplacement pur).

Sortie
------
  - trajectories.csv : format long (kind, rank, point_id, x, y, z,
    cumulative_time_motion_s, cumulative_energy_J)
  - trajectories_summary.csv : 1 ligne par kind avec les totaux et le
    tour sous forme de chaîne 'order'.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from src.config import Config

logger = logging.getLogger(__name__)

_TRAJ_COLUMNS = [
    "kind", "rank", "point_id", "x", "y", "z",
    "cumulative_time_motion_s", "cumulative_energy_J",
]
_SUMMARY_COLUMNS = [
    "kind", "order", "n_waypoints",
    "total_time_motion_s", "total_time_stab_s", "total_time_s",
    "total_energy_J",
]

_KINDS = ("time_opt", "energy_opt", "compromise")


class TrajectoryExtractor:
    """
    Sélectionne les 3 trajectoires représentatives et produit les CSV
    consommés par BLOC 9 (profils) et BLOC 10 (validation).
    """

    def __init__(
        self,
        config: Config,
        points: pd.DataFrame,
        cost_matrix: pd.DataFrame,
        solutions: pd.DataFrame | List[dict] | Path | str,
        stabilization_time_s: float | None = None,
    ) -> None:
        self.config = config
        self.points = self._index_points(points)
        self.cost_matrix = self._index_costs(cost_matrix)
        self.solutions = self._coerce_solutions(solutions)

        # La stabilisation est un coût constant par point visité.
        n_points = len(self.points)
        self.stabilization_time_s = (
            float(stabilization_time_s)
            if stabilization_time_s is not None
            else float(n_points) * float(config.T_stabilisation)
        )

    # ------------------------------------------------------------------
    # Sélection des 3 trajectoires
    # ------------------------------------------------------------------
    def select(self) -> Dict[str, Dict[str, Any]]:
        """
        Retourne un dict {kind: solution_row_dict} pour les 3 kinds.
        Utilise argmin et la distance normalisée à l'idéal.
        """
        df = self.solutions
        if df.empty:
            raise ValueError("Le front de Pareto est vide.")

        times = df["time"].to_numpy(dtype=float)
        energies = df["energy"].to_numpy(dtype=float)

        idx_time = int(np.argmin(times))
        idx_energy = int(np.argmin(energies))
        idx_compromise = self._select_compromise(times, energies)

        selection = {
            "time_opt": df.iloc[idx_time].to_dict(),
            "energy_opt": df.iloc[idx_energy].to_dict(),
            "compromise": df.iloc[idx_compromise].to_dict(),
        }
        logger.info(
            "Sélection : time_opt=#%s (t=%.3f), energy_opt=#%s (E=%.3f), "
            "compromise=#%s (t=%.3f, E=%.3f)",
            selection["time_opt"]["solution_id"], selection["time_opt"]["time"],
            selection["energy_opt"]["solution_id"], selection["energy_opt"]["energy"],
            selection["compromise"]["solution_id"],
            selection["compromise"]["time"], selection["compromise"]["energy"],
        )
        return selection

    # ------------------------------------------------------------------
    # Construction des waypoints d'une trajectoire
    # ------------------------------------------------------------------
    def build_waypoints(self, kind: str, solution: Dict[str, Any]) -> pd.DataFrame:
        """
        DataFrame long d'une trajectoire :
          kind, rank, point_id, x, y, z,
          cumulative_time_motion_s, cumulative_energy_J
        """
        order_ids = [int(x) for x in str(solution["order"]).split(";")]
        rows: List[Dict[str, Any]] = []
        cum_t = 0.0
        cum_e = 0.0
        for rank, pid in enumerate(order_ids):
            if rank > 0:
                prev = order_ids[rank - 1]
                cum_t += self.cost_matrix[(prev, pid)]["time"]
                cum_e += self.cost_matrix[(prev, pid)]["energy"]
            pt = self.points[pid]
            rows.append({
                "kind": kind,
                "rank": rank,
                "point_id": pid,
                "x": pt["x"],
                "y": pt["y"],
                "z": pt["z"],
                "cumulative_time_motion_s": cum_t,
                "cumulative_energy_J": cum_e,
            })
        return pd.DataFrame(rows, columns=_TRAJ_COLUMNS)

    # ------------------------------------------------------------------
    # Résumé
    # ------------------------------------------------------------------
    def build_summary(
        self, selection: Dict[str, Dict[str, Any]]
    ) -> pd.DataFrame:
        rows: List[Dict[str, Any]] = []
        for kind in _KINDS:
            sol = selection[kind]
            order_ids = [int(x) for x in str(sol["order"]).split(";")]
            total_t_motion = float(sol["time"])
            total_t_stab = float(self.stabilization_time_s)
            rows.append({
                "kind": kind,
                "order": str(sol["order"]),
                "n_waypoints": len(order_ids),
                "total_time_motion_s": total_t_motion,
                "total_time_stab_s": total_t_stab,
                "total_time_s": total_t_motion + total_t_stab,
                "total_energy_J": float(sol["energy"]),
            })
        return pd.DataFrame(rows, columns=_SUMMARY_COLUMNS)

    # ------------------------------------------------------------------
    # Pipeline complet
    # ------------------------------------------------------------------
    def run_and_save(
        self, output_dir: Path | str = "data/outputs"
    ) -> Dict[str, Path]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        selection = self.select()

        # Concatenate 3 waypoint DataFrames
        traj_frames = [
            self.build_waypoints(kind, selection[kind]) for kind in _KINDS
        ]
        traj_df = pd.concat(traj_frames, ignore_index=True)
        traj_csv = output_dir / "trajectories.csv"
        traj_df.to_csv(traj_csv, index=False, float_format="%.6f")

        summary_df = self.build_summary(selection)
        summary_csv = output_dir / "trajectories_summary.csv"
        summary_df.to_csv(summary_csv, index=False, float_format="%.6f")

        logger.info("TrajectoryExtractor : 2 CSV écrits dans %s", output_dir)
        return {"trajectories": traj_csv, "summary": summary_csv}

    # ------------------------------------------------------------------
    # Utilitaires privés
    # ------------------------------------------------------------------
    @staticmethod
    def _index_points(points: pd.DataFrame) -> Dict[int, Dict[str, float]]:
        required = ["id", "x", "y", "z"]
        missing = [c for c in required if c not in points.columns]
        if missing:
            raise ValueError(f"Colonnes manquantes dans points : {missing}.")
        idx: Dict[int, Dict[str, float]] = {}
        for _, row in points.iterrows():
            idx[int(row["id"])] = {
                "x": float(row["x"]),
                "y": float(row["y"]),
                "z": float(row["z"]),
            }
        return idx

    @staticmethod
    def _index_costs(cost_matrix: pd.DataFrame) -> Dict[tuple, Dict[str, float]]:
        required = ["i", "j", "time", "energy", "feasible"]
        missing = [c for c in required if c not in cost_matrix.columns]
        if missing:
            raise ValueError(f"Colonnes manquantes dans cost_matrix : {missing}.")
        idx: Dict[tuple, Dict[str, float]] = {}
        for _, row in cost_matrix.iterrows():
            key = (int(row["i"]), int(row["j"]))
            idx[key] = {
                "time": float(row["time"]),
                "energy": float(row["energy"]),
                "feasible": bool(row["feasible"]),
            }
        return idx

    @staticmethod
    def _coerce_solutions(
        solutions: pd.DataFrame | List[dict] | Path | str
    ) -> pd.DataFrame:
        if isinstance(solutions, pd.DataFrame):
            df = solutions.copy()
        elif isinstance(solutions, (Path, str)):
            df = pd.read_csv(Path(solutions))
        elif isinstance(solutions, list):
            df = pd.DataFrame(solutions)
        else:
            raise TypeError(
                f"solutions doit être DataFrame, liste de dicts, ou chemin CSV, "
                f"reçu {type(solutions).__name__}."
            )
        required = ["solution_id", "time", "energy", "order"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Colonnes manquantes dans solutions : {missing}.")
        return df.reset_index(drop=True)

    @staticmethod
    def _select_compromise(times: np.ndarray, energies: np.ndarray) -> int:
        """
        Indice de la solution minimisant la distance euclidienne à l'idéal
        (0, 0) après normalisation min-max des deux objectifs.

        Cas dégénéré : si un des ranges est nul, on considère la
        normalisation correspondante comme identiquement nulle.
        """
        def _norm(x: np.ndarray) -> np.ndarray:
            lo, hi = float(x.min()), float(x.max())
            rng = hi - lo
            if rng < 1e-12:
                return np.zeros_like(x)
            return (x - lo) / rng

        t_n = _norm(times)
        e_n = _norm(energies)
        d = np.sqrt(t_n ** 2 + e_n ** 2)
        return int(np.argmin(d))
