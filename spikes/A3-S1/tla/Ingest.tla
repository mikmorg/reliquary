------------------------------- MODULE Ingest -------------------------------
(***************************************************************************)
(* A3-S1 (run B): TLA+ model of the Reliquary v0 ingest protocol.          *)
(* THROWAWAY research model, not production code.                          *)
(*                                                                         *)
(* Models docs/research/a3-ingest-protocol.md F1-F7 and D1 SR-04..SR-12:   *)
(*   - per-upload staging keys; the claim is an advisory lease;            *)
(*   - typed dedup answers (MISSING / IN_FLIGHT / COMMITTED) that never    *)
(*     mean safe; the device always sends its own signed record;           *)
(*   - a device safety valve (re-upload when its item is stuck);           *)
(*   - queue messages are hints; reconciliation by listing meta/ is the    *)
(*     path of record; the homelab acks after a durable inbox write;       *)
(*   - the durable-commit contract: verify + put_blob -> archive record    *)
(*     and store receipt -> publish -> delete staging (homelab only);      *)
(*   - D1 (Worker state) is a cache that can be rolled back.               *)
(*                                                                         *)
(* DESIGN = "v0": the analyst's F1-F7 as written (record sent after        *)
(*   Complete; homelab GCs completed objects that have no record after a   *)
(*   grace period).                                                        *)
(* DESIGN = "v1": record-first Complete (the Complete call carries the     *)
(*   signed record; the Worker writes meta/ before completing), so a       *)
(*   completed staging object always has a record and no orphan GC exists.*)
(* Both designs: a record whose upload is gone (no multipart, no object)   *)
(*   and whose content is not home gets a typed reject "content-missing".  *)
(*                                                                         *)
(* Abstractions (README lists all):                                        *)
(*   - an item IS its dedup ID; uploaded bytes are "good" or "bad"         *)
(*     (corrupted / poisoned). HMAC and SHA-256 collisions not modelled.   *)
(*   - submission <<d, c, k>> = attempt k of device d for item c, k<=K;    *)
(*     one record and at most one upload per submission.                   *)
(*   - time is not modelled. Timers are nondeterministic actions; a timer  *)
(*     firing "too early" is a counted fault, a timely one is fair.        *)
(*   - receipts are genuine (honest homelab key). Forgery and a malicious  *)
(*     Worker are D1-S2 / D4 scope.                                        *)
(***************************************************************************)
EXTENDS Naturals, FiniteSets, TLC

CONSTANTS
  Dev, Item,     \* model values
  Hold,          \* set of <<d, c>>: device d holds item c
  K,             \* attempt slots per pair
  Faults,        \* enabled fault classes (subset of FaultClasses)
  MaxFaults,     \* total fault budget across all classes
  DESIGN,        \* "v0" or "v1"
  BUG            \* "none" = design as proposed; else an injected mutant

FaultClasses == {"kill", "devcrash", "lostresp", "homecrash", "down", "abort",
                 "r2loss", "bad", "gcrace", "rollback", "spurious"}
ASSUME Faults \subseteq FaultClasses /\ DESIGN \in {"v0", "v1"} /\ K \in Nat \ {0}

Sub == { <<p[1], p[2], k>> : p \in Hold, k \in 1..K }
PairOf(s) == <<s[1], s[2]>>
ItemOf(s) == s[2]
SubOf(p, k) == <<p[1], p[2], k>>

VARIABLES
  alive, phase, att,                                      \* devices
  kind, row, lease, mp, stg, meta, queue, relay, mark,    \* cloud (D1 = row, lease, relay, mark)
  up, inbox, pc, blob, arch, issued, rej,                 \* homelab (pc volatile)
  delStg, delMeta, orphan,                                \* history, read by invariants only
  faults                                                  \* fault budget used

devVars   == <<alive, phase, att>>
cloudVars == <<kind, row, lease, mp, stg, meta, queue, relay, mark>>
homeVars  == <<up, inbox, pc, blob, arch, issued, rej>>
histVars  == <<delStg, delMeta, orphan>>
vars == <<devVars, cloudVars, homeVars, histVars, faults>>

Fault(f) == f \in Faults /\ faults < MaxFaults
Spend == faults' = faults + 1

CurSub(p) == SubOf(p, att[p])

TypeOK ==
  /\ alive \in [Dev -> BOOLEAN]
  /\ phase \in [Hold -> {"idle", "uploading", "staged", "awaiting", "safe"}]
  /\ att \in [Hold -> 0..K]
  /\ kind \in [Sub -> {"none", "hit", "up"}]
  /\ row \in [Sub -> {"none", "claimed", "staged", "committed", "rejected", "gone"}]
  /\ lease \in [Sub -> BOOLEAN] /\ mp \in [Sub -> BOOLEAN] /\ meta \in [Sub -> BOOLEAN]
  /\ stg \in [Sub -> {"none", "good", "bad"}]
  /\ queue \subseteq Sub /\ relay \subseteq Sub /\ inbox \subseteq Sub
  /\ mark \in [Item -> BOOLEAN] /\ up \in BOOLEAN
  /\ pc \in [Sub -> 0..3]
  /\ blob \in [Item -> {"none", "good", "bad"}]
  /\ arch \subseteq Sub /\ rej \subseteq Sub /\ issued \in [Sub -> 0..2]
  /\ delStg \subseteq Sub /\ delMeta \subseteq Sub /\ orphan \subseteq Sub
  /\ faults \in 0..MaxFaults

Init ==
  /\ alive = [d \in Dev |-> TRUE]
  /\ phase = [p \in Hold |-> "idle"] /\ att = [p \in Hold |-> 0]
  /\ kind = [s \in Sub |-> "none"] /\ row = [s \in Sub |-> "none"]
  /\ lease = [s \in Sub |-> FALSE] /\ mp = [s \in Sub |-> FALSE]
  /\ stg = [s \in Sub |-> "none"] /\ meta = [s \in Sub |-> FALSE]
  /\ queue = {} /\ relay = {} /\ mark = [c \in Item |-> FALSE]
  /\ up = TRUE /\ inbox = {} /\ pc = [s \in Sub |-> 0]
  /\ blob = [c \in Item |-> "none"] /\ arch = {} /\ rej = {}
  /\ issued = [s \in Sub |-> 0]
  /\ delStg = {} /\ delMeta = {} /\ orphan = {}
  /\ faults = 0

-----------------------------------------------------------------------------
(* The Worker's typed dedup answer, from D1 only (may be stale or rolled   *)
(* back). COMMITTED needs a relayed receipt for the content (content-only  *)
(* verification, CE section 10). No answer ever marks an item safe.        *)
(* A live lease held by the asking device itself never yields IN_FLIGHT    *)
(* (self-supersede; found necessary by this model, see README F-B1).       *)
Answer(c, d) ==
  IF mark[c] /\ \E s \in relay : ItemOf(s) = c THEN "COMMITTED"
  ELSE IF \E s \in Sub : /\ ItemOf(s) = c
                        /\ \/ row[s] = "claimed" /\ lease[s] /\ (s[1] /= d \/ BUG = "self_lease")
                           \/ row[s] = "staged"
       THEN "IN_FLIGHT" ELSE "MISSING"

HasReceipt(p)  == \E k \in 1..att[p] : SubOf(p, k) \in relay
HasArchived(p) == \E k \in 1..att[p] : SubOf(p, k) \in arch

UploadAlive(s) ==   \* this upload can still reach the homelab without help
  /\ kind[s] = "up"
  /\ \/ /\ alive[s[1]] /\ att[PairOf(s)] = s[3]
        /\ phase[PairOf(s)] \in {"uploading", "staged"} /\ (mp[s] \/ stg[s] = "good")
     \/ (meta[s] \/ s \in inbox) /\ stg[s] = "good"

Progressable(s) ==  \* the homelab can still commit record s with no new device action
  /\ (meta[s] \/ s \in inbox) /\ s \notin rej
  /\ \/ blob[ItemOf(s)] = "good"
     \/ kind[s] = "up" /\ stg[s] = "good"
     \/ kind[s] = "hit" /\ \E s2 \in Sub : ItemOf(s2) = ItemOf(s) /\ UploadAlive(s2)

(* The 24 h "awaiting commit" valve timer fires (fairly) only when nothing *)
(* already in the system will produce this device's receipt. A premature  *)
(* firing is the "spurious" fault.                                         *)
Stuck(p) == ~HasArchived(p) /\ ~Progressable(CurSub(p))

-----------------------------------------------------------------------------
(* Device *)

NewUpload(p) ==
  LET s == SubOf(p, att[p] + 1) IN
  /\ att' = [att EXCEPT ![p] = @ + 1]
  /\ kind' = [kind EXCEPT ![s] = "up"]
  /\ row' = [row EXCEPT ![s] = "claimed"]
  /\ lease' = [lease EXCEPT ![s] = TRUE]
  /\ mp' = [mp EXCEPT ![s] = TRUE]
  /\ phase' = [phase EXCEPT ![p] = "uploading"]

Start(p) ==
  /\ alive[p[1]] /\ phase[p] = "idle" /\ att[p] < K
  /\ LET a == Answer(p[2], p[1]) IN
       IF a = "MISSING" THEN NewUpload(p) /\ UNCHANGED <<meta, queue>>
       ELSE IF a = "COMMITTED" /\ BUG = "safe_on_committed_answer"
            THEN phase' = [phase EXCEPT ![p] = "safe"] /\ UNCHANGED <<att, kind, row, lease, mp, meta, queue>>
            ELSE LET s == SubOf(p, att[p] + 1) IN       \* dedup hit: record with no content object
                 /\ att' = [att EXCEPT ![p] = @ + 1]
                 /\ kind' = [kind EXCEPT ![s] = "hit"]
                 /\ meta' = [meta EXCEPT ![s] = TRUE]
                 /\ queue' = queue \cup {s}
                 /\ phase' = [phase EXCEPT ![p] = "awaiting"]
                 /\ UNCHANGED <<row, lease, mp>>
  /\ UNCHANGED <<alive, stg, relay, mark, homeVars, histVars, faults>>

(* Worker completes the multipart upload. v1: writes the record to meta/ first. *)
WorkerComplete(s, bytes) ==
  /\ stg' = [stg EXCEPT ![s] = bytes]
  /\ mp' = [mp EXCEPT ![s] = FALSE]
  /\ row' = [row EXCEPT ![s] = "staged"]
  /\ lease' = [lease EXCEPT ![s] = FALSE]
  /\ IF DESIGN = "v1" THEN meta' = [meta EXCEPT ![s] = TRUE] /\ queue' = queue \cup {s}
                      ELSE UNCHANGED <<meta, queue>>

AfterComplete == IF DESIGN = "v1" THEN "awaiting" ELSE "staged"

Complete(p) ==
  /\ alive[p[1]] /\ phase[p] = "uploading"
  /\ LET s == CurSub(p) IN
       \/ mp[s] /\ WorkerComplete(s, "good") /\ UNCHANGED faults
          /\ phase' = [phase EXCEPT ![p] = AfterComplete]
       \/ mp[s] /\ Fault("bad") /\ Spend /\ WorkerComplete(s, "bad")   \* corrupted / poisoned bytes
          /\ phase' = [phase EXCEPT ![p] = AfterComplete]
       \/ /\ ~mp[s] /\ (row[s] = "staged" \/ stg[s] /= "none")      \* lost response: already staged
          /\ phase' = [phase EXCEPT ![p] = AfterComplete]
          /\ UNCHANGED <<stg, mp, row, lease, meta, queue, faults>>
       \/ /\ ~mp[s] /\ row[s] /= "staged" /\ stg[s] = "none"         \* NoSuchUpload: restart
          /\ phase' = [phase EXCEPT ![p] = "idle"]
          /\ row' = [row EXCEPT ![s] = "gone"]
          /\ UNCHANGED <<stg, mp, lease, meta, queue, faults>>
  /\ UNCHANGED <<alive, att, kind, relay, mark, homeVars, histVars>>

CompleteLostResponse(p) ==   \* Worker completed; the device never heard
  /\ alive[p[1]] /\ phase[p] = "uploading" /\ Fault("lostresp")
  /\ mp[CurSub(p)] /\ WorkerComplete(CurSub(p), "good") /\ Spend
  /\ UNCHANGED <<alive, phase, att, kind, relay, mark, homeVars, histVars>>

SendRecord(p) ==             \* v0 only: record sent after Complete
  /\ alive[p[1]] /\ phase[p] = "staged"
  /\ meta' = [meta EXCEPT ![CurSub(p)] = TRUE]
  /\ queue' = queue \cup {CurSub(p)}
  /\ phase' = [phase EXCEPT ![p] = IF BUG = "safe_on_staged" THEN "safe" ELSE "awaiting"]
  /\ UNCHANGED <<alive, att, kind, row, lease, mp, stg, relay, mark, homeVars, histVars, faults>>

Fetch(p) ==
  /\ alive[p[1]] /\ phase[p] = "awaiting" /\ HasReceipt(p)
  /\ phase' = [phase EXCEPT ![p] = "safe"]
  /\ UNCHANGED <<alive, att, cloudVars, homeVars, histVars, faults>>

Recheck(p) ==   \* back-off re-check of a dedup hit, or of an own rejected/abandoned upload
  /\ BUG /= "no_valve"
  /\ alive[p[1]] /\ phase[p] = "awaiting" /\ att[p] < K /\ ~HasReceipt(p)
  /\ kind[CurSub(p)] = "hit" \/ row[CurSub(p)] \in {"rejected", "gone"}
  /\ Answer(p[2], p[1]) = "MISSING"
  /\ NewUpload(p)
  /\ UNCHANGED <<alive, stg, meta, queue, relay, mark, homeVars, histVars, faults>>

Valve(p) ==
  /\ BUG /= "no_valve"
  /\ alive[p[1]] /\ phase[p] = "awaiting" /\ att[p] < K /\ ~HasReceipt(p) /\ Stuck(p)
  /\ NewUpload(p)
  /\ UNCHANGED <<alive, stg, meta, queue, relay, mark, homeVars, histVars, faults>>

SpuriousValve(p) ==
  /\ alive[p[1]] /\ phase[p] = "awaiting" /\ att[p] < K /\ ~HasReceipt(p)
  /\ Fault("spurious") /\ Spend
  /\ NewUpload(p)
  /\ UNCHANGED <<alive, stg, meta, queue, relay, mark, homeVars, histVars>>

DevCrash(p) ==  \* crash that loses the upload journal: restart with a new submission
  /\ alive[p[1]] /\ phase[p] \in {"uploading", "staged"} /\ Fault("devcrash") /\ Spend
  /\ phase' = [phase EXCEPT ![p] = "idle"]
  /\ UNCHANGED <<alive, att, cloudVars, homeVars, histVars>>

Kill(d) ==      \* device gone for good
  /\ alive[d] /\ Fault("kill") /\ Spend
  /\ alive' = [alive EXCEPT ![d] = FALSE]
  /\ UNCHANGED <<phase, att, cloudVars, homeVars, histVars>>

-----------------------------------------------------------------------------
(* Cloud, R2, queue *)

LeaseExpire(s) ==
  /\ lease[s] /\ lease' = [lease EXCEPT ![s] = FALSE]
  /\ UNCHANGED <<devVars, kind, row, mp, stg, meta, queue, relay, mark, homeVars, histVars, faults>>

R2AbortActive(s) ==   \* the 7-day auto-abort hits an upload that is still going
  /\ mp[s] /\ Fault("abort") /\ Spend
  /\ mp' = [mp EXCEPT ![s] = FALSE]
  /\ UNCHANGED <<devVars, kind, row, lease, stg, meta, queue, relay, mark, homeVars, histVars>>

LifecycleAbort(s) ==  \* AbortIncompleteMultipartUpload cleans parts nobody will complete
  /\ mp[s] /\ ~(alive[s[1]] /\ phase[PairOf(s)] = "uploading" /\ att[PairOf(s)] = s[3])
  /\ mp' = [mp EXCEPT ![s] = FALSE]
  /\ UNCHANGED <<devVars, kind, row, lease, stg, meta, queue, relay, mark, homeVars, histVars, faults>>

R2Loss(s) ==          \* R2 loses (or an operator deletes) a good staged object
  /\ stg[s] = "good" /\ Fault("r2loss") /\ Spend
  /\ stg' = [stg EXCEPT ![s] = "none"]
  /\ UNCHANGED <<devVars, kind, row, lease, mp, meta, queue, relay, mark, homeVars, histVars>>

LifecycleExpire(s) == \* mutant: an Expiration lifecycle rule on staging/
  /\ BUG = "staging_expiry" /\ stg[s] /= "none"
  /\ stg' = [stg EXCEPT ![s] = "none"] /\ delStg' = delStg \cup {s}
  /\ UNCHANGED <<devVars, kind, row, lease, mp, meta, queue, relay, mark, homeVars, delMeta, orphan, faults>>

QueueDrop(s) ==       \* drop / retention expiry / max_retries deletion: unbounded, never fair
  /\ s \in queue /\ queue' = queue \ {s}
  /\ UNCHANGED <<devVars, kind, row, lease, mp, stg, meta, relay, mark, homeVars, histVars, faults>>

D1Rollback ==         \* Time Travel restore / partial wipe: one fact per fault
  /\ Fault("rollback") /\ Spend
  /\ \/ \E s \in relay : relay' = relay \ {s} /\ UNCHANGED <<row, lease, mark>>
     \/ \E c \in Item : mark[c] /\ mark' = [mark EXCEPT ![c] = FALSE] /\ UNCHANGED <<row, lease, relay>>
     \/ \E s \in Sub : /\ row[s] \in {"staged", "committed", "rejected", "gone"}
                       /\ row' = [row EXCEPT ![s] = "claimed"] /\ lease' = [lease EXCEPT ![s] = TRUE]
                       /\ UNCHANGED <<relay, mark>>
     \/ \E s \in Sub : /\ row[s] \in {"committed", "rejected", "gone"}
                       /\ row' = [row EXCEPT ![s] = "staged"] /\ UNCHANGED <<relay, mark, lease>>
  /\ UNCHANGED <<devVars, kind, mp, stg, meta, queue, homeVars, histVars>>

-----------------------------------------------------------------------------
(* Homelab *)

Down ==
  /\ up /\ Fault("down") /\ Spend
  /\ up' = FALSE /\ pc' = [s \in Sub |-> 0]
  /\ UNCHANGED <<devVars, cloudVars, inbox, blob, arch, issued, rej, histVars>>

Up ==
  /\ ~up /\ up' = TRUE
  /\ UNCHANGED <<devVars, cloudVars, inbox, pc, blob, arch, issued, rej, histVars, faults>>

HomeCrash ==
  /\ up /\ (\E s \in Sub : pc[s] /= 0) /\ Fault("homecrash") /\ Spend
  /\ pc' = [s \in Sub |-> 0]
  /\ UNCHANGED <<devVars, cloudVars, up, inbox, blob, arch, issued, rej, histVars>>

Pull(s) ==            \* write the hint to the durable inbox, then ack
  /\ up /\ s \in queue
  /\ inbox' = inbox \cup {s} /\ queue' = queue \ {s}
  /\ IF BUG = "delete_on_pull"
       THEN /\ stg' = [stg EXCEPT ![s] = "none"] /\ meta' = [meta EXCEPT ![s] = FALSE]
            /\ delStg' = IF stg[s] /= "none" THEN delStg \cup {s} ELSE delStg
            /\ delMeta' = IF meta[s] THEN delMeta \cup {s} ELSE delMeta
       ELSE UNCHANGED <<stg, meta, delStg, delMeta>>
  /\ UNCHANGED <<devVars, kind, row, lease, mp, relay, mark, up, pc, blob, arch, issued, rej, orphan, faults>>

Reconcile ==          \* list meta/; republish receipts and marks; repair stale D1 rows
  /\ up /\ BUG /= "no_reconcile"
  /\ inbox' = inbox \cup {s \in Sub : meta[s]}
  /\ IF BUG = "no_republish"
       THEN UNCHANGED <<relay, mark, row>>
       ELSE /\ relay' = relay \cup arch
            /\ mark' = [c \in Item |-> mark[c] \/ blob[c] = "good"]
            /\ row' = [s \in Sub |->
                        IF kind[s] = "up" /\ s \in arch THEN "committed"
                        ELSE IF s \in rej THEN "rejected"
                        ELSE IF row[s] \in {"claimed", "staged"} /\ ~mp[s] /\ stg[s] = "none" THEN "gone"
                        ELSE row[s]]
  /\ <<inbox', relay', mark', row'>> /= <<inbox, relay, mark, row>>
  /\ UNCHANGED <<devVars, kind, lease, mp, stg, meta, queue, up, pc, blob, arch, issued, rej, histVars, faults>>

NoRecordComing(s) == ~(alive[s[1]] /\ att[PairOf(s)] = s[3] /\ phase[PairOf(s)] \in {"uploading", "staged"})

OrphanCandidate(s) == DESIGN = "v0" /\ up /\ stg[s] /= "none" /\ ~meta[s] /\ s \notin inbox /\ s \notin arch

OrphanGC(s) ==        \* v0: grace period over and nobody will send the record (fair)
  /\ OrphanCandidate(s) /\ NoRecordComing(s)
  /\ stg' = [stg EXCEPT ![s] = "none"] /\ delStg' = delStg \cup {s} /\ orphan' = orphan \cup {s}
  /\ UNCHANGED <<devVars, kind, row, lease, mp, meta, queue, relay, mark, homeVars, delMeta, faults>>

OrphanGCRace(s) ==    \* v0: grace period ran out on a slow device that will still send it
  /\ OrphanCandidate(s) /\ ~NoRecordComing(s) /\ Fault("gcrace") /\ Spend
  /\ stg' = [stg EXCEPT ![s] = "none"] /\ delStg' = delStg \cup {s} /\ orphan' = orphan \cup {s}
  /\ UNCHANGED <<devVars, kind, row, lease, mp, meta, queue, relay, mark, homeVars, delMeta>>

(* Step A: verify + put_blob (durable), or dedup, or a typed reject. *)
IngestA(s) ==
  LET c == ItemOf(s) IN
  /\ up /\ s \in inbox /\ pc[s] = 0
  /\ CASE s \in arch /\ BUG /= "resign_receipt" ->
            pc' = [pc EXCEPT ![s] = 2] /\ UNCHANGED <<blob, rej, row>>
       [] s \in rej -> pc' = [pc EXCEPT ![s] = 3] /\ UNCHANGED <<blob, rej, row>>
       [] blob[c] = "good" -> pc' = [pc EXCEPT ![s] = 1] /\ UNCHANGED <<blob, rej, row>>
       [] kind[s] = "up" /\ stg[s] = "good" ->
            blob' = [blob EXCEPT ![c] = "good"] /\ pc' = [pc EXCEPT ![s] = 1] /\ UNCHANGED <<rej, row>>
       [] kind[s] = "up" /\ stg[s] = "bad" /\ BUG = "no_verify" ->
            blob' = [blob EXCEPT ![c] = "bad"] /\ pc' = [pc EXCEPT ![s] = 1] /\ UNCHANGED <<rej, row>>
       [] kind[s] = "up" /\ (stg[s] = "bad" \/ (~mp[s] /\ stg[s] = "none")) ->
            \* verification failed, or content-missing: log durably, publish, then clean up
            /\ rej' = rej \cup {s} /\ row' = [row EXCEPT ![s] = "rejected"]
            /\ pc' = [pc EXCEPT ![s] = 3] /\ UNCHANGED blob
       [] OTHER -> FALSE   \* pending: a hit whose content is not home yet, or upload still open
  /\ UNCHANGED <<devVars, kind, lease, mp, stg, meta, queue, relay, mark, up, inbox, arch, issued, histVars, faults>>

IngestB(s) ==   \* archive the record; sign and durably store the receipt (once)
  /\ up /\ s \in inbox /\ pc[s] = 1
  /\ arch' = arch \cup {s}
  /\ issued' = [issued EXCEPT ![s] = IF @ = 0 THEN 1 ELSE IF BUG = "resign_receipt" THEN 2 ELSE @]
  /\ pc' = [pc EXCEPT ![s] = 2]
  /\ UNCHANGED <<devVars, cloudVars, up, inbox, blob, rej, histVars, faults>>

IngestC(s) ==   \* publish receipt and commit mark to the Worker (idempotent upsert)
  /\ up /\ s \in inbox /\ pc[s] = 2
  /\ relay' = relay \cup {s}
  /\ mark' = [mark EXCEPT ![ItemOf(s)] = TRUE]
  /\ row' = IF kind[s] = "up" THEN [row EXCEPT ![s] = "committed"] ELSE row
  /\ pc' = [pc EXCEPT ![s] = 3]
  /\ UNCHANGED <<devVars, kind, lease, mp, stg, meta, queue, up, inbox, blob, arch, issued, rej, histVars, faults>>

IngestD(s) ==   \* only now delete staging and the record object (homelab credentials)
  /\ up /\ s \in inbox
  /\ pc[s] = 3 \/ (BUG = "delete_before_archive" /\ pc[s] = 1)
  /\ stg' = [stg EXCEPT ![s] = "none"] /\ meta' = [meta EXCEPT ![s] = FALSE]
  /\ delStg' = IF stg[s] /= "none" THEN delStg \cup {s} ELSE delStg
  /\ delMeta' = IF meta[s] THEN delMeta \cup {s} ELSE delMeta
  /\ inbox' = inbox \ {s} /\ pc' = [pc EXCEPT ![s] = 0]
  /\ UNCHANGED <<devVars, kind, row, lease, mp, queue, relay, mark, up, blob, arch, issued, rej, orphan, faults>>

-----------------------------------------------------------------------------
Next ==
  \/ \E p \in Hold : \/ Start(p) \/ Complete(p) \/ CompleteLostResponse(p) \/ SendRecord(p)
                     \/ Fetch(p) \/ Recheck(p) \/ Valve(p) \/ SpuriousValve(p) \/ DevCrash(p)
  \/ \E d \in Dev : Kill(d)
  \/ \E s \in Sub : \/ LeaseExpire(s) \/ R2AbortActive(s) \/ LifecycleAbort(s) \/ R2Loss(s)
                    \/ LifecycleExpire(s) \/ QueueDrop(s) \/ Pull(s) \/ OrphanGC(s) \/ OrphanGCRace(s)
                    \/ IngestA(s) \/ IngestB(s) \/ IngestC(s) \/ IngestD(s)
  \/ D1Rollback \/ Down \/ Up \/ HomeCrash \/ Reconcile

Fairness ==
  /\ \A p \in Hold : /\ WF_vars(Start(p)) /\ WF_vars(Complete(p)) /\ WF_vars(SendRecord(p))
                     /\ WF_vars(Fetch(p)) /\ WF_vars(Recheck(p)) /\ WF_vars(Valve(p))
  /\ \A s \in Sub : /\ WF_vars(LeaseExpire(s)) /\ WF_vars(LifecycleAbort(s)) /\ WF_vars(Pull(s))
                    /\ WF_vars(OrphanGC(s)) /\ WF_vars(IngestA(s)) /\ WF_vars(IngestB(s))
                    /\ WF_vars(IngestC(s)) /\ WF_vars(IngestD(s))
  /\ WF_vars(Up) /\ WF_vars(Reconcile)

Spec == Init /\ [][Next]_vars /\ Fairness

-----------------------------------------------------------------------------
(* Safety (names match a3-ingest-protocol.md, section "Spikes") *)

\* I1: staged/record objects are deleted only after a durable commit (blob +
\*     archived record), a durable rejection, or as a no-record orphan.
I1_NoDeleteBeforeCommit ==
  /\ \A s \in delStg : (s \in arch /\ blob[ItemOf(s)] = "good") \/ s \in rej \/ s \in orphan
  /\ \A s \in delMeta : s \in arch \/ s \in rej

\* I2: "safe" => the device holds a receipt => blob durable + its record archived.
I2_SafeOnlyWithReceipt ==
  \A p \in Hold : phase[p] = "safe" => HasArchived(p) /\ blob[p[2]] = "good"

\* I3: dedup never merges different plaintexts.
I3_NoFalseMerge == \A c \in Item : blob[c] /= "bad"

\* I4: at most one distinct receipt per record.
I4_OneReceiptPerRecord == \A s \in Sub : issued[s] <= 1

\* I6: the Worker's relay is a cache of homelab receipts.
I6_RelayIsCache == relay \subseteq arch

\* I7: the homelab never GCs a staged object whose record later arrives.
I7_NoDanglingRecord == \A s \in orphan : ~meta[s] /\ s \notin inbox

\* Model adequacy (not a protocol property): a live stuck pair never runs
\* out of attempt slots; if violated, raise K before reading liveness.
SlotsSuffice ==
  \A p \in Hold : alive[p[1]] /\ att[p] = K =>
     ~(phase[p] = "idle" \/ (phase[p] = "awaiting" /\ ~HasReceipt(p) /\ Stuck(p)))

-----------------------------------------------------------------------------
(* Liveness *)

\* L1: every live holder eventually reaches "safe".
L1_EventuallySafe == \A p \in Hold : <>(phase[p] = "safe" \/ ~alive[p[1]])

\* L2 (PLAN): every claimed item ends committed or re-claimable (never stuck in flight).
L2_CommittedOrReclaimable == \A c \in Item : <>[](blob[c] = "good" \/ \A d \in Dev : Answer(c, d) = "MISSING")

\* L3 (A3-S2 pass criterion "no orphans after reconciliation"): staging and
\*     multipart drain; every record whose content is home is consumed.
L3_Drains ==
  <>[](/\ \A s \in Sub : stg[s] = "none" /\ ~mp[s]
       /\ \A s \in Sub : meta[s] => blob[ItemOf(s)] /= "good")

\* L4: the Worker's commit marks converge again after rollback.
L4_CacheConverges == \A c \in Item : <>[](blob[c] = "good" => mark[c])
=============================================================================
