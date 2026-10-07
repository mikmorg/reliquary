#!/bin/bash
# mutants (expected to FAIL) and v0 runs; each run uses only the fault classes it needs
M=$(dirname "$0"); R="python3 $M/run.py"
$R 2x1 --K 2 --faults bad --bug no_verify --safety-only
$R 2x1 --K 2 --faults "" --bug delete_on_pull --safety-only
$R 2x1 --K 2 --faults "" --bug delete_before_archive --safety-only
$R 2x1 --K 2 --faults "" --bug staging_expiry --safety-only
$R 2x1 --K 2 --faults homecrash --bug resign_receipt --safety-only
$R 2x1 --K 2 --faults "" --bug safe_on_committed_answer --safety-only
$R 2x1 --K 2 --design v0 --faults "" --bug safe_on_staged --safety-only
$R 2x1 --K 3 --faults devcrash --bug self_lease
$R 2x1 --K 3 --faults r2loss --bug no_valve
$R 2x1 --K 3 --faults "" --bug no_reconcile
$R 2x1 --K 3 --faults rollback --bug no_republish
# v0 (analyst F1-F7 as written)
$R 2x1 --K 3 --design v0 --faults gcrace --safety-only
$R 2x1 --K 3 --design v0 --faults gcrace --no-i7 --tag noI7
$R 2x1 --K 3 --design v0 --faults "" 
