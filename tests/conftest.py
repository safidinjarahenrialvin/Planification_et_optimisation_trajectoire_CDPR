"""Fixtures communes aux tests du projet."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import pandas as pd

from services.configuration_service import ConfigurationService
from src.config import Config


@pytest.fixture
def run_fixture(tmp_path: Path) -> Path:
    """Prépare un run complet isolé à partir du snapshot scientifique versionné."""
    repository_root = Path(__file__).parents[1]
    snapshot = repository_root / "tests" / "fixtures" / "reference_run"
    run_dir = tmp_path / "run_export_fixture"
    shutil.copytree(snapshot, run_dir)

    effective = ConfigurationService.validate(
        Config.with_n(3, zero_loss=True),
        K=5,
        pop_size=30,
        n_gen=100,
        seed=42,
    )
    ConfigurationService.write_snapshot(run_dir, effective)
    return run_dir


@pytest.fixture
def legacy_baseline_run_fixture(run_fixture: Path) -> Path:
    """Run historique valide dont le kind de référence est baseline_nn."""
    for filename in ("comparison.csv", "baseline_zigzag.csv"):
        path = run_fixture / filename
        frame = pd.read_csv(path)
        mask = frame["kind"] == "baseline_zigzag"
        assert mask.any()
        frame.loc[mask, "kind"] = "baseline_nn"
        frame.to_csv(path, index=False)

    diagnostic_path = run_fixture / "comparison_diagnostic.json"
    diagnostic = json.loads(diagnostic_path.read_text(encoding="utf-8"))
    diagnostic["baseline_kind"] = "baseline_nn"
    diagnostic_path.write_text(
        json.dumps(diagnostic, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return run_fixture
