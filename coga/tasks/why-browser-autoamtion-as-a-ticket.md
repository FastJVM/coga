---
slug: why-browser-autoamtion-as-a-ticket
title: why browser autoamtion as a ticket
status: done
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

## Investigation

- Current behavior is direct, not inferred: `copy_fresh_templates()` copies the
  packaged tree except `bootstrap/`; `_do_init()` then calls
  `_prune_onboarding_tickets()` only for a filled repo, and that function's
  allowlist contains only `coga-build`. The browser ticket therefore survives
  both empty- and filled-repo init. Existing tests explicitly assert this.
- The history records conflicting deliberate choices, rather than a simple
  forgotten prune-list update. Commit `b58b242b` (2026-05-29) added the browser
  workflow, contexts, skills, and ticket together so they would "ship as
  framework defaults." Commit `d73e3978` (2026-06-10) then deleted the live
  dogfood ticket as a "speculative launcher; methodology lives in browser/
  workflows, contexts, and skills," but left the packaged template behind.
  Commit `e455b4c3` (2026-06-18) later introduced the empty/filled onboarding
  gate, changed the packaged browser ticket's owner from `zach` to the
  stampable `new-user`, and added tests saying the browser draft "ships on
  every repo (not gated)." The near-empty task-list premise was therefore not
  an invariant at that time, even though the earlier live-ticket deletion had
  already articulated the cleaner primitive boundary.
- The historical intent does not make the present representation a good fit.
  The file describes a reusable entry point, not work the installing user
  chose. Init nevertheless materializes it as a real `draft`, attributes it to
  that user, and exposes it in normal task status. The packaged `coga/log.md`
  also carries its original `2026-05-28 ... [human:zach] created` audit line,
  making the new repo look as though it inherited someone else's work history.
- Removing only this seeded ticket does not remove the browser battery:
  `browser/build-automation`, the `browser/*` contexts, and the package-backed
  `browser/playwright` skill resolve independently of the task file.

## Recommendation

**Remove `src/coga/resources/templates/coga/tasks/browser-automation.md` from
the init payload; do not merely add it to the filled-repo prune list.** Keep the
browser workflow, contexts, and Playwright skill available as the reusable
battery. If a browser demo is useful, put a *concrete example task* under
`example/coga/tasks/` rather than moving this generic launcher unchanged. A
short docs/orientation pointer can preserve discovery without manufacturing
work in every user's task list.

Why: a ticket should assert real, chosen work. This file instead advertises a
capability and waits for the user to supply the actual task. Materializing it
as a normal draft, stamping the installer as its owner, and carrying the
original author's audit line blur that boundary. The June 10 live-copy
deletion already captured the right separation: methodology belongs in the
browser battery; a concrete automation gets its own ticket when requested.

### Options weighed

1. **Remove from shipped tasks; use `example/` for a concrete demo
   (recommended).** Keeps every installed task list truthful and leaves all
   browser capability available. Cost: lower zero-click discoverability;
   mitigate with a small docs/orientation mention if that proves important.
2. **Add it to `_ONBOARDING_TICKET_DIRS`.** Minimal code change and cleans
   filled repos, but leaves an unsolicited feature draft in every empty repo
   and misclassifies a browser launcher as onboarding. It preserves the
   semantic problem behind another filename exception.
3. **Leave it as-is.** Best immediate discoverability and faithful to the
   explicit June 18 test contract. Cost: status/audit pollution and a generic
   capability masquerading as user-owned work; not worth it.
4. **Make the whole browser battery opt-in.** Cleans the surface but removes
   useful reusable capability and adds installation/configuration machinery.
   This is broader than the problem and conflicts with the small-surface
   posture.

A package-backed stateless bootstrap launcher is a possible future UX, but it
is not a simple destination move: bootstrap launches are single-shot while
the current router spans a four-step workflow. Do not fold that redesign into
the cleanup follow-up.

### Follow-up scope if accepted

- Delete the packaged browser task; the live `coga/tasks/` copy is already
  absent, so this restores rather than breaks live/template consistency.
- Remove the stale browser-automation line from the packaged `coga/log.md`.
- Replace init tests that assert universal browser-ticket seeding with
  assertions that empty and filled installs contain no browser draft.
- Optionally add a concrete browser example plus one discoverability pointer.
- Leave the browser workflow, contexts, and skill untouched.

No code change is part of this decision ticket.

## Decision

Nick accepted removal of the seeded `browser-automation` task and directed the
follow-up to preserve the entry point as a skill with user-facing documentation.
The implementation should:

- delete `src/coga/resources/templates/coga/tasks/browser-automation.md` and
  its stale packaged `coga/log.md` audit entry;
- move the router methodology currently encoded in
  `browser/build-automation` into a bundled `browser/build-automation` skill,
  keeping `browser/playwright` as the separate lower-level execution skill;
- expose that skill through a stateless package-backed bootstrap launcher so
  invoking browser-automation setup does not create a standing task merely by
  installing Coga;
- document the launcher and the distinction between the orchestration skill
  and Playwright runner in the user-facing docs;
- update init/bootstrap/compose tests while leaving the browser contexts and
  runtime capability available.

This removes the remaining product judgment from the implementation. Create
the follow-up with an agent-owned workflow so it can run without another
destination decision from Nick.

## Report

Produced the recommendation and recorded Nick's decision inline above. The
implementation follow-up landed at
`coga/tasks/move-browser-automation-entry-point-out-of-seeded.md` with
`code/with-review`, step 1 `implement`, assigned to `codex`.

The follow-up is scoped to delete the seeded packaged task and stale packaged
log entry, preserve the browser automation entry point as a
`browser/build-automation` skill plus stateless package-backed launcher,
document the user-facing path, and update tests while leaving the browser
runtime capability available.
