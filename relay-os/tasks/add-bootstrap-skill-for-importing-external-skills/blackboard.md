The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: bootstrap-import-skill
worktree: /home/n/Code/codex/relay-bootstrap-import
pr: (not opened yet — open-pr step)

## Design decisions (with nick, interactive)

- **Provenance reuses the existing mechanism, not a new format.** Relay already
  ships `relay skill install-url` / `status` / `update`, which write
  `.relay-source.json` (`schema: relay.skill-source.v1`) beside an imported
  skill: `source_url`, `selector`, `installed_ref`, `installed_at`/`updated_at`,
  `source_digest`/`source_tree_digest`/`installed_tree_digest`, and the
  hand-edited `local_adaptation_notes`. Those fields satisfy the ticket's
  provenance requirement (source URL, upstream repo, import date, local changes
  via digests, reason for adaptation via notes). The new skill points at this;
  it does NOT define a parallel markdown provenance block.
- **OpenClaw / ClawHub is the prior art nick referenced.** It's a 2026 agent
  platform with a skills marketplace — same SKILL.md format, `clawhub install`
  CLI, thousands of community skills. Relay's analog is `install-url`; the gap
  is Relay has no *search* command, so discovery = web/GitHub browsing of
  registries (`openclaw/agent-skills`, VoltAgent awesome-list, GitHub
  `path:SKILL.md`).
- **Discovery hooks into the existing gap point ("how do I know").** Not
  speculative trawling. The trigger is the moment `bootstrap/ticket` step 4
  already detects a missing skill (a workflow step refs a non-existent `skill:`,
  or the interview surfaces a recurring process need). The hook flips
  "create it inline" → "search first, then decide import/adapt/write." What to
  search is derived from task domain + missing capability.

## What changed

- NEW bundled skill `bootstrap/import`:
  `src/relay/resources/templates/relay-os/bootstrap/skills/bootstrap/import/SKILL.md`.
  Decision tree (import / adapt / write), registry-search guidance, provenance
  via the real `.relay-source.json` mechanism, where imported skills live
  (`relay-os/skills/<ns>/<name>/`), the "don't import broad/command-baked
  skills" anti-pattern, and a worked dev unit-testing example. Authored in the
  SOURCE template (the live `relay-os/bootstrap/` copy is gitignored +
  regenerated on `relay init --update`). Force-added (`git add -f`) per the
  bootstrap/.gitignore gotcha.
- Thin hook in `bootstrap/ticket` step 4: before hand-writing a skill, follow
  `bootstrap/import` first. Source template copy only.

## Verification

- `python -m pytest` → 635 passed (run with the shim venv + PYTHONPATH=src
  against the worktree, since the worktree has no editable install).
- `relay validate --json` (primary checkout) → 95 ok, 65 issues, all
  pre-existing draft warnings (`missing-workflow` etc.) unrelated to this
  change; no errors introduced.
- No example/ fixture change needed: the seeded fixture carries no bootstrap
  skills (`example/relay-os/bootstrap/skills/bootstrap/` does not exist), and
  this change is docs-only (no prompt-composition / workflow-semantics shift).
