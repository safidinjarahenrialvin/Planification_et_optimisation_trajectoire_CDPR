#!/usr/bin/env python3
"""Mesure les coûts observables des exports et des campagnes SP2.

Les mesures sont volontairement séparées des décisions scientifiques : elles décrivent
un environnement et une configuration donnés, sans produire d'ETA générale.
"""
from __future__ import annotations

import argparse
import json
import resource
import subprocess
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path
from typing import Any, Sequence

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from services.export_service import ExportService  # noqa: E402


def path_size_bytes(path: Path) -> int:
    """Retourne la taille cumulée des fichiers d'un chemin."""
    if path.is_file():
        return path.stat().st_size
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _maxrss_mb() -> float:
    """Retourne le pic RSS du processus courant, en mégaoctets."""
    # Linux reports KiB; macOS reports bytes. The sandbox and CI are Linux,
    # but keeping the branch makes the measurement script less surprising.
    value = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value / (1024.0 if sys.platform.startswith("linux") else 1024.0**2)


def measure_zip(path: Path) -> dict[str, Any]:
    """Mesure la construction en mémoire d'une archive ZIP d'un run."""
    before_size = path_size_bytes(path)
    tracemalloc.start()
    start = time.perf_counter()
    payload = ExportService.zip_run(path)
    elapsed = time.perf_counter() - start
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "path": str(path),
        "input_size_bytes": before_size,
        "zip_size_bytes": len(payload),
        "compression_ratio": round(len(payload) / before_size, 6) if before_size else None,
        "wall_time_s": round(elapsed, 6),
        "python_peak_allocated_bytes": peak_bytes,
    }


def measure_command(label: str, command: Sequence[str], output_dir: Path) -> dict[str, Any]:
    """Mesure une commande enfant et conserve son résumé de sortie."""
    children_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    start = time.perf_counter()
    completed = subprocess.run(
        list(command),
        cwd=_PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = time.perf_counter() - start
    children_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    stdout_tail = completed.stdout[-2000:]
    stderr_tail = completed.stderr[-2000:]
    return {
        "label": label,
        "command": list(command),
        "returncode": completed.returncode,
        "wall_time_s": round(elapsed, 6),
        "child_cpu_time_s": round(
            (children_after.ru_utime - children_before.ru_utime)
            + (children_after.ru_stime - children_before.ru_stime),
            6,
        ),
        "child_peak_rss_mb_cumulative": round(children_after.ru_maxrss / 1024.0, 3),
        "output_size_bytes": path_size_bytes(output_dir) if output_dir.exists() else 0,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/evidence/cost-measurement-20261029.json"),
        help="Fichier JSON de résultats.",
    )
    parser.add_argument(
        "--fast-output-dir",
        type=Path,
        default=None,
        help="Dossier du smoke test; un dossier temporaire est utilisé par défaut.",
    )
    parser.add_argument(
        "--run-fast",
        action="store_true",
        help="Exécute un smoke test FAST avant de le mesurer.",
    )
    parser.add_argument(
        "--run-nominal",
        action="store_true",
        help="Exécute la qualification nominale avant de mesurer ses artefacts.",
    )
    parser.add_argument(
        "--nominal-output-dir",
        type=Path,
        default=None,
        help="Dossier de campagne nominale; les artefacts versionnés sont utilisés par défaut.",
    )
    parser.add_argument("--nominal-seeds", type=int, nargs="+", default=[42, 43, 44])
    parser.add_argument("--nominal-pop-size", type=int, default=500)
    parser.add_argument("--nominal-n-gen", type=int, default=1500)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    measurements: dict[str, Any] = {
        "schema_version": 1,
        "measured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python": sys.version,
        "platform": sys.platform,
        "process_peak_rss_mb": round(_maxrss_mb(), 3),
        "exports": [],
        "commands": [],
        "limitations": [
            "Les durées sont des observations de cet environnement et de cette configuration.",
            "child_peak_rss_mb_cumulative est cumulatif entre commandes du même processus parent.",
            "Aucune conclusion scientifique n'est déduite de ces mesures d'exploitation.",
        ],
    }

    with tempfile.TemporaryDirectory(prefix="tandem-cost-") as temporary:
        temp_root = Path(temporary)
        fast_dir = args.fast_output_dir or temp_root / "fast"
        if args.run_fast:
            measurements["commands"].append(
                measure_command(
                    "pipeline_fast",
                    [
                        sys.executable,
                        "scripts/run_pipeline.py",
                        "--fast",
                        "--output-dir",
                        str(fast_dir),
                    ],
                    fast_dir,
                )
            )
        elif not fast_dir.exists():
            raise FileNotFoundError(
                f"Dossier FAST absent : {fast_dir}. Utilisez --run-fast ou --fast-output-dir."
            )
        measurements["exports"].append(measure_zip(fast_dir))

        nominal_dir = args.nominal_output_dir or Path("data/qualification/nominal-9x9")
        if args.run_nominal:
            nominal_dir = args.nominal_output_dir or temp_root / "nominal-9x9"
            measurements["commands"].append(
                measure_command(
                    "qualification_nominale_9x9",
                    [
                        sys.executable,
                        "scripts/qualify_nominal.py",
                        "--output-dir",
                        str(nominal_dir),
                        "--seeds",
                        *(str(seed) for seed in args.nominal_seeds),
                        "--pop-size",
                        str(args.nominal_pop_size),
                        "--n-gen",
                        str(args.nominal_n_gen),
                    ],
                    nominal_dir,
                )
            )
        if not nominal_dir.exists():
            raise FileNotFoundError(f"Dossier nominal absent : {nominal_dir}")

        for seed in args.nominal_seeds:
            seed_dir = nominal_dir / f"seed_{seed}"
            if seed_dir.exists():
                measurements["exports"].append(measure_zip(seed_dir))
        measurements["campaign"] = {
            "path": str(nominal_dir),
            "artifact_size_bytes": path_size_bytes(nominal_dir),
            "seed_count_measured": len(measurements["exports"]) - 1,
        }

    measurements["process_peak_rss_mb_after"] = round(_maxrss_mb(), 3)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(measurements, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(measurements, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
