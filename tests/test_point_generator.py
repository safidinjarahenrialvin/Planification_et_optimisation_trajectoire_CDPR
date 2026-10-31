"""
Tests unitaires — BLOC 4 (PointGenerator)
==========================================

Référence : contrat de génération de grille SP2 (BLOC 4).

Critères :
  - Reproduction exacte pour au moins deux configurations N différentes.
  - Ordre (id, ligne, colonne) cohérent avec BLOC 3.
  - Étendue de grille conforme à Config.
  - FOV report bien formé.
  - Écriture CSV et JSON correcte.
  - Aucune constante en dur (test paramétrique).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.config import Config
from src.point_generator import PointGenerator


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def cfg() -> Config:
    return Config()


@pytest.fixture
def pg(cfg: Config) -> PointGenerator:
    return PointGenerator(cfg)


# ----------------------------------------------------------------------
# T1 — Forme et colonnes du DataFrame
# ----------------------------------------------------------------------
def test_generate_shape_and_columns(pg: PointGenerator) -> None:
    df = pg.generate()
    assert isinstance(df, pd.DataFrame)
    assert df.shape == (81, 6)
    assert list(df.columns) == ["id", "x", "y", "z", "ligne", "colonne"]


# ----------------------------------------------------------------------
# T2 — Ordre (id, ligne, colonne) row-major
# ----------------------------------------------------------------------
def test_generate_ordering(pg: PointGenerator) -> None:
    df = pg.generate()
    n_col = pg.config.n_colonnes
    assert df["id"].tolist() == list(range(81))
    assert (df["ligne"] == df["id"] // n_col).all()
    assert (df["colonne"] == df["id"] % n_col).all()
    assert df.iloc[0]["ligne"] == 0 and df.iloc[0]["colonne"] == 0
    assert df.iloc[-1]["ligne"] == pg.config.n_rangs - 1
    assert df.iloc[-1]["colonne"] == n_col - 1


# ----------------------------------------------------------------------
# T3 — Étendue et pas de la grille
# ----------------------------------------------------------------------
def test_generate_extent(pg: PointGenerator) -> None:
    df = pg.generate()
    xs = np.sort(df["x"].unique())
    ys = np.sort(df["y"].unique())
    assert xs.shape == (9,)
    assert ys.shape == (9,)
    assert xs[0] == pytest.approx(-0.80)
    assert xs[-1] == pytest.approx(+0.80)
    assert ys[0] == pytest.approx(-0.80)
    assert ys[-1] == pytest.approx(+0.80)
    # L'espacement provient de la configuration par défaut.
    assert np.allclose(np.diff(xs), 0.20)
    assert np.allclose(np.diff(ys), 0.20)


# ----------------------------------------------------------------------
# T4 — z constant et égal à z_absolu_r0
# ----------------------------------------------------------------------
def test_z_constant(pg: PointGenerator) -> None:
    df = pg.generate()
    assert df["z"].nunique() == 1
    assert df["z"].iloc[0] == pytest.approx(pg.config.z_absolu_r0)


# ----------------------------------------------------------------------
# T5 — Grille centrée sur (0, 0)
# ----------------------------------------------------------------------
def test_grid_centered(pg: PointGenerator) -> None:
    df = pg.generate()
    assert df["x"].mean() == pytest.approx(0.0, abs=1e-12)
    assert df["y"].mean() == pytest.approx(0.0, abs=1e-12)


# ----------------------------------------------------------------------
# T6 — Origin tuple : shift sans déformation
# ----------------------------------------------------------------------
def test_origin_tuple_shifts_grid() -> None:
    """
    Vérifie qu'un décalage de grille préserve la structure (id, ligne,
    colonne) et décale les coordonnées de la valeur demandée.

    NOTE : on utilise une config 5×5 (±0.5 m) car avec la config 7×7
    par défaut (±0.75 m), la grille remplit déjà exactement la zone
    opérationnelle et aucun shift non nul n'est possible sans sortir
    des limites (voir test_origin_shift_out_of_bounds_raises).
    """
    cfg_small = Config(n_rangs=5, n_colonnes=5)
    pg_small = PointGenerator(cfg_small)

    df_centre = pg_small.generate(origin="centre")
    df_shift = pg_small.generate(origin=(0.2, -0.1))

    # Structure identique
    assert (df_centre["id"] == df_shift["id"]).all()
    assert (df_centre["ligne"] == df_shift["ligne"]).all()
    assert (df_centre["colonne"] == df_shift["colonne"]).all()
    # Coordonnées décalées de (0.2, -0.1)
    assert np.allclose(df_shift["x"] - df_centre["x"], 0.2)
    assert np.allclose(df_shift["y"] - df_centre["y"], -0.1)


def test_origin_shift_out_of_bounds_raises(pg: PointGenerator) -> None:
    """
    Avec la config 7×7 par défaut, tout shift non nul sort de la zone
    opérationnelle (±0.75 m). Le garde-fou _verify_extent doit lever.
    """
    with pytest.raises(ValueError, match="Étendue X"):
        pg.generate(origin=(0.5, -0.5))


def test_origin_invalid(pg: PointGenerator) -> None:
    with pytest.raises(ValueError, match="origin"):
        pg.generate(origin="coin_haut_gauche")


# ----------------------------------------------------------------------
# T7 — N paramétrique (aucune constante en dur)
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "n_rangs, n_colonnes, expected_N",
    [
        (7, 7, 49),
        (5, 5, 25),
        (3, 3, 9),
        (7, 5, 35),
    ],
)
def test_N_parametric(n_rangs: int, n_colonnes: int, expected_N: int) -> None:
    cfg = Config(n_rangs=n_rangs, n_colonnes=n_colonnes)
    df = PointGenerator(cfg).generate()
    assert len(df) == expected_N
    assert df["id"].tolist() == list(range(expected_N))


# ----------------------------------------------------------------------
# T8 — Rapport FOV : structure et valeurs
# ----------------------------------------------------------------------
def test_fov_report_structure(pg: PointGenerator) -> None:
    report = pg.fov_report()
    assert set(report.keys()) == {
        "config_summary", "grid_extent", "fov_footprint",
        "overlap", "alerts",
    }
    assert report["config_summary"]["N"] == 81
    assert report["config_summary"]["n_rangs"] == 9
    assert report["grid_extent"]["half_x_m"] == pytest.approx(0.80)
    assert report["grid_extent"]["half_y_m"] == pytest.approx(0.80)


def test_fov_footprint_values(pg: PointGenerator) -> None:
    """W_h ≈ 36.2 cm, W_v ≈ 27.2 cm (valeur recalculée sans arrondi doc)."""
    report = pg.fov_report()
    assert report["fov_footprint"]["W_h_cm"] == pytest.approx(36.21, abs=0.05)
    assert report["fov_footprint"]["W_v_cm"] == pytest.approx(27.22, abs=0.05)


def test_overlap_positive_for_v3_2(pg: PointGenerator) -> None:
    """
    v3.2 : esp = 20 cm. Empreinte FOV = 36.19 × 27.23 cm.
    Recouvrement attendu :
      overlap_x = 36.19 − 20 = 16.19 cm
      overlap_y = 27.23 − 20 =  7.23 cm
    """
    report = pg.fov_report()
    assert report["overlap"]["x_cm"] == pytest.approx(16.19, abs=0.05)
    assert report["overlap"]["y_cm"] == pytest.approx(7.23, abs=0.05)
    assert report["overlap"]["covers_fully_x"] is True
    assert report["overlap"]["covers_fully_y"] is True


def test_alerts_empty_v3_1(pg: PointGenerator) -> None:
    """Avec la config v3.1, aucune alerte ne doit être levée."""
    report = pg.fov_report()
    assert report["alerts"] == []


# ----------------------------------------------------------------------
# T9 — save_csv : écriture et relecture
# ----------------------------------------------------------------------
def test_save_csv_roundtrip(pg: PointGenerator, tmp_path: Path) -> None:
    df = pg.generate()
    out = tmp_path / "pts.csv"
    result = pg.save_csv(df, out)
    assert result == out
    assert out.exists()

    df2 = pd.read_csv(out)
    assert list(df2.columns) == list(df.columns)
    assert len(df2) == len(df)
    # Comparaison numérique à 1e-5 (précision d'écriture %.6f)
    assert np.allclose(df2["x"].to_numpy(), df["x"].to_numpy(), atol=1e-5)
    assert np.allclose(df2["y"].to_numpy(), df["y"].to_numpy(), atol=1e-5)
    assert np.allclose(df2["z"].to_numpy(), df["z"].to_numpy(), atol=1e-5)
    assert (df2["id"].to_numpy() == df["id"].to_numpy()).all()


# ----------------------------------------------------------------------
# T10 — save_json : écriture et relecture
# ----------------------------------------------------------------------
def test_save_json_roundtrip(pg: PointGenerator, tmp_path: Path) -> None:
    report = pg.fov_report()
    out = tmp_path / "report.json"
    result = pg.save_json(report, out)
    assert result == out
    assert out.exists()

    with out.open("r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["config_summary"]["N"] == report["config_summary"]["N"]
    assert loaded["alerts"] == report["alerts"]
    assert loaded["fov_footprint"]["W_h_cm"] == pytest.approx(
        report["fov_footprint"]["W_h_cm"]
    )


# ----------------------------------------------------------------------
# T11 — run() : pipeline complet
# ----------------------------------------------------------------------
def test_run_creates_both_files(pg: PointGenerator, tmp_path: Path) -> None:
    paths = pg.run(output_dir=tmp_path)
    assert set(paths.keys()) == {"csv", "json"}
    assert paths["csv"].exists()
    assert paths["json"].exists()
    assert paths["csv"].name == "points_generes.csv"
    assert paths["json"].name == "points_generes_report.json"


# ----------------------------------------------------------------------
# T12 — Création automatique des répertoires parents
# ----------------------------------------------------------------------
def test_run_creates_missing_dirs(pg: PointGenerator, tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b" / "c"
    paths = pg.run(output_dir=nested)
    assert paths["csv"].parent.exists()
    assert paths["json"].parent.exists()
