"""
Tests unitaires — BLOC 10 (Validator)
========================================

Référence : contrat de validation des artefacts SP2 (BLOC 10).

Tests rapides (sans NSGA-II) : génération de CSV synthétiques, un seul
run de validation. Le test d'intégration complète est marqué @pytest.mark.slow.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest

from src.config import Config
from src.robot_model import RobotModel
from src.validator import Validator
from src.wfw import WFW


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def cfg() -> Config:
    return Config()


@pytest.fixture
def validator(cfg: Config, tmp_path: Path) -> Validator:
    robot = RobotModel(cfg)
    wfw = WFW(robot, cfg)
    return Validator(cfg, robot, wfw, output_dir=tmp_path)


def _write_minimal_outputs(output_dir: Path, cfg: Config) -> None:
    """
    Écrit un ensemble minimal de CSV valides (grille 3×3) pour exercer le
    Validator sans passer par tout le pipeline NSGA-II.

    Notes de construction (pour éviter les fausses alertes du Validator) :
      - solutions_pareto : les points sont sur une droite STRICTEMENT
        DÉCROISSANTE (t ↑, e ↓) → tous non dominés par construction.
      - profiles : la vitesse synthétique est plafonnée à 0.03 m/s
        (< v_max = 0.045). Le but est de tester les 3 propriétés du check
        (|v| ≤ v_max, v = 0 aux waypoints, monotonie stricte du temps),
        pas de simuler une vraie LSPB.
    """
    # --- points_filtres : grille 3×3 → 9 points
    ids, xs, ys = [], [], []
    pid = 0
    for iy in range(3):
        for ix in range(3):
            ids.append(pid)
            xs.append((ix - 1) * 0.25)
            ys.append((iy - 1) * 0.25)
            pid += 1
    pts = pd.DataFrame({
        "id": ids, "x": xs, "y": ys, "z": [cfg.z_absolu_r0] * 9,
        "ligne": [i // 3 for i in range(9)],
        "colonne": [i % 3 for i in range(9)],
    })
    pts.to_csv(output_dir / "points_filtres.csv", index=False)

    # --- cost_matrix : toutes paires symétriques
    rows = []
    for i in ids:
        for j in ids:
            d = float(np.hypot(xs[i] - xs[j], ys[i] - ys[j]))
            rows.append({
                "i": i, "j": j, "distance": d,
                "time": 0.0 if i == j else 5.0 + d,
                "energy": 0.0 if i == j else 3.0 + d,
                "feasible": 1,
            })
    pd.DataFrame(rows).to_csv(output_dir / "cost_matrix.csv", index=False)

    # --- solutions_pareto : 12 solutions NON DOMINÉES
    # Droite strictement décroissante : t ↑ ⇒ e ↓ ⇒ aucune dominance possible.
    ts = np.linspace(8.0, 20.0, 12)
    es = 40.0 - 1.5 * ts           # t=8 → 28.0 ; t=20 → 10.0
    sols = []
    for k, (t, e) in enumerate(zip(ts, es)):
        sols.append({
            "solution_id": k, "time": float(t), "energy": float(e),
            "order": "4;0;1;2;3;5;6;7;8;4",
        })
    pd.DataFrame(sols).to_csv(output_dir / "solutions_pareto.csv", index=False)

    # --- trajectories : 3 kinds, 10 waypoints chacun (N'+1 = 10)
    ids_seq = [4, 0, 1, 2, 3, 5, 6, 7, 8, 4]
    traj_rows = []
    for kind in ("time_opt", "energy_opt", "compromise"):
        cum_t, cum_e = 0.0, 0.0
        for rank, pid_ in enumerate(ids_seq):
            if rank > 0:
                prev = ids_seq[rank - 1]
                row = next(r for r in rows if r["i"] == prev and r["j"] == pid_)
                cum_t += row["time"]
                cum_e += row["energy"]
            traj_rows.append({
                "kind": kind, "rank": rank, "point_id": pid_,
                "x": xs[pid_], "y": ys[pid_], "z": cfg.z_absolu_r0,
                "cumulative_time_motion_s": cum_t,
                "cumulative_energy_J": cum_e,
            })
    pd.DataFrame(traj_rows).to_csv(output_dir / "trajectories.csv", index=False)

    # --- trajectories_summary : totaux cohérents avec le profil (t_total)
    summary_rows = []
    for kind, t_total, e_total in [
        ("time_opt", 40.0, 30.0),
        ("energy_opt", 60.0, 12.0),
        ("compromise", 50.0, 20.0),
    ]:
        summary_rows.append({
            "kind": kind,
            "order": "4;0;1;2;3;5;6;7;8;4",
            "n_waypoints": 10,
            "total_time_motion_s": t_total,
            "total_time_stab_s": 18.0,   # 9 × 2 s
            "total_time_s": t_total + 18.0,
            "total_energy_J": e_total,
        })
    pd.DataFrame(summary_rows).to_csv(
        output_dir / "trajectories_summary.csv", index=False
    )

    # --- profiles : vitesse plafonnée à 0.03 m/s (< v_max = 0.045)
    v_peak_synth = 0.03
    prof_rows = []
    for kind, t_total in [("time_opt", 40.0), ("energy_opt", 60.0),
                          ("compromise", 50.0)]:
        t_offset = 0.0
        n_segments = len(ids_seq) - 1   # 9
        T_seg = t_total / n_segments
        n_samples = 10
        for seg_id in range(n_segments):
            p_i = np.array([xs[ids_seq[seg_id]], ys[ids_seq[seg_id]],
                            cfg.z_absolu_r0])
            p_j = np.array([xs[ids_seq[seg_id + 1]], ys[ids_seq[seg_id + 1]],
                            cfg.z_absolu_r0])
            d = float(np.linalg.norm(p_j - p_i))
            u = (p_j - p_i) / d if d > 1e-12 else np.zeros(3)
            start_k = 0 if seg_id == 0 else 1
            for k in range(start_k, n_samples + 1):
                t_l = T_seg * k / n_samples
                alpha = t_l / T_seg
                p = p_i + alpha * (p_j - p_i)
                v_scalar = v_peak_synth * 4.0 * alpha * (1.0 - alpha)
                v_vec = v_scalar * u
                prof_rows.append({
                    "kind": kind, "segment_id": seg_id,
                    "t": t_offset + t_l,
                    "x": float(p[0]), "y": float(p[1]), "z": float(p[2]),
                    "vx": float(v_vec[0]), "vy": float(v_vec[1]),
                    "vz": float(v_vec[2]),
                })
            t_offset += T_seg
    pd.DataFrame(prof_rows).to_csv(output_dir / "profiles.csv", index=False)


# ----------------------------------------------------------------------
# T1 — Charge les CSV et ne lève pas
# ----------------------------------------------------------------------
def test_load_all_succeeds(validator: Validator, cfg: Config, tmp_path: Path) -> None:
    _write_minimal_outputs(tmp_path, cfg)
    data = validator._load_all()
    assert set(data.keys()) == {
        "points_filtres", "cost_matrix", "solutions_pareto",
        "trajectories", "trajectories_summary", "profiles",
    }


def test_load_all_raises_when_missing(validator: Validator) -> None:
    with pytest.raises(FileNotFoundError, match="points_filtres"):
        validator._load_all()


# ----------------------------------------------------------------------
# T2 — Check config : PASS
# ----------------------------------------------------------------------
def test_check_config_pass(validator: Validator) -> None:
    r = validator._check_config_consistency()
    assert r.status == "PASS"
    assert r.metrics["N"] == 81   # v3.2


# ----------------------------------------------------------------------
# T3 — Check points_filtres : PASS (avec WFW re-vérifié)
# ----------------------------------------------------------------------
def test_check_points_filtres_pass(validator: Validator, cfg: Config,
                                    tmp_path: Path) -> None:
    _write_minimal_outputs(tmp_path, cfg)
    pts = pd.read_csv(tmp_path / "points_filtres.csv")
    # Grille 3×3 centrée : tous faisables d'après les tests BLOC 3
    r = validator._check_points_filtres(pts)
    assert r.status == "PASS", r.detail
    assert r.metrics["n_points"] == 9


# ----------------------------------------------------------------------
# T4 — Check cost_matrix : PASS
# ----------------------------------------------------------------------
def test_check_cost_matrix_pass(validator: Validator, cfg: Config,
                                 tmp_path: Path) -> None:
    _write_minimal_outputs(tmp_path, cfg)
    cm = pd.read_csv(tmp_path / "cost_matrix.csv")
    r = validator._check_cost_matrix(cm)
    assert r.status == "PASS", r.detail
    assert r.metrics["n_infeasible_pairs"] == 0
    assert r.metrics["max_asym_time_s"] < 1e-6


def test_check_cost_matrix_partial_pairs_warns_without_crashing(
    validator: Validator,
) -> None:
    cm = pd.DataFrame([
        {"i": 0, "j": 0, "time": 0.0, "energy": 0.0, "feasible": 1},
        {"i": 0, "j": 1, "time": 1.0, "energy": 2.0, "feasible": 1},
        {"i": 1, "j": 0, "time": 1.0, "energy": 2.0, "feasible": 1},
    ])

    result = validator._check_cost_matrix(cm)

    assert result.status == "PASS"
    assert result.metrics["n_reciprocal_missing"] == 0


def test_check_cost_matrix_missing_reciprocal_warns(
    validator: Validator,
) -> None:
    cm = pd.DataFrame([
        {"i": 0, "j": 0, "time": 0.0, "energy": 0.0, "feasible": 1},
        {"i": 0, "j": 1, "time": 1.0, "energy": 2.0, "feasible": 1},
    ])

    result = validator._check_cost_matrix(cm)

    assert result.status == "WARN"
    assert result.metrics["n_reciprocal_missing"] == 1


# ----------------------------------------------------------------------
# T5 — Check solutions : PASS (12 non dominées)
# ----------------------------------------------------------------------
def test_check_solutions_pass(validator: Validator, cfg: Config,
                              tmp_path: Path) -> None:
    _write_minimal_outputs(tmp_path, cfg)
    sols = pd.read_csv(tmp_path / "solutions_pareto.csv")
    r = validator._check_solutions(sols)
    assert r.status == "PASS", r.detail
    assert r.metrics["n_dominated"] == 0


def test_check_solutions_warns_below_three_distinct_compromises(
    validator: Validator,
) -> None:
    solutions = pd.DataFrame([
        {"solution_id": 0, "time": 8.0, "energy": 28.0, "order": "0;1"},
        {"solution_id": 1, "time": 8.0, "energy": 28.0, "order": "1;0"},
    ])

    result = validator._check_solutions(solutions)

    assert result.status == "WARN"
    assert result.metrics["n_solutions"] == 1
    assert result.metrics["n_dominated"] == 0


def test_check_solutions_passes_with_three_distinct_compromises(
    validator: Validator,
) -> None:
    solutions = pd.DataFrame([
        {"solution_id": 0, "time": 8.0, "energy": 28.0, "order": "0;1"},
        {"solution_id": 1, "time": 12.0, "energy": 22.0, "order": "0;1"},
        {"solution_id": 2, "time": 16.0, "energy": 16.0, "order": "0;1"},
    ])

    result = validator._check_solutions(solutions)

    assert result.status == "PASS"
    assert result.metrics["n_solutions"] == 3
    assert result.metrics["n_dominated"] == 0


# ----------------------------------------------------------------------
# T6 — Check trajectories : PASS
# ----------------------------------------------------------------------
def test_check_trajectories_pass(validator: Validator, cfg: Config,
                                  tmp_path: Path) -> None:
    _write_minimal_outputs(tmp_path, cfg)
    t = pd.read_csv(tmp_path / "trajectories.csv")
    s = pd.read_csv(tmp_path / "trajectories_summary.csv")
    r = validator._check_trajectories(t, s)
    assert r.status == "PASS", r.detail


# ----------------------------------------------------------------------
# T7 — Check profiles : PASS
# ----------------------------------------------------------------------
def test_check_profiles_pass(validator: Validator, cfg: Config,
                              tmp_path: Path) -> None:
    _write_minimal_outputs(tmp_path, cfg)
    p = pd.read_csv(tmp_path / "profiles.csv")
    r = validator._check_profiles(p)
    assert r.status == "PASS", r.detail


# ----------------------------------------------------------------------
# T8 — Validation complète : overall PASS
# ----------------------------------------------------------------------
def test_validate_overall_pass(validator: Validator, cfg: Config,
                                tmp_path: Path) -> None:
    _write_minimal_outputs(tmp_path, cfg)
    report = validator.validate()
    assert report["overall_status"] == "PASS", json.dumps(report, indent=2)
    assert report["summary"]["n_fail"] == 0
    assert report["summary"]["n_total"] == 7


# ----------------------------------------------------------------------
# T9 — Génération des 4 figures
# ----------------------------------------------------------------------
def test_plot_all_creates_figures(validator: Validator, cfg: Config,
                                   tmp_path: Path) -> None:
    _write_minimal_outputs(tmp_path, cfg)
    paths = validator.plot_all()
    expected = {
        "wfw", "pareto", "profiles",
        "trajectories_3d_time_opt",
        "trajectories_3d_energy_opt",
        "trajectories_3d_compromise",
    }
    assert set(paths.keys()) == expected
    for p in paths.values():
        assert p.exists() and p.stat().st_size > 0


# ----------------------------------------------------------------------
# T10 — Rapport d'hypothèses : JSON + Markdown
# ----------------------------------------------------------------------
def test_hypothesis_report(validator: Validator, tmp_path: Path) -> None:
    paths = validator.write_hypothesis_report()
    assert paths["json"].exists()
    assert paths["markdown"].exists()

    with paths["json"].open() as f:
        data = json.load(f)
    codes = [h["code"] for h in data["hypotheses"]]
    assert codes == ["B1", "B2", "B3", "B4", "B5"]
    assert data["version"] == "v3.2"
    # Vérifie quelques valeurs clés
    b1 = next(h for h in data["hypotheses"] if h["code"] == "B1")
    # Masse ≈ 0.384 kg (plateforme 300×240 par défaut)
    # On extrait la valeur numérique de la chaîne pour comparer.
    import re
    match = re.search(r"([\d.]+)", b1["valeur"])
    assert match is not None
    masse_str = match.group(1)
    masse_val = float(masse_str)
    assert masse_val == pytest.approx(0.384, abs=1e-3)
    b4 = next(h for h in data["hypotheses"] if h["code"] == "B4")
    assert "N = 81" in b4["valeur"]

    # Markdown contient bien les 5 sections
    md = paths["markdown"].read_text(encoding="utf-8")
    for code in ("B1", "B2", "B3", "B4", "B5"):
        assert f"## {code}" in md


# ----------------------------------------------------------------------
# T11 — run_all : pipeline complet
# ----------------------------------------------------------------------
def test_run_all(validator: Validator, cfg: Config, tmp_path: Path) -> None:
    _write_minimal_outputs(tmp_path, cfg)
    info = validator.run_all()
    assert info["validation"]["overall_status"] == "PASS"
    assert info["validation_report"].exists()

    assert set(info["figures"].keys()) == {
        "wfw", "pareto", "profiles",
        "trajectories_3d_time_opt",
        "trajectories_3d_energy_opt",
        "trajectories_3d_compromise",
    }

    assert info["hypotheses_report"]["json"].exists()
    assert info["hypotheses_report"]["markdown"].exists()
    # Le rapport de validation est bien relisible
    with info["validation_report"].open() as f:
        reloaded = json.load(f)
    assert reloaded["overall_status"] == "PASS"


# ----------------------------------------------------------------------
# T12 — Détection d'incohérence : front dominé → FAIL
# ----------------------------------------------------------------------
def test_validate_detects_dominated_front(validator: Validator, cfg: Config,
                                          tmp_path: Path) -> None:
    _write_minimal_outputs(tmp_path, cfg)
    # Réécrit solutions_pareto avec une solution dominée
    bad = pd.DataFrame([
        {"solution_id": 0, "time": 1.0, "energy": 1.0, "order": "4;0;1;2;3;5;6;7;8;4"},
        {"solution_id": 1, "time": 2.0, "energy": 2.0, "order": "4;0;1;2;3;5;6;7;8;4"},
    ])
    bad.to_csv(tmp_path / "solutions_pareto.csv", index=False)
    report = validator.validate()
    # #1 est dominée par #0
    assert report["overall_status"] == "FAIL"
    sol_check = next(c for c in report["checks"] if c["name"] == "solutions_pareto")
    assert sol_check["status"] == "FAIL"
    assert sol_check["metrics"]["n_dominated"] == 1
