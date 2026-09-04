---
slug: guard-the-browser-dochub-and-playwright-live-vs-pa
title: Guard the browser dochub and playwright live-vs-packaged pair in test_packaging
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow: code/with-review
secrets: null
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
