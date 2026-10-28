#!/bin/sh
cd "$(dirname "$0")/.."
for model in bonsai-2:4b bonsai-2:2b; do
  for mode in vision ocr; do
    tag=$(echo "$model" | tr ':' '-')-$mode
    uv run claimdocbench run-baseline --model "$model" --mode "$mode" --split-dir out/dev --subset smoke --out "runs/smoke/$tag.jsonl" > "runs/smoke/$tag.log" 2>&1
  done
done
echo SMOKE_DONE
