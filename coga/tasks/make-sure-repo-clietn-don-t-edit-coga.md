---
slug: make-sure-repo-clietn-don-t-edit-coga
title: make sure repo clietn don't edit coga
status: active
owner: nicktoper
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 1 (design)
---

## Description

When Dream runs in a client repo — one that has Coga installed but is not the
Coga source repo (multiply, magicator) — it treats the installed Coga OS tree as
part of its own corpus and reports findings about Coga infrastructure. Those
findings are noise in the client repo: Phase 6 routes them to proposal PRs
against a repo that does not own the code they describe, and the client's real
backlog gets diluted.

Teach Dream to recognise it is not running in the Coga source repo and to keep
Coga-owned files out of its findings. What it does notice about Coga is not
discarded — it appends to a dedicated upstream file in the client repo, and a
new recurring job in the Coga repo sweeps configured client checkouts, reads
those files, and files real tickets here.

## Context

### Where the current behavior comes from

The Dream scan skills are written from inside the Coga source repo and never
distinguish Coga-owned files from the client's own:

- `src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/scan/scan-protocol/SKILL.md:8-9`
  calls both decide-half scans "read-only sweeps over **Coga's own** corpus".
- `.../scan/contract-audit/SKILL.md:55-74` audits `coga/` against
  `src/coga/resources/templates/coga/` — a pairing that only exists here.
- `.../scan/knowledge-scan/SKILL.md:47-53` defines the corpus as the configured
  contexts dir, `coga/skills/**`, and `coga/workflows/**`, with no notion of
  which tree owns them.

### The exclusion is a subset of `coga/`, not `coga/` itself

This is the trap, and an earlier draft of this ticket got it backwards. In a
client repo `coga/` is *also where the client's own knowledge lives* — `coga
init` seeds it and the client's contexts, skills, workflows, tasks, and log all
sit under it (`example/coga/` shows the shape). Since `knowledge-scan` defines
the corpus as exactly those directories, **excluding `coga/` wholesale would
exclude 100% of Dream's corpus** and Dream would find nothing at all.

What is actually Coga-owned in a client repo is a subset: `coga/contexts/coga/**`
(init installs the OS contexts, including `recurring/SKILL.md`), the shipped
`coga/recurring/<name>/` templates, `coga/.agent-skills/bootstrap/**`, `.coga/`,
and the Coga-authored sections of `CLAUDE.md` / `AGENTS.md`. Drawing that line
precisely is the hard part of this ticket.

### Precedent to generalise from

`knowledge-scan/SKILL.md:55-59` already solves the same shape of problem for
installer-managed skills:

> Installer-managed skills are **outside the corpus**. `coga/skills/` mixes
> repo-authored skills with upstream trees that `coga skill install` and `coga
> skill update` place and refresh wholesale. **The manifest's `ref` list in
> `src/coga/resources/managed-skills.toml` is the whole test.**

A manifest-driven "these paths are not yours" test is the model to extend —
Coga-installed OS files are the same category as installer-managed skills.
Prefer that over the narrower escape hatch at `contract-audit/SKILL.md:76` ("In
a downstream repo with no packaged source tree or explicit pair list, omit this
group"), which only covers the live/packaged twin comparison.

### The pieces of work

1. **Repo identity** — how Dream tells the Coga source repo from a client repo.
   Whatever signal is chosen must be stated once and reused, not re-derived per
   scan. `src/coga/` + `tests/test_packaging.py` is the obvious candidate but is
   also true of a fork or vendored copy; an explicit config marker may be more
   honest. Open for the design step.
2. **Exclusion** — in a client repo, Coga-owned paths (the subset above) leave
   the scan corpus and never reach `## Findings` or Phase 6 routing.
3. **Upstream capture** — Coga-infra observations append to a dedicated file in
   the client repo (proposal: `coga/upstream-coga.md`, append-only, one entry per
   observation carrying repo, date, and evidence path).
4. **Upstream processor** — a new recurring task here under `coga/recurring/`
   sweeps a configured list of client checkouts, reads each upstream file,
   creates Coga tickets for new entries, and watermarks what it processed so
   re-runs do not duplicate.

Direction is deliberately **Coga-repo-pulls**, not client-pushes: a client repo
then needs no credentials for this repo and no knowledge of where it lives. The
cost, accepted: the sweep only works on a machine that has every client checkout,
and the checkout list has to be maintained.

### Recurring-task facts the processor needs

Inlined rather than attaching the 52.6 KiB `coga/recurring` context, which would
have been 82% of this ticket's composed prompt while covering one of four pieces:

- A recurring task is `coga/recurring/<name>/ticket.md` with a cron `schedule:`
  in frontmatter; the directory name must not start with an underscore.
- The reserved sibling `ticket.py` is the deterministic half. `coga launch` runs
  it as `[sys.executable, "<task>/ticket.py"]` with no operands, copied into each
  period task and run headlessly before any agent phase.
- **The recurring task's own blackboard persists across every run and is where
  last-run cursors live** — that is the watermark mechanism, no new state file
  needed.
- Authoring path: create the directory by hand or `coga recurring promote`, then
  `coga validate --json`.
- A template may name any resolvable workflow and attach any resolvable contexts;
  there is no recurring-capable registry to register in.

`coga/recurring/blocker-reminders/` is the closest existing model — a one-step
workflow plus a `ticket.py` that scans, writes watermarks, and syncs through git.
Read it before designing the processor. Attach `coga/recurring` at the implement
step only if the design turns out to need the sweep or control-branch machinery.

### Constraints

- **The config key needs a core change, and that is expected here.**
  `src/coga/config.py:440` defines `_ALLOWED_LOCAL_SECTIONS = frozenset({"user",
  "agents", "notification", "git"})`, and `_reject_unknown_sections` (line 497)
  hard-fails on anything else — an unrecognised top-level key in
  `coga.local.toml` makes *every* coga command exit. So the checkout list is not
  documentation: it needs the section added to that frozenset, a parser, a
  dataclass field, and config tests. Config parsing is shared infra with many
  consumers, so this does not breach the microkernel rule.
- Agents may not edit `coga.toml` or `coga.local.toml`
  (`src/coga/resources/prompt.md:117`). Define the key and its shape, then ask
  the human to fill in the checkout paths. **The ticket cannot be verified
  end-to-end until they do** — treat that as a launch prerequisite, not a
  surprise at implement time.
- The processor's deterministic half goes in its sibling `ticket.py`, not
  `src/coga/`. Adding a recurring job is not by itself a reason to put code in
  core (`CLAUDE.md`, microkernel rule).
- **Packaging twins.** The Dream *scan* skills are bundled batteries with no live
  counterpart under `coga/skills/` — the packaged tree is the only copy, and
  `coga/.agent-skills/` is a generated, gitignored symlink view of it
  (`coga/.gitignore:13`). But `coga/recurring/dream/ticket.md` **is** an enforced
  twin of `src/coga/resources/templates/coga/recurring/dream/ticket.md`, and
  Phase 6 is defined there — editing one copy without the other fails
  `tests/test_packaging.py`. Decide explicitly whether the new upstream-processor
  template ships downstream at all; it only makes sense in this repo, so it
  likely needs to be unpackaged or listed in `INTENTIONALLY_DIVERGENT_TWINS`.
- Keep green: `tests/test_dream_skill_scripts.py`,
  `tests/test_dream_worker_templates.py`, `tests/test_dream_validate_drift.py`,
  `tests/test_packaging.py`, and the config tests.

### Verification

These tests pass today and will keep passing whether or not the change works, so
the design step must define acceptance beyond them. At minimum:

- A Dream run in a client repo produces zero findings naming Coga-owned paths,
  and a non-zero corpus (proving the exclusion did not empty the scan).
- The same run in this repo is unchanged.
- The processor turns a hand-written upstream file into tickets, and a second run
  over the same file creates none.

### Out of scope

- Changing what Dream considers a finding *within* the client's own product.
- Any transport requiring the client repo to reach into this one.
- Retrofitting upstream files for Dream runs that already happened.

### Related

`coga/tasks/dream-shouldn-t-touch-coga-in-coga-enabled-repo.md` is the same idea,
filed empty; canceled in favour of this ticket.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
