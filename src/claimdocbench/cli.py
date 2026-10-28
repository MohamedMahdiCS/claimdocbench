"""Command-line interface: `claimdocbench generate ...`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from claimdocbench.dataset import generate_split


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="claimdocbench", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="generate a dataset split")
    gen.add_argument("--split", default="dev", help="split name, e.g. dev, test, smoke")
    gen.add_argument("--n", type=int, default=50, help="number of claim packets")
    gen.add_argument("--seed", type=int, default=0)
    gen.add_argument("--out", type=Path, default=Path("out"))

    args = parser.parse_args(argv)
    if args.command == "generate":
        summary = generate_split(args.split, args.n, args.seed, args.out)
        counts = {k: v for k, v in summary.items() if k != "packets"}
        print(json.dumps(counts, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
