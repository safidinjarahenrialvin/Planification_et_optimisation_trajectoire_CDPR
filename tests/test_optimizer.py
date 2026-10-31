"""
Tests unitaires — BLOC 7 (Optimizer)
======================================

Référence : contrat d'optimisation des trajectoires SP2 (BLOC 7).

Configuration de test : grille 3×3 (N=9), K=2 sous-pas pour la matrice.
NSGA-II avec pop_size=20, n_gen=10 pour rester rapide.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.config import Config
from src.cost_calculator import CostCalculator
from src.optimizer import Optimizer, TourProblem
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
    calc = CostCalculator(cfg_small, RobotModel(cfg_small))
    return calc.build_matrix(points_small, K=2, verbose=False)


@pytest.fixture
def optimizer(cfg_small: Config, points_small: pd.DataFrame,
              cost_matrix_small: pd.DataFrame) -> Optimizer:
    return Optimizer(cfg_small, points_small, cost_matrix_small)


# ----------------------------------------------------------------------
# T1 — Identification du centre
# ----------------------------------------------------------------------
def test_center_identification(optimizer: Optimizer) -> None:
    # Grille 3×3 → id center = 1*3 + 1 = 4
    assert optimizer.center_id == 4
    assert len(optimizer.non_center_ids) == 8
    assert 4 not in optimizer.non_center_ids


# ----------------------------------------------------------------------
# T2 — Décodage d'une permutation en tour complet
# ----------------------------------------------------------------------
def test_tour_problem_decode(optimizer: Optimizer) -> None:
    problem = TourProblem(
        optimizer.cost_matrix, optimizer.center_id, optimizer.non_center_ids,
    )
    x = np.arange(problem.n)   # permutation identité
    pos = problem._decode_positions(x)
    assert pos[0] == 0                              # position centre
    assert pos[-1] == 0                             # retour au centre
    assert len(pos) == problem.n + 2
    # Les positions 1..n sont toutes couvertes exactement une fois
    interior = pos[1:-1]
    assert sorted(interior.tolist()) == list(range(1, problem.n + 1))


# ----------------------------------------------------------------------
# T3 — Évaluation d'une permutation : reconstruction manuelle
# ----------------------------------------------------------------------
def test_tour_problem_evaluate_matches_manual(optimizer: Optimizer) -> None:
    problem = TourProblem(
        optimizer.cost_matrix, optimizer.center_id, optimizer.non_center_ids,
    )
    x = np.arange(problem.n)
    F = problem._evaluate(x, out={}) or None  # ← nécessaire ? non, on lit out

    # La méthode _evaluate pymoo remplit out["F"] — on appelle via _evaluate
    out: dict = {}
    problem._evaluate(np.atleast_2d(x), out=out)
    F = out["F"][0]

    # Reconstruction manuelle à partir du cost_matrix
    pos = problem._decode_positions(x)
    ids = problem.pos_to_id[pos]
    expected_t = 0.0
    expected_e = 0.0
    for k in range(len(ids) - 1):
        i, j = int(ids[k]), int(ids[k + 1])
        row = optimizer.cost_matrix[
            (optimizer.cost_matrix["i"] == i)
            & (optimizer.cost_matrix["j"] == j)
        ].iloc[0]
        expected_t += float(row["time"])
        expected_e += float(row["energy"])
    assert F[0] == pytest.approx(expected_t, abs=1e-6)
    assert F[1] == pytest.approx(expected_e, abs=1e-6)


# ----------------------------------------------------------------------
# T4 — Run NSGA-II : structure des solutions
# ----------------------------------------------------------------------
def test_run_returns_valid_solutions(optimizer: Optimizer) -> None:
    solutions, _ = optimizer.run(pop_size=20, n_gen=10, seed=42)
    assert len(solutions) > 0
    for sol in solutions:
        for key in ("solution_id", "time", "energy", "order"):
            assert key in sol
        ids = [int(x) for x in sol["order"].split(";")]
        # Départ et retour au centre
        assert ids[0] == optimizer.center_id
        assert ids[-1] == optimizer.center_id
        # Longueur = N' + 1 = 10 pour 3×3
        assert len(ids) == 10
        # Toutes les ids non-centre exactement une fois
        interior = [i for i in ids[1:-1]]
        assert sorted(interior) == sorted(optimizer.non_center_ids.tolist())


def test_run_reports_each_generation(optimizer: Optimizer) -> None:
    events: list[tuple[int, int]] = []

    solutions, _ = optimizer.run(
        pop_size=20,
        n_gen=10,
        seed=42,
        progress_callback=lambda generation, total: events.append((generation, total)),
    )

    assert solutions
    assert [total for _, total in events] == [10] * 10
    assert [generation for generation, _ in events] == list(range(1, 11))


# ----------------------------------------------------------------------
# T5 — Non-dominance du front
# ----------------------------------------------------------------------
def test_pareto_front_non_dominated(optimizer: Optimizer) -> None:
    solutions, _ = optimizer.run(pop_size=30, n_gen=20, seed=42)
    F = np.array([[s["time"], s["energy"]] for s in solutions])
    n = len(F)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            # j domine i si F[j] ≤ F[i] partout et < quelque part
            if (F[j] <= F[i]).all() and (F[j] < F[i]).any():
                pytest.fail(
                    f"Solution {i} dominée par {j} : "
                    f"F[{i}]={F[i]}, F[{j}]={F[j]}"
                )


# ----------------------------------------------------------------------
# T6 — Reproductibilité (seed)
# ----------------------------------------------------------------------
def test_run_reproducible(optimizer: Optimizer) -> None:
    sols_a, _ = optimizer.run(pop_size=20, n_gen=10, seed=7)
    sols_b, _ = optimizer.run(pop_size=20, n_gen=10, seed=7)
    assert len(sols_a) == len(sols_b)
    for a, b in zip(sols_a, sols_b):
        assert a["time"] == pytest.approx(b["time"], abs=1e-9)
        assert a["energy"] == pytest.approx(b["energy"], abs=1e-9)
        assert a["order"] == b["order"]


# ----------------------------------------------------------------------
# T7 — save : écriture des 2 CSV + relecture
# ----------------------------------------------------------------------
def test_save_roundtrip(optimizer: Optimizer, tmp_path: Path) -> None:
    solutions, _ = optimizer.run(pop_size=20, n_gen=10, seed=42)
    paths = optimizer.save(solutions, tmp_path)
    assert paths["solutions"].exists()
    assert paths["orders"].exists()

    df_sol = pd.read_csv(paths["solutions"])
    assert list(df_sol.columns) == ["solution_id", "time", "energy", "order"]
    assert len(df_sol) == len(solutions)

    df_ord = pd.read_csv(paths["orders"])
    assert list(df_ord.columns) == ["solution_id", "rank", "point_id"]
    # Chaque solution a 10 lignes (N'+1 waypoints)
    for sid in df_sol["solution_id"]:
        n_rows = (df_ord["solution_id"] == sid).sum()
        assert n_rows == 10


# ----------------------------------------------------------------------
# T8 — run_and_save : pipeline complet
# ----------------------------------------------------------------------
def test_run_and_save_pipeline(optimizer: Optimizer, tmp_path: Path) -> None:
    info = optimizer.run_and_save(
        output_dir=tmp_path, pop_size=20, n_gen=10, seed=42,
    )
    assert info["n_solutions"] > 0
    assert info["paths"]["solutions"].exists()
    assert info["paths"]["orders"].exists()


# ----------------------------------------------------------------------
# T9 — Pénalité d'infaisabilité (test isolé sur problème mocké)
# ----------------------------------------------------------------------
def test_infeasible_pair_penalized() -> None:
    """
    Construit une matrice avec une paire infaisable et vérifie que la
    pénalité est appliquée si et seulement si cette paire apparaît
    consécutivement dans le tour.

    Note sur la construction du test :
    non_center_ids = [0, 1, 2, 3, 5, 6, 7, 8]  → index k ↦ id (non_center_ids[k])
    Un tour est décodé en [centre, x[0]+1, x[1]+1, …, x[n-1]+1, centre] (en positions),
    puis en ids. Pour que (8, 0) apparaisse, il faut que id 8 soit immédiatement
    suivi de id 0 dans le corps du tour.
    """
    import pandas as pd
    from src.optimizer import _PENALTY

    points = pd.DataFrame({
        "id": [0, 1, 2, 3, 4, 5, 6, 7, 8],
        "x": [-0.5, 0.0, 0.5, -0.5, 0.0, 0.5, -0.5, 0.0, 0.5],
        "y": [-0.5, -0.5, -0.5, 0.0, 0.0, 0.0, 0.5, 0.5, 0.5],
        "z": [0.45] * 9,
        "ligne": [0, 0, 0, 1, 1, 1, 2, 2, 2],
        "colonne": [0, 1, 2, 0, 1, 2, 0, 1, 2],
    })

    rows = []
    for i in points["id"]:
        for j in points["id"]:
            feasible = 1 if (i, j) not in [(0, 8), (8, 0)] else 0
            rows.append({
                "i": int(i), "j": int(j),
                "distance": 1.0, "time": 1.0, "energy": 1.0,
                "feasible": feasible,
            })
    matrix = pd.DataFrame(rows)

    problem = TourProblem(
        matrix,
        center_id=4,
        non_center_ids=np.array([0, 1, 2, 3, 5, 6, 7, 8]),
    )

    # x_bad  : corps = [1,2,3,5,6,7,8,0] → contient la paire (8, 0) → pénalisé
    # x_good : corps = [0,1,2,3,5,6,7,8] → toutes les paires faisables
    x_bad = np.array([1, 2, 3, 4, 5, 6, 7, 0])
    x_good = np.array([0, 1, 2, 3, 4, 5, 6, 7])

    out_bad: dict = {}
    problem._evaluate(np.atleast_2d(x_bad), out=out_bad)
    out_good: dict = {}
    problem._evaluate(np.atleast_2d(x_good), out=out_good)

    # Vérification des tours décodés (utile en cas de régression)
    pos_bad = problem._decode_positions(x_bad)
    ids_bad = problem.pos_to_id[pos_bad]
    assert (8, 0) in list(zip(ids_bad[:-1], ids_bad[1:]))

    # Le tour infaisable est pénalisé
    assert out_bad["F"][0, 0] >= _PENALTY
    assert out_bad["F"][0, 1] >= _PENALTY

    # Le tour faisable ne l'est pas
    assert out_good["F"][0, 0] < _PENALTY
    assert out_good["F"][0, 1] < _PENALTY
    # Bonus : sur cette matrice plate (time=1), le coût total vaut 9 (9 sauts)
    assert out_good["F"][0, 0] == pytest.approx(9.0)
    assert out_good["F"][0, 1] == pytest.approx(9.0)
