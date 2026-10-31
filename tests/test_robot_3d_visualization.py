"""Tests du composant 3D partagé entre CLI et Streamlit."""
from pathlib import Path

import pandas as pd
import pytest

from src.config import Config
from services.result_service import ResultService
from visualization.robot_animation import build_robot_animation_figure
from visualization.robot_3d import SceneOptions, build_robot_figure, load_config_snapshot


def test_build_robot_figure_exposes_expected_layers() -> None:
    config = Config.with_n(9)
    points = pd.DataFrame({"id": [1], "x": [0.0], "y": [0.0], "z": [0.45]})
    trajectory = pd.DataFrame({
        "kind": ["time_opt"], "rank": [0], "x": [0.0], "y": [0.0], "z": [0.45],
    })
    figure = build_robot_figure(
        config,
        points_df=points,
        trajectory_df=trajectory,
        options=SceneOptions(show_plants=True, show_center=True, show_trajectory=True),
    )
    names = {trace.name for trace in figure.data}
    assert "Bâti" in names
    assert "Câbles" in names
    assert "Plateforme mobile" in names
    assert "Points de vue (1)" in names
    assert "Plants : tiges" in names
    assert "Centre de la plateforme" in names
    assert "Trajectoire (1 waypoints)" in names


def test_load_config_snapshot_preserves_robot_geometry(run_fixture: Path) -> None:
    config = load_config_snapshot(run_fixture / "config.json")
    assert config.N == 9
    assert config.ancrages_A.shape == (3, 8)
    assert config.attaches_B.shape == (3, 8)
    assert config.z_absolu_r0 == pytest.approx(0.45)


def test_robot_figure_bounds_large_trajectory_rendering() -> None:
    config = Config.with_n(9)
    trajectory = pd.DataFrame({
        "kind": ["time_opt"] * 3001,
        "rank": list(range(3001)),
        "x": [0.0] * 3001,
        "y": [0.0] * 3001,
        "z": [0.45] * 3001,
    })

    figure = build_robot_figure(
        config,
        trajectory_df=trajectory,
        options=SceneOptions(show_trajectory=True),
    )

    rendered = next(
        trace
        for trace in figure.data
        if trace.name and trace.name.startswith("Trajectoire")
    )
    assert len(rendered.x) <= 2500


def test_robot_animation_uses_real_profile_and_bounded_frames(run_fixture: Path) -> None:
    results = ResultService.load(run_fixture)
    config = load_config_snapshot(run_fixture / "config.json")
    profile = results.profiles[results.profiles["kind"] == "time_opt"]
    figure = build_robot_animation_figure(
        config,
        profile,
        points_df=results.points_filtered,
    )

    assert 1 < len(figure.frames) <= 120
    assert len(figure.layout.sliders[0].steps) == len(figure.frames)
    assert any(trace.name == "Plateforme animée" for trace in figure.data)
