"""
Tests unitaires — BLOC 6 (CostCalculator)
==========================================

Référence : contrat de calcul des coûts SP2 (BLOC 6).

Configuration de test : grille 3×3 et quelques sous-pas pour maîtriser
le temps d'exécution. Le test d'intégration sur la grille 9×9 complète est
marqué @pytest.mark.slow.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.config import Config
from src.cost_calculator import CostCalculator
from src.point_generator import PointGenerator
from src.robot_model import RobotModel


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def cfg_small() -> Config:
    """Config 3×3 (N=9) pour tests rapides."""
    return Config(n_rangs=3, n_colonnes=3)


@pytest.fixture
def cfg_full() -> Config:
    return Config()


@pytest.fixture
def calc_small(cfg_small: Config) -> CostCalculator:
    return CostCalculator(cfg_small, RobotModel(cfg_small))


@pytest.fixture
def points_small(cfg_small: Config) -> pd.DataFrame:
    return PointGenerator(cfg_small).generate()


# ----------------------------------------------------------------------
# T1 — Profil LSPB : cas trapézoïdal et triangulaire
# ----------------------------------------------------------------------
def test_lspb_time_trapezoidal(calc_small: CostCalculator) -> None:
    """Pour d = 0.25 m (> d_full = 0.0675 m), profil trapézoïdal."""
    t = calc_small.lspb_time(0.25)
    # Attendu : 2·(v_max/a_max) + (d − v_max²/a_max)/v_max = 3 + 4.0556 ≈ 7.0556 s
    assert t == pytest.approx(7.0556, abs=1e-3)


def test_lspb_time_triangular(calc_small: CostCalculator) -> None:
    """Pour d = 0.01 m (< 0.0675 m), profil triangulaire."""
    d = 0.01
    t = calc_small.lspb_time(d)
    # Attendu : 2·sqrt(d/a_max) = 2·sqrt(0.01/0.03) ≈ 1.1547 s
    assert t == pytest.approx(2.0 * np.sqrt(d / 0.03), abs=1e-6)


def test_lspb_time_zero(calc_small: CostCalculator) -> None:
    assert calc_small.lspb_time(0.0) == 0.0


def test_lspb_time_symmetric(calc_small: CostCalculator) -> None:
    """LSPB ne dépend que de la distance, donc symétrique."""
    for d in [0.05, 0.25, 1.0]:
        assert calc_small.lspb_time(d) == calc_small.lspb_time(d)


# ----------------------------------------------------------------------
# T2 — QP à norme minimale : vérification directe sur une pose
# ----------------------------------------------------------------------
def test_solve_tension_centre(calc_small: CostCalculator) -> None:
    """Vérifie que le QP résout correctement l'équilibre au centre."""
    cfg = calc_small.config
    robot = calc_small.robot
    p_center = np.array([0.0, 0.0, cfg.z_absolu_r0])
    W = robot.structure_matrix(p_center)

    T, ok = calc_small._solve_tension(W)
    assert ok
    assert T is not None

    # Équilibre respecté
    residual = W @ T - calc_small._rhs
    assert np.linalg.norm(residual) < 1e-8

    # Bornes respectées
    assert np.all(T >= cfg.T_min - 1e-8)
    assert np.all(T <= cfg.T_max + 1e-8)


# ----------------------------------------------------------------------
# T3 — Symétrie temps : time(i,j) = time(j,i)
# ----------------------------------------------------------------------
def test_time_symmetric(calc_small: CostCalculator, points_small: pd.DataFrame) -> None:
    matrix = calc_small.build_matrix(points_small, K=2, verbose=False)
    for _, row in matrix.iterrows():
        i, j = int(row["i"]), int(row["j"])
        t_ij = row["time"]
        t_ji = matrix.loc[(matrix["i"] == j) & (matrix["j"] == i), "time"].iloc[0]
        assert abs(t_ij - t_ji) < 1e-6, f"Temps non symétrique pour ({i},{j})"


# ----------------------------------------------------------------------
# T4 — Symétrie énergie : |E(i,j) − E(j,i)| < 1e-3 J
# ----------------------------------------------------------------------
def test_energy_symmetric(calc_small: CostCalculator, points_small: pd.DataFrame) -> None:
    matrix = calc_small.build_matrix(points_small, K=3, verbose=False)
    for _, row in matrix.iterrows():
        if row["feasible"] == 0:
            continue
        i, j = int(row["i"]), int(row["j"])
        e_ij = row["energy"]
        e_ji = matrix.loc[(matrix["i"] == j) & (matrix["j"] == i), "energy"].iloc[0]
        assert abs(e_ij - e_ji) < 1e-3, (
            f"Énergie non symétrique pour ({i},{j}) : "
            f"{e_ij:.6e} vs {e_ji:.6e}"
        )


# ----------------------------------------------------------------------
# T5 — Diagonale : distance=0, temps=0, énergie=0, feasible=1
# ----------------------------------------------------------------------
def test_diagonal_entries(calc_small: CostCalculator, points_small: pd.DataFrame) -> None:
    matrix = calc_small.build_matrix(points_small, K=2, verbose=False)
    diag = matrix[matrix["i"] == matrix["j"]]
    assert len(diag) == len(points_small)
    assert (diag["distance"] == 0).all()
    assert (diag["time"] == 0).all()
    assert (diag["energy"] == 0).all()
    assert (diag["feasible"] == 1).all()


# ----------------------------------------------------------------------
# T6 — Format CSV conforme au §6
# ----------------------------------------------------------------------
def test_csv_columns(calc_small: CostCalculator, points_small: pd.DataFrame) -> None:
    matrix = calc_small.build_matrix(points_small, K=2, verbose=False)
    assert list(matrix.columns) == ["i", "j", "distance", "time", "energy", "feasible"]


# ----------------------------------------------------------------------
# T7 — Toutes les paires faisables sur grille 3×3 (config v3.1)
# ----------------------------------------------------------------------
def test_all_pairs_feasible(calc_small: CostCalculator, points_small: pd.DataFrame) -> None:
    matrix = calc_small.build_matrix(points_small, K=2, verbose=False)
    assert (matrix["feasible"] == 1).all(), (
        f"Paires infaisables détectées :\n"
        f"{matrix.loc[matrix['feasible'] == 0].to_string()}"
    )


# ----------------------------------------------------------------------
# T8 — Distance conforme à ||p_j − p_i||₂
# ----------------------------------------------------------------------
def test_distance_correct(calc_small: CostCalculator, points_small: pd.DataFrame) -> None:
    matrix = calc_small.build_matrix(points_small, K=2, verbose=False)
    for _, row in matrix.iterrows():
        p_i = points_small.loc[points_small["id"] == row["i"], ["x", "y", "z"]].iloc[0].to_numpy()
        p_j = points_small.loc[points_small["id"] == row["j"], ["x", "y", "z"]].iloc[0].to_numpy()
        d_expected = float(np.linalg.norm(p_i - p_j))
        assert row["distance"] == pytest.approx(d_expected, abs=1e-9)


# ----------------------------------------------------------------------
# T9 — Terme stabilisation
# ----------------------------------------------------------------------
def test_stabilization_term(calc_small: CostCalculator) -> None:
    assert calc_small.stabilization_term(9) == pytest.approx(18.0)   # 9 × 2 s
    assert calc_small.stabilization_term(49) == pytest.approx(98.0)  # 49 × 2 s


# ----------------------------------------------------------------------
# T10 — save : écriture CSV et relecture
# ----------------------------------------------------------------------
def test_save_roundtrip(calc_small: CostCalculator, points_small: pd.DataFrame,
                        tmp_path: Path) -> None:
    matrix = calc_small.build_matrix(points_small, K=2, verbose=False)
    out = tmp_path / "costs.csv"
    calc_small.save(matrix, out)
    assert out.exists()
    df2 = pd.read_csv(out)
    assert list(df2.columns) == list(matrix.columns)
    assert len(df2) == len(matrix)


# ----------------------------------------------------------------------
# T11 — run : pipeline complet
# ----------------------------------------------------------------------
def test_run_pipeline(calc_small: CostCalculator, points_small: pd.DataFrame,
                      tmp_path: Path) -> None:
    info = calc_small.run(points_small, output_dir=tmp_path, K=2)
    assert info["csv"].exists()
    assert info["n_points"] == 9
    assert info["stabilization_time_s"] == pytest.approx(18.0)
    assert info["n_infeasible_pairs"] == 0


# ----------------------------------------------------------------------
# T12 — Entrée malformée
# ----------------------------------------------------------------------
def test_load_points_rejects_bad_input(calc_small: CostCalculator) -> None:
    bad = pd.DataFrame({"id": [0], "x": [0.0]})  # y, z manquants
    with pytest.raises(ValueError, match="Colonnes manquantes"):
        calc_small.build_matrix(bad, K=2, verbose=False)


# ----------------------------------------------------------------------
# T13 (slow) — Matrice complète de la configuration par défaut
# ----------------------------------------------------------------------
@pytest.mark.slow
def test_build_full_matrix_v3_2(cfg_full: Config) -> None:
    """
    Test d'intégration sur la grille 9×9 complète (N=81).
    Durée estimée : ~3-5 min selon la machine. Marqué slow.

    Note : la Config v3.2 impose des bornes ±0.80 m qui dépassent le WFW
    en X. Le filtre (BLOC 5) n'est pas appliqué ici — on teste le calcul
    sur tous les points bruts, dont certains peuvent être infaisables.
    """
    from src.point_filter import PointFilter
    from src.wfw import WFW

    robot = RobotModel(cfg_full)
    wfw = WFW(robot, cfg_full)
    points_all = PointGenerator(cfg_full).generate()

    # Filtrage préalable (comme le pipeline) pour ne garder que les faisables
    pf = PointFilter(cfg_full, wfw)
    result = pf.filter(points_all)
    points = result.points_retenus

    calc = CostCalculator(cfg_full, robot)
    info = calc.run(points, output_dir="data/outputs", K=10)

    # Référence géométrique actuelle : 31 points retenus sur 81.
    assert info["n_points"] == 31
    assert info["n_infeasible_pairs"] == 0
