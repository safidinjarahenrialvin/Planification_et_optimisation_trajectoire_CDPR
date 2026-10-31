"""Animation pédagogique du robot à câbles depuis un profil scientifique réel."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.config import Config
from src.robot_model import RobotModel
from visualization.robot_3d import SceneOptions, build_robot_figure


@dataclass(frozen=True)
class AnimationOptions:
    """Paramètres d’affichage, sans modifier les données du run."""

    max_frames: int = 120
    frame_duration_ms: int = 80


def build_robot_animation_figure(
    config: Config,
    profile_df: pd.DataFrame,
    *,
    points_df: pd.DataFrame | None = None,
    options: AnimationOptions | None = None,
) -> go.Figure:
    """Construit une animation Plotly depuis les positions temporelles du profil."""
    options = options or AnimationOptions()
    required = {"t", "x", "y", "z"}
    missing = required - set(profile_df.columns)
    if missing:
        raise ValueError(f"Colonnes profil manquantes : {sorted(missing)}")
    if options.max_frames < 2:
        raise ValueError("max_frames doit être >= 2")

    profile = profile_df.sort_values("t").drop_duplicates("t")
    if len(profile) < 2:
        raise ValueError("Un profil doit contenir au moins deux instants")
    indices = np.linspace(
        0, len(profile) - 1, min(options.max_frames, len(profile)), dtype=int
    )
    samples = profile.iloc[indices].reset_index(drop=True)

    figure = build_robot_figure(
        config,
        points_df=points_df,
        options=SceneOptions(
            show_frame=True,
            show_supports=True,
            show_cables=False,
            show_platform=False,
            show_points=points_df is not None and not points_df.empty,
            show_center=True,
        ),
    )
    robot = RobotModel(config)
    anchors = robot.A
    trace_indices: list[int] = []
    for cable_index in range(8):
        start = anchors[:, cable_index]
        end = robot.attach_positions(samples.iloc[0][["x", "y", "z"]].to_numpy())[
            :, cable_index
        ]
        figure.add_trace(
            go.Scatter3d(
                x=[start[0], end[0]],
                y=[start[1], end[1]],
                z=[start[2], end[2]],
                mode="lines",
                line={"color": "#455a64", "width": 3},
                name="Câbles animés" if cable_index == 0 else None,
                showlegend=cable_index == 0,
                hoverinfo="skip",
            )
        )
        trace_indices.append(len(figure.data) - 1)

    platform_trace_index = len(figure.data)
    figure.add_trace(_platform_mesh(config, samples.iloc[0][["x", "y", "z"]].to_numpy()))

    frames: list[go.Frame] = []
    for frame_index, sample in samples.iterrows():
        center = sample[["x", "y", "z"]].to_numpy(dtype=float)
        attachments = robot.attach_positions(center)
        frame_data = []
        for cable_index in range(8):
            start = anchors[:, cable_index]
            end = attachments[:, cable_index]
            frame_data.append(
                go.Scatter3d(
                    x=[start[0], end[0]],
                    y=[start[1], end[1]],
                    z=[start[2], end[2]],
                )
            )
        frame_data.append(_platform_mesh(config, center))
        frames.append(
            go.Frame(
                name=str(frame_index),
                data=frame_data,
                traces=[*trace_indices, platform_trace_index],
                layout={
                        "title": f"Robot à câbles : t = {sample['t']:.2f} s",
                },
            )
        )

    figure.frames = frames
    figure.update_layout(
        title=(
            f"Animation pédagogique : profil réel : durée {samples.iloc[-1]['t']:.2f} s"
        ),
        updatemenus=[
            {
                "type": "buttons",
                "showactive": False,
                "x": 0.02,
                "y": 0,
                "xanchor": "left",
                "yanchor": "top",
                "buttons": [
                    {
                        "label": "Lecture",
                        "method": "animate",
                        "args": [
                            None,
                            {
                                "frame": {"duration": options.frame_duration_ms, "redraw": True},
                                "fromcurrent": True,
                                "transition": {"duration": 0},
                            },
                        ],
                    },
                    {
                        "label": "Pause",
                        "method": "animate",
                        "args": [
                            [None],
                            {
                                "frame": {"duration": 0, "redraw": False},
                                "mode": "immediate",
                            },
                        ],
                    },
                ],
            }
        ],
        sliders=[
            {
                "active": 0,
                "x": 0.14,
                "y": 0,
                "len": 0.82,
                "xanchor": "left",
                "yanchor": "top",
                "currentvalue": {"prefix": "Échantillon : "},
                "steps": [
                    {
                        "label": f"{sample['t']:.1f}s",
                        "method": "animate",
                        "args": [
                            [str(index)],
                            {
                                "mode": "immediate",
                                "frame": {"duration": 0, "redraw": True},
                            },
                        ],
                    }
                    for index, sample in samples.iterrows()
                ],
            }
        ],
    )
    return figure


def _platform_mesh(config: Config, center: np.ndarray) -> go.Mesh3d:
    b = config.attaches_B
    xmin, xmax = float(b[0].min()), float(b[0].max())
    ymin, ymax = float(b[1].min()), float(b[1].max())
    zmin, zmax = float(b[2].min()), float(b[2].max())
    return go.Mesh3d(
        x=[center[0] + value for value in (xmin, xmax, xmax, xmin, xmin, xmax, xmax, xmin)],
        y=[center[1] + value for value in (ymin, ymin, ymax, ymax, ymin, ymin, ymax, ymax)],
        z=[center[2] + value for value in (zmin, zmin, zmin, zmin, zmax, zmax, zmax, zmax)],
        i=[0, 0, 0, 1, 1, 2, 4, 4, 5, 6, 2, 3],
        j=[1, 2, 3, 5, 6, 3, 5, 7, 6, 7, 6, 7],
        k=[2, 3, 1, 6, 2, 7, 6, 5, 7, 4, 7, 4],
        color="#1565c0",
        opacity=0.9,
        flatshading=True,
        name="Plateforme animée",
        hoverinfo="skip",
    )
