---
slug: vendored-skills-carry-no-coga-source-json-so-coga
title: Correct recurring/skill-update's provenance claim to match how skills are actually managed
status: active
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
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
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 1 (implement)
---

## Description

The weekly `recurring/skill-update` template describes a mechanism this repo does not use:

> Imported skills live as plain directories under `coga/skills/` with `.coga-source.json`
> provenance. […] walks every imported skill with recorded provenance

No `.coga-source.json` exists anywhere in the repo. The file is real —
`src/coga/skill_manager.py` defines `SOURCE_METADATA` / `SOURCE_SCHEMA`
(`coga.skill-source.v1`), writes it in `install_url_skill`, and reads it in
`status_skills` / `update_skills` — but nothing under `coga/skills/` was installed that way.

**The decision is made: correct the template, do not backfill provenance.** The template's
prose is what is wrong; the code and the skill tree are both behaving correctly.

Rewrite the `## Description` of `coga/recurring/skill-update/ticket.md` so it describes what
`coga skill update --all --pr` actually does against this repo's four skill categories:

- **`delegated (github)`** — the seven `google-agents-cli-*` packs. These are what the weekly
  run actually updates, via `_update_gh_backed_skills` handing off to `gh skill`. The current
  template never mentions gh delegation at all, which is the substantive omission.
- **`local-override`** — `browser/dochub`, `browser/playwright`, `code/*`, `coga/*`. Repo-local
  copies that shadow bundled package-backed skills; they refresh with the coga package, not
  from a URL. `.coga-source.json` is the wrong mechanism for these by construction.
- **`unmanaged`** — `_template`, `direct/body`, `anthropic/skill-creator`. Hand-authored or
  hand-vendored; intentionally outside the update loop.
- **`package-backed (bundled)`** — already described correctly by the existing template.

State plainly that hand-vendored packs carry human-readable provenance instead
(`anthropic/skill-creator/ATTRIBUTION.md` pins `anthropics/skills` at `f458cee3`;
`browser/playwright/NOTICE.txt` names `microsoft/playwright-cli`) and are deliberately not
machine-managed. Keep the existing, accurate paragraphs about local adaptations never being
overwritten, the quiet no-op week, and the loud non-zero exit on follow-up statuses.

Keep `.coga-source.json` support in `skill_manager.py` as-is — it is live code for
`coga skill install-url`, just unexercised by this repo's current skill set.

## Context

### Do not backfill

Only `anthropic/skill-creator` is a genuine hand-vendored external import, and it has no
install-url source to record — writing a `.coga-source.json` for it would be inventing machine
provenance for a hand-copied tree, and would then make the weekly job try to "update" it from a
URL nobody installed it from. `browser/playwright` looks vendored but reports `local-override`:
it shadows a bundled package-backed skill and refreshes with the package.

### The command is not a no-op

The original framing of this ticket ("walks nothing") was wrong. Verify with `coga skill status`
before writing: `coga skill update --all` delegates the seven `google-agents-cli-*` packs to
`gh skill` (`skill_manager.py:237`, `:285`). The weekly PR run does real work today — the
template just describes the wrong reason for it.

### Edit both copies

`coga/recurring/skill-update/ticket.md` has a packaged mirror at
`src/coga/resources/templates/coga/recurring/skill-update/ticket.md`. They are currently
byte-identical but are **not** in `tests/test_packaging.py::IDENTICAL_LIVE_PACKAGED_PAIRS`, so
nothing will catch it if you edit only one. Edit both, per CLAUDE.md's sync rule.

### Documentation is thin, not wrong

`docs/reference.md` mentions `.coga-source.json` only obliquely, in the `install-url` entry
(line ~450). No doc change is required by this ticket; if the rewritten template makes a natural
place to cross-reference, that is optional.

### Provenance

Found by Dream 2026-08-24 — Phase 2 shards 13, 14, 15 (merged), corroborated by Phase 3 shards
ca-04 and ca-05. PR #708, which this ticket was originally sequenced behind, merged 2026-08-25;
that constraint is discharged.

### Split out of this ticket

Two follow-ups that arrived here from Dream Phase 6 now have their own tickets:

- `guard-the-browser-dochub-and-playwright-live-vs-pa` — packaging-test coverage for the
  `browser/{dochub,playwright}` mirrors.
- `validate-that-committed-skill-scripts-with-a-sheba` — validator check for committed scripts
  that carry a shebang but not the executable bit.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
