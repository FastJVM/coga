---
title: Guard the browser dochub and playwright live-vs-packaged pair in test_packaging
status: done
owner: nicktoper
agent: claude
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
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
---

## Description

`coga/skills/browser/dochub` and `coga/skills/browser/playwright` each have a packaged mirror
under `src/coga/resources/templates/coga/bootstrap/skills/browser/`. CLAUDE.md requires the two
copies stay in sync, but neither pair appears in
`tests/test_packaging.py::IDENTICAL_LIVE_PACKAGED_PAIRS`, so nothing catches a one-sided edit.

They are byte-identical today (verified 2026-09-01, `diff -r` clean for both trees), so this is a
pure guard-add: register the pairs and the existing test starts covering them. If the test fails
on its first run, that is a real drift that appeared since — fix the drift, don't relax the test.

## Context

### Why this is not already covered

PR #719 fixed `name:` frontmatter and the `$PWCLI` path in these skills. Its follow-up commit
("Keep vendored skill names slash-free and propagate fixes to packaged copies") did propagate to
the packaged mirrors, which is why they match now — but the guard was never added, so the next
edit is unprotected again.

### The list is file pairs, not directory pairs

`IDENTICAL_LIVE_PACKAGED_PAIRS` is an explicit allowlist of individual file pairs compared with
`read_bytes()`. Its header comment is deliberate: "Most bootstrap templates are curated copies
that intentionally diverge from the live `coga/` tree, so this is an explicit allowlist, not a
tree diff." Respect that — do not swap in a recursive tree comparison for the whole skills tree.

`dochub` is a single file (`SKILL.md`). `playwright` is nine:

    SKILL.md, LICENSE.txt, NOTICE.txt, agents/openai.yaml,
    assets/playwright.png, assets/playwright-small.svg,
    references/cli.md, references/workflows.md, scripts/playwright_cli.sh

Ten hand-written tuples is a lot of boilerplate for two directories that must match in full. A
reasonable alternative is a second, narrower constant — e.g. `IDENTICAL_LIVE_PACKAGED_TREES` —
holding the two directory pairs, with a companion test that walks both sides and asserts the file
sets and bytes match. That also catches a file *added* to one side only, which enumerated pairs
cannot. Either shape is acceptable; pick one and say why in the PR body. The byte comparison
already handles the binary `.png` / `.svg` assets correctly.

### Do not try to pair build-automation

`src/coga/resources/templates/coga/bootstrap/skills/browser/build-automation/SKILL.md` is
packaged-only — there is no `coga/skills/browser/build-automation` to pair it with. A tree-walk
implementation must not assume every packaged `browser/*` directory has a live twin.

### Adjacent unguarded pair, if you want it

`coga/recurring/skill-update/ticket.md` and
`src/coga/resources/templates/coga/recurring/skill-update/ticket.md` are also byte-identical and
also absent from the list, even though the sibling `ticket.py` pair *is* registered. Adding it is
a one-line change and squarely in the spirit of this ticket. Note that ticket
`vendored-skills-carry-no-coga-source-json-so-coga` edits that template's prose — if both are in
flight, sequence this one after it or expect a rebase.

### Verification

`python -m pytest tests/test_packaging.py` should pass unchanged. Confirm the guard actually
bites by temporarily editing one side and watching the test fail before reverting.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Already satisfied

Closed without a branch: the ticket's premise (a hand-maintained
`IDENTICAL_LIVE_PACKAGED_PAIRS` allowlist) was retired by PR #758 (`93db7dad`,
2026-09-08, "Live and packaged twin pairs are edited together by convention but
not enforced by any test"). `tests/test_packaging.py` now derives every twin
from the packaged tree via `_discover_live_packaged_twins()`, mapping
`templates/coga/bootstrap/skills/<path>` -> `coga/skills/<path>`, and
`IDENTICAL_LIVE_PACKAGED_PAIRS` is the derived, non-exempt subset. Verified
2026-09-13 in the primary checkout on `main` (`f3c75606`):

- **dochub pair registered** — `coga/skills/browser/dochub/SKILL.md` appears in
  `IDENTICAL_LIVE_PACKAGED_PAIRS` (printed the tuple from the test module).
- **playwright pair registered, all nine files** — `SKILL.md`, `LICENSE.txt`,
  `NOTICE.txt`, `agents/openai.yaml`, `assets/playwright.png`,
  `assets/playwright-small.svg`, `references/cli.md`,
  `references/workflows.md`, `scripts/playwright_cli.sh` all appear as pairs.
  Derivation also covers the "file added to one side only" case the ticket
  wanted: a new packaged file with a live counterpart becomes a pair on the
  next walk, no registration needed.
- **build-automation not paired** — `bootstrap/skills/browser/build-automation/`
  has no live counterpart and is absent from `LIVE_PACKAGED_TWINS`.
- **adjacent `recurring/skill-update/ticket.md` pair registered** — present
  alongside the `ticket.py` pair.
- **trees byte-identical** — `diff -r` clean for both `dochub` and
  `playwright` live-vs-packaged trees.
- **guard bites** — appended a line to
  `coga/skills/browser/playwright/references/cli.md`, and the pair showed up
  as drifted in `test_live_and_packaged_copies_stay_identical`; reverted.
- **no test change needed** — the derivation replaces the allowlist, so the
  ticket's "two directory-pair constant" alternative is moot; CLAUDE.md already
  documents the derived rule ("There is no list to register a new twin in").

## Adjacent finding (not fixed here)

`python -m pytest tests/test_packaging.py` currently fails on `main` for an
unrelated pair: `coga/contexts/coga/codebase/SKILL.md` vs its packaged twin
under `bootstrap/contexts/coga/codebase/`. Symptom: the live copy carries the
per-skill `gh skill update` / `classify_gh_update_output` / `text.py` ANSI
stripper prose that the packaged copy lacks. Cause: `74692b23 Sync coga state`
(2026-09-12) landed the live side on `main`, while the matching packaged-copy
edit (22 insertions) still sits on the unmerged `skill-update-per-skill`
branch (worktree `../coga-skill-update-per-skill`). It resolves when that
branch merges; if it does not, the packaged twin needs the same 22 lines.
Not this ticket's pair, so left alone per `code/implement` scoping.
