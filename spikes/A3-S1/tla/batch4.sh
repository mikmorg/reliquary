#!/bin/bash
M=$(dirname "$0"); R="python3 $M/run.py"
$R 2x1 --K 2 --max-faults 1 --faults devcrash --bug self_lease --tag demo --timeout 600
$R 2x1 --K 2 --max-faults 1 --faults devcrash --tag demo --timeout 600
$R 2x1 --K 3 --max-faults 1 --faults devcrash --tag only-devcrash-long --timeout 2400
$R 2x1 --K 3 --max-faults 1 --faults r2loss --tag only-r2loss-long --timeout 2400
