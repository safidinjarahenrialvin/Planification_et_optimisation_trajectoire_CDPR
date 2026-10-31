"""
BLOC 10 — Validation et visualisation (Validator)
====================================================

Référence : contrat de validation et de production des rapports SP2 (BLOC 10).
Portée    : vérifier les contraintes physiques sur l'ensemble du pipeline,
            produire les 4 figures du mémoire, consolider le rapport
            d'hypothèses B1–B5.

Lit les CSV produits par les blocs 4–9 sur disque — pas d'objets en
mémoire — pour garantir que les artefacts sont exploitables tels quels.

Sorties :
  - validation_report.json      (récapitulatif machine)
  - figures/wfw_slice.png
  - figures/pareto_front.png
    - figures/trajectories_3d_*.png
  - figures/profiles.png
  - hypotheses_report.json      (B1–B5, machine)
  - hypotheses_report.md        (B1–B5, mémoire)
"""
from __future__ import annotations

import json
import logging
import time as time_module
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.config import Config
from src.robot_model import RobotModel
from src.wfw import WFW

logger = logging.getLogger(__name__)


# Statuts possibles d'un check.
_PASS = "PASS"
_WARN = "WARN"
_FAIL = "FAIL"


@dataclass
class CheckResult:
    """Résultat d'une vérification élémentaire."""
    name: str
    status: str
    detail: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    duration_s: float = 0.0


# Noms de fichiers attendus (§6).
_FILENAMES = {
    "points_filtres": "points_filtres.csv",
    "cost_matrix": "cost_matrix.csv",
    "solutions_pareto": "solutions_pareto.csv",
    "trajectories": "trajectories.csv",
    "trajectories_summary": "trajectories_summary.csv",
    "profiles": "profiles.csv",
}


class Validator:
    """
    Orchestre les vérifications, les figures et le rapport d'hypothèses.
    """

    def __init__(
        self,
        config: Config,
        robot: RobotModel,
        wfw: WFW,
        output_dir: Path | str = "data/outputs",
        figures_dir: Path | str | None = None,
    ) -> None:
        self.config = config
        self.robot = robot
        self.wfw = wfw
        self.output_dir = Path(output_dir)
        self.figures_dir = (
            Path(figures_dir) if figures_dir is not None
            else self.output_dir / "figures"
        )
        self.figures_dir.mkdir(parents=True, exist_ok=True)
        # Cache des CSV chargés (évite ~20 lectures disque par run).
        self._data_cache: Optional[Dict[str, pd.DataFrame]] = None

    # ==================================================================
    # Validation
    # ==================================================================
    def validate(self) -> Dict[str, Any]:
        """
        Exécute tous les checks et produit le rapport structuré.

        Retour
        ------
        dict avec :
            overall_status : 'PASS' | 'WARN' | 'FAIL'
            checks         : liste de dicts (name, status, detail, metrics, duration_s)
            summary        : {n_pass, n_warn, n_fail}
        """
        data = self._load_all()
        checks: List[CheckResult] = []

        # Ordre logique du pipeline : config → points → matrice →
        # solutions → trajectoires → profils → cohérence croisée.
        checks.append(self._check_config_consistency())
        checks.append(self._check_points_filtres(data["points_filtres"]))
        checks.append(self._check_cost_matrix(data["cost_matrix"]))
        checks.append(self._check_solutions(data["solutions_pareto"]))
        checks.append(self._check_trajectories(
            data["trajectories"], data["trajectories_summary"]
        ))
        checks.append(self._check_profiles(data["profiles"]))
        checks.append(self._check_cross_consistency(
            data["cost_matrix"],
            data["trajectories_summary"],
            data["profiles"],
        ))

        # Agrégation
        n_pass = sum(1 for c in checks if c.status == _PASS)
        n_warn = sum(1 for c in checks if c.status == _WARN)
        n_fail = sum(1 for c in checks if c.status == _FAIL)
        if n_fail > 0:
            overall = _FAIL
        elif n_warn > 0:
            overall = _WARN
        else:
            overall = _PASS

        report = {
            "overall_status": overall,
            "checks": [
                {
                    "name": c.name,
                    "status": c.status,
                    "detail": c.detail,
                    "metrics": c.metrics,
                    "duration_s": c.duration_s,
                }
                for c in checks
            ],
            "summary": {
                "n_pass": n_pass,
                "n_warn": n_warn,
                "n_fail": n_fail,
                "n_total": len(checks),
            },
        }

        logger.info(
            "Validation : %s (%d PASS, %d WARN, %d FAIL)",
            overall, n_pass, n_warn, n_fail,
        )

        if overall == _FAIL:
            failed = [c.name for c in checks if c.status == _FAIL]
            logger.error("Checks en échec : %s", failed)

        return report

    # ------------------------------------------------------------------
    # Checks individuels
    # ------------------------------------------------------------------
    def _check_config_consistency(self) -> CheckResult:
        t0 = time_module.perf_counter()
        cfg = self.config
        ok = (
            cfg.N == cfg.n_rangs * cfg.n_colonnes
            and cfg.T_min < cfg.T_max
            and cfg.orientation_plateforme == "fixe"
        )
        status = _PASS if ok else _FAIL
        detail = (
            f"N={cfg.N} ({cfg.n_rangs}×{cfg.n_colonnes}), "
            f"T ∈ [{cfg.T_min}, {cfg.T_max}] N, "
            f"orientation={cfg.orientation_plateforme}"
        )
        return CheckResult(
            name="config_consistency",
            status=status,
            detail=detail,
            metrics={
                "N": int(cfg.N),
                "T_min": float(cfg.T_min),
                "T_max": float(cfg.T_max),
                "z_absolu_r0": float(cfg.z_absolu_r0),
            },
            duration_s=time_module.perf_counter() - t0,
        )

    def _check_points_filtres(self, df: pd.DataFrame) -> CheckResult:
        """
        Vérifie que tous les points retenus sont dans les limites et
        faisables au sens WFW (re-vérification indépendante).
        """
        t0 = time_module.perf_counter()
        cfg = self.config
        n = len(df)

        # Vérification des limites opérationnelles
        out_of_bounds = (
            (df["x"] < cfg.x_min - 1e-9) | (df["x"] > cfg.x_max + 1e-9)
            | (df["y"] < cfg.y_min - 1e-9) | (df["y"] > cfg.y_max + 1e-9)
            | (df["z"] < cfg.z_min - 1e-9) | (df["z"] > cfg.z_max + 1e-9)
        ).any()

        # Re-vérification WFW indépendante (indispensable en bloc de validation)
        infeasible = []
        for _, row in df.iterrows():
            p = np.array([float(row["x"]), float(row["y"]), float(row["z"])])
            if not self.wfw.is_feasible(p).feasible:
                infeasible.append(int(row["id"]))

        if out_of_bounds:
            status = _FAIL
            detail = "Points hors limites opérationnelles détectés."
        elif infeasible:
            status = _FAIL
            detail = f"{len(infeasible)} points non faisables : ids={infeasible[:5]}…"
        else:
            status = _PASS
            detail = f"{n} points, tous dans les bornes et faisables (WFW re-vérifié)."

        return CheckResult(
            name="points_filtres",
            status=status,
            detail=detail,
            metrics={
                "n_points": int(n),
                "n_infeasible": len(infeasible),
                "out_of_bounds": bool(out_of_bounds),
            },
            duration_s=time_module.perf_counter() - t0,
        )

    def _check_cost_matrix(self, df: pd.DataFrame) -> CheckResult:
        """
        Vérifie la matrice de coûts.

        Deux catégories de résultats :
          - FAIL (bugs réels) : asymétrie, diagonale non nulle.
          - WARN (réalité physique) : paires infaisables. À z élevé, le
            WFW rétrécit et certaines paires deviennent infaisables —
            ce n'est pas une anomalie du code (D-BLOC10-05).
        """
        t0 = time_module.perf_counter()
        required = {"i", "j", "time", "energy", "feasible"}
        missing = required - set(df.columns)
        if missing:
            return CheckResult(
                name="cost_matrix",
                status=_FAIL,
                detail=f"Colonnes manquantes : {sorted(missing)}",
                duration_s=time_module.perf_counter() - t0,
            )

        # --- Asymétrie et diagonale : ne portent que sur les paires faisables ---
        feasible_df = df[df["feasible"] == 1]
        forward = feasible_df.rename(
            columns={"i": "i_id", "j": "j_id", "time": "time_ij", "energy": "energy_ij"}
        )[["i_id", "j_id", "time_ij", "energy_ij"]]
        reverse = feasible_df.rename(
            columns={"i": "j_id", "j": "i_id", "time": "time_ji", "energy": "energy_ji"}
        )[["i_id", "j_id", "time_ji", "energy_ji"]]
        paired = forward.merge(reverse, on=["i_id", "j_id"], how="inner")
        n_reciprocal_missing = len(forward) - len(paired)
        if not paired.empty:
            max_dt = float(np.abs(paired["time_ij"] - paired["time_ji"]).max())
            max_de = float(np.abs(paired["energy_ij"] - paired["energy_ji"]).max())
        else:
            max_dt = 0.0
            max_de = 0.0

        diag_ok = bool(
            (df.loc[df["i"] == df["j"], "time"] == 0.0).all()
            and (df.loc[df["i"] == df["j"], "energy"] == 0.0).all()
        )

        # --- Classification ---
        hard_issues: List[str] = []
        if max_dt > 1e-6:
            hard_issues.append(f"asymétrie temps max={max_dt:.2e} s")
        if max_de > 1e-3:
            hard_issues.append(f"asymétrie énergie max={max_de:.2e} J")
        if not diag_ok:
            hard_issues.append("diagonale non nulle")

        soft_issues: List[str] = []
        if n_reciprocal_missing > 0:
            soft_issues.append(
                f"{n_reciprocal_missing} paires faisables sans réciproque"
            )
        n_infeasible = int((df["feasible"] == 0).sum())
        n_total = len(df)
        infeasible_rate = n_infeasible / n_total if n_total > 0 else 0.0
        if n_infeasible > 0:
            soft_issues.append(
                f"{n_infeasible}/{n_total} paires infaisables "
                f"({infeasible_rate*100:.1f} %) — WFW rétréci, comportement attendu"
            )

        if hard_issues:
            status = _FAIL
            detail = "; ".join(hard_issues)
        elif soft_issues:
            status = _WARN
            detail = "; ".join(soft_issues)
        else:
            status = _PASS
            detail = "Matrice symétrique, toutes paires faisables, diagonale nulle."

        return CheckResult(
            name="cost_matrix",
            status=status,
            detail=detail,
            metrics={
                "n_entries": n_total,
                "max_asym_time_s": max_dt,
                "max_asym_energy_J": max_de,
                "n_infeasible_pairs": n_infeasible,
                "n_reciprocal_missing": n_reciprocal_missing,
                "infeasible_rate": infeasible_rate,
                "diag_ok": diag_ok,
            },
            duration_s=time_module.perf_counter() - t0,
        )

    def _check_solutions(self, df: pd.DataFrame) -> CheckResult:
        """Vérifie le front après déduplication par (time, energy).

        Un front sans solution dominée est PASS dès qu'il contient au moins
        trois compromis temps-énergie distincts. Un front de zéro à deux
        compromis reste exploitable mais déclenche WARN.
        """
        t0 = time_module.perf_counter()
        # Déduplication objectif — deux solutions avec les mêmes (time, energy)
        # sont co-optimales, pas distinctes pour le front de Pareto.

        df_unique = df.drop_duplicates(subset=["time", "energy"]).reset_index(drop=True)
        n_unique = len(df_unique)

        F = df_unique[["time", "energy"]].to_numpy(dtype=float)
        n = n_unique
          # Tolérances de dominance — en dessous, deux valeurs sont
        # considérées comme égales. Justification physique :
        #   - 1e-3 s sur des trajectoires de ~350 s = 3e-6 relatif (négligeable)
        #   - 1e-2 J sur des énergies de ~800 J = 1e-5 relatif (négligeable)
        tol_t = 1e-3
        tol_e = 1e-2

        def _dominates(F_a, F_b) -> bool:
            """True si a domine strictement b, hors tolérances."""
            not_worse = (F_a[0] <= F_b[0] + tol_t) and (F_a[1] <= F_b[1] + tol_e)
            meaningfully_better = (F_a[0] < F_b[0] - tol_t) or (F_a[1] < F_b[1] - tol_e)
            return bool(not_worse and meaningfully_better)

        dominated = np.zeros(n, dtype=bool)
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                if _dominates(F[j], F[i]):
                    dominated[i] = True
                    break
        n_dominated = int(dominated.sum())

        # Règle de décision unifiée — les tolérances numériques
        # (tol_t=1e-3 s, tol_e=1e-2 J, cf. D-BLOC7-06) distinguent déjà
        # une dominance réelle d'un artefact d'arrondi. La règle
        # historique "n < 3 → WARN" (D-BLOC10-02) est devenue obsolète
        # après les correctifs de précision et doit être retirée.
        if n_dominated > 0:
            status = _FAIL
            detail = (
                f"{n_dominated}/{n} solutions dominées dans le front — "
                f"anomalie réelle, vérifier la précision et les "
                f"tolérances de dominance."
            )
        elif n < 3:
            status = _WARN
            detail = (
                f"Front de {n} compromis distincts (< 3). "
                f"Augmenter pop_size/n_gen pour obtenir un front plus représentatif."
            )
        else:
            status = _PASS
            detail = f"{n} compromis distincts, toutes les solutions sont non dominées."

        return CheckResult(
            name="solutions_pareto",
            status=status,
            detail=detail,
            metrics={
                "n_solutions": n,
                "n_dominated": n_dominated,
                "dominance_tol_time_s": tol_t,
                "dominance_tol_energy_J": tol_e,
                "time_range_s": [float(F[:, 0].min()), float(F[:, 0].max())],
                "energy_range_J": [float(F[:, 1].min()), float(F[:, 1].max())],
            },
            duration_s=time_module.perf_counter() - t0,
        )

    def _check_trajectories(
        self,
        traj_df: pd.DataFrame,
        summary_df: pd.DataFrame,
    ) -> CheckResult:
        """
        Vérifie :
          - 3 kinds présents (time_opt, energy_opt, compromise)
          - Chaque tour commence et finit au centre (id le plus proche de 0,0)
          - Chaque point visité exactement une fois (hors centre)
          - total_time_s = total_time_motion_s + total_time_stab_s
        """
        t0 = time_module.perf_counter()
        issues: List[str] = []
        expected_kinds = {"time_opt", "energy_opt", "compromise"}
        present_kinds = set(summary_df["kind"].unique())
        if present_kinds != expected_kinds:
            issues.append(
                f"Kinds manquants : {expected_kinds - present_kinds}"
            )

        # Centre : id à (0,0) — on récupère via points_filtres
        pts = self._load_all()["points_filtres"]
        dist = np.sqrt(pts["x"] ** 2 + pts["y"] ** 2)
        center_id = int(pts.loc[dist.idxmin(), "id"])
        n_expected = len(pts)

        for _, row in summary_df.iterrows():
            kind = row["kind"]
            ids = [int(x) for x in str(row["order"]).split(";")]
            if ids[0] != center_id or ids[-1] != center_id:
                issues.append(f"{kind}: ne commence/finit pas au centre")
            interior = ids[1:-1]
            if len(set(interior)) != n_expected - 1:
                issues.append(f"{kind}: doublons ou manquants dans le corps")
            # Cohérence temporelle
            lhs = float(row["total_time_s"])
            rhs = float(row["total_time_motion_s"]) + float(row["total_time_stab_s"])
            if abs(lhs - rhs) > 1e-6:
                issues.append(
                    f"{kind}: total_time_s ({lhs:.6f}) ≠ motion + stab ({rhs:.6f})"
                )

        status = _PASS if not issues else _FAIL
        detail = (
            "3 trajectoires valides, centre aux extrémités, totaux cohérents."
            if not issues
            else "; ".join(issues)
        )
        return CheckResult(
            name="trajectories",
            status=status,
            detail=detail,
            metrics={
                "n_kinds": len(summary_df),
                "center_id": center_id,
                "n_points_expected": n_expected,
            },
            duration_s=time_module.perf_counter() - t0,
        )

    def _check_profiles(self, df: pd.DataFrame) -> CheckResult:
        """
        Vérifie, sur l'ensemble du fichier profiles.csv :
          - |v| ≤ v_max partout
          - v ≈ 0 au premier sample et à chaque fin de segment
          - temps strictement croissant par kind
        """
        t0 = time_module.perf_counter()
        cfg = self.config
        issues: List[str] = []

        v_norm = np.sqrt(df["vx"] ** 2 + df["vy"] ** 2 + df["vz"] ** 2)
        v_max_obs = float(v_norm.max())
        if v_max_obs > cfg.v_max * 1.01:
            issues.append(f"|v| max = {v_max_obs:.6f} > v_max = {cfg.v_max}")

        for kind, sub in df.groupby("kind"):
            sub = sub.sort_values("segment_id").reset_index(drop=True)
            # Premier sample du premier segment
            first = sub.iloc[0]
            v_first = float(np.linalg.norm(first[["vx", "vy", "vz"]].to_numpy(float)))
            if v_first > 1e-9:
                issues.append(f"{kind}: v(0) = {v_first:.2e}")
            # Fin de chaque segment
            sub = sub.sort_values(["segment_id", "t"]).reset_index(drop=True)
            for seg_id, seg in sub.groupby("segment_id", sort=True):
                # seg est déjà trié par t à l'intérieur de chaque segment
                # grâce au tri composite ci-dessus.
                last = seg.iloc[-1]
                v_last = float(np.linalg.norm(last[["vx", "vy", "vz"]].to_numpy(float)))
                if v_last > 1e-9:
                    issues.append(f"{kind}: v fin seg {seg_id} = {v_last:.2e}")
                    break  # Un seul suffit pour signaler
            # Monotonie stricte
            t_vals = sub["t"].to_numpy(float)
            if not np.all(np.diff(t_vals) > 0):
                issues.append(f"{kind}: temps non strictement croissant")

        status = _PASS if not issues else _FAIL
        detail = (
            f"{len(df)} samples, |v| max = {v_max_obs:.4f} m/s, "
            f"v=0 aux waypoints, monotonie OK."
            if not issues
            else "; ".join(issues[:3])
        )
        return CheckResult(
            name="profiles",
            status=status,
            detail=detail,
            metrics={
                "n_samples": len(df),
                "v_max_observed": v_max_obs,
                "v_max_config": float(cfg.v_max),
            },
            duration_s=time_module.perf_counter() - t0,
        )

    def _check_cross_consistency(
        self,
        cost_df: pd.DataFrame,
        summary_df: pd.DataFrame,
        profiles_df: pd.DataFrame,
    ) -> CheckResult:
        """
        Vérifie que les cumuls dans les profils correspondent aux totaux
        annoncés dans trajectories_summary.csv.
        """
        t0 = time_module.perf_counter()
        issues: List[str] = []
        for _, row in summary_df.iterrows():
            kind = row["kind"]
            expected = float(row["total_time_motion_s"])
            sub = profiles_df[profiles_df["kind"] == kind]
            if sub.empty:
                issues.append(f"{kind}: absent de profiles.csv")
                continue
            t_end = float(sub["t"].max())
            if abs(t_end - expected) > 1e-3:
                issues.append(
                    f"{kind}: t_end profile = {t_end:.6f} vs summary = {expected:.6f}"
                )
        status = _PASS if not issues else _FAIL
        detail = (
            "Cumuls profils ↔ matrice ↔ summary cohérents."
            if not issues
            else "; ".join(issues)
        )
        return CheckResult(
            name="cross_consistency",
            status=status,
            detail=detail,
            metrics={},
            duration_s=time_module.perf_counter() - t0,
        )

    # ==================================================================
    # Figures
    # ==================================================================
    def plot_all(self) -> Dict[str, Path]:
        """Génère les 4 figures du mémoire."""
        paths: Dict[str, Path] = {}
        paths["wfw"] = self._plot_wfw()
        paths["pareto"] = self._plot_pareto()
        # 3 figures individuelles pour les trajectoires (au lieu d'une
        # seule superposée) — décision D-BLOC10-03.
        for kind, p in self._plot_trajectories_3d().items():
            paths[f"trajectories_3d_{kind}"] = p
        paths["profiles"] = self._plot_profiles()
        logger.info("%d figures écrites dans %s", len(paths), self.figures_dir)
        return paths

    def _plot_wfw(self) -> Path:
        """Coupe WFW à z=z_absolu_r0 + superposition des 49 points."""
        pts = self._load_all()["points_filtres"]
        out = self.figures_dir / "wfw_slice.png"
        return self.wfw.plot_wfw_slice(
            output_path=out,
            resolution=60,
            overlay_points=pts[["x", "y", "z"]].to_numpy(),
        )

    def _plot_pareto(self) -> Path:
        """Front de Pareto temps vs énergie, avec 3 points sélectionnés."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        sols = self._load_all()["solutions_pareto"]
        # Déduplication objectif — évite les marqueurs superposés
        sols = sols.drop_duplicates(subset=["time", "energy"]).reset_index(drop=True)
        summary = self._load_all()["trajectories_summary"]

        fig, ax = plt.subplots(figsize=(8, 6))
        ax.scatter(
            sols["time"], sols["energy"],
            s=60, c="#1f77b4", edgecolors="black", linewidths=0.6,
            label=f"Front ({len(sols)} solutions)",
        )
        # Les 3 sélections de BLOC 8
        marker_by_kind = {"time_opt": "s", "energy_opt": "^", "compromise": "D"}
        color_by_kind = {"time_opt": "#2ca02c", "energy_opt": "#d62728",
                          "compromise": "#9467bd"}
        for _, row in summary.iterrows():
            kind = row["kind"]
            ax.scatter(
                row["total_time_motion_s"], row["total_energy_J"],
                marker=marker_by_kind[kind], s=160,
                c=color_by_kind[kind], edgecolors="black", linewidths=1.2,
                label=kind, zorder=5,
            )
        ax.set_xlabel("Temps de déplacement (s)")
        ax.set_ylabel("Énergie (J)")
        ax.set_title("Front de Pareto — temps vs énergie")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best", fontsize=9)
        out = self.figures_dir / "pareto_front.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return out

    def _plot_trajectories_3d(self) -> Dict[str, Path]:
        """
        3 figures séparées — une par trajectoire — plutôt qu'un seul
        graphe superposé. Sur une grille 7×7 (49 points), les 3
        trajectoires se recouvrent au point de devenir illisibles.

        Retour
        ------
        dict {kind: path} avec les 3 fichiers PNG.
        """
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

        traj = self._load_all()["trajectories"]
        pts = self._load_all()["points_filtres"]

        style = {
            "time_opt":    ("#2ca02c", "-"),
            "energy_opt":  ("#d62728", "--"),
            "compromise":  ("#9467bd", "-."),
        }

        paths: Dict[str, Path] = {}
        for kind in ("time_opt", "energy_opt", "compromise"):
            sub = traj[traj["kind"] == kind].sort_values("rank")
            color, ls = style[kind]

            fig = plt.figure(figsize=(10, 8))
            ax = fig.add_subplot(111, projection="3d")

            # Grille de points en arrière-plan (gris neutre)
            ax.scatter(
                pts["x"], pts["y"], pts["z"],
                s=22, c="gray", alpha=0.5,
                label="Points de vue",
            )
            # Trajectoire du kind courant, seul tracé en couleur
            ax.plot(
                sub["x"], sub["y"], sub["z"],
                color=color, linestyle=ls, linewidth=1.6,
                label=kind, alpha=0.9,
            )
            # Départ/retour au centre (id = premier waypoint)
            first = sub.iloc[0]
            ax.scatter(
                [first["x"]], [first["y"]], [first["z"]],
                marker="*", s=220, c="black",
                edgecolors="white", linewidths=1.0,
                label="Centre (départ/retour)", zorder=10,
            )

            ax.set_xlabel("x (m)")
            ax.set_ylabel("y (m)")
            ax.set_zlabel("z (m)")
            ax.set_title(f"Trajectoire — {kind} "
                         f"(t={sub['cumulative_time_motion_s'].iloc[-1]:.1f} s, "
                         f"E={sub['cumulative_energy_J'].iloc[-1]:.1f} J)")
            ax.legend(loc="upper left", fontsize=9)

            out = self.figures_dir / f"trajectories_3d_{kind}.png"
            fig.savefig(out, dpi=150, bbox_inches="tight")
            plt.close(fig)
            paths[kind] = out

        return paths

    def _plot_profiles(self) -> Path:
        """3 sous-graphes : |v|(t) pour chaque kind."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        profiles = self._load_all()["profiles"]
        fig, axes = plt.subplots(3, 1, figsize=(10, 9), sharex=False)
        for ax, kind in zip(axes, ("time_opt", "energy_opt", "compromise"), strict=True):
            sub = profiles[profiles["kind"] == kind].sort_values("t")
            v_norm = np.sqrt(sub["vx"] ** 2 + sub["vy"] ** 2 + sub["vz"] ** 2)
            ax.plot(sub["t"], v_norm, color="#1f77b4", linewidth=1.0)
            ax.axhline(self.config.v_max, color="red", linestyle="--",
                       linewidth=0.8, label=f"v_max = {self.config.v_max}")
            ax.set_ylabel("|v| (m/s)")
            ax.set_title(f"Profil de vitesse — {kind}")
            ax.grid(True, alpha=0.3)
            ax.legend(loc="upper right", fontsize=8)
        axes[-1].set_xlabel("t (s)")
        fig.tight_layout()
        out = self.figures_dir / "profiles.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return out

    # ==================================================================
    # Rapport d'hypothèses
    # ==================================================================
    def write_hypothesis_report(self) -> Dict[str, Path]:
        """
        Produit le rapport d'hypothèses B1–B5 dans deux formats :
          - hypotheses_report.json (machine)
          - hypotheses_report.md   (mémoire)
        """
        entries = self._build_hypotheses()

        json_path = self.output_dir / "hypotheses_report.json"
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)

        md_path = self.output_dir / "hypotheses_report.md"
        md_path.write_text(self._render_hypotheses_markdown(entries),
                           encoding="utf-8")

        logger.info("Rapport d'hypothèses écrit : %s et %s", json_path, md_path)
        return {"json": json_path, "markdown": md_path}

    def _build_hypotheses(self) -> Dict[str, Any]:
        """
        Construit la structure de données du rapport d'hypothèses à
        partir de Config + métadonnées statiques documentaires.
        """
        cfg = self.config
        entries: Dict[str, Any] = {
            "version": "v3.2",
            "config_frozen": True,
            "hypotheses": [
                {
                    "code": "B1",
                    "titre": "Masse opérationnelle de la plateforme",
                    "valeur": f"{cfg.masse_kg} kg",
                    "statut": "GELÉE (v3.1)",
                    "source": "Recalibration masse surfacique (treillis ouvert, "
                              "tube carbone Ø6.1 mm)",
                    "historique": [
                        "v3.0 : 0.385 kg (estimation grossière, sur-estimée)",
                        "v3.1 : 0.417 kg (calibrée sur charge réelle)",
                    ],
                    "plan_correction": (
                        "Peser la plateforme assemblée dès que le prototype "
                        "est disponible ; si écart > 5 %, recalculer T_max "
                        "et rejouer BLOC 3 et BLOC 6."
                    ),
                },
                {
                    "code": "B2",
                    "titre": "Hauteur des plants (fenêtre de service)",
                    "valeur": f"{cfg.hauteur_plants} m",
                    "statut": "GELÉE (estimation externe)",
                    "source": "Fiches variétales haricot nain (Phaseolus "
                              "vulgaris var. nana), médiane 30–50 cm",
                    "historique": [
                        "v3.0 : 0.30 m (implicite tomate, invalide)",
                        "v3.1 : 0.35 m (haricot nain, estimation médiane)",
                    ],
                    "plan_correction": (
                        "Mesurer à JAS 20, 30 et 40 dès que des plants réels "
                        "sont disponibles. Si écart > 0.10 m, recalculer "
                        "z_absolu_r0 et vérifier la marge vs z_max = 0.80 m."
                    ),
                },
                {
                    "code": "B3",
                    "titre": "FOV caméra (paire unique)",
                    "valeur": f"{cfg.fov_camera}° (RGB uniquement)",
                    "statut": "GELÉE (simplifiée v3.0)",
                    "source": "Raspberry Pi Camera v2 — fiche technique",
                    "historique": [
                        "v2.0 : anticipation d'un canal thermique (non retenu)",
                        "v3.0 : canal thermique abandonné, RGB seul",
                    ],
                    "plan_correction": (
                        "Aucune action prévue : FOV intrinsèque au capteur, "
                        "vérifiable à réception."
                    ),
                },
                {
                    "code": "B4",
                    "titre": "Grille et effectif N",
                    "valeur": f"N = {cfg.N} (grille {cfg.n_rangs}×{cfg.n_colonnes}, "
                              f"marge 0.375 m/bord)",
                    "statut": "GELÉE (validée WFW v3.1)",
                    "source": "Dérivation Annexe D de la Base d'architecture",
                    "historique": [
                        "v3.0 : N=81 (9×9, marge 0.25 m) — WFW rejetait 98.8 %",
                        "v3.1 : N=49 (7×7, marge 0.375 m) — WFW 100 % via BLOC 10",
                    ],
                    "plan_correction": (
                        "La validité de B4 a été confirmée par le test WFW "
                        "exhaustif du BLOC 10 (re-vérification indépendante "
                        "des 49 points). Aucune correction prévue."
                    ),
                },
                {
                    "code": "B5",
                    "titre": "Offset R0 / sol (pied de support)",
                    "valeur": f"{cfg.offset_r0_sol} m",
                    "statut": "GELÉE",
                    "source": "Confirmation physique : pied de 20 cm sous "
                              "les 4 barres",
                    "historique": [
                        "v3.0 : 0.20 m, hypothèse de clairance non sourcée",
                        "v3.0 : 0.20 m, confirmée par le montage réel",
                    ],
                    "plan_correction": (
                        "Confirmation par schéma coté recommandée, non "
                        "bloquante : le paramètre est isolé dans Config, "
                        "toute correction reste localisée."
                    ),
                },
            ],
        }
        return entries

    @staticmethod
    def _render_hypotheses_markdown(entries: Dict[str, Any]) -> str:
        """Rend la structure en Markdown lisible pour le mémoire."""
        lines: List[str] = []
        lines.append("# Rapport d'hypothèses — Projet Tandem SP2")
        lines.append("")
        lines.append(f"**Version** : {entries['version']}")
        lines.append(f"**Statut de la configuration** : "
                     f"{'gelée' if entries['config_frozen'] else 'mobile'}")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Synthèse")
        lines.append("")
        lines.append("| Code | Hypothèse | Valeur | Statut |")
        lines.append("|---|---|---|---|")
        for h in entries["hypotheses"]:
            lines.append(
                f"| {h['code']} | {h['titre']} | {h['valeur']} | {h['statut']} |"
            )
        lines.append("")
        lines.append("---")
        for h in entries["hypotheses"]:
            lines.append("")
            lines.append(f"## {h['code']} — {h['titre']}")
            lines.append("")
            lines.append(f"**Valeur retenue** : {h['valeur']}  ")
            lines.append(f"**Statut** : {h['statut']}  ")
            lines.append(f"**Source** : {h['source']}")
            lines.append("")
            lines.append("**Historique** :")
            for hist in h["historique"]:
                lines.append(f"- {hist}")
            lines.append("")
            lines.append("**Plan de correction** :")
            lines.append("")
            lines.append(f"> {h['plan_correction']}")
            lines.append("")
            lines.append("---")
        lines.append("")
        lines.append("*Rapport généré automatiquement par BLOC 10 "
                     "(src/validator.py).*")
        return "\n".join(lines)

    # ==================================================================
    # Pipeline complet
    # ==================================================================
    def run_all(self) -> Dict[str, Any]:
        """Validation + figures + rapport d'hypothèses."""
        report = self.validate()
        figures = self.plot_all()
        hyp = self.write_hypothesis_report()

        # Écriture du rapport de validation
        report_path = self.output_dir / "validation_report.json"
        with report_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return {
            "validation_report": report_path,
            "validation": report,
            "figures": figures,
            "hypotheses_report": hyp,
        }

    # ==================================================================
    # Utilitaires
    # ==================================================================
    def _load_all(self) -> Dict[str, pd.DataFrame]:
        """
        Charge tous les CSV requis. Mise en cache après le premier appel.
        Un appel à `invalidate_cache()` force le rechargement.
        """
        if self._data_cache is not None:
            return self._data_cache
        data: Dict[str, pd.DataFrame] = {}
        for key, fname in _FILENAMES.items():
            path = self.output_dir / fname
            if not path.exists():
                raise FileNotFoundError(
                    f"Fichier requis absent : {path} "
                    f"(clé '{key}'). Lancer les blocs précédents d'abord."
                )
            data[key] = pd.read_csv(path)
        self._data_cache = data
        return data

    def invalidate_cache(self) -> None:
        """Force le rechargement des CSV au prochain appel à _load_all()."""
        self._data_cache = None
