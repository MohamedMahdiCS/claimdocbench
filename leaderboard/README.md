# Leaderboard

Every row is a scorer report in [`results/`](results/), built into a static page by
`claimdocbench leaderboard` and published with GitHub Pages.

## Add your system

1. Download the test split and run your system on every packet, including the injection twins
   listed under `twins` in `index.json`:

   ```bash
   uv run claimdocbench download --split test
   ```

2. Write one JSON line per packet. `packet_id`, `decision` and `payable_amount` are required.
   Add `confidence`, `fields`, `evidence`, `integrity_flags`, `injection_detected`,
   `latency_s` and `cost_usd` to be scored on the other columns.

3. Score it and name it:

   ```bash
   uv run claimdocbench evaluate --split-dir out/test --predictions preds.jsonl \
     --system "Your system (model, hardware)" --report leaderboard/results/your-system.json
   ```

4. Open a pull request with the report and a sentence on how the system works.

Please don't tune on `test`. Use `dev` for that.
