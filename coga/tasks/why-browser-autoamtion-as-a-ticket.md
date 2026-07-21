---
slug: why-browser-autoamtion-as-a-ticket
title: why browser autoamtion as a ticket
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow:
  name: autonomy/assist-only
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: human
  - name: report-to-coga
    skills: []
    assignee: agent
secrets: null
script: null
step: 2 (human-owns-and-finishes)
---

## Description

Investigate why a `browser-automation` ticket ships into every fresh Coga
install's task list, decide whether that's the right place, and recommend
where it should actually live. Produce a short written recommendation with the
options laid out and a clear recommended option; the human makes the final
call on the destination. This ticket ends at the recommendation + decision —
if a code change is warranted, it becomes a follow-up.

## Context

A fresh `coga init` copies the whole `src/coga/resources/templates/coga/` tree
into the target repo. Two tickets are seeded into `tasks/` this way:

- `coga-build` — the onboarding/bootstrap interview ticket. On a *filled* repo
  this is pruned by `_prune_onboarding_tickets` (see
  `src/coga/commands/init.py:185`, `_ONBOARDING_TICKET_DIRS`), on the reasoning
  that "a real project doesn't want the bootstrap interview seeded for it."
- `browser-automation`
  (`src/coga/resources/templates/coga/tasks/browser-automation.md`) — a
  plug-and-play "turn a described browser task into a Playwright automation"
  entry point, wired to the `browser/build-automation` workflow and the
  `browser/api-first` context (its frontmatter `skills:` is `[]`; the
  `browser/playwright` skill is referenced only in the ticket prose, reached
  via the workflow, not wired on the ticket).

The asymmetry to investigate: `browser-automation` is **not** in the prune
list, so unlike `coga-build` it lands in every init'd repo (including filled
real projects) as a live `draft` ticket and stays. It reads as a feature demo
seeded into the user's own task list — arguably the wrong place. A new
install's task list should probably be near-empty, not pre-loaded with a
browser-automation feature ticket.

Before inferring the asymmetry is an oversight, check intent: `git log` /
`git blame` both `browser-automation.md` and the `_ONBOARDING_TICKET_DIRS`
prune list to see who added them and whether the difference was deliberate.
The "near-empty task list is the intended new-install state" premise is itself
an assumption — resolve it from history, not by inference.

Options to weigh (destination decided during the ticket, not pre-committed):
add it to the init prune list; move it to `example/coga/` as a demo fixture;
make the whole browser battery opt-in; or **leave it as-is with a
justification** — this last one is a genuinely acceptable outcome, not a
strawman, if history shows the seeding is intentional. The browser
workflow/skills/contexts themselves are batteries and are not in scope — this
is only about the seeded *ticket*. Confirm the actual install behavior by
reading `init.py` rather than assuming; the browser battery (workflow,
`browser/*` contexts, `browser/playwright` skill) should stay available even
if the seeded ticket moves or is pruned.

Follow-up note for whoever implements any move/prune: the destination change
touches the *packaged* template
(`src/coga/resources/templates/coga/tasks/browser-automation.md`), which is
what init copies; per CLAUDE.md the live `coga/tasks/` copy must stay in sync,
so a follow-up must not edit only one copy.

<!-- coga:blackboard -->

## Findings (from init.py + git history)

**Install behavior, confirmed in `src/coga/commands/init.py`:** the template
ships exactly two tickets (`browser-automation.md`, `coga-build.md`). On a
*filled* repo (or any nested init), `_prune_onboarding_tickets` removes only
`coga-build` (`_ONBOARDING_TICKET_DIRS = ("coga-build",)`, init.py:185), then
`_stamp_user_into_delivered_tickets` stamps the new user as owner/human of
whatever remains. Net effect: every real project that runs `coga init` gets a
draft "Browser automation" ticket owned by a user who never created it —
right after init prints "Skipped the onboarding ticket … create tasks with
`coga ticket` when you're ready."

**History — the seeding was incidental, not designed:**

- `b58b242b` (2026-05-29, zach): ported the browser artifacts wholesale from
  the separate browser-automation repo "as framework defaults" — workflow,
  contexts, skills, *and* the task dir, including a template `log.md` line
  attributing the ticket's creation to zach. The commit frames it as bundling
  validated artifacts; nothing presents the seeded ticket as an onboarding
  design choice.
- `e455b4c3` (#391, 2026-06-18, zach): introduced the empty/filled gate and
  the prune list. Its stated rationale is narrowly about the interview ("a
  real project doesn't want the bootstrap interview seeded for it"). The same
  PR *did* touch `browser-automation.md` — but only mechanically, to swap the
  hardcoded `zach` owner for the `new-user` placeholder. No recorded decision
  that browser-automation should survive into filled repos; it just wasn't
  the PR's subject.
- Later touches (`245d9d9a`, `d0645a19`, `83c2dacf`, `c6580174`) are format
  migrations and the rebrand — all mechanical.

**Corroborating signals it doesn't belong in `tasks/`:**

- Nothing anywhere advertises it: `docs/vision.md` never mentions browser;
  neither the `coga-build` onboarding ticket nor README/agent guides point at
  it. Its "plug-and-play entry point" value is undiscoverable — a user meets
  it only as an unexplained draft in `coga status`.
- The coga repo's own live `coga/tasks/` doesn't carry it — the team's
  revealed preference.
- The template `log.md` still ships the stale
  `2026-05-28 … [browser-automation] [human:zach] created` line into every
  new install — further evidence the task-dir port was never re-examined as
  a seeding decision.

So the "near-empty task list is the intended new-install state" premise
checks out for filled repos (that's exactly what #391's gate and init's own
messaging express); browser-automation simply predates the gate and was never
reconsidered against it.

## Options

1. **Add `browser-automation` to the prune list** — minimal diff; filled
   repos get an empty task list, empty repos keep the demo. Downsides: the
   list is documented as *onboarding* tickets (rationale doesn't transfer),
   and empty-repo users still get an unexplained draft sitting next to
   `coga-build`, whose interview already generates the starter tickets that
   fit *their* project.
2. **Stop seeding it entirely; keep it as a demo fixture in
   `example/coga/tasks/` (recommended)** — no install ever gets an unasked
   ticket; the ticket survives as a legible example of a workflow-wired
   ticket (example/ currently has only `auto/`) and as test-fixture coverage.
   The battery (workflow, `browser/*` contexts, `browser/playwright` skill)
   still ships, so `coga ticket "automate X in the browser"` reaches the same
   flow. Downside: loses the zero-setup launch path — but that path is
   unadvertised today, so nothing discoverable is lost; a README/agent-guide
   line about the browser battery can replace it (follow-up).
3. **Make the whole browser battery opt-in** — out of scope per the ticket;
   also unnecessary, since the batteries are inert until referenced.
4. **Leave as-is with justification** — defensible only if history showed
   deliberate seeding; it shows the opposite (wholesale port, prune gate
   authored later with a rationale that never considered it).

## Recommendation

**Option 2.** Remove `browser-automation.md` from
`src/coga/resources/templates/coga/tasks/` and land it in
`example/coga/tasks/` as a demo/fixture. Rationale: the seeding is an
artifact of the May port, contradicted by the June prune gate's intent, by
init's own "create tasks when you're ready" messaging, and by the team's own
task list. If a lighter touch is preferred, option 1 is the acceptable
fallback — but it keeps the incoherence for empty repos and stretches the
prune list's meaning.

**Follow-up items if option 2 (or 1) is chosen:**

- Edit the *packaged* template (`src/coga/resources/templates/coga/tasks/`);
  live `coga/tasks/` already lacks the ticket, so no sync edit needed there.
- Drop the stale `[browser-automation] [human:zach] created` line from
  `src/coga/resources/templates/coga/log.md` in the same change.
- Consider one line in the agent guide / README pointing at the
  `browser/build-automation` workflow so the battery stays discoverable.
- Check `update.py` (`init --update`) for whether existing installs should
  have the untouched draft ticket migrated out, or left alone (suggest:
  leave alone — it's user-owned state after stamping).

**Weak spots / assumptions:** intent is inferred from commit messages and
diffs — zach may have deliberately wanted the demo seeded and just not
written it down; worth a one-line confirm before the follow-up lands. "Team's
own repo lacks it" may reflect ordinary task-list cleanup rather than a
placement judgment.
