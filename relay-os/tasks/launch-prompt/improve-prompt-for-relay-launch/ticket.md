---
title: improve prompt for relay launch
status: active
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/architecture
- relay/principles
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
step: 1 (implement)
---

## Description

Trim and restructure the Relay launch base prompt so it is shorter and less
repetitive without losing any load-bearing rule. The base prompt
(`prompt.md`) is inlined into every composed launch by `compose.py`, so its
length is a compounding token cost paid on every run. This is a mechanical /
structural cleanup with high-confidence wins; the broader editorial/voice pass
is a separate sibling ticket
(`review-and-edit-the-relay-launch-prompt-editorial`, owned by nick), in the
same `launch-prompt/` task directory.

Concrete changes:

1. **Dedupe repeated rules.** The bump / don't-go-backward /
   don't-set-status-done / don't-relay-launch-from-inside rules each appear
   3–4× ("Finishing a step" prose, its bulleted Rules, and "What you don't
   do"). State each once, authoritatively; shrink "What you don't do" to only
   items not covered elsewhere.
2. **Move agent-can't-act-on reference out of the base prompt.** Supervisor
   respawn/teardown semantics and human-only `bump --to` / `--backward`
   mechanics are reference an agent can't act on. Relocate to a context (likely
   `relay-os/contexts/relay/architecture`, which already covers prompt
   composition and the launch planes) rather than paying for it every launch.
   Confirm the destination is actually loaded on the launches where the
   reference matters — otherwise the relocation just hides the rule.
3. **Lead with the core loop.** Surface the load-bearing instruction (read
   blackboard → do work → run `bump` LAST then stop; never stop silently; if
   blocked, `panic`) up top; demote the rest to reference.
4. **Tighten the mode overlays to deltas only.** Keep interactive's genuinely
   new content (present human always gets a real response; don't go mute on
   `done`); drop re-statements of the base ("still write to blackboard",
   "exit cleanly").

Done = the trimmed prompt preserves every behavioral rule and the PR records a
before/after token measurement.

## Context

- The launch prompt is assembled by `src/relay/compose.py`
  (`compose_prompt_report`), in order: header → base prompt (`prompt.md`) →
  mode overlay (`prompt-interactive.md` / `prompt-auto.md`) → global rules →
  repo context → contexts → inline `## Context` → skill → workflow-inline →
  `## Description`. Only the base prompt and the two mode overlays are in
  scope here.
- The prompt files have a **single canonical home**:
  `src/relay/resources/prompt.md`, `prompt-interactive.md`, and
  `prompt-auto.md`, loaded via `_resource()` in `compose.py`. There is no
  `templates/relay-os/prompt*.md` and no live `relay-os/` copy — CLAUDE.md's
  "keep both copies in sync" rule is about shipped contexts/templates, not
  these prompts. Edit the resources copy only; do not hand-edit the vendored
  `relay-os/.relay/` snapshot (a build artifact).
- This prompt is the **behavioral contract** for every launched agent — per
  CLAUDE.md, behavior changes must keep the matching `relay-os/contexts/relay/`
  contexts (e.g. `architecture`, `principles`) accurate. Don't drop a rule to
  save tokens; relocate it.
- `compose_prompt_report` exposes per-layer byte/token sizes — use it to
  produce the before/after measurement for the PR description.
- Verification: `python -m pytest` and `relay validate --json`. Note
  `tests/test_compose.py` has assertions on exact prompt text (e.g. it checks a
  specific phrase is *absent* from the prompt) — a green run does not by itself
  prove rules were preserved, so re-read the prompt-text assertions there and
  diff old-vs-new rule coverage by hand, don't rely on pytest alone.
