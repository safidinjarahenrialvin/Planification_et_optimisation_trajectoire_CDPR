#!/usr/bin/env python3
"""Analyse la stabilité du front Pareto d'une campagne multi-seeds."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from services.pareto_stability import write_stability_report  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyse reproductible de la stabilité Pareto entre seeds."
    )
    parser.add_argument("--campaign-dir", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = write_stability_report(args.campaign_dir)
    aggregate = report["aggregates"]
    print(f"seeds={','.join(str(seed) for seed in report['seeds'])}")
    print(
        "pareto_cardinality="
        f"{aggregate['n_solutions']['min']}-"
        f"{aggregate['n_solutions']['max']}"
    )
    print(
        "normalized_hausdorff_mean="
        f"{aggregate['normalized_hausdorff']['mean']:.6f}"
    )
    print(
        "time_interval_overlap_min="
        f"{aggregate['time_interval_overlap']['min']:.6f}"
    )
    print(f"json={args.campaign_dir / 'pareto_stability_report.json'}")
    print(f"markdown={args.campaign_dir / 'pareto_stability_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
