"""Validation et sérialisation de la configuration effective SP2.

Cette couche ne remplace pas les règles scientifiques de ``src.config.Config``.
Elle les rend explicites et ajoute les paramètres d'exécution du pipeline pour
que la CLI et la future GUI utilisent le même contrat.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, ClassVar, Dict

import numpy as np

from src.config import Config


@dataclass(frozen=True)
class EffectiveConfiguration:
    """Configuration scientifique et paramètres d'exécution validés."""

    config: Config
    K: int
    pop_size: int
    n_gen: int
    seed: int
    fingerprint: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": 1,
            "fingerprint": self.fingerprint,
            "scientific": ConfigurationService.serialize_config(self.config),
            "execution": {
                "K": self.K,
                "pop_size": self.pop_size,
                "n_gen": self.n_gen,
                "seed": self.seed,
            },
        }


class ConfigurationService:
    """Point d'entrée unique pour contrôler la configuration effective."""

    _DOMAINS: ClassVar[Dict[str, set[str]]] = {
        "geometry": {
            "parcelle_x", "parcelle_y", "n_rangs", "n_colonnes", "esp_x",
            "esp_y", "ancrages_A", "attaches_B", "orientation_plateforme",
        },
        "mechanics": {"masse_kg", "T_min", "T_max"},
        "operational_limits": {
            "x_min", "x_max", "y_min", "y_max", "z_min", "z_max",
        },
        "kinematics": {"v_max", "a_max", "T_acc", "T_dec", "T_stabilisation"},
        "agronomy_vision": {
            "z_vol", "hauteur_plants", "offset_r0_sol", "fov_camera",
            "z_absolu_r0_override",
        },
        "optimization_defaults": {"nsga_pop_size", "nsga_n_gen", "nsga_seed"},
    }

    @classmethod
    def validate(
        cls,
        config: Config,
        *,
        K: int,
        pop_size: int,
        n_gen: int,
        seed: int,
    ) -> EffectiveConfiguration:
        """Valide explicitement Config et les options avant un calcul long."""
        if not isinstance(config, Config):
            raise TypeError(
                f"config doit être une instance de Config, reçu {type(config)!r}."
            )
        for name, value in {
            "K": K,
            "pop_size": pop_size,
            "n_gen": n_gen,
            "seed": seed,
        }.items():
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} doit être un entier, reçu {value!r}.")
        if K < 1:
            raise ValueError(f"K doit être >= 1, reçu {K}.")
        if pop_size < 2:
            raise ValueError(f"pop_size doit être >= 2, reçu {pop_size}.")
        if n_gen < 1:
            raise ValueError(f"n_gen doit être >= 1, reçu {n_gen}.")
        fingerprint = cls.fingerprint(config, K, pop_size, n_gen, seed)
        return EffectiveConfiguration(
            config=config,
            K=K,
            pop_size=pop_size,
            n_gen=n_gen,
            seed=seed,
            fingerprint=fingerprint,
        )

    @classmethod
    def fingerprint(
        cls, config: Config, K: int, pop_size: int, n_gen: int, seed: int,
    ) -> str:
        """Retourne l'empreinte historique stable utilisée pour ``--resume``."""
        parts = [
            f"N={config.N}",
            f"n_rangs={config.n_rangs}",
            f"n_colonnes={config.n_colonnes}",
            f"esp=({config.esp_x:.6f},{config.esp_y:.6f})",
            f"bounds=X[{config.x_min},{config.x_max}]"
            f"Y[{config.y_min},{config.y_max}]Z[{config.z_min},{config.z_max}]",
            f"platform_mass={config.masse_kg:.6f}",
            f"attaches_hash={hashlib.sha256(config.attaches_B.tobytes()).hexdigest()[:16]}",
            f"T=[{config.T_min},{config.T_max}]",
            f"z_absolu_r0={config.z_absolu_r0:.6f}",
            f"z_vol={config.z_vol:.6f}",
            f"fov=({config.fov_camera[0]:.6f},{config.fov_camera[1]:.6f})",
            f"v_max={config.v_max:.6f}",
            f"a_max={config.a_max:.6f}",
            f"T_stabilisation={config.T_stabilisation:.6f}",
            f"K={K}",
            f"pop={pop_size}",
            f"gen={n_gen}",
            f"seed={seed}",
        ]
        # Preserve all historical automatic fingerprints while ensuring that
        # an explicit override is distinguishable, even at the same altitude.
        if config.z_absolu_r0_override is not None:
            parts.append("z_absolu_r0_mode=override")
        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]

    @classmethod
    def serialize_config(cls, config: Config) -> Dict[str, Any]:
        """Convertit Config en données JSON avec unités et valeurs dérivées."""
        raw: Dict[str, Any] = {}
        for field in fields(config):
            raw[field.name] = cls._json_value(getattr(config, field.name))

        domains: Dict[str, Dict[str, Any]] = {}
        assigned: set[str] = set()
        for domain, names in cls._DOMAINS.items():
            domains[domain] = {
                name: raw[name] for name in sorted(names) if name in raw
            }
            assigned.update(names)
        domains["other"] = {
            name: value for name, value in raw.items() if name not in assigned
        }

        return {
            "domains": domains,
            "derived": {
                "N": config.N,
                "z_absolu_sol_m": config.z_absolu_sol,
                "z_absolu_r0_m": config.z_absolu_r0,
            },
            "units": {
                "length": "m",
                "mass": "kg",
                "tension": "N",
                "speed": "m/s",
                "acceleration": "m/s²",
                "angle": "deg",
                "time": "s",
            },
        }

    @classmethod
    def write_snapshot(
        cls, output_dir: Path, effective: EffectiveConfiguration,
    ) -> Path:
        """Écrit la configuration effective de manière atomique et lisible."""
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "config.json"
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(effective.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
        return path

    @staticmethod
    def _json_value(value: Any) -> Any:
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, tuple):
            return [ConfigurationService._json_value(item) for item in value]
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, float):
            if not math.isfinite(value):
                raise ValueError(f"Valeur non finie dans la configuration : {value!r}.")
            return value
        if isinstance(value, (str, int, bool)) or value is None:
            return value
        raise TypeError(f"Valeur de configuration non sérialisable : {value!r}.")
