## Rollout 0

I’ll check the checkout procedure, write and verify `result.txt`, then record the evidence, reconcile with the local origin, and advance one step. I’ll keep the changes limited to this trial task.


---

I’m using the supplied `trial/write` and `trial/report` skills. The checkout is clean on `main`, and the ticket is at `write`. I found Coga’s checkout instructions in the installed package and will read them before editing.


---

`result.txt` contains exactly `ready` followed by one newline; the read-back check passed. I recorded the path and content in the blackboard. I’ll check for upstream changes once more, then run `coga bump` and stop.
