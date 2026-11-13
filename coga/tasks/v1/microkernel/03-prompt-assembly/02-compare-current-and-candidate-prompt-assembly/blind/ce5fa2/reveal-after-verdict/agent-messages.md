## Rollout 0

I’ll check the checkout guidance, write and verify `result.txt`, then record the evidence and finish the step. I’ll use the local origin for reconciliation.


---

The checkout is clean on `main`, and the ticket is still at `write` with no recorded branch or PR. I’m applying `trial/write` and `trial/report`, along with Coga’s manual checkout procedure.


---

`result.txt` contains exactly `ready` followed by one newline, verified by reading back all 6 bytes. The blackboard records the evidence, and the final fetch found no drift from local `origin/main`. I’ll now bump the task to the owner-held `judge` step.
