## Rollout 0

I’ll inspect `result.txt` and the checkout state, then record the finding on the blackboard. I won’t advance the owner’s judge step.

---

`result.txt` is exactly `ready\n` (six bytes), so it passes. I’m applying `trial/report` to record that evidence on the blackboard; the task will remain at the owner’s judge step.

---

Pass: `coga/tasks/owner-assist/result.txt` contains exactly `ready` followed by one newline (`ready\n`, six bytes).

Recorded the evidence in the blackboard. The task remains at `judge`; no advancement performed.

---

I’ll recheck the result and report the review without advancing the workflow.

---

Review passed: `result.txt` contains exactly `ready` followed by one newline (six bytes). No issues found. The workflow remains at `judge`; no advancement performed.

---

The owner step remains at `judge`, with no workflow advancement.