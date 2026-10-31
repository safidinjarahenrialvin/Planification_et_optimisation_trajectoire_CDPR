#!/usr/bin/env python3
"""
Balayage (T_min, T_max) → couverture WFW.
============================================

Calcule le WFW sur une grille échantillonnée pour plusieurs valeurs
couplées de T_min et T_max, et tabule pour chaque paire :
  - % de couverture (feasible / total)
  - bbox (étendue min/max du feasible set en X, Y, Z)
  - rayons utiles (demi-étendues)
  - volume de l'enveloppe convexe
  - faisabilité du centre

Exploite l'imbrication : WFW(T_min, T_max) ⊂ WFW(T_min', T_max') si
T_min ≥ T_min' et T_max ≤ T_max'. Le plus grand WFW (T_min=0, T_max=∞)
est calculé en premier, puis sert de masque global pour les autres.

Usage
-----
    # Balayage complet par défaut (~3-4 min)
    python scripts/sweep_wfw.py

    # Aperçu rapide (~40 s)
    python scripts/sweep_wfw.py --quick

    # Plages personnalisées
    python scripts/sweep_wfw.py --t-min-list 0 1 5 20 --t-max-list 58 500

    # Reprise après interruption (skip paires déjà dans le CSV)
    python scripts/sweep_wfw.py --resume

    # Ajout d'une heatmap de couverture
    python scripts/sweep_wfw.py --plot

Sorties
-------
    data/outputs/wfw_sweep.csv          (résultats tabulaires)
    data/outputs/figures/wfw_sweep_heatmap.png  (si --plot)
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.config import Config, DEFAULT_PLATFORM         # noqa: E402
from src.robot_model import RobotModel  # noqa: E402
from src.wfw import WFW                 # noqa: E402


logger = logging.getLogger("sweep_wfw")


# ===========================================================================
# Plages par défaut
# ===========================================================================
_DEFAULT_T_MIN_LIST: List[float] = [0.0, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0,
                                     10.0, 15.0, 20.0, 30.0]
_DEFAULT_T_MAX_LIST: List[float] = [5.0, 10.0, 20.0, 30.0, 58.0, 80.0,
                                     100.0, 200.0, 500.0]

# Valeur sentinelle pour T_max = ∞ (assez grande pour ne pas contraindre
# le LP, mais pas astronomique pour éviter des problèmes numériques HiGHS)
_UNBOUNDED_T_MAX = 1.0e4

# Résolutions par défaut
_DEFAULT_N_XY = 20
_DEFAULT_N_Z = 12
_QUICK_N_XY = 12
_QUICK_N_Z = 8

# Colonnes du CSV de sortie (ordre figé)
_CSV_COLUMNS = [
    "t_min_N", "t_max_N",
    "n_total", "n_feasible", "pct_coverage",
    "bbox_x_min", "bbox_x_max", "bbox_y_min", "bbox_y_max",
    "bbox_z_min", "bbox_z_max",
    "radius_x", "radius_y", "radius_z",
    "hull_volume_m3", "bbox_volume_m3",
    "center_feasible",
    "n_lp_calls", "duration_s",
]


# ===========================================================================
# Fonctions de calcul
# ===========================================================================
def _evaluate_pair(
    robot: RobotModel,
    config: Config,
    t_min: float,
    t_max: float,
    x_grid: np.ndarray,
    y_grid: np.ndarray,
    z_grid: np.ndarray,
    restrict_mask: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, int, float]:
    """
    Teste la faisabilité WFW sur la grille pour une paire (t_min, t_max).

    Retourne (feasible_bool_array, n_lp_calls, duration_s).
    """
    cfg_t = replace(config, T_min=float(t_min), T_max=float(t_max))
    wfw = WFW(robot, cfg_t)

    n_xy = len(x_grid)
    n_z = len(z_grid)
    feasible = np.zeros((n_xy, n_xy, n_z), dtype=bool)
    n_calls = 0
    t0 = time.perf_counter()

    for k in range(n_z):
        for i in range(n_xy):
            for j in range(n_xy):
                if restrict_mask is not None and not restrict_mask[i, j, k]:
                    continue
                p = np.array([x_grid[i], y_grid[j], z_grid[k]])
                feasible[i, j, k] = wfw.is_feasible(p).feasible
                n_calls += 1

    return feasible, n_calls, time.perf_counter() - t0


def _extract_metrics(
    feasible: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    t_min: float,
    t_max: float,
    n_lp_calls: int,
    duration_s: float,
) -> Dict:
    """
    Extrait les métriques d'un volume : % couverture, bbox, rayons,
    volume du hull, faisabilité du centre.
    """
    n_total = int(feasible.size)
    idx = np.argwhere(feasible)
    n_feasible = len(idx)

    # Indices du centre (point le plus proche de x=0, y=0)
    i_c = int(np.argmin(np.abs(x)))
    j_c = int(np.argmin(np.abs(y)))
    center_any_z = bool(feasible[i_c, j_c, :].any())

    row: Dict = {
        "t_min_N": float(t_min),
        "t_max_N": float(t_max),
        "n_total": n_total,
        "n_feasible": n_feasible,
        "pct_coverage": (100.0 * n_feasible / n_total) if n_total else 0.0,
        "n_lp_calls": int(n_lp_calls),
        "duration_s": float(duration_s),
        "center_feasible": center_any_z,
    }

    if n_feasible == 0:
        for k in ("bbox_x_min", "bbox_x_max", "bbox_y_min", "bbox_y_max",
                  "bbox_z_min", "bbox_z_max", "radius_x", "radius_y",
                  "radius_z", "hull_volume_m3", "bbox_volume_m3"):
            row[k] = float("nan")
        return row

    xs = x[idx[:, 0]]
    ys = y[idx[:, 1]]
    zs = z[idx[:, 2]]

    xmin, xmax = float(xs.min()), float(xs.max())
    ymin, ymax = float(ys.min()), float(ys.max())
    zmin, zmax = float(zs.min()), float(zs.max())

    row["bbox_x_min"] = xmin
    row["bbox_x_max"] = xmax
    row["bbox_y_min"] = ymin
    row["bbox_y_max"] = ymax
    row["bbox_z_min"] = zmin
    row["bbox_z_max"] = zmax
    row["radius_x"] = (xmax - xmin) / 2.0
    row["radius_y"] = (ymax - ymin) / 2.0
    row["radius_z"] = (zmax - zmin) / 2.0
    row["bbox_volume_m3"] = (
        (xmax - xmin) * (ymax - ymin) * (zmax - zmin)
    )

    # Volume du hull convexe (approximation du volume WFW)
    row["hull_volume_m3"] = _hull_volume(xs, ys, zs)
    return row


def _hull_volume(xs: np.ndarray, ys: np.ndarray, zs: np.ndarray) -> float:
    """Volume de l'enveloppe convexe des points. 0 si dégénéré."""
    from scipy.spatial import ConvexHull, QhullError
    if len(xs) < 4:
        return 0.0
    pts = np.column_stack([xs, ys, zs])
    # Cap pour la performance (même logique que WFW3DViewer)
    if len(pts) > 5000:
        rng = np.random.default_rng(42)
        sel = rng.choice(len(pts), size=5000, replace=False)
        pts = pts[sel]
    try:
        return float(ConvexHull(pts).volume)
    except QhullError:
        return 0.0


# ===========================================================================
# CSV et heatmap
# ===========================================================================
def _save_csv(rows: List[Dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows, columns=_CSV_COLUMNS)
    df.to_csv(path, index=False, float_format="%.6f")
    logger.info("CSV sweep écrit : %s (%d lignes)", path, len(df))


def _load_existing_pairs(path: Path) -> Set[Tuple[float, float]]:
    """Retourne les paires (t_min, t_max) déjà présentes dans le CSV."""
    if not path.exists():
        return set()
    try:
        df = pd.read_csv(path)
    except Exception:
        return set()
    if not {"t_min_N", "t_max_N"}.issubset(df.columns):
        return set()
    return {(round(float(r.t_min_N), 6), round(float(r.t_max_N), 6))
            for r in df.itertuples()}


def _plot_heatmap(
    rows: List[Dict],
    path: Path,
    t_min_list: List[float],
    t_max_list: List[float],
    include_unbounded: bool,
) -> None:
    """
    Heatmap de pct_coverage avec T_min en abscisse et T_max en ordonnée.

    Les listes `t_min_list` et `t_max_list` proviennent des paramètres
    CLI effectifs — pas des valeurs par défaut — pour garantir que
    l'ordre des axes corresponde au balayage réel (D-TOOLING-10).
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    df = pd.DataFrame(rows)
    if df.empty:
        logger.warning("Aucune donnée à tracer.")
        return

    # T_max = ∞ → libellé lisible
    df["t_max_label"] = df["t_max_N"].apply(
        lambda v: "∞" if v >= _UNBOUNDED_T_MAX else f"{v:g}"
    )
    pivot = df.pivot_table(
        index="t_max_label", columns="t_min_N",
        values="pct_coverage", aggfunc="first",
    )

    # Ordonner les axes selon les listes CLI effectives
    t_max_order_labels = [f"{v:g}" for v in sorted(t_max_list)]
    if include_unbounded:
        t_max_order_labels.append("∞")
    t_max_order = [lbl for lbl in t_max_order_labels if lbl in pivot.index]
    pivot = pivot.reindex(t_max_order)

    # Colonnes T_min triées dans l'ordre croissant des valeurs CLI
    t_min_order = sorted(t_min_list)
    cols_present = [c for c in t_min_order if c in pivot.columns]
    pivot = pivot[cols_present]
    # Convention d'axe Y mathématique : T_max croît de bas en haut.
    # `imshow` place l'index 0 en haut, donc on inverse l'ordre des
    # lignes du pivot pour que la plus grande valeur (∞) soit en haut.
    pivot = pivot.iloc[::-1]

    # Colonnes T_min triées dans l'ordre croissant des valeurs CLI
    t_min_order = sorted(t_min_list)
    cols_present = [c for c in t_min_order if c in pivot.columns]
    pivot = pivot[cols_present]

    fig, ax = plt.subplots(figsize=(11, 6))
    im = ax.imshow(
        pivot.values, aspect="auto", cmap="viridis",
        vmin=0.0, vmax=max(100.0, np.nanmax(pivot.values)),
    )
    # Annotations dans chaque cellule
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            val = pivot.values[i, j]
            if not np.isnan(val):
                ax.text(
                    j, i, f"{val:.0f}", ha="center", va="center",
                    color="white" if val < 50 else "black",
                    fontsize=9, fontweight="bold",
                )
    ax.set_xticks(range(pivot.shape[1]))
    ax.set_xticklabels([f"{v:g}" for v in pivot.columns])
    ax.set_yticks(range(pivot.shape[0]))
    ax.set_yticklabels(pivot.index)
    ax.set_xlabel("T_min (N)")
    ax.set_ylabel("T_max (N)")
    ax.set_title("Couverture WFW (%) — balayage (T_min, T_max)")
    fig.colorbar(im, ax=ax, label="% faisable")
    fig.tight_layout()

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Heatmap écrite : %s", path)


# ===========================================================================
# Boucle principale
# ===========================================================================
def _build_grids(
    config: Config,
    n_xy: int,
    n_z: int,
    bounds: Optional[Tuple[Tuple[float, float], Tuple[float, float],
                             Tuple[float, float]]] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Construit les trois axes d'échantillonnage."""
    if bounds is None:
        A = config.ancrages_A
        xb = (float(A[0, :].min()), float(A[0, :].max()))
        yb = (float(A[1, :].min()), float(A[1, :].max()))
        zb = (float(A[2, :].min()), float(A[2, :].max()))
    else:
        xb, yb, zb = bounds
    x = np.linspace(xb[0], xb[1], n_xy)
    y = np.linspace(yb[0], yb[1], n_xy)
    z = np.linspace(zb[0], zb[1], n_z)
    return x, y, z


def run_sweep(
    config: Config,
    t_mins: List[float],
    t_maxs: List[float],
    n_xy: int,
    n_z: int,
    include_unbounded: bool,
    output_csv: Path,
    plot: bool,
    resume: bool,
) -> List[Dict]:
    """Exécute le balayage complet et écrit le CSV (mode append si resume)."""
    robot = RobotModel(config)
    x, y, z = _build_grids(config, n_xy, n_z)
    n_lp_per_pair = n_xy * n_xy * n_z

    # Construire la liste des paires valides
    t_maxs_eff = list(t_maxs)
    if include_unbounded and _UNBOUNDED_T_MAX not in t_maxs_eff:
        t_maxs_eff.append(_UNBOUNDED_T_MAX)

    pairs: List[Tuple[float, float]] = []
    for t_min in t_mins:
        for t_max in t_maxs_eff:
            if t_min < t_max:
                pairs.append((float(t_min), float(t_max)))

    logger.info(
        "Balayage : %d paires valides, résolution %d×%d×%d (%d LP/pair).",
        len(pairs), n_xy, n_xy, n_z, n_lp_per_pair,
    )

    # Mode resume : charger les paires déjà calculées
    existing: Set[Tuple[float, float]] = set()
    if resume:
        existing = _load_existing_pairs(output_csv)
        if existing:
            logger.info("Reprise : %d paires déjà dans %s.",
                        len(existing), output_csv)

    # Charger les lignes existantes si resume (pour ne pas les perdre)
    prior_rows: List[Dict] = []
    if resume and output_csv.exists():
        try:
            prior_rows = pd.read_csv(output_csv).to_dict("records")
        except Exception:
            prior_rows = []

    # ------------------------------------------------------------------
    # Étape 1 — Volume global (T_min=0, T_max=∞) comme masque
    # ------------------------------------------------------------------
    global_mask: Optional[np.ndarray] = None
    if (0.0, _UNBOUNDED_T_MAX) in pairs:
        logger.info("=== Calcul du masque global T_min=0, T_max=∞ ===")
        feas, n_calls, dt = _evaluate_pair(
            robot, config, 0.0, _UNBOUNDED_T_MAX, x, y, z,
        )
        global_mask = feas.copy()
        n_feas = int(feas.sum())
        logger.info(
            "Masque global : %d/%d points faisables (%.2f %%) en %.1f s.",
            n_feas, feas.size, 100.0 * n_feas / feas.size, dt,
        )

    # ------------------------------------------------------------------
    # Étape 2 — Boucle sur toutes les paires
    # ------------------------------------------------------------------
    rows: List[Dict] = []
    total = len(pairs)
    t_start_all = time.perf_counter()

    for idx, (t_min, t_max) in enumerate(pairs, start=1):
        key = (round(t_min, 6), round(t_max, 6))
        if key in existing:
            logger.info("[%3d/%3d] SKIP (déjà dans le CSV) T_min=%.2f T_max=%.2f",
                        idx, total, t_min, t_max)
            continue

        label = "∞" if t_max >= _UNBOUNDED_T_MAX else f"{t_max:g}"
        logger.info("[%3d/%3d] T_min=%5.2f N, T_max=%6s N",
                    idx, total, t_min, label)

        # Utiliser le masque global sauf si on calcule la paire globale
        # elle-même (auquel cas le masque est redondant).
        mask = None
        if global_mask is not None and not (
            t_min == 0.0 and t_max >= _UNBOUNDED_T_MAX
        ):
            mask = global_mask

        feas, n_calls, dt = _evaluate_pair(
            robot, config, t_min, t_max, x, y, z,
            restrict_mask=mask,
        )
        row = _extract_metrics(
            feas, x, y, z, t_min, t_max, n_calls, dt,
        )
        rows.append(row)

        if row["n_feasible"] == 0:
            logger.info("  → aucun point faisable")
        else:
            logger.info(
                "  → %d/%d faisables (%.2f %%), bbox X [%.3f, %.3f], "
                "Y [%.3f, %.3f], Z [%.3f, %.3f], %.1f s",
                row["n_feasible"], row["n_total"], row["pct_coverage"],
                row["bbox_x_min"], row["bbox_x_max"],
                row["bbox_y_min"], row["bbox_y_max"],
                row["bbox_z_min"], row["bbox_z_max"],
                dt,
            )

    # Écriture CSV = lignes antérieures + nouvelles
    all_rows = prior_rows + rows
    _save_csv(all_rows, output_csv)

    total_dt = time.perf_counter() - t_start_all
    logger.info("Balayage terminé en %.1f s.", total_dt)

    if plot:
        _plot_heatmap(
            all_rows,
            output_csv.parent / "figures" / "wfw_sweep_heatmap.png",
            t_min_list=t_mins,
            t_max_list=t_maxs,
            include_unbounded=include_unbounded,
        )

    return all_rows


# ===========================================================================
# CLI
# ===========================================================================
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Balayage (T_min, T_max) du WFW.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--t-min-list", type=float, nargs="+",
                   default=_DEFAULT_T_MIN_LIST,
                   help=f"Valeurs de T_min (défaut : {_DEFAULT_T_MIN_LIST}).")
    p.add_argument("--t-max-list", type=float, nargs="+",
                   default=_DEFAULT_T_MAX_LIST,
                   help=f"Valeurs de T_max (défaut : {_DEFAULT_T_MAX_LIST}).")
    p.add_argument("--no-unbounded", action="store_true",
                   help="Ne pas ajouter T_max=∞.")
    p.add_argument("--quick", action="store_true",
                   help=f"Résolution rapide ({_QUICK_N_XY}×{_QUICK_N_XY}×{_QUICK_N_Z}).")
    p.add_argument("--n-xy", type=int, default=_DEFAULT_N_XY,
                   help=f"Points par axe XY (défaut : {_DEFAULT_N_XY}).")
    p.add_argument("--n-z", type=int, default=_DEFAULT_N_Z,
                   help=f"Points sur Z (défaut : {_DEFAULT_N_Z}).")
    p.add_argument("--output-csv", type=Path,
                   default=Path("data/outputs/wfw_sweep.csv"),
                   help="CSV de sortie.")
    p.add_argument("--plot", action="store_true",
                   help="Générer aussi une heatmap de couverture.")
    p.add_argument("--resume", action="store_true",
                   help="Reprendre en skippant les paires déjà dans le CSV.")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--platform", type=str, default=DEFAULT_PLATFORM,
                   help=f"Taille de la plateforme. Défaut : "
                        f"{DEFAULT_PLATFORM}. "
                        f"Autres noms connus : 250x200, 700x560, 630x630. "
                        f"Ou dimension libre 'WxH' en mm (ex. 400x300).")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)-7s] %(name)-22s | %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.quick:
        n_xy, n_z = _QUICK_N_XY, _QUICK_N_Z
    else:
        n_xy, n_z = args.n_xy, args.n_z

    config = Config.with_n(9, platform=args.platform)
    logger.info(
        "Plateforme %s : masse %.1f g.",
        args.platform, config.masse_kg * 1000,
    )

    # Avertissement de traçabilité : le sweep échantillonne l'enveloppe
    # des ancrages, pas les limites opérationnelles.
    A = config.ancrages_A
    logger.info(
        "Échantillonnage : X ∈ [%.3f, %.3f], Y ∈ [%.3f, %.3f], Z ∈ [%.3f, %.3f] m",
        A[0, :].min(), A[0, :].max(),
        A[1, :].min(), A[1, :].max(),
        A[2, :].min(), A[2, :].max(),
    )

    # Suffixe conditionnel (D-CONFIG-13) : ajoute le nom de la
    # plateforme au CSV si elle diffère du défaut. La vérification
    # `not in stem` évite un double suffixe quand l'utilisateur a
    # déjà nommé son fichier avec la plateforme.
    out_csv = args.output_csv
    if (
        args.platform != DEFAULT_PLATFORM
        and "sweep" in out_csv.stem
        and args.platform not in out_csv.stem
    ):
        out_csv = out_csv.with_name(
            f"{out_csv.stem}_{args.platform}{out_csv.suffix}"
        )
    logger.info("CSV de sortie : %s", out_csv)

    run_sweep(
        config=config,
        t_mins=list(args.t_min_list),
        t_maxs=list(args.t_max_list),
        n_xy=n_xy,
        n_z=n_z,
        include_unbounded=not args.no_unbounded,
        output_csv=out_csv,
        plot=args.plot,
        resume=args.resume,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
