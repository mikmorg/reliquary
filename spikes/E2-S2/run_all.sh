#!/bin/sh
# E2-S2: trust-model check of the metric field inventory, then the emulated pipeline.
# Needs python3 (stdlib only) and the `age` / `age-keygen` CLIs on PATH. About 1 minute.
set -e
cd "$(dirname "$0")"
mkdir -p evidence
python3 metrics_model.py evidence/metrics-check.json
python3 simulate.py evidence > evidence/simulate-stdout.json
echo "done: see evidence/"
