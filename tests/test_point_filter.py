"""
Tests unitaires — BLOC 5 (PointFilter)
=======================================

Référence : contrat de filtrage des points SP2 (BLOC 5).

Critères :
    - séparation entre points retenus et rejets sur une grille de test faisable.
  - Verrou du centre (exception si infaisable).
  - Classification Cause A / Cause B correcte et séparée.
  - Rapport cohérent, alertes conditionnelles aux seuils.
  - Écriture CSV + JSON conforme au contrat §6.
  - Les 4 fichiers sont bien écrits par save()/run().
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from src.config import Config
from src.point_filter import CenterNotFeasibleError, PointFilter
from src.point_generator import PointGenerator
from src.robot_model import RobotModel
from src.wfw import WFW, WFWSolution


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def cfg() -> Config:
    return Config()


@pytest.fixture
def wfw(cfg: Config) -> WFW:
    return WFW(RobotModel(cfg), cfg)


@pytest.fixture
def pf(cfg: Config, wfw: WFW) -> PointFilter:
    return PointFilter(cfg, wfw)


@pytest.fixture
def grid_df(cfg: Config) -> pd.DataFrame:
    return PointGenerator(cfg).generate()


def _feasible_solution() -> WFWSolution:
    """Solution WFW factice (faisable) pour les mocks."""
    return WFWSolution(
        feasible=True,
        tensions=np.full(8, 10.0),
        residual=0.0,
        status=0,
        message="mock",
    )


def _infeasible_solution() -> WFWSolution:
    """Solution WFW factice (infaisable) pour les mocks."""
    return WFWSolution(
        feasible=False,
        tensions=None,
        residual=float("nan"),
        status=2,
        message="mock-infeasible",
    )


# ----------------------------------------------------------------------
# T1 — Grille de test faisable : aucun rejet
# ----------------------------------------------------------------------
def test_filter_grid_v3_5_partial_kept(pf: PointFilter, grid_df: pd.DataFrame) -> None:
    """
    v3.5 : grille 9×9 (N=81) couvrant ±0.80 m sur la plateforme 300×240.
    Le WFW (radius_x ≈ 0.57, radius_y ≈ 0.34) rejette la majorité des
    points en Cause B. Attendu ~25-40 points retenus.
    """
    result = pf.filter(grid_df)
    assert result.summary["n_total"] == 81
    # Fourchette adaptée à la plateforme 300×240
    assert 25 <= result.summary["n_kept"] <= 40
    assert result.summary["n_rejected_cause_a"] == 0
    assert result.summary["n_rejected_cause_b"] > 0
    # Alerte de taux de rejet attendue (> 15 %)
    assert any("Taux de rejet" in a for a in result.alerts)


# ----------------------------------------------------------------------
# T2 — Format de sortie identique à points_generes (§6)
# ----------------------------------------------------------------------
def test_filter_output_format(pf: PointFilter, grid_df: pd.DataFrame) -> None:
    result = pf.filter(grid_df)
    assert list(result.points_retenus.columns) == [
        "id", "x", "y", "z", "ligne", "colonne"
    ]
    # Aucun rejet : DataFrames vides mais de forme correcte
    assert list(result.points_rejetes_cause_a.columns) == [
        "id", "x", "y", "z", "ligne", "colonne", "cause", "raison"
    ]
    assert list(result.points_rejetes_cause_b.columns) == [
        "id", "x", "y", "z", "ligne", "colonne", "cause", "raison"
    ]


# ----------------------------------------------------------------------
# T3 — Ordre préservé par id
# ----------------------------------------------------------------------
def test_filter_preserves_id_order(pf: PointFilter, grid_df: pd.DataFrame) -> None:
    """Les ids retenus sont triés, sous-ensemble de 0..80."""
    result = pf.filter(grid_df)
    ids = result.points_retenus["id"].tolist()
    assert ids == sorted(ids)
    assert set(ids).issubset(set(range(81)))


# ----------------------------------------------------------------------
# T4 — Centre correctement identifié
# ----------------------------------------------------------------------
def test_filter_centre_identification(pf: PointFilter, grid_df: pd.DataFrame) -> None:
    result = pf.filter(grid_df)
    assert result.centre["feasible"] is True
    assert result.centre["x"] == pytest.approx(0.0)
    assert result.centre["y"] == pytest.approx(0.0)
    # Grille 9×9 centrée → id = 4*9 + 4 = 40
    assert result.centre["id"] == 40


# ----------------------------------------------------------------------
# T5 — Verrou : centre infaisable → exception
# ----------------------------------------------------------------------
def test_filter_centre_infeasible_raises(cfg: Config, grid_df: pd.DataFrame) -> None:
    fake_wfw = MagicMock()
    fake_wfw.is_feasible.return_value = _infeasible_solution()
    pf = PointFilter(cfg, fake_wfw)
    with pytest.raises(CenterNotFeasibleError):
        pf.filter(grid_df)


# ----------------------------------------------------------------------
# T6 — Cause B : point infaisable hors centre
# ----------------------------------------------------------------------
def test_filter_cause_b_classification(cfg: Config, grid_df: pd.DataFrame) -> None:
    """Mock : centre faisable, un point non-centre infaisable."""
    target_id = 41  # voisin immédiat du centre (40) dans la grille 9×9
    centre_row = grid_df.loc[grid_df["id"] == 40].iloc[0]
    target_row = grid_df.loc[grid_df["id"] == target_id].iloc[0]

    def fake_is_feasible(p):
        # Le centre est faisable, le point cible non.
        if (abs(p[0] - centre_row["x"]) < 1e-9
                and abs(p[1] - centre_row["y"]) < 1e-9):
            return _feasible_solution()
        if (abs(p[0] - target_row["x"]) < 1e-9
                and abs(p[1] - target_row["y"]) < 1e-9):
            return _infeasible_solution()
        return _feasible_solution()

    fake_wfw = MagicMock()
    fake_wfw.is_feasible.side_effect = fake_is_feasible
    pf = PointFilter(cfg, fake_wfw)

    result = pf.filter(grid_df)
    assert result.summary["n_kept"] == 80    # (81 - 1 rejet) car le mock force tout faisable sauf 1
    assert result.summary["n_rejected_cause_b"] == 1
    assert result.summary["n_rejected_cause_a"] == 0
    rejected = result.points_rejetes_cause_b
    assert len(rejected) == 1
    assert int(rejected.iloc[0]["id"]) == target_id
    assert rejected.iloc[0]["cause"] == "B"

# ----------------------------------------------------------------------
# T7 — Cause A : point hors limites
# ----------------------------------------------------------------------
def test_filter_cause_a_classification(cfg: Config, grid_df: pd.DataFrame) -> None:
    """Injecte un point hors limites (x=2.0) : doit être Cause A."""
    df = grid_df.copy()
    # On remplace un point non-centre par un point hors limites
    target_idx = df.index[df["id"] == 10][0]
    df.loc[target_idx, "x"] = 2.0

    fake_wfw = MagicMock()
    fake_wfw.is_feasible.return_value = _feasible_solution()  # toujours OK
    pf = PointFilter(cfg, fake_wfw)

    result = pf.filter(df)
    assert result.summary["n_rejected_cause_a"] == 1
    assert result.summary["n_rejected_cause_b"] == 0
    rejected = result.points_rejetes_cause_a
    assert int(rejected.iloc[0]["id"]) == 10
    assert "x=" in rejected.iloc[0]["raison"]


# ----------------------------------------------------------------------
# T8 — Alerte sur taux de rejet ≥ seuil
# ----------------------------------------------------------------------
def test_filter_alert_reject_rate(cfg: Config, grid_df: pd.DataFrame,
                                  caplog: pytest.LogCaptureFixture) -> None:
    """
    Mock : centre faisable, tous les autres infaisables.
    Depuis D-BLOC5-01, cette situation lève InsufficientPointsError.
    """
    from src.point_filter import InsufficientPointsError

    centre_row = grid_df.loc[grid_df["id"] == 40].iloc[0]

    def fake(p):
        if (abs(p[0] - centre_row["x"]) < 1e-9
                and abs(p[1] - centre_row["y"]) < 1e-9):
            return _feasible_solution()
        return _infeasible_solution()

    fake_wfw = MagicMock()
    fake_wfw.is_feasible.side_effect = fake
    pf = PointFilter(cfg, fake_wfw)

    with caplog.at_level("WARNING", logger="src.point_filter"):
        with pytest.raises(InsufficientPointsError, match="Trop peu"):
            pf.filter(grid_df)

    # Vérifier que le message d'erreur contient les bons détails
    assert any("Cause B" in rec.message or "Trop peu" in rec.message
               for rec in caplog.records)


# ----------------------------------------------------------------------
# T9 — Seuils paramétrables
# ----------------------------------------------------------------------
def test_filter_custom_thresholds(cfg: Config, grid_df: pd.DataFrame) -> None:
    """Avec un seuil de rejet très permissif, pas d'alerte même à 0 rejet."""
    fake_wfw = MagicMock()
    fake_wfw.is_feasible.return_value = _feasible_solution()
    pf = PointFilter(cfg, fake_wfw)
    result = pf.filter(grid_df, reject_rate_threshold=0.99)
    assert result.summary["reject_rate_threshold"] == 0.99
    assert result.alerts == []


# ----------------------------------------------------------------------
# T10 — Lecture depuis CSV Path (au lieu du DataFrame)
# ----------------------------------------------------------------------
def test_filter_accepts_csv_path(pf: PointFilter, grid_df: pd.DataFrame,
                                 tmp_path: Path) -> None:
    csv = tmp_path / "grid.csv"
    grid_df.to_csv(csv, index=False)
    result_df = pf.filter(grid_df)
    result_csv = pf.filter(csv)
    assert result_csv.summary == result_df.summary
    assert (result_csv.points_retenus["id"].tolist()
            == result_df.points_retenus["id"].tolist())


# ----------------------------------------------------------------------
# T11 — save : écriture des 4 fichiers
# ----------------------------------------------------------------------
def test_save_writes_four_files(pf: PointFilter, grid_df: pd.DataFrame,
                                tmp_path: Path) -> None:
    result = pf.filter(grid_df)
    paths = pf.save(result, tmp_path)
    assert set(paths.keys()) == {
        "points_filtres", "points_rejetes_cause_a",
        "points_rejetes_cause_b", "report",
    }
    for p in paths.values():
        assert Path(p).exists()
    # JSON lisible
    with paths["report"].open("r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert 25 <= loaded["summary"]["n_kept"] <= 40
    assert loaded["centre"]["feasible"] is True


# ----------------------------------------------------------------------
# T12 — run : pipeline complet
# ----------------------------------------------------------------------
def test_run_creates_all_files(pf: PointFilter, grid_df: pd.DataFrame,
                               tmp_path: Path) -> None:
    paths = pf.run(grid_df, output_dir=tmp_path)
    assert paths["points_filtres"].name == "points_filtres.csv"
    assert paths["report"].name == "point_filter_report.json"
    # Relecture cohérente
    reloaded = pd.read_csv(paths["points_filtres"])
    assert 25 <= len(reloaded) <= 40


# ----------------------------------------------------------------------
# T13 — Entrée malformée
# ----------------------------------------------------------------------
def test_filter_rejects_missing_columns(pf: PointFilter) -> None:
    bad = pd.DataFrame({"id": [0], "x": [0.0]})  # colonnes manquantes
    with pytest.raises(ValueError, match="Colonnes manquantes"):
        pf.filter(bad)


# ----------------------------------------------------------------------
# T14 — Centre absent de la grille → erreur explicite
# ----------------------------------------------------------------------
def test_filter_centre_missing_raises(cfg: Config) -> None:
    """
    Grille 4×4 (pair) : aucun point exactement au centre. Config R4
    accepte une grille paire si l'étendue tient, donc on teste le cas ici.
    """
    cfg_even = Config(n_rangs=4, n_colonnes=4, esp_x=0.25, esp_y=0.25,
                      x_min=-0.75, x_max=0.75, y_min=-0.75, y_max=0.75)
    pg = PointGenerator(cfg_even)
    df = pg.generate()

    fake_wfw = MagicMock()
    fake_wfw.is_feasible.return_value = _feasible_solution()
    pf = PointFilter(cfg_even, fake_wfw)

    with pytest.raises(ValueError, match="Centre"):
        pf.filter(df)
