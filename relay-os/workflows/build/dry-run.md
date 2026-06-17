---
name: build/dry-run
description: Human-in-the-loop dry run of the relay build onboarding flow across empty / filled / ±CLAUDE.md repos. The agent role-plays `relay build` (not yet built), actually creates the starter tickets in throwaway fixture repos so the human can launch one or two, and the human scores each run against a rubric. Output: findings that feed the relay-build-onboarding-flow design.
steps:
  - name: prepare-fixtures
    assignee: agent
  - name: dry-run-and-score
    assignee: agent
  - name: synthesize
    assignee: agent
---

## prepare-fixtures

Stand up three throwaway fixture repos with the human (they get deleted after
— that's fine). Each must be a real relay repo so the dry run can actually
create and launch tickets in it:

1. **empty** — a fresh dir, `relay init`, nothing else.
2. **filled, no CLAUDE.md** — a dir with real-ish content (a README, some
   source/config — reuse `~/Desktop/admin-*` or a copy of a real repo), then
   `relay init`. Make sure there is NO CLAUDE.md / AGENTS.md.
3. **filled, with CLAUDE.md** — same as #2 plus a representative CLAUDE.md (an
   agent guide describing the repo).

For each, after `relay init`: set `[notification.slack] enabled = false` in
that repo's `relay.local.toml` so `relay create` / `relay launch` work offline
(these fixtures have no Slack webhook), and set `user` so launch doesn't fail
loud on the missing-user gate. Record each fixture's absolute path on the
blackboard under a `## Fixtures` heading. Bump when all three exist and are
init'd.

Do NOT create tickets in this (relay-cli) repo — every ticket in this workflow
is created inside the fixture repos (cd into them), never here.

## dry-run-and-score

For each fixture in turn (empty → filled → filled+CLAUDE.md), role-play
`relay build` end to end. The command does not exist yet — you are its
stand-in for this dry run:

1. Ask the one scripted question: **"What do you want to build?"**
2. Run an agent-led follow-up chat — a few sharp questions you choose from the
   answer. Draw out intent; don't interrogate.
3. Scan the fixture repo (README, source, config, and CLAUDE.md if present).
   On the empty repo the scan finds nothing — that is the point of that leg.
4. Draft a short spec/vision (a few sentences) and show it to the human.
5. **Actually create a starter batch of tickets in that fixture repo** — cd
   into the fixture and use that repo's own `relay` to create them (drafts are
   fine; 3–6 is the target). Make at least one substantive enough that the
   human can `relay launch` it and watch it run.
6. Invite the human to launch one or two of the created tickets to feel it.

Then walk the human through the rubric and record their answers verbatim on the
blackboard under `## Scores — <fixture>`:

- **Intent capture (1–5):** does the spec reflect what they said they want?
- **Operational recall (X / N):** of the real facts in the repo, how many did
  the scan surface? (the `init-questions` measure — answers-only ≈ 7/20, scan
  ≈ 20/20). N/A for the empty repo.
- **Ticket batch quality (count / total):** how many of the created tickets
  would they launch as-is? Did the one(s) they launched feel real?
- **Friction:** roughly how many turns / how much effort to reach launchable
  tickets?
- **Empty-repo check:** for the empty leg, is the starter set useful or hollow?

The human is the judge of efficiency — you present and record, they score. Bump
when all three fixtures have a scorecard on the blackboard.

## synthesize

Read the three scorecards and write a findings section on the blackboard that
answers what the `relay-build-onboarding-flow` design needs:

- Is one scripted question enough to capture intent, or is a second beat needed?
- Is the scan load-bearing on filled repos (does it recover facts the question
  misses)? Confirm or refute the `init-questions` finding for this flow.
- Is the empty-repo batch good enough, or does it need different treatment?
- Recommended batch size, and any concrete fixes to the flow.

These findings are the deliverable — they feed the
`marketing/relay-build-onboarding-flow` design step. Remind the human they can
now delete the fixture repos, then `relay mark done`.
