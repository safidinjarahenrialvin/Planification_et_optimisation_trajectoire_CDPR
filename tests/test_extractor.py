"""
Tests unitaires — BLOC 8 (TrajectoryExtractor)
================================================

Référence : contrat d'extraction des trajectoires SP2 (BLOC 8).

Utilise un front de Pareto synthétique pour tester les sélections
argmin/compromise, puis un front réel 3×3 (optimizer) pour les tests
d'intégration.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.config import Config
from src.cost_calculator import CostCalculator
from src.extractor import TrajectoryExtractor
from src.optimizer import Optimizer
from src.point_generator import PointGenerator
from src.robot_model import RobotModel


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def cfg_small() -> Config:
    return Config(n_rangs=3, n_colonnes=3)


@pytest.fixture
def points_small(cfg_small: Config) -> pd.DataFrame:
    return PointGenerator(cfg_small).generate()


@pytest.fixture
def cost_matrix_small(cfg_small: Config, points_small: pd.DataFrame) -> pd.DataFrame:
    return CostCalculator(cfg_small, RobotModel(cfg_small)).build_matrix(
        points_small, K=2, verbose=False,
    )


@pytest.fixture
def solutions_real(cfg_small: Config, points_small: pd.DataFrame,
                    cost_matrix_small: pd.DataFrame) -> pd.DataFrame:
    opt = Optimizer(cfg_small, points_small, cost_matrix_small)
    sols, _ = opt.run(pop_size=20, n_gen=10, seed=42)
    return pd.DataFrame(sols)


def _synthetic_front() -> pd.DataFrame:
    """
    Front synthétique avec 5 solutions clairement identifiables :
      - #0 : temps min (1.0), énergie max (10.0)
      - #1 : énergie min (1.0), temps max (10.0)
      - #2 : compromis (time=5.5, energy=5.5) → point idéal normalisé
      - #3, #4 : dominées (temps ET énergie plus élevés que #0 ou #1)
    """
    return pd.DataFrame([
        {"solution_id": 0, "time": 1.0, "energy": 10.0, "order": "0;1;0"},
        {"solution_id": 1, "time": 10.0, "energy": 1.0, "order": "0;2;0"},
        {"solution_id": 2, "time": 5.5, "energy": 5.5, "order": "0;3;0"},
        {"solution_id": 3, "time": 7.0, "energy": 7.0, "order": "0;4;0"},
        {"solution_id": 4, "time": 8.0, "energy": 8.0, "order": "0;5;0"},
    ])


# ----------------------------------------------------------------------
# T1 — argmin time / energy
# ----------------------------------------------------------------------
def test_select_argmin(cfg_small: Config, points_small: pd.DataFrame,
                       cost_matrix_small: pd.DataFrame) -> None:
    ex = TrajectoryExtractor(
        cfg_small, points_small, cost_matrix_small, _synthetic_front(),
    )
    sel = ex.select()
    assert sel["time_opt"]["solution_id"] == 0
    assert sel["time_opt"]["time"] == 1.0
    assert sel["energy_opt"]["solution_id"] == 1
    assert sel["energy_opt"]["energy"] == 1.0


# ----------------------------------------------------------------------
# T2 — Compromis : point le plus proche de l'idéal normalisé
# ----------------------------------------------------------------------
def test_select_compromise_synthetic(cfg_small: Config,
                                     points_small: pd.DataFrame,
                                     cost_matrix_small: pd.DataFrame) -> None:
    ex = TrajectoryExtractor(
        cfg_small, points_small, cost_matrix_small, _synthetic_front(),
    )
    sel = ex.select()
    # #2 est exactement au milieu en normalisé (0.5, 0.5) → distance sqrt(0.5)
    # #3 est (0.667, 0.667) → distance 0.943
    # #4 est (0.778, 0.778) → distance 1.10
    # → #2 doit gagner
    assert sel["compromise"]["solution_id"] == 2


# ----------------------------------------------------------------------
# T3 — Compromis avec range nul (dégénéré)
# ----------------------------------------------------------------------
def test_select_compromise_degenerate_range(cfg_small: Config,
                                            points_small: pd.DataFrame,
                                            cost_matrix_small: pd.DataFrame) -> None:
    """Tous les temps identiques : la normalisation time = 0 partout."""
    df = pd.DataFrame([
        {"solution_id": 0, "time": 5.0, "energy": 10.0, "order": "0;1;0"},
        {"solution_id": 1, "time": 5.0, "energy": 1.0, "order": "0;2;0"},
        {"solution_id": 2, "time": 5.0, "energy": 5.0, "order": "0;3;0"},
    ])
    ex = TrajectoryExtractor(cfg_small, points_small, cost_matrix_small, df)
    sel = ex.select()
    # Time identiques → argmin renvoie premier (idx 0)
    assert sel["time_opt"]["solution_id"] == 0
    # Le compromis minimise |e_norm| → plus petite énergie = #1
    assert sel["compromise"]["solution_id"] == 1


# ----------------------------------------------------------------------
# T4 — Front à une seule solution : les 3 kinds coïncident
# ----------------------------------------------------------------------
def test_single_solution_front(cfg_small: Config, points_small: pd.DataFrame,
                               cost_matrix_small: pd.DataFrame) -> None:
    df = pd.DataFrame([
        {"solution_id": 0, "time": 3.0, "energy": 4.0, "order": "0;1;0"},
    ])
    ex = TrajectoryExtractor(cfg_small, points_small, cost_matrix_small, df)
    sel = ex.select()
    assert sel["time_opt"]["solution_id"] == 0
    assert sel["energy_opt"]["solution_id"] == 0
    assert sel["compromise"]["solution_id"] == 0


# ----------------------------------------------------------------------
# T5 — Front vide → erreur
# ----------------------------------------------------------------------
def test_empty_front_raises(cfg_small: Config, points_small: pd.DataFrame,
                            cost_matrix_small: pd.DataFrame) -> None:
    df = pd.DataFrame(columns=["solution_id", "time", "energy", "order"])
    ex = TrajectoryExtractor(cfg_small, points_small, cost_matrix_small, df)
    with pytest.raises(ValueError, match="vide"):
        ex.select()


# ----------------------------------------------------------------------
# T6 — build_waypoints : format et cumul corrects
# ----------------------------------------------------------------------
def test_build_waypoints_format(cfg_small: Config, points_small: pd.DataFrame,
                                cost_matrix_small: pd.DataFrame) -> None:
    ex = TrajectoryExtractor(
        cfg_small, points_small, cost_matrix_small, _synthetic_front(),
    )
    sel = ex.select()
    wp = ex.build_waypoints("time_opt", sel["time_opt"])
    # 3 waypoints (order = "0;1;0")
    assert len(wp) == 3
    assert list(wp.columns) == [
        "kind", "rank", "point_id", "x", "y", "z",
        "cumulative_time_motion_s", "cumulative_energy_J",
    ]
    assert (wp["kind"] == "time_opt").all()
    assert wp["rank"].tolist() == [0, 1, 2]
    assert wp["point_id"].tolist() == [0, 1, 0]
    # Cumul : premier = 0, croissant ensuite
    assert wp.iloc[0]["cumulative_time_motion_s"] == 0.0
    assert wp.iloc[0]["cumulative_energy_J"] == 0.0
    assert wp.iloc[-1]["cumulative_time_motion_s"] > 0.0
    assert wp.iloc[-1]["cumulative_energy_J"] > 0.0


# ----------------------------------------------------------------------
# T7 — Cumul final = somme des coûts sur les paires consécutives
# ----------------------------------------------------------------------
def test_waypoints_cumulative_matches_cost_matrix(
    cfg_small: Config, points_small: pd.DataFrame,
    cost_matrix_small: pd.DataFrame,
) -> None:
    ex = TrajectoryExtractor(
        cfg_small, points_small, cost_matrix_small, _synthetic_front(),
    )
    sel = ex.select()
    wp = ex.build_waypoints("time_opt", sel["time_opt"])
    ids = wp["point_id"].tolist()
    expected_t = 0.0
    expected_e = 0.0
    for k in range(len(ids) - 1):
        row = cost_matrix_small[
            (cost_matrix_small["i"] == ids[k])
            & (cost_matrix_small["j"] == ids[k + 1])
        ].iloc[0]
        expected_t += float(row["time"])
        expected_e += float(row["energy"])
    assert wp.iloc[-1]["cumulative_time_motion_s"] == pytest.approx(expected_t, abs=1e-6)
    assert wp.iloc[-1]["cumulative_energy_J"] == pytest.approx(expected_e, abs=1e-6)


# ----------------------------------------------------------------------
# T8 — build_summary : 3 lignes, colonnes attendues, stab constante
# ----------------------------------------------------------------------
def test_build_summary(cfg_small: Config, points_small: pd.DataFrame,
                       cost_matrix_small: pd.DataFrame) -> None:
    ex = TrajectoryExtractor(
        cfg_small, points_small, cost_matrix_small, _synthetic_front(),
    )
    summary = ex.build_summary(ex.select())
    assert len(summary) == 3
    assert set(summary["kind"]) == {"time_opt", "energy_opt", "compromise"}
    # Le terme stab est identique pour les 3 (N'=9 → 18 s)
    assert (summary["total_time_stab_s"] == 18.0).all()
    # total_time_s = total_time_motion_s + stab
    assert np.allclose(
        summary["total_time_s"],
        summary["total_time_motion_s"] + summary["total_time_stab_s"],
    )


# ----------------------------------------------------------------------
# T9 — Terme stabilisation paramétrable
# ----------------------------------------------------------------------
def test_stabilization_override(cfg_small: Config, points_small: pd.DataFrame,
                                cost_matrix_small: pd.DataFrame) -> None:
    ex = TrajectoryExtractor(
        cfg_small, points_small, cost_matrix_small, _synthetic_front(),
        stabilization_time_s=50.0,
    )
    summary = ex.build_summary(ex.select())
    assert (summary["total_time_stab_s"] == 50.0).all()


# ----------------------------------------------------------------------
# T10 — run_and_save : 2 CSV écrits et lisibles
# ----------------------------------------------------------------------
def test_run_and_save(cfg_small: Config, points_small: pd.DataFrame,
                      cost_matrix_small: pd.DataFrame, tmp_path: Path) -> None:
    ex = TrajectoryExtractor(
        cfg_small, points_small, cost_matrix_small, _synthetic_front(),
    )
    paths = ex.run_and_save(output_dir=tmp_path)
    assert paths["trajectories"].exists()
    assert paths["summary"].exists()

    df_traj = pd.read_csv(paths["trajectories"])
    df_sum = pd.read_csv(paths["summary"])
    assert set(df_traj["kind"]) == {"time_opt", "energy_opt", "compromise"}
    assert len(df_sum) == 3
    # Chaque kind a bien ses waypoints dans le CSV long
    for k in ("time_opt", "energy_opt", "compromise"):
        sub = df_traj[df_traj["kind"] == k]
        assert len(sub) == 3  # 3 waypoints pour "0;X;0"


# ----------------------------------------------------------------------
# T11 — Solutions acceptées sous 3 formats (DF, liste, CSV)
# ----------------------------------------------------------------------
def test_solutions_formats_equivalent(cfg_small: Config,
                                      points_small: pd.DataFrame,
                                      cost_matrix_small: pd.DataFrame,
                                      tmp_path: Path) -> None:
    df = _synthetic_front()
    list_form = df.to_dict("records")
    csv_path = tmp_path / "sols.csv"
    df.to_csv(csv_path, index=False)

    ex_df = TrajectoryExtractor(cfg_small, points_small, cost_matrix_small, df)
    ex_list = TrajectoryExtractor(cfg_small, points_small, cost_matrix_small, list_form)
    ex_csv = TrajectoryExtractor(cfg_small, points_small, cost_matrix_small, csv_path)

    s_df = ex_df.select()
    s_list = ex_list.select()
    s_csv = ex_csv.select()
    for k in ("time_opt", "energy_opt", "compromise"):
        assert s_df[k]["solution_id"] == s_list[k]["solution_id"]
        assert s_df[k]["solution_id"] == s_csv[k]["solution_id"]


# ----------------------------------------------------------------------
# T12 — Front réel (issu du BLOC 7 sur grille 3×3)
# ----------------------------------------------------------------------
def test_real_front_integration(cfg_small: Config, points_small: pd.DataFrame,
                                cost_matrix_small: pd.DataFrame,
                                solutions_real: pd.DataFrame) -> None:
    """Vérifie que l'extraction fonctionne sur un front réel de NSGA-II."""
    ex = TrajectoryExtractor(
        cfg_small, points_small, cost_matrix_small, solutions_real,
    )
    sel = ex.select()
    # time_opt a le temps minimal sur tout le front
    assert sel["time_opt"]["time"] == pytest.approx(solutions_real["time"].min())
    assert sel["energy_opt"]["energy"] == pytest.approx(solutions_real["energy"].min())
    # Le compromis est sur le front (id présent)
    assert sel["compromise"]["solution_id"] in solutions_real["solution_id"].tolist()
