# Blackboard — readme-and-docs

## Design step (2026-06-20) — verification log

The ticket arrived already carrying a full spec (Description / AC / Proposed
Shape / Out of Scope / Decisions). The design step's job here was to verify
that spec against real CLI behavior, refine the gaps, and surface decisions —
not author from scratch. All claims were ground-truthed against the
`~/Desktop/relay-cli` checkout (the `relay` on PATH runs this source).

Confirmed real / accurate:

- `relay init --user <name>` — required for a fresh init (`relay init --help`).
  Seeds `tasks/relay-build/` onboarding ticket, stamps `new-user` →
  `<name>` on owner/human/assignee, prunes it on a non-empty repo
  (`src/relay/commands/init.py`, `_ONBOARDING_TICKET_DIRS = ("relay-build",)`).
- `relay build` = alias → `relay launch relay-build` (`relay.toml` `[aliases]`).
  Launches the `build/onboarding` workflow (`gather-and-spec` →
  `generate-batch`): one scripted question → agent chat → vision written to
  `contexts/product/vision/SKILL.md` + a batch of draft tickets → `relay launch
  <slug>`. So `init --user → build → launch` does land a newcomer on a
  launchable ticket — the stated Win holds.
- `relay digest` exists (flags `--quiet-empty` / `--announce-empty`); no README
  entry today. `relay validate` exists (`--json`, `--task`, `--fix`,
  `--idle-hours`, `--max-blackboard-kb`, `--check-slack`, `--check-github`);
  also no dedicated README entry.
- License = `AGPL-3.0-or-later` (`pyproject.toml`, `LICENSE` present).
- vision.md stale items at the specced lines: repo URL `relay-dev/relay` (L14),
  "six-command CLI" (L22), `[FILL IN WITH REAL NUMBERS]` (L246).
- README stale items: hand-edit `user =` / `relay ticket "First task"` block
  (L133-139); `gh skill` "once those commands land" (L100) — contradicted by
  the README's own `### relay skill` section, which treats `gh skill` as a
  shipped public preview.

## Resolved questions (answered by zach, in-session)

1. **Install duplication.** `## Development` (L772-781) also has `git clone` +
   `pip install -e .`, so "one source of install truth" was not fully covered.
   → **Decision: Dev references Getting Started**, keeps only dev-only commands.
   Folded into AC + Proposed Shape item 3.
2. **Three onboarding narratives.** Getting Started (`init→build→launch`) vs the
   existing `## Task lifecycle` path and `relay ticket` "usual boot sequence",
   both centered on `relay ticket`.
   → **Decision: light cross-reference** — one line distinguishing them; do not
   rewrite those sections. Folded into AC + Proposed Shape item 2.

No open questions remain. Spec is ready for `review-design`.
