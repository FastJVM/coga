# Legacy migration evidence

`phone-home-old.py` is the unmodified PR 880 source:
`ac14d63fc:coga/recurring/phone-home/ticket.py`, Git blob
`ad652767501e33d50e531c17ccc0cc44bdfbb853`. It is an archived test baseline,
not a shipped implementation or fallback.

`dream-old.md` contains the actual Phase 1/5 command paragraphs from the
pre-migration Dream template, which named the removed `coga run
validate-drift` and `coga run cleanup-orphan-markers` recipes. The tests
reconcile it with the old, new and fork passages shipped in
`coga/edge-code/edge-code-upgrades.md`, then run the reconciled commands
against an installed wheel and a full local Dream fork.
