#!/bin/bash
M=$(dirname "$0"); R="python3 $M/run.py"
$R 2x1 --K 3 --max-faults 1 --safety-only --tag allfaults --timeout 1500
$R 3x1 --K 3 --max-faults 1 --safety-only --tag allfaults --timeout 1500
$R 3x3ring --K 2 --max-faults 0 --faults "" --safety-only --tag nofaults --timeout 1500
$R 2x1 --K 3 --max-faults 2 --safety-only --tag allfaults --timeout 1500
$R 3x3ring --K 2 --max-faults 1 --safety-only --tag allfaults --timeout 1500
