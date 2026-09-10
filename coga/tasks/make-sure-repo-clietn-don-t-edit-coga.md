---
slug: make-sure-repo-clietn-don-t-edit-coga
title: make sure repo clietn don't edit coga
status: draft
owner: nicktoper
human: nick
agent: claude
assignee: claude
contexts:
  - coga/recurring
skills: []
workflow: code/with-review
secrets: null
---

## Description

When Dream runs in a client repo — one that has Coga installed but is not the
Coga source repo (multiply, magicator) — it scans the Coga OS tree alongside
the client's own product and reports findings about Coga infrastructure. Those
findings are noise in the client repo: Phase 6 routes them to proposal PRs
against a repo that does not own the code they describe, and the client's real
backlog gets diluted.

Teach Dream to recognise that it is not running in the Coga source repo and to
keep Coga infra out of its findings. Anything it does notice about Coga is not
discarded — it is written to a dedicated upstream file in the client repo, and
a new recurring job in the Coga repo sweeps configured client checkouts, reads
those files, and files real tickets here.

## Context

### Where the current behavior comes from

The Dream scan skills are written from inside the Coga source repo and never
define the corpus as "the client's product":

- `src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/scan/scan-protocol/SKILL.md:9`
  calls both decide-half scans "read-only sweeps over **Coga's own** corpus".
- `.../scan/contract-audit/SKILL.md` audits `coga/` against
  `src/coga/resources/templates/coga/` — a pairing that only exists here.
- `.../scan/knowledge-scan/SKILL.md` partitions "every ticket and knowledge
  file" with no notion of which tree owns them.

One narrow escape hatch already exists at `contract-audit/SKILL.md:63` ("In a
downstream repo with no packaged source tree or explicit pair list, omit this
group"). It only covers the live/packaged twin comparison — generalise from it
rather than inventing a second mechanism.

### The three pieces of work

1. **Repo identity.** Decide how Dream tells the Coga source repo from a client
   repo. Presence of `src/coga/` plus `tests/test_packaging.py` is the obvious
   signal; whatever is chosen must be stated once and reused by all three
   pieces, not re-derived per scan.
2. **Exclusion.** In a client repo, the Coga OS tree (`coga/`, `.coga/`, and the
   installed package) is out of the scan corpus and out of `## Findings`. It
   must not reach Phase 6 routing.
3. **Upstream capture + processor.** Coga-infra observations go to a dedicated
   file in the client repo (proposal: `coga/upstream-coga.md`, append-only, one
   entry per observation with repo, date, and evidence path). A new recurring
   task in *this* repo under `coga/recurring/` sweeps a configured list of
   client repo checkouts, reads each upstream file, creates Coga tickets for
   new entries, and watermarks what it has already processed so re-runs do not
   duplicate.

The sweep list is machine-specific, so it belongs in `coga.local.toml`, not
`coga.toml`. Note that the base prompt forbids agents from editing either file
— the implementer must define the key and ask the human to fill it in.

### Constraints

- The deterministic half of the new recurring task goes in its exact sibling
  `ticket.py`, not in `src/coga/`. Adding a recurring job is not a reason to
  put code in core. See the microkernel rule in `CLAUDE.md`.
- The Dream skills are bundled batteries with **no live counterpart** under
  `coga/skills/`: the packaged tree is the only copy, and `coga/.agent-skills/`
  is a generated, gitignored symlink view of it. Edit the packaged path; there
  is no twin to keep in sync, so `tests/test_packaging.py` pairs nothing here.
  That does not hold for anything else this ticket touches — a new file added
  under `coga/` that also ships as a template does become an enforced pair.
- Existing Dream tests to keep green: `tests/test_dream_skill_scripts.py`,
  `tests/test_dream_worker_templates.py`, `tests/test_dream_validate_drift.py`.

### Out of scope

- Changing what Dream considers a finding *within* the client's own product.
- Any transport that requires the client repo to reach into this one — the
  direction is Coga-repo-pulls, decided deliberately over client-pushes.
- Retrofitting upstream files for Dream runs that already happened.

### Related

`coga/tasks/dream-shouldn-t-touch-coga-in-coga-enabled-repo.md` is the same
idea, filed empty; it is being canceled in favour of this ticket.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
