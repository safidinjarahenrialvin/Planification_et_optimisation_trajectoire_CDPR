"""
BLOC 7 — Optimiseur (Optimizer)
=================================

Référence : contrat d'optimisation des trajectoires du pipeline SP2 (BLOC 7).
Portée    : ordonnancement optimal des N' points de vue par NSGA-II,
            avec départ/retour obligatoires au centre.

Objectifs (2) :
  - temps    : somme des time(i,j) sur les paires consécutives du tour
  - énergie  : somme des energy(i,j) sur les paires consécutives du tour

Le terme stabilisation (N' × T_stab) est un décalage constant appliqué
en BLOC 8 — il n'est PAS inclus dans la fitness (il ne change pas l'ordre).

Chromosome
----------
    Permutation des N'-1 points non centraux.
  Le tour complet est reconstruit :
      tour = [centre, non_centre[x[0]], …, non_centre[x[N'-2]], centre]
  Le centre est donc fixé implicitement en début et fin — pas de
  contrainte de position à encoder.

Symétrie temps/énergie
------------------------
  Les matrices sont symétriques (BLOC 6, testé), donc l'orientation
  n'affecte pas les coûts. Toutefois un tour aller ≠ tour retour (ordre
  des visites différent), donc le problème d'ordonnancement reste non
  trivial.

Format CSV (§6)
---------------
  solutions_pareto.csv : solution_id, time, energy, order
      - order : chaîne d'identifiants séparés par ';', centre inclus aux deux extrémités
  solutions_orders.csv : solution_id, rank, point_id
      - format long, plus simple à parser pour BLOC 8
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

import numpy as np
import pandas as pd
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.callback import Callback
from pymoo.core.problem import Problem
from pymoo.operators.crossover.ox import OrderCrossover
from pymoo.operators.mutation.inversion import InversionMutation
from pymoo.operators.sampling.rnd import PermutationRandomSampling
from pymoo.optimize import minimize

from src.config import Config

logger = logging.getLogger(__name__)

GenerationProgressCallback = Callable[[int, int], None]


_CSV_SOLUTION_COLUMNS = ["solution_id", "time", "energy", "order"]
_CSV_ORDER_COLUMNS = ["solution_id", "rank", "point_id"]

# Pénalité pour paire infaisable — assez grande pour être toujours
# dominée, assez petite pour ne pas casser les comparaisons.
_PENALTY = 1e6


class DegenerateFrontError(RuntimeError):
    """
    Levée quand toutes les solutions du front de Pareto sont pénalisées
    (aucun tour faisable trouvé). Symptôme d'un graphe de faisabilité
    sans chemin hamiltonien, typiquement avec trop peu de points ou
    des segments tous infaisables.
    """


class _GenerationCallback(Callback):
    """Adaptateur pymoo vers le contrat de progression du projet."""

    def __init__(self, callback: GenerationProgressCallback, total: int) -> None:
        super().__init__()
        self._callback = callback
        self._total = total

    def notify(self, algorithm) -> None:
        self._callback(int(algorithm.n_gen), self._total)


# ===========================================================================
# Problème pymoo
# ===========================================================================
class TourProblem(Problem):
    """
    Problème NSGA-II sur les permutations de points non-centre.

    Construit des matrices (n+1, n+1) indexées par POSITION dans la
    séquence de visite : position 0 = centre, positions 1..n = points
    non-centre dans l'ordre canonique de `non_center_ids`.
    """

    def __init__(
        self,
        cost_matrix: pd.DataFrame,
        center_id: int,
        non_center_ids: np.ndarray,
    ) -> None:
        self.center_id = int(center_id)
        self.non_center_ids = np.asarray(non_center_ids, dtype=int)
        self.n = len(self.non_center_ids)

        # Mapping position ↔ id
        self.pos_to_id = np.concatenate([[self.center_id], self.non_center_ids])
        self.id_to_pos = {int(pid): p for p, pid in enumerate(self.pos_to_id)}

        # Matrices (n+1, n+1) par position.
        # ATTENTION : feasible_mat est initialisée à False. Une paire
        # absente du cost_matrix est donc traitée comme INFAISABLE (et
        # pénalisée), au lieu d'être considérée "faisable à coût nul"
        # — ce qui trichait la fitness. Seule la diagonale est rétablie
        # à True explicitement (self-loop triviale).
        time_mat = np.zeros((self.n + 1, self.n + 1), dtype=float)
        energy_mat = np.zeros((self.n + 1, self.n + 1), dtype=float)
        feasible_mat = np.zeros((self.n + 1, self.n + 1), dtype=bool)
        np.fill_diagonal(feasible_mat, True)

        for _, row in cost_matrix.iterrows():
            i, j = int(row["i"]), int(row["j"])
            pi = self.id_to_pos.get(i)
            pj = self.id_to_pos.get(j)
            if pi is None or pj is None:
                continue
            time_mat[pi, pj] = float(row["time"])
            energy_mat[pi, pj] = float(row["energy"])
            feasible_mat[pi, pj] = bool(row["feasible"])

        self.time_mat = time_mat
        self.energy_mat = energy_mat
        self.feasible_mat = feasible_mat

        super().__init__(
            n_var=self.n,
            n_obj=2,
            n_ieq_constr=0,
            xl=0,
            xu=self.n - 1,
            vtype=int,
        )

    # ------------------------------------------------------------------
    def _decode_positions(self, x: np.ndarray) -> np.ndarray:
        """
        x : permutation de 0..n-1
        Retourne la séquence de POSITIONS dans pos_to_id :
            [0, x[0]+1, x[1]+1, …, x[n-1]+1, 0]
        """
        x = np.asarray(x, dtype=int)
        return np.concatenate([[0], x + 1, [0]])

    def _evaluate(self, X, out, *args, **kwargs) -> None:
        X = np.atleast_2d(np.asarray(X))
        n_sol = X.shape[0]
        F = np.zeros((n_sol, 2), dtype=float)
        for k in range(n_sol):
            pos = self._decode_positions(X[k])
            i_idx = pos[:-1]
            j_idx = pos[1:]
            feasible = self.feasible_mat[i_idx, j_idx]
            if feasible.all():
                F[k, 0] = float(self.time_mat[i_idx, j_idx].sum())
                F[k, 1] = float(self.energy_mat[i_idx, j_idx].sum())
            else:
                n_bad = int((~feasible).sum())
                F[k, 0] = _PENALTY * (1 + n_bad)
                F[k, 1] = _PENALTY * (1 + n_bad)
        out["F"] = F


# ===========================================================================
# Optimiseur
# ===========================================================================
class Optimizer:
    """Orchestre NSGA-II sur la matrice de coûts de BLOC 6."""

    def __init__(
        self,
        config: Config,
        points: pd.DataFrame,
        cost_matrix: pd.DataFrame,
    ) -> None:
        self.config = config
        self.points = points.copy()
        self.cost_matrix = cost_matrix.copy()
        self.center_id = self._identify_center_id(points)
        self.non_center_ids = np.array(
            sorted(int(pid) for pid in points["id"] if int(pid) != self.center_id),
            dtype=int,
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _identify_center_id(points: pd.DataFrame) -> int:
        """
        Le centre est le point le plus proche de (0, 0). En grille
        centrée avec n impair, il est unique.
        """
        dist = np.sqrt(points["x"] ** 2 + points["y"] ** 2)
        idx = dist.idxmin()
        if dist.loc[idx] > 1e-9:
            raise ValueError(
                "Centre (0, 0) absent des points : la grille doit être "
                "centrée (n impair)."
            )
        return int(points.loc[idx, "id"])

    # ------------------------------------------------------------------
    def run(
        self,
        pop_size: int | None = None,
        n_gen: int | None = None,
        seed: int | None = None,
        verbose: bool = False,
        progress_callback: GenerationProgressCallback | None = None,
    ) -> Tuple[List[Dict[str, Any]], Any]:
        """
        Lance NSGA-II et retourne (solutions, result_pymoo).

        Chaque solution est un dict {solution_id, time, energy, order}.
        `time` et `energy` sont des valeurs de DÉPLACEMENT (sans
        stabilisation — celle-ci sera ajoutée par BLOC 8).
        """
        pop_size = pop_size if pop_size is not None else self.config.nsga_pop_size
        n_gen = n_gen if n_gen is not None else self.config.nsga_n_gen
        seed = seed if seed is not None else self.config.nsga_seed

        problem = TourProblem(
            self.cost_matrix, self.center_id, self.non_center_ids,
        )

        algorithm = NSGA2(
            pop_size=pop_size,
            sampling=PermutationRandomSampling(),
            crossover=OrderCrossover(),
            mutation=InversionMutation(),
            eliminate_duplicates=True,
        )

        callback = _GenerationCallback(progress_callback, n_gen) if progress_callback else None

        minimize_kwargs = {
            "seed": seed,
            "verbose": verbose,
            "save_history": False,
        }
        if callback is not None:
            minimize_kwargs["callback"] = callback
        res = minimize(problem, algorithm, ("n_gen", n_gen), **minimize_kwargs)

        # Front de Pareto (pymoo renvoie par défaut les solutions optimales
        # pour un problème multi-objectif dans res.X / res.F).
        # Lecture explicite du front de Pareto (res.opt) plutôt que
        # res.X/res.F.
        opt = res.opt
        X = np.atleast_2d(opt.get("X"))
        F = np.atleast_2d(opt.get("F"))

        # Post-filtrage strict de non-dominance (D-BLOC7-05).
        # pymoo peut laisser passer des couples quasi-dominés à cause
        # d'une tolérance numérique interne. On refait le tri ici avec
        # une comparaison stricte. Opération O(n²) avec n petit (< 100).
        keep_mask = self._strict_non_dominated_mask(F)
        X = X[keep_mask]
        F = F[keep_mask]

        # Détection de front dégénéré : si toutes les solutions ont
        # time ≥ _PENALTY, aucun tour faisable n'a été trouvé.
        if F.shape[0] == 0 or np.all(F[:, 0] >= _PENALTY):
            raise DegenerateFrontError(
                f"Front NSGA-II dégénéré : toutes les solutions sont "
                f"pénalisées (time ≥ {_PENALTY:.0e}). Aucun tour faisable "
                f"n'existe dans le graphe de faisabilité. Vérifier "
                f"cost_matrix.csv (paires infaisables) et réduire la "
                f"difficulté (moins de points, extent plus petit)."
            )


        n_pymoo = len(keep_mask)
        n_kept = int(keep_mask.sum())
        if n_kept < n_pymoo:
            logger.info(
                "Post-filtrage non-dominance : %d/%d solutions conservées "
                "(%d dominées retirées du front pymoo).",
                n_kept, n_pymoo, n_pymoo - n_kept,
            )

        solutions: List[Dict[str, Any]] = []
        for k in range(X.shape[0]):
            pos = problem._decode_positions(X[k])
            tour_ids = problem.pos_to_id[pos]
            solutions.append({
                "solution_id": k,
                "time": float(F[k, 0]),
                "energy": float(F[k, 1]),
                "order": ";".join(str(int(pid)) for pid in tour_ids),
            })

        logger.info(
            "NSGA-II : %d solutions non dominées après post-filtrage "
            "(pop_size=%d, n_gen=%d, seed=%d).",
            len(solutions), pop_size, n_gen, seed,
        )
        return solutions, res

    # ------------------------------------------------------------------
    @staticmethod
    def _strict_non_dominated_mask(F: np.ndarray) -> np.ndarray:
        """
        Retourne un masque booléen des lignes de F qui ne sont dominées
        par aucune autre ligne, avec tolérances numériques.

        A domine B si :
          - A ≤ B + tol sur les deux objectifs
          - A < B − tol sur au moins un objectif

        Tolérances cohérentes avec le Validator (D-BLOC7-06).
        """
        tol_t = 1e-3   # s
        tol_e = 1e-2   # J
        n = F.shape[0]
        keep = np.ones(n, dtype=bool)
        for i in range(n):
            if not keep[i]:
                continue
            for j in range(n):
                if i == j or not keep[j]:
                    continue
                not_worse = (F[j, 0] <= F[i, 0] + tol_t) and (F[j, 1] <= F[i, 1] + tol_e)
                better = (F[j, 0] < F[i, 0] - tol_t) or (F[j, 1] < F[i, 1] - tol_e)
                if not_worse and better:
                    keep[i] = False
                    break
        return keep


    # ------------------------------------------------------------------
    def save(
        self,
        solutions: List[Dict[str, Any]],
        output_dir: Path | str,
    ) -> Dict[str, Path]:
        """
        Écrit 2 CSV :
          - solutions_pareto.csv : format compact (§6)
          - solutions_orders.csv : format long (parsing facilité)
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        df_sol = pd.DataFrame(solutions, columns=_CSV_SOLUTION_COLUMNS)
        csv_sol = output_dir / "solutions_pareto.csv"

        # Précision 15 chiffres significatifs = float64 exact.
        # Le défaut %.6e induisait une perte d'information qui faisait
        # apparaître des solutions "dominées" en apparence (D-BLOC7-06).
        df_sol.to_csv(csv_sol, index=False, float_format="%.15e")

        rows: List[Dict[str, int]] = []
        for sol in solutions:
            ids = [int(x) for x in sol["order"].split(";")]
            for rank, pid in enumerate(ids):
                rows.append({
                    "solution_id": int(sol["solution_id"]),
                    "rank": rank,
                    "point_id": pid,
                })
        df_ord = pd.DataFrame(rows, columns=_CSV_ORDER_COLUMNS)
        csv_ord = output_dir / "solutions_orders.csv"
        df_ord.to_csv(csv_ord, index=False)

        logger.info(
            "Optimizer : %d solutions écrites dans %s", len(solutions), output_dir,
        )
        return {"solutions": csv_sol, "orders": csv_ord}

    # ------------------------------------------------------------------
    def run_and_save(
        self,
        output_dir: Path | str = "data/outputs",
        pop_size: int | None = None,
        n_gen: int | None = None,
        seed: int | None = None,
        verbose: bool = False,
        progress_callback: GenerationProgressCallback | None = None,
    ) -> Dict[str, Any]:
        """Pipeline complet : run + save."""
        solutions, _ = self.run(
            pop_size=pop_size,
            n_gen=n_gen,
            seed=seed,
            verbose=verbose,
            progress_callback=progress_callback,
        )
        paths = self.save(solutions, output_dir)
        return {
            "n_solutions": len(solutions),
            "paths": paths,
            "solutions": solutions,
        }
