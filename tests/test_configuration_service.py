"""Tests de la couche de configuration contrôlée."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.configuration_service import ConfigurationService
from src.config import Config


def test_validate_returns_stable_effective_configuration() -> None:
    config = Config.with_n(3, zero_loss=True)
    effective = ConfigurationService.validate(
        config, K=5, pop_size=30, n_gen=100, seed=42,
    )

    assert len(effective.fingerprint) == 16
    assert effective.to_dict()["execution"] == {
        "K": 5, "pop_size": 30, "n_gen": 100, "seed": 42,
    }
    assert effective.to_dict()["scientific"]["derived"]["N"] == 9


def test_manual_r0_override_has_distinct_fingerprint_from_automatic_mode() -> None:
    automatic = ConfigurationService.validate(
        Config.with_n(3, zero_loss=True),
        K=5,
        pop_size=30,
        n_gen=100,
        seed=42,
    )
    imposed_at_same_height = ConfigurationService.validate(
        Config.with_n(3, zero_loss=True, z_absolu_r0_override=0.45),
        K=5,
        pop_size=30,
        n_gen=100,
        seed=42,
    )

    assert automatic.fingerprint == "d9003d974052d6ff"
    assert imposed_at_same_height.config.z_absolu_r0 == pytest.approx(0.45)
    assert imposed_at_same_height.fingerprint != automatic.fingerprint


def test_validate_rejects_non_integer_execution_parameter() -> None:
    config = Config.with_n(3, zero_loss=True)
    with pytest.raises(ValueError, match=r"K doit être un entier"):
        ConfigurationService.validate(
            config, K=5.0, pop_size=30, n_gen=100, seed=42,  # type: ignore[arg-type]
        )


def test_serialize_config_groups_values_with_units() -> None:
    serialized = ConfigurationService.serialize_config(
        Config.with_n(3, zero_loss=True),
    )

    assert "geometry" in serialized["domains"]
    assert "kinematics" in serialized["domains"]
    assert serialized["units"]["length"] == "m"
    assert serialized["units"]["speed"] == "m/s"
    assert serialized["domains"]["geometry"]["n_rangs"] == 3
    assert isinstance(serialized["domains"]["geometry"]["attaches_B"], list)


def test_write_snapshot_is_valid_json(tmp_path: Path) -> None:
    effective = ConfigurationService.validate(
        Config.with_n(3, zero_loss=True),
        K=5,
        pop_size=30,
        n_gen=100,
        seed=42,
    )
    path = ConfigurationService.write_snapshot(tmp_path, effective)

    document = json.loads(path.read_text(encoding="utf-8"))
    assert path == tmp_path / "config.json"
    assert document["fingerprint"] == effective.fingerprint
    assert not (tmp_path / "config.json.tmp").exists()
