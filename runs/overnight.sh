#!/bin/sh
# Day 3 overnight: single-prompt baselines on test, OpenAdjuster v0 on dev.
cd "$(dirname "$0")/.."
uv run --no-sync claimdocbench baseline approve-all --split-dir out/test --out runs/test/approve-all.jsonl
for cfg in "bonsai-2:4b vision" "bonsai-2:4b ocr" "bonsai-2:2b vision"; do
  set -- $cfg
  tag=$(echo "$1" | tr ':' '-')-$2
  uv run --no-sync claimdocbench run-baseline --model "$1" --mode "$2" --split-dir out/test \
    --out "runs/test/single-prompt-$tag.jsonl" > "runs/test/single-prompt-$tag.log" 2>&1
done
cd ../openadjuster && uv run openadjuster run --split-dir ../claimdocbench/out/dev \
  --out ../claimdocbench/runs/dev/openadjuster-v0.jsonl > ../claimdocbench/runs/dev/openadjuster-v0.log 2>&1
echo OVERNIGHT_DONE
