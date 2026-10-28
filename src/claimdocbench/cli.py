"""Command-line interface for ClaimDocBench."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from claimdocbench.dataset import generate_split, tree_hash


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="claimdocbench", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="generate a dataset split")
    gen.add_argument("--split", default="dev", help="split name, e.g. dev, test, heldout")
    gen.add_argument("--n", type=int, default=50, help="number of claim packets")
    gen.add_argument("--seed", type=int, default=0)
    gen.add_argument("--out", type=Path, default=Path("out"))
    gen.add_argument("--heldout", action="store_true", help="use held-out-only layouts")

    hsh = sub.add_parser("hash", help="print the tree hash of a generated split")
    hsh.add_argument("path", type=Path)

    ev = sub.add_parser("evaluate", help="score a predictions file against a split")
    ev.add_argument("--split-dir", type=Path, required=True)
    ev.add_argument("--predictions", type=Path, required=True)
    ev.add_argument("--report", type=Path, help="write the full JSON report here")
    ev.add_argument("--subset", choices=["all", "smoke"], default="all")

    base = sub.add_parser("baseline", help="write predictions from a model-free baseline")
    base.add_argument("name", choices=["approve-all", "oracle"])
    base.add_argument("--split-dir", type=Path, required=True)
    base.add_argument("--out", type=Path, required=True)

    aud = sub.add_parser("audit", help="check planted problems are detectable")
    aud.add_argument("split_dir", type=Path)

    args = parser.parse_args(argv)
    if args.command == "generate":
        summary = generate_split(args.split, args.n, args.seed, args.out, heldout=args.heldout)
        print(
            json.dumps(
                {k: v for k, v in summary.items() if k not in ("packets", "smoke")}, indent=2
            )
        )
    elif args.command == "hash":
        digest, count = tree_hash(args.path)
        print(json.dumps({"path": str(args.path), "files": count, "sha256": digest}))
    elif args.command == "evaluate":
        from claimdocbench.scoring import evaluate, render_markdown

        report = evaluate(args.split_dir, args.predictions, subset=args.subset)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(render_markdown(report))
    elif args.command == "audit":
        from claimdocbench.audit import audit_split

        result = audit_split(args.split_dir)
        print(
            json.dumps(
                {
                    **result,
                    "problems": result["problems"][:20],
                    "problem_count": len(result["problems"]),
                },
                indent=2,
            )
        )
        return 1 if result["problems"] else 0
    elif args.command == "baseline":
        from claimdocbench.baselines import predictions, write_jsonl

        write_jsonl(predictions(args.name, args.split_dir), args.out)
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
