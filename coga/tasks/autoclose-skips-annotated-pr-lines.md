---
slug: autoclose-skips-annotated-pr-lines
title: Autoclose skips annotated PR lines
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- dev/code
skills: []
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 3 (pr)
---

## Description

`_PR_LINE_RE` in `src/coga/autoclose.py` is anchored to `$`, so a `## Dev`
`pr:` line carrying any trailing annotation after the URL parses as "no PR" and
the ticket is skipped — silently, since the sweep still prints `no tickets
bumped` and exits 0. Stop anchoring to `$` (or strip the trailing annotation) so
the URL is the capture, matching `_BRANCH_LINE_RE` / `_WORKTREE_LINE_RE`, which
already tolerate exactly this.

## Context

### The regex

`src/coga/autoclose.py:115` (line numbers throughout are as of 2026-08-19;
prefer the symbol names — the file has already drifted once since this was
filed):

```python
_PR_LINE_RE = re.compile(r"^\s*(?:-\s*)?pr:\s*(\S+)\s*$", re.MULTILINE)
```

The comment directly above it (`:110-114`) already reasons about this failure
mode for the `- ` list-prefix case — "a bulleted `pr:` line is invisible to the
sweep, so a merged final-step ticket is silently skipped and left stranded
`in_progress`" — and then the same sentence applies verbatim to a trailing
annotation, which the `$` anchor still rejects.

The siblings at `:123` and `:127` capture `(.+?)` and normalize afterwards:

```python
_BRANCH_LINE_RE = re.compile(r"^\s*(?:-\s*)?branch:\s*(.+?)\s*$", re.MULTILINE)
_WORKTREE_LINE_RE = re.compile(r"^\s*(?:-\s*)?worktree:\s*(.+?)\s*$", re.MULTILINE)
```

`parse_branch_name` / `parse_worktree_path` (`:139`, `:163`) do the normalizing:
a leading backtick delimits the value through its matching closing backtick
(which is what makes `` branch: `name` (annotation) `` work), and an unmatched
backtick falls back to whole-line stripping. Whatever shape the `pr:` fix takes,
it should land in the same place — normalization inside `parse_pr_url`, not a
third bespoke line-regex dialect. A URL cannot contain whitespace, so dropping
the `$` anchor and keeping the `(\S+)` capture is likely sufficient on its own.

Backtick-stripping (so `` pr: `<url>` (annotation) `` also parses) is worth
adding for symmetry with the siblings, but note it is **speculative**: nothing
currently writes that shape — `open_pr.set_dev_pr` writes a bare line. If you
add it, add it because the doc edit below documents the shape, not because
something in the tree depends on it.

### Don't trade a silent skip for a loud one

`parse_worktree_path` deliberately rejects placeholder values
(`if not path or path.startswith("(")`, `:184`). `parse_pr_url` has no
equivalent, and today the `$` anchor accidentally covers for that: a line like
`pr: (not opened yet)` or `pr: none — blocked on CI` simply fails to match and
yields `None`, which is benign.

Once the anchor is gone, `(\S+)` captures `(not` / `none`, which flows to
`pr_state` → `gh pr view` → `GhError`, which `run_autoclose_recipe` (`:602`)
catches and turns into **exit 2 — aborting the sweep for every remaining
ticket**. That converts a silent single-ticket skip into a whole-sweep failure
for a different class of input. Mirror the `startswith("(")` guard, and
consider rejecting any capture `parse_pr_number` can't read a `/pull/<n>` out
of. This needs its own test.

### Blast radius is wider than the sweep

`parse_pr_url` is shared infra, not an autoclose-private helper. Consumers as of
2026-08-19:

- `src/coga/step_gate.py:45` (lazy import inside `_has_pr`) — backs the
  `requires: pr` bump gate. An annotated `pr:` line therefore also makes
  `coga bump` refuse to advance the PR step of `code/with-review` /
  `code/with-self-review`. The literal message (`step_gate.py:87`) is
  ``Cannot advance: this step requires a recorded `pr` artifact on the
  blackboard, but none is present.`` plus a remediation line.
- `src/coga/open_pr.py:338, :533` — the idempotency check (`already`) and the
  post-write round-trip check (`parse_pr_url(current_blackboard) != url`). **The
  fix changes behavior here too, in a good way:** today an annotated line parses
  as `None != url`, so `set_dev_pr` rewrites the whole line and destroys the
  annotation; after the fix it compares equal, the rewrite is skipped, and the
  annotation survives. Assert that explicitly in a test rather than letting it
  land by accident. The `already`-mismatch note at `:543` (`replaced a stale
  pr: line`) also becomes reachable in new cases. Note `open_pr.py` carries its
  *own* `_PR_LINE_RE` at `:149` (`^(?P<prefix>\s*(?:-\s*)?)pr:.*$`) which
  already tolerates annotations and rewrites the whole line — leave it alone,
  but know it's there before writing the round-trip test.
- `src/coga/branchcleanup.py:468` — branch-sweep / retire protection.
- `src/coga/pr_assist.py:82`, `src/coga/commands/launch.py:307, :1574, :1936`.

The fix is one regex, but the test plan should cover the gate and the open-pr
round-trip, not only the sweep.

### Tests

`tests/test_autoclose.py:144-181` holds five existing `parse_pr_url` tests;
`test_parse_pr_url_list_item_form` (`:176`) is the closest precedent and the
best template to copy for the annotated case.

The regression surface is bigger than that file: `tests/test_open_pr.py` and
`tests/test_open_pr_command.py` assert through `parse_pr_url` in roughly fifteen
places, and `tests/test_launch.py:1056` does too — those cover the open-pr
behavior change above. `tests/test_autoclose_sweep.py` and `tests/test_retire.py`
cover the sweep and retire paths.

### Doc sync

`dev/code` is the only place documenting the `pr:` line's shape. The
backtick-delimit-then-annotate rule is **not** stated in the `branch:` /
`worktree:` bullets — it lives in a shared paragraph that explicitly scopes
itself to "`branch:` and `worktree:` are machine-readable fields". So this is
**two touches per file**, and editing only the bullet leaves the paragraph
contradicting it:

- the shared paragraph at `coga/contexts/dev/code/SKILL.md:100-116` — widen its
  scope to include `pr:`;
- the `pr:` bullet at `:126` ("the full PR URL, one line") — state the
  annotation rule.

Per `CLAUDE.md`, make both edits in **both** copies:

- `coga/contexts/dev/code/SKILL.md` (live repo copy)
- `src/coga/resources/templates/coga/bootstrap/contexts/dev/code/SKILL.md` (packaged)

They are byte-identical today (8572 bytes each); keep them so.

### This ticket dogfoods its own gate

The PR step of the chosen workflow is one of the broken consumers. On the normal
path `coga open-pr` writes a bare line and nothing goes wrong — but if you
hand-write an annotated `pr:` line during a manual recovery, `coga bump` will
refuse to advance the very ticket that fixes that refusal. Don't be surprised
by it.

### Live casualty

In the `admin` repo, `xero-reconcile-reminder` (final step 4/4, PR #55 merged
2026-06-10) sat stranded `in_progress` from that merge until Zach hand-closed it
on 2026-07-31, because its line read:

```
- pr: <url> (no CI configured on the repo — …)
```

That ticket has since been closed and deleted, so this defect has no
outstanding victim — it is the regex, not a stranded ticket, that needs fixing.
It also means there is **no reproduction outside a synthetic fixture**; don't go
looking for a real stranded ticket to verify against.

### The documentation alternative was considered and rejected

The other available fix is to keep the `$` anchor and document "the `pr:` line
carries a bare URL and nothing else". That was written up as a separate `admin`
ticket and closed as superseded: the constraint is the odd one out (its
`branch:` / `worktree:` siblings tolerate annotations), and fixing the regex
deletes the need for the sentence. **If this is instead resolved by keeping the
anchor**, the sentence's home is the `dev/code` `pr:` bullet named above — the
only place describing the line's shape, and the only one omitting an annotation
rule.

### Origin

Verified against the package source during the 2026-08-15 Dream run in the
`admin` repo (Phase 3 contract audit), filed from
`admin/carry-three-verified-coga-bugs-upstream`.

<!-- coga:blackboard -->

## Dev
pr: https://github.com/FastJVM/coga/pull/706
branch: pr-line-annotations
worktree: /home/n/Code/claude/coga-pr-line-annotations

## Implement (done)

**The fix** — `src/coga/autoclose.py`:
- `_PR_LINE_RE` now captures `(.+?)` like `_BRANCH_LINE_RE` / `_WORKTREE_LINE_RE`
  instead of an anchored `(\S+)$`.
- `parse_pr_url` normalizes the capture the same way the siblings do: a leading
  backtick delimits the value through its matching closing backtick, an
  unmatched backtick falls back to whole-line stripping, then only the first
  whitespace-delimited token is kept (a URL never contains whitespace).
- New `_looks_like_pr_url` guard. **Why:** without it the unanchored capture
  hands `(not` / `none` from `pr: (not opened yet)` to `gh pr view`, and the
  resulting `GhError` makes `run_autoclose_recipe` exit 2 — aborting the sweep
  for every remaining ticket. The guard accepts a value carrying `://` or a
  readable `/pull/<n>` and rejects the rest.

**Tradeoff accepted:** the guard is by value shape, not a `/pull/<n>` requirement
(which would reject non-GitHub PR links). A freeform non-URL value therefore
still parses as "no PR" — deliberate: a silent single-ticket skip beats a
whole-sweep failure.

**Docs** (`coga/contexts/dev/code/SKILL.md` + the packaged copy, kept
byte-identical, 9015 bytes each): widened the machine-readable-fields paragraph
to include `pr:` (noting a bare `pr:` value ends at the first whitespace, unlike
`branch:` / `worktree:` which consume the line), and stated the annotation rule
plus the placeholder caveat in the `pr:` bullet. Left
`coga/skills/code/implement/SKILL.md` alone — it speaks only to `branch:` /
`worktree:`, which the implement step writes.

**Tests added:**
- `tests/test_autoclose.py` — annotated / backtick-annotated / unclosed-backtick
  `parse_pr_url` forms, a parametrized placeholder-rejection test, and an
  end-to-end `sweep_merged` test closing a final-step ticket whose `pr:` line
  carries a trailing note (the live `xero-reconcile-reminder` shape).
- `tests/test_commands.py` — the `requires: pr` bump gate now accepts an
  annotated line (this ticket's own dogfooding case).
- `tests/test_open_pr.py` — the open-pr round-trip leaves a matching annotated
  line intact instead of rewriting it away.

**Verification:** `python -m pytest` in the feature worktree —
1889 passed, 1 failed. The failure is
`tests/test_packaging.py::test_wheel_includes_bootstrap_batteries`, environmental
and pre-existing (`No module named pip` in the venv); it fails identically on
unmodified `main`. `coga validate` not run: no validation behavior changed.
Branch rebased onto current `origin/main` (no new commits). Not pushed.

## Self-QA (done)

`/code-review` ran at default effort against `main...pr-line-annotations` and
reported five findings. `/simplify`'s four cleanup agents each went idle without
their findings reaching this session — the return channel did not deliver — so
the four angles (reuse / simplification / efficiency / altitude) were reviewed
directly against the diff instead of skipped. The reuse finding that pass
produced is the same duplication `/code-review` flagged, applied below.

**Applied** (commit `ac854e63`):

- *(medium, real regression)* `parse_pr_url` now scans **every** `pr:` line via
  `finditer` instead of taking only the first. The old anchored regex *failed to
  match* a placeholder line and kept searching; the new guard *rejects* a line
  the regex happily matches, so stopping at the first match stranded a ticket
  that recorded `pr: (not opened yet)` and appended the real link below it —
  reintroducing exactly the silent skip this ticket exists to delete.
- *(low)* `_PR_LINE_RE` now spells its whitespace runs `[ \t]`, not `\s`. `\s`
  matches newlines, so the non-greedy `(.+?)` on an empty `pr:` line reached
  past it and captured the next non-blank line. Same latent flaw exists in
  `_BRANCH_LINE_RE` / `_WORKTREE_LINE_RE`, but it is pre-existing there and out
  of this diff's scope — left for a follow-up rather than swept in.
- *(quality/reuse)* Extracted `_delimited_value`, now shared by all three
  `## Dev` parsers, replacing three verbatim copies of the backtick
  normalization (this change had added the third).
- *(low, docs)* The `pr:` bullet claimed a trailing annotation works "same as
  the two fields above" — false: a bare annotation on `branch:`/`worktree:` is
  swallowed into the value, which is why their backtick rule exists. Reworded to
  say `pr:` needs *no* backticks, because its value ends at the first
  whitespace. Both copies still byte-identical (9139 each).
- Two regression tests for the first two items.

**Skipped, for the human reviewer to weigh:** `/code-review` noted the widened
parse increases whole-sweep-abort exposure — an annotated line whose URL is
stale or its repo deleted now reaches `gh pr view`, and `_sweep_merged_into`
re-raises `GhError` when `quiet=False`, so `run_autoclose_recipe` exits 2 and
leaves every remaining ticket unswept. Real, but the fix (catch `GhError` per
ticket and continue with a note) changes autoclose's fail-loud exit-2 contract,
which is a design decision well outside "stop anchoring `_PR_LINE_RE` to `$`".
Left in the safer, unchanged state.

**Verification:** `python -m pytest` in the feature worktree — 1891 passed, 1
failed. Same single environmental failure as before
(`test_packaging.py::test_wheel_includes_bootstrap_batteries`, `No module named
pip`); confirmed failing identically on unmodified `main` this session. Working
tree clean. Branch not pushed — `coga open-pr` pushes it at the next step.
