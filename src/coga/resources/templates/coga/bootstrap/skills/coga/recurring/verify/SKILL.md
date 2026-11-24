---
name: coga/recurring/verify
description: Fire a Coga recurring job for real inside a disposable clone — local bare remote, local Slack catcher, no vault, no internet — so a change to a template, its `ticket.py`, or the recurring wiring can be exercised before it merges. Covers building the sandbox, firing, what to check afterwards, the probes worth running, and what a sandbox firing does not prove.
---

# Verify a recurring template

Verify from the checkout containing the intended template. Inspect the
local-first template selection, its workflow and required secrets. Use the
repo's supported test environment for real effects. `coga recurring list`
shows the templates and current periods. An on-demand
`coga recurring launch <name>` runs the job and records local state. Use a
separate working copy for a verification run when the real ledger or output
must remain untouched.

Inspect the period ticket and run record for the actual executor and
outcome. Stop on an error and preserve the relevant state and evidence.
