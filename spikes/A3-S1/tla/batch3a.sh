#!/bin/bash
M=$(dirname "$0"); R="python3 $M/run.py"
for f in lostresp homecrash down abort r2loss bad rollback spurious; do
  $R 2x1 --K 3 --max-faults 1 --faults $f --tag only-$f --timeout 700
done
