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

`blocker-reminders-old-{705,827}.py` and `skill-update-old-{705,827}.py` are
the two stock shim generations shipped while those jobs were registered
recipes, byte-for-byte from
`src/coga/resources/templates/coga/recurring/<name>/ticket.py`: PR 705
(`df1d06022`, direct import of the core module; blobs `6f84c3843db5` and
`039a1d5c9dee`) and PR 827 (`368ae080b`, `runner.run_recipe` plus the shim's
own bump; blobs `035f27cb0bcf` and `4cdc77598139`). They are archived
baselines for the shim adoption test, not shipped code.

`autoclose-old-{705,827,898}.py` are the three stock shim generations shipped
while autoclose was a registered recipe, byte-for-byte from
`src/coga/resources/templates/coga/recurring/autoclose-merged/ticket.py`:
PR 705 (`df1d06022`, direct import of `coga.autoclose`; blob `0e81e8875f82`),
PR 827 (`368ae080b`, `runner.run_recipe` plus the shim's own bump; blob
`e3e207bdc2de`) and PR 898 (`9a7e0dd9a`, which also ran the repository-wide
`branch-sweep` recipe before the bump; blob `185e30482e53`). They are archived
baselines for the shim adoption test, not shipped code.
