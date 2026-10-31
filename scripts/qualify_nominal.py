#!/usr/bin/env python3
"""Lance une campagne reproductible de qualification nominale 9×9."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from services.qualification_service import QualificationSpec, run_qualification  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Campagne multi-seeds de qualification nominale SP2.",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    parser.add_argument("--n", type=int, default=9)
    parser.add_argument("--platform", default="300x240")
    parser.add_argument("--zero-loss", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--K", type=int, default=10)
    parser.add_argument("--pop-size", type=int, default=500)
    parser.add_argument("--n-gen", type=int, default=1500)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    spec = QualificationSpec(
        n=args.n,
        platform=args.platform,
        zero_loss=args.zero_loss,
        K=args.K,
        pop_size=args.pop_size,
        n_gen=args.n_gen,
        seeds=tuple(args.seeds),
    )
    records = run_qualification(spec, args.output_dir)
    for record in records:
        print(
            f"seed={record.seed} status={record.status} "
            f"validation={record.validation_status} "
            f"pareto={record.n_pareto_solutions}"
        )
    return 0 if all(record.status == "COMPLETED" for record in records) else 2


if __name__ == "__main__":
    raise SystemExit(main())
