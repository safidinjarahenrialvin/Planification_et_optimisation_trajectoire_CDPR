"""Tests du support oral généré depuis les artefacts scientifiques."""

from pathlib import Path

from services.presentation_service import build_jury_script
from services.result_service import ResultService

REFERENCE = Path(__file__).parents[1] / "tests" / "fixtures" / "reference_run"


def test_jury_script_uses_reference_metrics_and_limits() -> None:
    results = ResultService.load(REFERENCE)
    script = build_jury_script("reference-demo", results)

    assert "`reference-demo`" in script
    assert "9 retenus" in script
    assert "Trajectoire temps optimal" in script
    assert "Trajectoire énergie optimale" in script
    assert "temps de mouvement" in script
    assert "temps total" in script
    assert "WARN" in script
    assert "Point de vigilance" in script
