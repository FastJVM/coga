---
slug: vendored-skills-carry-no-coga-source-json-so-coga
title: Vendored skills carry no .coga-source.json so coga skill update walks nothing
status: draft
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

Coga ships a real skill-provenance mechanism: `.coga-source.json` (schema `coga.skill-source.v1`)
is written by `coga skill install-url` and read by `coga skill status` / `coga skill update`
(`src/coga/skill_manager.py`), and it is documented in `docs/reference.md`. **Not one skill under
`coga/skills/` carries that file.**

The weekly `recurring/skill-update` template asserts the opposite — "Imported skills live as plain
directories under `coga/skills/` with `.coga-source.json` provenance" — and runs
`coga skill update --all --pr` to "walk every imported skill with recorded provenance". It walks
nothing that way. Two skills are self-declared verbatim imports with hand-written provenance
instead (`anthropic/skill-creator/ATTRIBUTION.md` pins upstream `anthropics/skills` at `f458cee3`;
`browser/playwright/NOTICE.txt` names `microsoft/playwright-cli`), and `coga skill status` reports
both as unmanaged.

Decide: backfill `.coga-source.json` for the genuinely vendored packs, or change the template's
claim to match reality. Note `coga skill update --all` also delegates gh-backed skills, which the
template does not mention.

## Context

Found by Dream 2026-08-24 — Phase 2 shards 13, 14, 15 independently (merged), corroborated by
Phase 3 shards ca-04 and ca-05. The seven `google-agents-cli-*` packs are currently touched by
open PR #708, so sequence this after that merges.

### Follow-up surfaced during Dream Phase 6 (PR #719)

PR #719 fixed `name:` frontmatter and the `$PWCLI` path in the live
`coga/skills/browser/{dochub,playwright}` copies. The **packaged mirrors** under
`src/coga/resources/templates/coga/bootstrap/skills/browser/` carry the same drift and were
deliberately left untouched to keep that PR inside its stated scope.

No test covers that pair — they are absent from
`tests/test_packaging.py::IDENTICAL_LIVE_PACKAGED_PAIRS` — so nothing will catch the divergence.
CLAUDE.md's rule ("check both the live repo copy under `coga/` and the packaged copy … keep them in
sync") says they should match. Decide whether to sync them and add the pair to the packaging test, or
document the divergence as intentional.

Also from #719: the playwright wrapper `coga/skills/browser/playwright/scripts/playwright_cli.sh`
was committed `100644` while every sibling vendored script is `100755`, so the documented
`"$PWCLI" …` invocation failed permission-denied. Fixed in #719; worth a validator check so a
non-executable committed script is caught rather than discovered by a failing agent run.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
