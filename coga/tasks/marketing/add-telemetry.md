---
title: Add PostHog phone-home telemetry for V1 product-market-fit signal
status: active
owner: nicktoper
agent: claude
contexts:
- coga/period-task
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
step: 1 (design)
---

## Description

Give Coga a basic product-market-fit signal: how many repos run it, how many
tickets each has, and whether those tickets are moving. Ship it as a
**recurring "phone-home" battery** — `coga/recurring/phone-home/` with a
deterministic `ticket.py` that runs on the operator's `coga recurring`
sweep, aggregates counts from the repo's own `coga/log.md` and
`coga/tasks/`, sends them to a Coga PostHog project, and posts the same
summary to the repo's Slack channel so the operator sees exactly what left
the machine. Telemetry is **on by default and switched off with
`[telemetry] enabled = false`** in `coga.toml` or `coga.local.toml`.

This reverses `coga/principles` #5's telemetry ban. **Owner decision
(nicktoper, 2026-09-20, attended session): change the principle.** V1 needs
to know whether the product works; a small or biased sample is acceptable,
and the "considered and rejected (2026-06)" install-ping note in that
principle is superseded. The design evaluator and implementer treat the
reversal as settled, not as a finding. Amending the principle, README, and
the contexts that own the "no instrumentation" fact is in scope, in the
same PR as the code.

Done means: a fresh `coga init` repo phones home on its first sweep with an
install event and a heartbeat; the owner sees both rows by HogQL query in
the Coga PostHog project (a 200 from capture proves nothing — only the
query does); `[telemetry] enabled = false` provably sends nothing; the
principle, README, and context twins say what the product now does.

## Context

### What to measure (owner, 2026-09-20)

Decided: **installs** (`coga_installed`, once, with coga/OS/Python
versions), **ticket count by status** at run time, and **movement** — bumps
in the period. Carrier: one `coga_heartbeat` per run plus `coga_installed`
on the first run. Per-command CLI instrumentation was rejected: the
recurring shape keeps the network call out of ordinary commands, keeps it
inspectable (one script, one payload), and makes the opt-out verifiable.
The owner is unsure about anything further (launches, marks, blocks, agent
used) — the design may propose more with a one-line reason each and should
expect cuts.

Movement comes from `coga/log.md`, whose transition lines are written by
`logfile.append_log` with each command's own message — `created`,
`activated`, `launched`, `advanced to step N (...)`, `auto-bumped on merge
of PR #N → done`, `completed`, `blocked:`, `unblocked`. No context documents
that verb grammar; the design derives it from the real lines and pins it
with a fixture test.

**Never sent:** slugs, titles, bodies, blackboards, repo name or remote,
paths, branch names, owner/agent names, Slack IDs, log lines. Counts and
version strings only. The design defines the property allowlist and an
exhaustive serialization test that fails on any extra property — that test
is the data boundary.

### Identity and cross-run state — one unit: the repo

`distinct_id` is a **repo id**, minted on the first run and stored with the
log cursor and the "installed sent" flag in the template's blackboard
(`coga/recurring/phone-home/ticket.md` below the fence), declared via the
template's `state_keys:` frontmatter so `coga bump` checks they moved
(`period_state`, per `coga/period-task`). Everything is per-repo and
committed, so clones agree: one `coga init` = one install. (A per-checkout
id in gitignored `.coga/` would disagree with a committed cursor — clone #2
would mint an id but never send `coga_installed` — so it is not used.)
Owner confirmed this unit on 2026-09-20. Consequences the design must handle: the cursor advances on every run, even
a quiet one, or the `state_keys` check raises the important-Slack alert;
and phone-home is the first shipped `ticket.py` to write a template
blackboard (`taskfile.upsert_blackboard`), so each run commits to the
control branch through the ordinary sync path.

### Shape

- Model: the `ticket.py`-backed batteries (`blocker-reminders` is the
  smallest — `runner.run_recipe(load_config(), "blocker-reminders", [])`
  then `python -m coga.cli bump $COGA_TASK_SLUG`). The logic is a fixed
  `runner.RECIPES` entry, where `CLAUDE.md` puts the recurring jobs.
- Files and their packaged twins (`tests/test_packaging.py` derives every
  pair; byte-identity required): `coga/recurring/phone-home/{ticket.md,
  ticket.py}` ↔ `src/coga/resources/templates/coga/recurring/phone-home/`;
  `coga/workflows/phone-home/run.md` (one-step, like
  `blocker-reminders/run.md`) ↔ `.../templates/coga/workflows/phone-home/run.md`.
  Contexts twin under `.../templates/coga/bootstrap/contexts/`; `coga/usage`
  and the `marketing/*` contexts have no twin.
- `coga/recurring` (`coga/contexts/coga/recurring/SKILL.md`) is cited, not
  attached; read §Dropping a new recurring task, §Extend recurring with a
  task-specific workflow, and §Last-run state lives in the recurring task's
  blackboard. Load-bearing facts: the sweep get-or-creates
  `coga/tasks/recurring/phone-home/` per period and runs the sibling
  `ticket.py` with no agent; a new template fires retroactively on its first
  sweep; the sweep is invoked by an operator-owned scheduler outside Coga,
  and the `owner` gate applies only when `coga.toml` sets `owner` (a fresh
  `coga init` ships it commented out). So a repo phones home only when
  someone schedules `coga recurring` — accepted for V1.
- Branch/PR bookkeeping follows the `code/implement` and `code/open-pr`
  skills' `## Dev` contract; `dev/code` is not attached (its §Superseded
  designs rule applies if the design pivots — read it then).
- Schedule: weekly, Monday morning with `branch-sweep` (owner, 2026-09-20:
  this is a PMF signal, not an optimization loop; daily is not wanted).
- Slack receipt goes through the existing `[notification.slack]` channel,
  is skipped when Slack is disabled, and never blocks or fails the send. It
  is a courtesy, not the disclosure: the disclosure is the `coga.toml`
  comment on `[telemetry]` plus README.
- Delivery: one POST per event, bounded timeout of a few seconds (a 10 s
  hang on sinkholed DNS delays the whole sweep), no queue, no retry; a
  failed send is one warning on the period blackboard, never a failed task.

### Config

`[telemetry] enabled = true` by default, resolved like `[git].enabled`
(`config._resolve_git_enabled`: shared then local, local wins) **and added
to `load_config`'s fixed top-level schema**, or every command fails on the
unknown table (`coga/architecture` §Config loading fails loud on unknown
keys). `enabled = false` short-circuits before identity minting, network,
and Slack. No other configuration surface.

### PostHog side — copy multiply, new project

Multiply (`~/Code/multiply`) settled the operational pattern; copy it:
`infra/posthog/README.md` §Settings that must stay true, §Keys, §CLI,
§Deleting a person; payload shape and the allowlist/serialization-test
pattern per `coga/tasks/v1/telemetry/posthog/3-client.md`; key-as-constant
rationale per `.../4-embed-the-capture-key-as-a-constant.md` (a `phc_` key
is write-only and designed to ship in client code; a leak means event spam,
fixed by rotation — which here means a release, since the key is in git
history). Create a **new project for Coga** in the same organization — never
send to multiply's `606347`.

Owner prerequisites, done at `review-design` (the gate the owner already
sits at): create the project with *Discard client IP data* on and GeoIP
off, put the capture key in the 1Password `coga` vault, record the project
id on the blackboard. `implement` reads the key from the vault into the
constant and does not start without it.

The test seam must be broad enough that `tests/`, `example/coga/`, and any
CI or dev checkout of this repo never reach the real project; name the
gating explicitly. Acceptance is manual: the PR body carries the
`posthog-cli api` HogQL query text, and the owner runs it at `review` with
the CLI credential at `~/.posthog/credentials.json`.

### Documents that change in the same PR

Owners of the fact (must): `coga/contexts/coga/principles/SKILL.md` #5
(the "No phoning home" sentence, the "network call you didn't initiate"
receipt, and the 2026-06 rejection note — keep it, add the dated
reversal) and its bootstrap twin; `coga/contexts/coga/architecture/SKILL.md`
("Coga creates no hosted account or telemetry identity"; `[telemetry]` next
to the other config keys) and its twin; `coga/contexts/coga/usage/SKILL.md`
(three mentions of the ban: description line and two body cross-refs);
`README.md` §Values; `docs/operations.md` (the switch beside the other
opt-outs). A short runbook — `docs/telemetry.md` or a
`coga/contexts/coga/telemetry/` context; the design picks per
`coga/architecture` §Where a fact lives.

Nice to have, not blocking: one-line updates to
`coga/contexts/marketing/distribution/SKILL.md`,
`coga/contexts/marketing/map/SKILL.md`, and
`coga/tasks/marketing/build-the-launch-plan.md`, which point at this ticket
as an empty concept.

### Out of scope

Per-command instrumentation; session/token usage; consent prompts or a
first-run dialog (V1 is disclosure + switch); dashboards beyond one saved
insight per measured quantity; retention/deletion tooling (document
multiply's persons-API procedure, do not build it).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
