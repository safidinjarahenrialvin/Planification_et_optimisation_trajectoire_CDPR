"""
Tests unitaires — WFW3DViewer
===============================

Résolutions volontairement très basses (8×8×5) pour rester rapides.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import numpy as np
import pytest

from src.config import Config
from src.robot_model import RobotModel
from src.wfw_3d import WFW3DViewer


@pytest.fixture
def cfg() -> Config:
    return Config()


@pytest.fixture
def robot(cfg: Config) -> RobotModel:
    return RobotModel(cfg)


@pytest.fixture
def viewer(cfg: Config, robot: RobotModel) -> WFW3DViewer:
    return WFW3DViewer(robot, cfg, n_xy=8, n_z=5)


# --- T1 : paramètres invalides ----------------------------------------
def test_invalid_n_xy_raises(cfg: Config, robot: RobotModel) -> None:
    with pytest.raises(ValueError, match="n_xy"):
        WFW3DViewer(robot, cfg, n_xy=2, n_z=5)


def test_invalid_n_z_raises(cfg: Config, robot: RobotModel) -> None:
    with pytest.raises(ValueError, match="n_z"):
        WFW3DViewer(robot, cfg, n_xy=8, n_z=1)


# --- T2 : bornes par défaut = enveloppe des ancrages ------------------
def test_default_bounds_match_anchors(viewer: WFW3DViewer, cfg: Config) -> None:
    A = cfg.ancrages_A
    assert viewer.x_bounds == (float(A[0, :].min()), float(A[0, :].max()))
    assert viewer.y_bounds == (float(A[1, :].min()), float(A[1, :].max()))
    assert viewer.z_bounds == (float(A[2, :].min()), float(A[2, :].max()))


# --- T3 : compute_volume : formes et invariants ------------------------
def test_compute_volume_shapes(viewer: WFW3DViewer) -> None:
    vol = viewer.compute_volume(t_min=10.0, t_max=58.0)
    assert vol.x.shape == (viewer.n_xy,)
    assert vol.y.shape == (viewer.n_xy,)
    assert vol.z.shape == (viewer.n_z,)
    assert vol.feasible.shape == (viewer.n_xy, viewer.n_xy, viewer.n_z)
    assert vol.feasible.dtype == bool
    assert 0.0 <= vol.feasible_ratio <= 1.0


def test_compute_volume_records_stats(viewer: WFW3DViewer) -> None:
    vol = viewer.compute_volume(t_min=5.0, t_max=58.0)
    assert vol.t_min == 5.0
    assert vol.n_lp_calls == viewer.n_xy * viewer.n_xy * viewer.n_z
    assert vol.duration_s > 0.0


# --- T4 : centre faisable à faible T_min -------------------------------
def test_center_feasible_at_low_t_min(viewer: WFW3DViewer, cfg: Config) -> None:
    vol = viewer.compute_volume(t_min=1.0, t_max=58.0)
    i_c = int(np.argmin(np.abs(vol.x)))
    j_c = int(np.argmin(np.abs(vol.y)))
    k_c = int(np.argmin(np.abs(vol.z - cfg.z_absolu_r0)))
    assert vol.feasible[i_c, j_c, k_c]


# --- T5 : imbrication WFW(20) ⊂ WFW(10) ⊂ WFW(5) ⊂ WCW(0) -------------
def test_workspace_volumes_contain_wfw(viewer: WFW3DViewer) -> None:
    """
    Le WFW (T_min > 0) est contenu dans le WCW (T_min = 0).
    Toute pose faisable en WFW doit être faisable en WCW.
    """
    vols = viewer.compute_workspace_volumes()
    assert set(vols.keys()) == {"wcw", "wfw"}
    # Imbrication : WFW ⊂ WCW
    assert not (vols["wfw"].feasible & ~vols["wcw"].feasible).any()


def test_workspace_volumes_use_config(viewer: WFW3DViewer) -> None:
    """Les t_min/t_max effectivement utilisés proviennent de Config."""
    vols = viewer.compute_workspace_volumes()
    assert vols["wfw"].t_min == pytest.approx(viewer.config.T_min)
    assert vols["wfw"].t_max == pytest.approx(viewer.config.T_max)
    assert vols["wcw"].t_min == 0.0
    assert vols["wcw"].t_max == pytest.approx(viewer.config.T_max)


# --- T6 : plot_combined écrit un PNG ----------------------------------
def test_plot_workspace_writes_png(viewer: WFW3DViewer, tmp_path: Path) -> None:
    """plot_workspace produit un PNG non vide et retourne les 2 volumes."""
    out = tmp_path / "workspace.png"
    vols = viewer.plot_workspace(out)
    assert out.exists() and out.stat().st_size > 0
    assert set(vols.keys()) == {"wcw", "wfw"}


def test_plot_workspace_returns_volumes(viewer: WFW3DViewer, tmp_path: Path) -> None:
    """plot_workspace retourne des volumes cohérents avec Config."""
    vols = viewer.plot_workspace(tmp_path / "c.png")
    assert vols["wcw"].t_min == 0.0
    assert vols["wcw"].t_max == pytest.approx(viewer.config.T_max)
    assert vols["wfw"].t_min == pytest.approx(viewer.config.T_min)
    assert vols["wfw"].t_max == pytest.approx(viewer.config.T_max)
    for v in vols.values():
        assert 0.0 <= v.feasible_ratio <= 1.0


# --- T7 : bornes custom -----------------------------------------------
def test_custom_bounds_respected(cfg: Config, robot: RobotModel) -> None:
    viewer = WFW3DViewer(
        robot, cfg,
        x_bounds=(-0.5, 0.5), y_bounds=(-0.5, 0.5), z_bounds=(0.2, 0.6),
        n_xy=6, n_z=4,
    )
    assert viewer.x_bounds == (-0.5, 0.5)
    assert viewer.z_bounds == (0.2, 0.6)
    vol = viewer.compute_volume(t_min=5.0, t_max=58.0)
    assert vol.x[0] == pytest.approx(-0.5)
    assert vol.x[-1] == pytest.approx(0.5)
    assert vol.z[0] == pytest.approx(0.2)
    assert vol.z[-1] == pytest.approx(0.6)




def test_robot_3d_build_figure_smoke() -> None:
    """
    Test de fumée : `Robot3DViewer.build_figure()` s'exécute sans
    NameError. Détecte les lignes manquantes dans le corps de la méthode.
    """
    from src.config import Config
    from src.robot_3d_viewer import Robot3DViewer

    config = Config.with_n(9)
    viewer = Robot3DViewer(config)
    fig = viewer.build_figure()
    assert fig is not None
    assert len(fig.data) > 0
