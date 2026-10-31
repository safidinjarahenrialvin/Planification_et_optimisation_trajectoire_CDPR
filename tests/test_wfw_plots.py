"""Tests des vues de couverture WFW."""
from __future__ import annotations

import pandas as pd

from visualization.wfw_plots import build_wfw_coverage_figure


def test_rejected_view_renders_pipeline_causes_a_and_b() -> None:
    generated = pd.DataFrame(
        {"id": [0, 1, 2], "x": [0.0, 0.1, 0.2], "y": [0.0, 0.1, 0.2]}
    )
    retained = generated.iloc[[0]].copy()
    rejected = pd.DataFrame(
        {
            "id": [1, 2],
            "x": [0.1, 0.2],
            "y": [0.1, 0.2],
            "cause": ["A", "B"],
        }
    )

    figure = build_wfw_coverage_figure(
        generated, retained, rejected, view="rejected"
    )

    assert [trace.name for trace in figure.data] == [
        "Rejetés : cause A",
        "Rejetés : cause B",
    ]
    assert [len(trace.x) for trace in figure.data] == [1, 1]
