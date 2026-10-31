"""
BLOC 11 — Comparateur (Comparator)
====================================

Référence : contrat de comparaison des trajectoires SP2 (BLOC 11).
Portée    : mesurer le gain des trajectoires optimisées vs une baseline
            zigzag, à points et modèle identiques (test d'équité §7).

Baseline zigzag
---------------
Balayage boustrophédon sur la grille, ligne par ligne :
  - ligne 0 : colonnes 0 → n-1
  - ligne 1 : colonnes n-1 → 0
  - ligne 2 : colonnes 0 → n-1
  - …
Le centre est fixé en début et en fin (départ/retour obligatoires).
Si le centre est dans le corps du zigzag, il est sauté (un seul passage).

Alternative `direction='cols'` : balayage colonne par colonne (par symétrie).

Format de sortie (§6)
---------------------
  - baseline_zigzag.csv : CSV waypoints de la baseline (mêmes colonnes
                          que trajectories.csv pour cohérence)
  - comparison.csv      : tableau 4 lignes (kind, time, energy, distance,
                          n_waypoints, gain_time_vs_baseline_pct,
                          gain_energy_vs_baseline_pct)
    - comparison.png      : figure des temps et énergies comparés.

Aucun recalcul géométrique nouveau : tout est extrait du cost_matrix
de BLOC 6. Le Comparator est purement analytique.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from visualization.labels import kind_label

from src.config import Config

logger = logging.getLogger(__name__)

_COMPARISON_COLUMNS = [
    "kind", "time_motion_s", "energy_J", "distance_m",
    "n_waypoints", "gain_time_vs_baseline_pct", "gain_energy_vs_baseline_pct",
]

_WAYPOINT_COLUMNS = [
    "kind", "rank", "point_id", "x", "y", "z",
    "cumulative_time_motion_s", "cumulative_energy_J",
]


class Comparator:
    """Compare la baseline zigzag aux 3 trajectoires optimisées."""

    def __init__(
        self,
        config: Config,
        points: pd.DataFrame,
        cost_matrix: pd.DataFrame,
        trajectories_summary: pd.DataFrame,
        trajectories: pd.DataFrame,
    ) -> None:
        self.config = config
        self.points_df = points.copy()
        self.points = self._index_points(points)
        self.cost = self._index_costs(cost_matrix)
        self.summary = trajectories_summary.copy()
        self.trajectories = trajectories.copy()
        self.center_id = self._identify_center_id(points)
        self._baseline_kind: str = "baseline_zigzag"  # défaut, recalculé dans build_zigzag_order

    # ------------------------------------------------------------------
    # Baseline zigzag
    # ------------------------------------------------------------------
    def build_zigzag_order(self, direction: str = "rows") -> List[int]:
        """
        Construit l'ordre de la baseline.

        Stratégie :
          - Grille complète (n_rangs × n_colonnes points) → balayage
            boustrophédon (zigzag), quasi-optimal sur grille régulière.
          - Grille incomplète (points filtrés par WFW) → heuristique du
            plus proche voisin, généralisation naturelle du zigzag.

        Dans les deux cas : départ et retour au centre (D-BLOC11-01).
        Le kind effectivement utilisé est exposé dans `self._baseline_kind`
        (`baseline_zigzag` ou `baseline_nn`) et propagé dans tous les CSV.
        """
        df = self.points_df
        n_r = self.config.n_rangs
        n_c = self.config.n_colonnes

        # --- Détection de grille complète ---
        full_grid = (
            len(df) == n_r * n_c
            and df["ligne"].nunique() == n_r
            and df["colonne"].nunique() == n_c
        )

        if full_grid:
            order = self._build_zigzag_full(n_r, n_c, direction)
            self._baseline_kind = "baseline_zigzag"
            logger.info(
                "Baseline : zigzag %s (grille complète %d×%d).",
                direction, n_r, n_c,
            )
        else:
            order = self._build_nearest_neighbor()
            self._baseline_kind = "baseline_nn"
            logger.warning(
                "Baseline : grille incomplète (%d points sur %d attendus). "
                "Bascule sur l'heuristique du plus proche voisin.",
                len(df), n_r * n_c,
            )

        # --- Départ/retour obligatoires au centre ---
        if order[0] != self.center_id or order[-1] != self.center_id:
            order = [x for x in order if x != self.center_id]
            order = [self.center_id, *order, self.center_id]

        return order

    def _build_zigzag_full(
        self, n_r: int, n_c: int, direction: str
    ) -> List[int]:
        """Zigzag boustrophédon sur grille régulière complète."""
        df = self.points_df
        grid: Dict[tuple, int] = {}
        for _, row in df.iterrows():
            grid[(int(row["ligne"]), int(row["colonne"]))] = int(row["id"])

        order: List[int] = []
        if direction == "rows":
            for i in range(n_r):
                cols = range(n_c) if i % 2 == 0 else range(n_c - 1, -1, -1)
                for j in cols:
                    order.append(grid[(i, j)])
        elif direction == "cols":
            for j in range(n_c):
                rows = range(n_r) if j % 2 == 0 else range(n_r - 1, -1, -1)
                for i in rows:
                    order.append(grid[(i, j)])
        else:
            raise ValueError(
                f"direction doit être 'rows' ou 'cols', reçu {direction!r}."
            )
        return order

    def _build_nearest_neighbor(self) -> List[int]:
        """
        Heuristique du plus proche voisin avec backtracking borné.

        Depuis le centre, on visite itérativement le point non visité
        le plus proche dont la paire (current → candidat) est FAISABLE
        dans cost_matrix. Si un blocage survient (aucun voisin faisable),
        on revient en arrière et on essaie une alternative.

        Le backtracking est borné par une limite de temps (5 s) pour
        éviter une explosion combinatoire sur les graphes denses. Sur
        les instances usuelles (< 50 points), la recherche directe
        aboutit en quelques millisecondes.
        """
        import time as _time

        ids_non_center = [i for i in self.points if i != self.center_id]
        if not ids_non_center:
            return [self.center_id, self.center_id]

        deadline = _time.perf_counter() + 5.0

        # --- Helpers ---
        def _feasible_neighbors(current: int, remaining: set) -> List[int]:
            """Candidats faisables depuis current, triés par distance²."""
            pc = self.points[current]
            cands: List[tuple] = []
            for cand in remaining:
                row = self.cost.get((current, cand))
                if row is None or not row["feasible"]:
                    continue
                pd_ = self.points[cand]
                d = (
                    (pc["x"] - pd_["x"]) ** 2
                    + (pc["y"] - pd_["y"]) ** 2
                    + (pc["z"] - pd_["z"]) ** 2
                )
                cands.append((d, cand))
            cands.sort()
            return [c for _, c in cands]

        def _dfs(current: int, remaining: set, path: List[int]) -> List[int] | None:
            if _time.perf_counter() > deadline:
                return None
            if not remaining:
                return path
            for nxt in _feasible_neighbors(current, remaining):
                result = _dfs(nxt, remaining - {nxt}, [*path, nxt])
                if result is not None:
                    return result
            return None  # impasse locale

        path = _dfs(self.center_id, set(ids_non_center), [self.center_id])
        if path is None:
            raise RuntimeError(
                f"Impossible de construire une baseline NN visitant les "
                f"{len(ids_non_center)} points : aucune séquence faisable "
                f"trouvée en 5 s. Le graphe de faisabilité n'admet "
                f"probablement pas de chemin hamiltonien."
            )

        # Retour au centre (vérif faisabilité)
        last = path[-1]
        row = self.cost.get((last, self.center_id))
        if row is None or not row["feasible"]:
            raise RuntimeError(
                f"Retour au centre impossible : paire "
                f"({last}, {self.center_id}) infaisable."
            )
        path.append(self.center_id)
        return path

    # ------------------------------------------------------------------
    # Évaluation d'un tour (baseline)
    # ------------------------------------------------------------------
    def evaluate_tour(self, order_ids: List[int]) -> Dict[str, Any]:
        """
        Calcule time, energy, distance cumulés pour un ordre donné.
        Utilise exclusivement cost_matrix — pas de recalcul géométrique.
        """
        t = 0.0
        e = 0.0
        d = 0.0
        for k in range(len(order_ids) - 1):
            i, j = order_ids[k], order_ids[k + 1]
            row = self.cost.get((i, j))
            if row is None:
                raise KeyError(f"Paire ({i}, {j}) absente du cost_matrix.")
            if not row["feasible"]:
                raise ValueError(f"Paire ({i}, {j}) infaisable.")
            t += row["time"]
            e += row["energy"]
            d += row["distance"]
        return {"time_motion_s": t, "energy_J": e, "distance_m": d}

    def build_baseline_dataframe(self, order_ids: List[int]) -> pd.DataFrame:
        """DataFrame long de la baseline (mêmes colonnes que trajectories.csv)."""
        rows: List[Dict[str, Any]] = []
        cum_t = 0.0
        cum_e = 0.0
        for rank, pid in enumerate(order_ids):
            if rank > 0:
                prev = order_ids[rank - 1]
                row = self.cost[(prev, pid)]
                cum_t += row["time"]
                cum_e += row["energy"]
            pt = self.points[pid]
            rows.append({
                "kind": self._baseline_kind,
                "rank": rank,
                "point_id": pid,
                "x": pt["x"], "y": pt["y"], "z": pt["z"],
                "cumulative_time_motion_s": cum_t,
                "cumulative_energy_J": cum_e,
            })
        return pd.DataFrame(rows, columns=_WAYPOINT_COLUMNS)

    # ------------------------------------------------------------------
    # Comparaison globale
    # ------------------------------------------------------------------
    def compare(self, direction: str = "rows") -> pd.DataFrame:
        """
        Construit le tableau 4 lignes :
          baseline_zigzag, time_opt, energy_opt, compromise.
        Les gains sont exprimés en % par rapport à la baseline
        (positif = amélioration).
        """
        order_zz = self.build_zigzag_order(direction=direction)
        baseline_metrics = self.evaluate_tour(order_zz)

        rows: List[Dict[str, Any]] = [{
            "kind": self._baseline_kind,
            "time_motion_s": baseline_metrics["time_motion_s"],
            "energy_J": baseline_metrics["energy_J"],
            "distance_m": baseline_metrics["distance_m"],
            "n_waypoints": len(order_zz),
            "gain_time_vs_baseline_pct": 0.0,
            "gain_energy_vs_baseline_pct": 0.0,
        }]

        base_t = baseline_metrics["time_motion_s"]
        base_e = baseline_metrics["energy_J"]

        for _, row in self.summary.iterrows():
            kind = str(row["kind"])
            t = float(row["total_time_motion_s"])
            e = float(row["total_energy_J"])
            # Distance de l'optimisé : on reconstruit depuis trajectories.csv
            sub = self.trajectories[self.trajectories["kind"] == kind]
            dist = self._tour_distance_from_waypoints(sub)
            rows.append({
                "kind": kind,
                "time_motion_s": t,
                "energy_J": e,
                "distance_m": dist,
                "n_waypoints": int(row["n_waypoints"]),
                "gain_time_vs_baseline_pct": (base_t - t) / base_t * 100.0,
                "gain_energy_vs_baseline_pct": (base_e - e) / base_e * 100.0,
            })

        return pd.DataFrame(rows, columns=_COMPARISON_COLUMNS)

    # ------------------------------------------------------------------
    # Figure comparative
    # ------------------------------------------------------------------

    def plot_comparison(
        self,
        comparison_df: pd.DataFrame,
        output_path: Path,
    ) -> Path:
        """
        2 sous-graphes (temps, énergie) avec barres groupées, 4 catégories.
        """
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        kinds = comparison_df["kind"].tolist()
        labels = [kind_label(kind) for kind in kinds]
        times = comparison_df["time_motion_s"].to_numpy()
        energies = comparison_df["energy_J"].to_numpy()

        colors = {
            "baseline_zigzag": "#7f7f7f",
            "baseline_nn": "#7f7f7f",   # même gris neutre
            "time_opt": "#2ca02c",
            "energy_opt": "#d62728",
            "compromise": "#9467bd",
        }
        bar_colors = [colors.get(k, "#000000") for k in kinds]

        fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

        # --- Temps ---
        ax = axes[0]
        bars = ax.bar(labels, times, color=bar_colors, edgecolor="black")
        for bar, v, k in zip(bars, times, kinds, strict=True):
            gain = comparison_df.loc[
                comparison_df["kind"] == k, "gain_time_vs_baseline_pct"
            ].iloc[0]
            label = f"{v:.1f} s"

            if k != self._baseline_kind:
                label += f"\n({gain:+.1f} %)"

            # Modification ici : v / 2 pour centrer, texte en blanc et gras
            ax.text(bar.get_x() + bar.get_width() / 2, v / 2,
                    label, ha="center", va="center", fontsize=10,
                    color="white", fontweight="bold")

        ax.set_ylabel("Temps de déplacement (s)")
        ax.set_title("Temps — baseline et trajectoires")
        ax.grid(True, axis="y", alpha=0.3)
        ax.tick_params(axis="x", rotation=15)

        # --- Énergie ---
        ax = axes[1]
        bars = ax.bar(labels, energies, color=bar_colors, edgecolor="black")

        # zip sur 'energies' : la hauteur v est en joules pour ce subplot.
        for bar, v, k in zip(bars, energies, kinds, strict=True):
            gain = comparison_df.loc[
                comparison_df["kind"] == k, "gain_energy_vs_baseline_pct"
            ].iloc[0]
            label = f"{v:.1f} J"

            if k != self._baseline_kind:
                label += f"\n({gain:+.1f} %)"

            # Modification ici : v / 2 pour centrer, texte en blanc et gras
            ax.text(bar.get_x() + bar.get_width() / 2, v / 2,
                    label, ha="center", va="center", fontsize=10,
                    color="white", fontweight="bold")

        ax.set_ylabel("Énergie (J)")
        ax.set_title("Énergie — baseline et trajectoires")
        ax.grid(True, axis="y", alpha=0.3)
        ax.tick_params(axis="x", rotation=15)

        fig.tight_layout()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info("Figure comparative écrite : %s", output_path)
        return output_path

    # ------------------------------------------------------------------
    # Pipeline complet
    # ------------------------------------------------------------------
    def run_and_save(
        self,
        output_dir: Path | str = "data/outputs",
        direction: str = "rows",
    ) -> Dict[str, Path]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        figures_dir = output_dir / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)

        order_zz = self.build_zigzag_order(direction=direction)
        baseline_df = self.build_baseline_dataframe(order_zz)
        csv_baseline = output_dir / "baseline_zigzag.csv"
        baseline_df.to_csv(csv_baseline, index=False, float_format="%.6f")

        comparison_df = self.compare(direction=direction)
        csv_comp = output_dir / "comparison.csv"
        comparison_df.to_csv(csv_comp, index=False, float_format="%.6f")

        png = self.plot_comparison(
            comparison_df, figures_dir / "comparison.png"
        )

        png_grid = self.plot_trajectories_grid(
            baseline_df, figures_dir / "trajectories_comparison_grid.png"
        )

        png_2d = self.plot_trajectories_2d(
            baseline_df, figures_dir / "trajectories_comparison_2d.png"
        )

        # Diagnostic — écrit dans un JSON à côté
        diag = self.diagnose()
        diag_path = output_dir / "comparison_diagnostic.json"
        import json as _json
        with diag_path.open("w", encoding="utf-8") as f:
            _json.dump(diag, f, indent=2, ensure_ascii=False)

        logger.info(
            "Comparator : baseline=%d waypoints, "
            "optimal_beats_baseline=%s, 2 CSV + 1 PNG + 1 JSON",
            len(order_zz), diag["optimal_beats_baseline"],
        )
        return {
            "baseline": csv_baseline,
            "comparison": csv_comp,
            "figure": png,
            "figure_grid": png_grid,
            "figure_2d": png_2d,
            "diagnostic": diag_path,
        }

    def diagnose(self) -> Dict[str, Any]:
        """
        Diagnostic de qualité : l'optimisation bat-elle la baseline ?

        Analyse par trajectoire (D-BLOC11-09). Distingue :
          - Dégradation "attendue" : time_opt est plus énergivore que la
            baseline, ou energy_opt est plus lente que la baseline. C'est
            la signature d'un trade-off multi-objectif normal.
          - Dégradation "anormale" : une trajectoire est strictement pire
            sur les DEUX objectifs — signe d'un problème d'optimisation.

        Retour
        ------
        dict avec :
            optimal_beats_baseline : bool (au moins une trajectoire
                strictement meilleure sur au moins un objectif, aucune
                strictement pire sur les deux)
            tradeoff_only : bool — dégradations uniquement attendues
            per_trajectory : gains par kind
            warning : message si dégradation anormale
        """
        df = self.compare()
        base = df[df["kind"] == self._baseline_kind].iloc[0]
        tol = 1e-6

        per_kind: Dict[str, Dict[str, float]] = {}
        has_anomaly = False
        has_any_improvement = False

        for _, row in df[df["kind"] != self._baseline_kind].iterrows():
            kind = str(row["kind"])
            g_t = float(row["gain_time_vs_baseline_pct"])
            g_e = float(row["gain_energy_vs_baseline_pct"])
            per_kind[kind] = {"gain_time_pct": g_t, "gain_energy_pct": g_e}

            # Amélioration sur au moins un objectif ?
            if g_t > tol or g_e > tol:
                has_any_improvement = True

            # Dégradation sur LES DEUX objectifs → anormal
            if g_t < -tol and g_e < -tol:
                has_anomaly = True

        # Signal : au moins une amélioration, aucune anomalie
        optimal_beats = has_any_improvement and not has_anomaly
        tradeoff_only = has_any_improvement and not has_anomaly

        warn: Any = None
        if has_anomaly:
            warn = (
                f"Anomalie détectée : au moins une trajectoire optimisée "
                f"est PIRE que la baseline sur les DEUX objectifs. "
                f"Détail : {per_kind}. Augmenter pop_size/n_gen ou "
                f"vérifier la fitness."
            )
            logger.warning(warn)
        elif not has_any_improvement:
            warn = (
                "Aucune trajectoire optimisée n'améliore la baseline sur "
                "au moins un objectif. Résultat suspect."
            )
            logger.warning(warn)

        # Pires gains observés (pour information, pas pour décider)
        worst_gain_t = min(v["gain_time_pct"] for v in per_kind.values())
        worst_gain_e = min(v["gain_energy_pct"] for v in per_kind.values())

        return {
            "baseline_kind": self._baseline_kind,
            "optimal_beats_baseline": bool(optimal_beats),
            "tradeoff_only": bool(tradeoff_only),
            "has_anomaly": bool(has_anomaly),
            "min_time_gain_pct": float(worst_gain_t),
            "min_energy_gain_pct": float(worst_gain_e),
            "baseline_time_s": float(base["time_motion_s"]),
            "baseline_energy_J": float(base["energy_J"]),
            "per_trajectory": per_kind,
            "warning": warn,
        }


    def plot_trajectories_grid(
        self,
        baseline_df: pd.DataFrame,
        output_path: Path,
    ) -> Path:
        """
        Grille 2×2 : baseline + 3 optimisées, côte à côte.
        Chaque sous-graphe affiche la grille complète en gris clair et
        la trajectoire correspondante en couleur.
        """
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

        # Positions de la grille complète (fond gris)
        pts = pd.DataFrame([
            {"x": v["x"], "y": v["y"], "z": v["z"]}
            for v in self.points.values()
        ])

        panels = [
            (self._baseline_kind, baseline_df, "#7f7f7f", "-"),
            ("time_opt",       self.trajectories[self.trajectories["kind"] == "time_opt"],
             "#2ca02c", "-"),
            ("energy_opt",     self.trajectories[self.trajectories["kind"] == "energy_opt"],
             "#d62728", "--"),
            ("compromise",     self.trajectories[self.trajectories["kind"] == "compromise"],
             "#9467bd", "-."),
        ]

        fig = plt.figure(figsize=(14, 11))
        for k, (kind, df, color, ls) in enumerate(panels):
            ax = fig.add_subplot(2, 2, k + 1, projection="3d")
            ax.scatter(pts["x"], pts["y"], pts["z"],
                       s=12, c="lightgray", alpha=0.6)
            df_sorted = df.sort_values("rank")
            ax.plot(df_sorted["x"], df_sorted["y"], df_sorted["z"],
                    color=color, linestyle=ls, linewidth=1.5)

            # Centre (départ/retour)
            first = df_sorted.iloc[0]
            ax.scatter([first["x"]], [first["y"]], [first["z"]],
                       marker="*", s=150, c="black",
                       edgecolors="white", linewidths=1.0, zorder=10)

            t_total = df_sorted["cumulative_time_motion_s"].iloc[-1]
            e_total = df_sorted["cumulative_energy_J"].iloc[-1]
            ax.set_title(f"{kind_label(kind)}\nt={t_total:.1f} s  |  E={e_total:.1f} J",
                         fontsize=11)
            ax.set_xlabel("x (m)", fontsize=9)
            ax.set_ylabel("y (m)", fontsize=9)
            ax.set_zlabel("z (m)", fontsize=9)
            ax.tick_params(labelsize=8)

        fig.suptitle("Comparaison baseline et trajectoires",
                     fontsize=14, y=0.995)
        fig.tight_layout()

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info("Figure grille comparative écrite : %s", output_path)
        return output_path

    def plot_trajectories_2d(
        self,
        baseline_df: pd.DataFrame,
        output_path: Path,
    ) -> Path:
        """
        Vue de dessus (2D) des 4 trajectoires : baseline + 3 optimisées.
        Grille 2×2, une trajectoire par sous-graphe.

        Complète la figure comparative en barres (plot_comparison) :
        celle-ci montre les **géométries** des tours, l'autre les **totaux**.
        """
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        pts = self.points_df  # grille complète en arrière-plan

        panels = [
            (self._baseline_kind, baseline_df, "#7f7f7f"),
            ("time_opt",
             self.trajectories[self.trajectories["kind"] == "time_opt"],
             "#2ca02c"),
            ("energy_opt",
             self.trajectories[self.trajectories["kind"] == "energy_opt"],
             "#d62728"),
            ("compromise",
             self.trajectories[self.trajectories["kind"] == "compromise"],
             "#9467bd"),
        ]

        fig, axes = plt.subplots(2, 2, figsize=(12, 12))

        for ax, (kind, df, color) in zip(axes.flat, panels, strict=True):
            # Grille en arrière-plan (points gris clair)
            ax.scatter(
                pts["x"], pts["y"],
                s=18, c="lightgray", zorder=1,
            )
            # Trajectoire
            df_sorted = df.sort_values("rank")
            ax.plot(
                df_sorted["x"], df_sorted["y"],
                "-", color=color, linewidth=1.8,
                zorder=3, alpha=0.85,
            )
            ax.scatter(
                df_sorted["x"], df_sorted["y"],
                s=10, c=color, zorder=4,
                edgecolors="white", linewidths=0.4,
            )
            # Centre (départ/retour) — marqueur étoile
            first = df_sorted.iloc[0]
            ax.scatter(
                [first["x"]], [first["y"]],
                marker="*", s=250, c="black",
                edgecolors="white", linewidths=1.0,
                zorder=5, label="Centre",
            )
            # Métriques dans le titre
            t_total = df_sorted["cumulative_time_motion_s"].iloc[-1]
            e_total = df_sorted["cumulative_energy_J"].iloc[-1]
            ax.set_title(
                f"{kind_label(kind)}\nt = {t_total:.1f} s  |  E = {e_total:.1f} J",
                fontsize=11,
            )
            ax.set_aspect("equal")
            ax.grid(alpha=0.3)
            ax.set_xlabel("x (m)")
            ax.set_ylabel("y (m)")

        fig.suptitle(
            "Trajectoires — vue de dessus (2D)",
            fontsize=14, y=0.995,
        )
        fig.tight_layout()

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info("Figure 2D comparative écrite : %s", output_path)
        return output_path



    # ------------------------------------------------------------------
    # Utilitaires
    # ------------------------------------------------------------------
    @staticmethod
    def _index_points(points: pd.DataFrame) -> Dict[int, Dict[str, float]]:
        required = ["id", "x", "y", "z"]
        missing = [c for c in required if c not in points.columns]
        if missing:
            raise ValueError(f"Colonnes manquantes dans points : {missing}.")
        return {
            int(row["id"]): {
                "x": float(row["x"]), "y": float(row["y"]), "z": float(row["z"]),
            }
            for _, row in points.iterrows()
        }

    @staticmethod
    def _index_costs(cost_matrix: pd.DataFrame) -> Dict[tuple, Dict[str, float]]:
        required = ["i", "j", "time", "energy", "feasible", "distance"]
        missing = [c for c in required if c not in cost_matrix.columns]
        if missing:
            raise ValueError(f"Colonnes manquantes dans cost_matrix : {missing}.")
        return {
            (int(row["i"]), int(row["j"])): {
                "time": float(row["time"]),
                "energy": float(row["energy"]),
                "distance": float(row["distance"]),
                "feasible": bool(row["feasible"]),
            }
            for _, row in cost_matrix.iterrows()
        }

    def _points_dataframe(self) -> pd.DataFrame:
        """Retourne le DataFrame original des points (avec ligne/colonne)."""
        return self.points_df

    @staticmethod
    def _identify_center_id(points: pd.DataFrame) -> int:
        dist = np.hypot(points["x"], points["y"])
        idx = dist.idxmin()
        if dist.loc[idx] > 1e-9:
            raise ValueError("Centre (0, 0) absent de la grille.")
        return int(points.loc[idx, "id"])

    def _tour_distance_from_waypoints(self, sub: pd.DataFrame) -> float:
        """Reconstruit la distance totale depuis les waypoints (rank-ordonnés)."""
        sub = sub.sort_values("rank").reset_index(drop=True)
        ids = sub["point_id"].astype(int).tolist()
        d = 0.0
        for k in range(len(ids) - 1):
            row = self.cost.get((ids[k], ids[k + 1]))
            if row is None:
                continue
            d += row["distance"]
        return d
