# Blackboard — relay-build-onboarding-flow (design step)

## Scope map (what this ticket owns vs. companions)

THIS ticket = the onboarding **flow content**:
- The new `build/onboarding` workflow (replaces `init/setup`) — the step prose
  the agent follows: ask → agent-led chat → spec (in-chat sign-off) → generate
  flat ticket batch. **Scan removed.**
- The delivered onboarding ticket template body (`relay-setup`→`relay-build`):
  Description/Context + workflow snapshot shape.
- Both the live (`relay-os/...`) and packaged
  (`src/relay/resources/templates/relay-os/...`) copies.

Companions (NOT this ticket):
- `relay-build-command` — `relay build` command (rename `setup.py`→`build.py`),
  CLI registration, init next-steps text, AND the file *renames* of the
  workflow + ticket template. Carries the latent launch() arg-count bug fix.
- `relay-init-captures-name` — name prompt in `relay init` + stamping name into
  delivered ticket (kills `new-user` placeholder); likely the empty/filled gate
  + seeding too.
- `relay-ticket-creates` (nick) — the `relay ticket` creation primitive the
  generate step rides. Still in design.

## Current-state findings (investigated 2026-06-17)

- Old flow = `relay-os/workflows/init/setup.md`: 5 steps — interview /
  scan-and-generate / resolve-open-questions / review-and-sign-off /
  apply-review. Aims at durable relay-os artifacts (contexts, rules, recurring),
  NOT a launchable ticket batch.
- Delivered ticket = packaged `tasks/relay-setup/ticket.md`, `status: active`,
  `owner/human: new-user` (placeholder), `workflow: init/setup`.
- `relay-os/workflows/build/dry-run.md` is the **validation harness** (role-plays
  the flow in fixtures), NOT the real flow. Its findings feed this design.
- `relay init` today seeds NO ticket — just prints next-steps pointing at
  `relay setup`. No empty/filled gate exists yet.
- `relay setup` (`commands/setup.py`) = init-if-needed + name-capture + launch
  `relay-setup`. Tested in `tests/test_setup.py` (those tests belong to the
  command rename ticket, not this one).
- No test or `relay validate` rule hard-asserts the *content* of the workflow /
  ticket template, so this ticket's content design has light test coupling.
- Generate step "rides `relay ticket`" but that primitive is still being
  designed by nick → dependency to flag, not resolve here.

## Open Questions (for review-design / present human)

1. **Workflow shape.** RESOLVED (zach, 2026-06-17): **2 steps.**
   - Step 1 `gather-and-spec` (agent, interactive): ask scripted question →
     agent-led chat (≤2 shape-defining follow-ups) → draft spec → in-chat
     sign-off → bump.
   - Step 2 `generate-batch` (agent): read the signed-off spec, create the flat
     draft-ticket batch, end in-chat with launch handoff → `relay mark done`.
   Rationale: each agent step is a fresh session (no carryover); the only clean
   session boundary is after the signed-off spec exists as a durable artifact —
   chat and spec can't be split because the spec is drafted from the live chat.
2. **Where the spec/vision doc persists.** RESOLVED (zach, 2026-06-17):
   **a short vision context** at `relay-os/contexts/product/vision/SKILL.md` in
   the user's repo — a few sentences (what / who / success + v1 scope shape),
   framed as a *living starter doc* the owner edits as the project evolves.
   Generated tickets reference it via `contexts: [product/vision]`. The raw
   intake/working notes stay transient on the blackboard; detail/decisions go to
   tickets. Key distinction that settled it: the durable artifact is the
   *distilled vision*, NOT the raw intake transcript — the batch alone gives
   future agents no project-level orientation, and a context is the right home
   for slow-drifting "what is this project" knowledge. Staleness contained by
   keeping it high-level (decisions → "decide/evaluate X" tickets).
3. **File ownership vs. command ticket's rename.** OPEN — for review-design.
   Recommend framing this
   ticket as "own the content wherever the files live" — edit whichever path
   exists (`init/setup`+`relay-setup` if command ticket hasn't landed, else the
   `build/onboarding`+`relay-build` names). Keeps the split clean and
   ordering-robust. Flag for review-design to confirm.
