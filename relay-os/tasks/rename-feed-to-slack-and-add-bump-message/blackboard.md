# Blackboard — rename feed → slack + bump --message

## Plan

### Code

1. `src/relay/commands/feed.py` → `src/relay/commands/slack.py`. Rename the
   `feed()` function to `slack()`. Update docstring/help text to reflect
   the "manual broadcast escape hatch" framing from the ticket.
2. `src/relay/cli.py`: import `slack` instead of `feed`, register
   `app.command("slack")`, swap `feed` → `slack` in `_BUILTIN_COMMANDS`.
3. `src/relay/commands/bump.py`: add `--message` Typer option. When set,
   append " — <message>" to the Slack broadcast text *and* to the log
   entry at all three sites (no-workflow done, past-final-step done,
   advanced-step). Empty string → fail loud, like `slack`'s rule.
4. Touch incidental refs:
   - `src/relay/commands/init.py` "bump/feed/panic/launch" string.
   - `relay-os/relay.toml` + template — comment listing broadcasts.

### Tests

- `tests/test_commands.py`: rename `test_feed_logs` → `test_slack_logs`,
  swap command name + log prefix. Add tests for `bump --message`:
  - advance step + message → log contains both step and message
  - no-workflow done + message → same
  - empty message → exit 2
- `tests/test_smoke.py`: swap the `feed` invocation for `slack` and
  update the docstring.

### Docs / contexts

- `src/relay/resources/prompt.md` (and -auto, -interactive) — rename
  the section, reframe as escape hatch, mention `bump --message` as
  the preferred path for transition-tied FYIs.
- `README.md` — rename the section, add `--message` to bump.
- `CLAUDE.md` — line 6 command list.
- `relay-os/contexts/relay/cli/SKILL.md` (+ template copy) — rename
  section, decision tree.
- `relay-os/contexts/relay/architecture/SKILL.md` (+ template) — line 83.
- `relay-os/contexts/relay/codebase/SKILL.md` — `feed.py` → `slack.py`.
- `relay-os/contexts/relay/sync/SKILL.md` (+ template) — bullet, file ref.
- `docs/spec.md` — multiple call sites; rename + add `--message`.
- `docs/design.md` line 81.

`docs/spec-audit.md` and `docs/vision.md` use "feed" both as the command
name and as a Slack-channel metaphor; touching the metaphor uses muddies
the diff, so I'll leave them — they're historical/essay docs.
The vendored `relay-os/.relay/...` copies refresh via
`relay init --update`, no manual edits.

## Decisions

- Log entry for `bump --message X`: format as `"advanced to step N (name) — X"` /
  `"task done — X"`. Keeps the audit trail complete and gives tests
  something to grep without monkeypatching `slack.post`.
- Slack broadcast format: `"👉 ... advanced *slug* → step N (name) — X"` /
  `"🎉 ... finished *slug* \"title\" — X"`. Same em-dash separator both
  places.
- Empty `--message ""` is an obvious mistake — fail loud (exit 2),
  matching `slack`'s rule.
- No `feed` alias for backwards compat. Ticket says "feed is gone."

## What landed

- `src/relay/commands/feed.py` → `src/relay/commands/slack.py`; renamed
  the function, log prefix `feed:` → `slack:`, docstring reframed as
  the manual broadcast escape hatch.
- `src/relay/cli.py` registers `slack`, drops `feed` from the
  built-ins set.
- `src/relay/commands/bump.py` adds `--message`. Empty rejects; non-
  empty appends ` — <message>` to both the log entry and the Slack
  broadcast at all three sites (no-workflow done, past-final-step
  done, advanced-step).
- Tests: rebuilt the feed test as a slack test, added four bump
  message tests (advance, no-workflow done, final-step done, empty
  rejection). Smoke test swapped `feed` for `slack`. 144/144 passing.
- Docs: README, CLAUDE.md, all three prompt files, the four affected
  contexts under `relay-os/contexts/relay/` plus their template
  copies under `src/relay/resources/templates/`, `docs/spec.md`,
  `docs/design.md`, and the `relay.toml` comment lines (active +
  template).
- Skipped: `docs/spec-audit.md` (historical audit doc) and
  `docs/vision.md` (essay where "feed" is metaphorical for the Slack
  channel itself, not the command name) — touching either dilutes the
  diff. Vendored `relay-os/.relay/...` copies refresh via
  `relay init --update`, no manual edits.

## Verification

- `python -m pytest` — 144/144 pass (was 144 before).
- `python -m relay --help` — lists `slack`, no `feed`.
- `python -m relay bump --help` — shows `--message`.
- `python -m relay slack --help` — same surface as the old `feed`.

## Final re-verification

- `.venv/bin/python -m pytest tests/test_commands.py tests/test_smoke.py`
  — 34 passed.
- `.venv/bin/python -m pytest` — 212 passed.
- `.venv/bin/python -m relay --help` — lists `slack`; no `feed`.
- `.venv/bin/python -m relay bump --help` — shows `--message`.
- `.venv/bin/python -m relay slack --help` — shows the manual FYI surface.
- `.venv/bin/python -m relay feed --help` — exits 2 with `No such command 'feed'`.

## Retro

status: processed
skill: retro/done-ticket
result: no-new-durable-knowledge
title: No new durable knowledge for rename-feed-to-slack-and-add-bump-message
