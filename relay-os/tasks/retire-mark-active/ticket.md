---
title: Retire relay mark active before launch
status: in_progress
mode: interactive
owner: zach
human: zach
agent: claude
assignee: codex
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 2 (peer-review)
---

## Description

`relay launch` already activates a ticket inline (`_auto_activate`) — launching
*is* the readiness signal — so the old "run `relay mark active` first" step is
already redundant in behavior. The runtime change has shipped; what remains is
documentation/template cleanup so we stop *teaching* the retired step.

Scope (decided 2026-06-16, interactive with zach):

- **Scrub the "activate before launch" guidance** from help text, agent guides,
  docs, and contexts so nothing tells a human or agent to run `relay mark
  active` as a prerequisite to launching.
- **Keep the `relay mark active` command** as a thin convenience. It still has
  legitimate uses (activating without launching) and is the named remedy in
  validate/error paths. Do **not** delete the `active` subcommand — only remove
  the *prerequisite-to-launch* framing.

## Context

- The behavior is already done: `relay launch` brings a draft/paused/done
  ticket to `active` via `_auto_activate` (`src/relay/commands/launch.py:226`,
  `:536`). The `relay mark active` command lives in
  `src/relay/commands/mark.py` and stays.
- **Out of scope:** workflow-less drafts (`workflow: null`) still can't be
  activated by launch ("no workflow, nothing to activate"). That is left as-is
  — a draft with no steps legitimately has nothing to run. Don't expand launch
  to handle it here.
- Distinction to hold throughout: **drop "activate before launch" framing,
  keep factual command mentions.** Lines that just document what `mark active`
  does (the command cheat-sheet, the workflow-less-refusal note, the "same
  remedy" error text) stay; lines that sequence it as a step you do *before*
  `relay launch` get reworded or removed.
- Touch points to scrub (verified 2026-06-16 — start here, but grep the repo
  for `mark active` to confirm completeness):
  - `README.md` — **highest-priority, most user-facing.** Has the prerequisite
    framing in several spots: the normal-path snippet (~line 164,
    `mark active` then `launch`), the boot-sequence step (~line 263), and
    ~line 411 ("launch … runs the `relay mark active` step for you"). Note
    ~line 274 (command cheat-sheet), ~279 (workflow-less refusal), and ~414
    (the "same remedy" error text) are factual mentions to **keep**.
  - `src/relay/commands/init.py:102` — `AGENT_GUIDE_TEMPLATE` lists
    `relay mark active <slug> — activate a draft before launch`. Reword so it
    no longer frames activation as a pre-launch step. This template is
    single-source (no packaged duplicate), so editing it here is sufficient.
  - `relay-os/contexts/relay/current-direction/SKILL.md:217` — shows the
    `mark active → launch` sequence as the flow.
  - `relay-os/contexts/relay/architecture/SKILL.md` and `.../sync/SKILL.md` —
    several references describing `mark active` as the activation path.
  - `relay-os/contexts/relay/roadmap/SKILL.md:145` — the
    `implicit-activation-inrpogress` roadmap entry literally tracks this work;
    update/close it rather than just scrubbing the phrase.
  - `docs/relay-vs-paperclip.md:70` — a table cell lists `mark active` as a
    human gate; factual, likely **keep** — judgment call.
  - Sync note: these `relay/` contexts are **not** duplicated under
    `src/relay/resources/templates/relay-os/` (only `_template`/`autonomy`/
    `browser` ship there), so the usual "sync both copies" rule does not apply
    to the files above. The one packaged file that mentions `mark active` is
    `src/relay/resources/templates/relay-os/relay.toml` — check whether it
    needs the same treatment.
- Surfaced while prototyping `relay build` (2026-06-16): the onboarding batch
  hands the human a bare `relay launch <slug>` with no mark-active step — see
  `marketing/relay-build-onboarding-flow`. That flow is already correct; this
  ticket makes the docs match it.
