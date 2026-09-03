---
slug: retire-never-removes-a-worktree-that-ran-the-tests
title: Retire never removes a worktree that ran the tests
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
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
step: 3 (implement)
---

## Description

`coga retire` promises to dispose of a finished ticket's feature checkout, and
the `dev/code` context tells agents to rely on that ("You do not remove your own
feature checkout. `coga retire` does"). In practice that half of retire almost
never fires. `remove_ticket_worktree` refuses the removal when
`git status --porcelain=v1 --untracked-files=all --ignored` reports *anything*
(`src/coga/branchcleanup.py:199-217`), and every code ticket's workflow runs
`python -m pytest` inside the feature worktree, which leaves `__pycache__/` and
`.pytest_cache/` behind. Pytest writes a `.gitignore` containing `*` into its
own cache directory, so `.pytest_cache/` reports as ignored in every repo
regardless of what the repo's `.gitignore` says. The refusal is not an edge case
— it is the normal outcome for a code ticket.

The knock-on is that the branch stays pinned by the surviving worktree, so
`branch-sweep` can only report it as `skipped-worktree-pinned`
(`src/coga/branchsweep.py:24`, `:138`), and neither cleanup path can ever
finish. Worktrees and branches accumulate until a human notices and clears them
by hand.

Two findings from the code shape the fix:

- **The gate's predicate is wrong, not its intent.** Retire already deletes the
  entire *tracked* working tree when it removes a worktree — tracked content is
  recoverable from git. The reason the gate reaches past git's own check into
  ignored files (`src/coga/branchcleanup.py:26`, `:309`) is that ignored files
  can be unique and unrecoverable: `.env`, `coga.local.toml`, `.secrets/`. The
  property the gate actually wants is **recoverable**, not **ignored**.
  `__pycache__/` and `.pytest_cache/` are recoverable by construction — they are
  derived from files already in the repo and regenerate on the next tool run.
  Deleting them alongside a checkout retire is already authorized to delete is
  not a new category of destruction.
- **No new plumbing is needed to delete them.** `git worktree remove` without
  `--force` refuses on modified-tracked and untracked files but *deletes*
  ignored ones. Once the gate lets a cache-only checkout through, the existing
  unforced `_git(root, "worktree", "remove", ...)` call already does the right
  thing.

The residue is real and has to stay visible. Of the seven worktrees in the
2026-08-14 audit, one also held a `coga/coga.local.toml` — exactly the precious
category, and it should keep preserving the checkout. Today it produces the same
undifferentiated refusal, echoed to a terminal that immediately scrolls under
retire's retro launch. So the second half of the fix is a distinct, actionable,
durable report for everything retire still refuses to touch.

## Acceptance Criteria

- [ ] A retiring ticket whose feature worktree's only local state is regenerable
      tool cache (`__pycache__/`, `.pytest_cache/`, `.ruff_cache/`,
      `.mypy_cache/`) has its worktree removed, and the branch cleanup that runs
      immediately after is no longer worktree-pinned.
- [ ] That removal is never silent: the success note names the cache deletion
      and its scale, e.g. `Worktree cleanup: removed linked worktree '<path>'
      (also deleted 158 regenerable cache entries under '__pycache__/',
      '.pytest_cache/').`
- [ ] Any tracked or untracked (non-ignored) state still preserves the checkout,
      with today's message and **no** force hint — `--force` there would destroy
      real work.
- [ ] Any ignored entry outside the regenerable set still preserves the
      checkout. Its message is distinct from the tracked/untracked one, says the
      blocking state is ignored-but-not-regenerable, samples the *blocking*
      entries only (cache noise no longer drowns the real reason), and prints
      the explicit opt-in: `git worktree remove --force '<path>'`, plus the note
      that `coga run branch-sweep` prunes the branch on its next run once the
      checkout is gone.
- [ ] Classification fails closed: any status record that does not parse into a
      recognized `XY <path>` pair is treated as blocking, never as regenerable.
- [ ] A non-ASCII or space-containing filename under a regenerable directory is
      still classified regenerable (the probe must not be defeated by git's path
      quoting).
- [ ] When retire preserves the checkout, the reason and the manual command land
      in the retire-created retro task body, not only on stdout. (See open
      question 3 — drop this criterion if the owner wants the minimal PR.)
- [ ] `coga/contexts/dev/code/SKILL.md` and
      `src/coga/resources/templates/coga/bootstrap/contexts/dev/code/SKILL.md`
      (currently byte-identical) both describe the shipped behavior in the
      "Who retires the checkout" section, in this PR.
- [ ] The worktree safety model in the `branchcleanup.py` module docstring
      matches the new gate.
- [ ] Regression tests cover: cache-only removal, mixed cache + precious ignored
      file preserved, ignored-only refusal printing the force line,
      tracked/untracked refusal *not* printing it, and quoted-path handling.
- [ ] `python -m pytest` green; `coga validate --json` clean.

## Proposed Shape

### 1. `src/coga/branchcleanup.py` — split local state into blocking vs regenerable

- Add a module constant beside the safety model:

  ```python
  # Ignored directories whose contents are derived from tracked files and
  # regenerate on the next tool run. Retire deletes these with the checkout;
  # everything else ignored is treated as unique and preserves it.
  REGENERABLE_IGNORED_DIRS: frozenset[str] = frozenset(
      {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
  )
  ```

- Add a small dataclass next to the existing result types:

  ```python
  @dataclass
  class _WorktreeLocalState:
      blocking: list[str] = field(default_factory=list)      # full status lines
      regenerable: list[str] = field(default_factory=list)   # full status lines
  ```

- Rewrite `_worktree_local_state` (`:306`) to return
  `tuple[_WorktreeLocalState, str | None]`:
  - Run the probe with `-z` added
    (`git status --porcelain=v1 --untracked-files=all --ignored -z`). `-z`
    disables git's C-style path quoting, so a cache file with a space or a
    non-ASCII name classifies correctly instead of arriving as `"__pycache__/\303\251.pyc"`.
    Verified: without `-z`, git emits `!! "__pycache__/a b.pyc"`.
  - Split stdout on `\0`, dropping the trailing empty record.
  - Parse each record as `XY = record[:2]`, expecting `record[2] == " "` and
    `path = record[3:]`. If `"R" in XY or "C" in XY`, consume the *next* record
    as the rename/copy source (porcelain `-z` emits it as a separate field).
  - A record is **regenerable** iff `XY == "!!"` and some component of
    `PurePosixPath(path)` is in `REGENERABLE_IGNORED_DIRS`. Everything else —
    including any record that does not parse — is **blocking**.
  - Keep returning the raw status lines (reconstructed as `f"{XY} {path}"`) so
    the existing repr-style sampling still reads the same.

- Extract the current three-entry sampling into a helper so both refusal
  messages share it:

  ```python
  def _sample(entries: list[str]) -> str:
      sample = ", ".join(repr(entry) for entry in entries[:3])
      if len(entries) > 3:
          sample += f", and {len(entries) - 3} more"
      return sample
  ```

- Rewrite the gate at `:208`. Refuse only when `state.blocking` is non-empty,
  and branch the wording on whether every blocking entry is ignored:
  - **All blocking entries are `!!`** — ignored but not regenerable:

    ```
    Worktree cleanup: '<path>' contains ignored local state retire will not
    delete ('!! coga/coga.local.toml') — left in place. Remove it yourself with
    `git worktree remove --force '<path>'`; `coga run branch-sweep` prunes the
    branch on its next run.
    ```

  - **Otherwise** — tracked or untracked state present: keep today's shape but
    drop "or ignored" from the wording, since ignored now has its own branch,
    and print **no** force hint.
  - In both cases sample `state.blocking`, not the full status list.

- On successful removal, when `state.regenerable` is non-empty, extend the
  existing success note with the count and the distinct regenerable directory
  names found (sorted, so the message is deterministic).

### 2. `src/coga/commands/retire.py` — make a preserved checkout durable

`_cleanup_checkout` (`:150`) currently returns `None` and the notes only reach
stdout, which scrolls away under the retro launch that follows. Return the
`WorktreeCleanupResult` (or `None` when cleanup was skipped), and when the
result recorded a worktree that was *not* removed, pass its notes into
`_retire_body` (`:302`) so the created retro task body carries one short
`## Checkout cleanup` paragraph with the reason and the exact manual command.
Omit the section entirely when the worktree was removed or none was recorded.
Cleanup failures stay swallowed exactly as today — this must not become a
precondition for retire.

### 3. Docs — both copies, same PR

`coga/contexts/dev/code/SKILL.md` and
`src/coga/resources/templates/coga/bootstrap/contexts/dev/code/SKILL.md` are
byte-identical today; keep them so. In "Who retires the checkout" (live copy
`:57-87`):

- Rewrite the "Before removal, retire checks tracked, untracked, **and ignored**
  files" paragraph: tracked and untracked state always preserves the checkout;
  ignored state preserves it too, *except* the regenerable tool caches
  (`__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`), which are
  deleted with the checkout and reported.
- Rewrite the survivor bullet "a worktree with tracked, untracked, or ignored
  local state (including caches and machine-local config)": caches no longer
  survive; machine-local config (`coga.local.toml`, `.env`, `.venv/`, `.coga/`)
  still does, and retire prints the `git worktree remove --force` line for it.

### 4. Tests — `tests/test_branchcleanup.py`, `tests/test_retire.py`

Mirror the existing `_add_worktree` / `_dev_blackboard` / `_cfg` fixtures and the
naming of the neighbours at `:431-596`:

- `test_cache_only_worktree_is_removed` — worktree holding
  `.pytest_cache/.gitignore` (contents `*`, self-ignoring, as pytest writes it)
  and a `__pycache__/x.cpython-312.pyc` under a repo `.gitignore` rule; assert
  `removed is True`, the directory is gone, and the note names the cache
  deletion.
- `test_precious_ignored_file_survives_alongside_cache` — the same worktree plus
  `credentials.secret`; assert preserved, the file intact, and the sampled
  entries name the secret and not the cache.
- `test_ignored_only_refusal_offers_the_force_command` — assert the note
  contains ``git worktree remove --force``.
- Extend `test_dirty_worktree_left_in_place` (`:535`) — assert the note does
  **not** contain `--force`.
- `test_non_ascii_cache_filename_is_still_regenerable` — proves the `-z` probe.
- A direct unit test of the classifier with a hand-built rename record
  (`R  new\0old\0`) proving the source path is consumed and not misread as a
  bare record, and with a malformed record proving it lands in `blocking`.
- `tests/test_retire.py` — the created retro task body carries the
  preserved-checkout hint when the worktree is left in place, and carries no
  `## Checkout cleanup` section when it is removed.

## Out of Scope

- **Ticket option (1), redirecting test caches out of the checkout**
  (`-p no:cacheprovider`, `-o cache_dir=…`, `PYTHONPYCACHEPREFIX`) via the
  `code/*` skills. With the regenerable set handled it buys retire nothing, and
  it is Python-specific instruction-reliance that only covers tooling we
  remember to redirect. If it is wanted for other reasons — keeping a feature
  worktree's `git status` readable — the durable form is env injection at launch
  (`src/coga/task_env.py` already owns a task env contract), not prose in a
  shipped skill. Its own ticket.
- **Making the regenerable set configurable** (`[retire]` in `coga.toml`). Ship
  the constant; add config when a non-Python repo actually needs it.
- **Ticket option (4), general ignored-unique vs ignored-regenerable
  inference.** `git check-ignore -v` names the rule that matched but not whether
  the file is precious: in this repo `__pycache__/` and `.env*` come from the
  same committed `.gitignore`. No signal, no machinery.
- **A `--force-checkout` flag on `coga retire`.** Retire launches the retro pass
  that deletes the task directory, so by the time a human reads the refusal the
  ticket may already be gone and `coga retire <slug>` would fail its
  `status: done` lookup. The actionable opt-in is the plain
  `git worktree remove --force` line, which is why the report prints that.
- **Adding `.venv/` or `.coga/` to the regenerable set.** Rebuildable but
  expensive, and sometimes hand-tuned; they keep preserving the checkout and get
  the force hint. (Open question 4.)
- **Autoclose naming the retire follow-up** — shipped by the sibling ticket
  `autoclose-should-name-the-retire-follow-up`.
- **Any `branchsweep.py` change.** It already preserves and reports
  worktree-pinned branches, and prunes the branch on its next run once retire
  has removed the checkout.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design notes (2026-08-18)

Investigated before writing the spec:

- `remove_ticket_worktree` gate is `src/coga/branchcleanup.py:208`, fed by
  `_worktree_local_state` at `:306`. The probe returns *every* status line, and
  the gate refuses on any of them.
- `.pytest_cache/` is self-ignoring: pytest writes `.pytest_cache/.gitignore`
  containing `*`. That is why the audit's refusals listed
  `!! .pytest_cache/.gitignore` even though the repo `.gitignore` never mentions
  the directory. Redirecting the cache per-repo would therefore not be a
  one-line `.gitignore` fix either.
- With `--untracked-files=all`, git lists ignored entries as individual file
  paths rather than collapsing to `dir/` (confirmed on this repo: 530
  `__pycache__` lines). So the classifier has to match on *path components*, not
  on a trailing-slash directory entry.
- Git's porcelain v1 quotes paths containing spaces or non-ASCII bytes
  (confirmed in a scratch repo: `!! "__pycache__/a b.pyc"`,
  `!! "__pycache__/\303\251.pyc"`). Hence the `-z` switch in the spec — without
  it the classifier would silently mis-handle those paths. Fail-closed either
  way, but `-z` avoids a needless refusal.
- `git worktree remove` without `--force` already deletes ignored files; the
  existing call site needs no change once the gate opens. Confirmed against the
  module's own docstring reasoning at `:26` and `:309`.
- `coga/contexts/dev/code/SKILL.md` and
  `src/coga/resources/templates/coga/bootstrap/contexts/dev/code/SKILL.md` are
  byte-identical today (`diff` clean). There is **no** copy under
  `resources/templates/coga/contexts/` — only `browser` and `_template` live
  there — so the bootstrap path is the second copy to update.
- The sibling `autoclose-should-name-the-retire-follow-up` shipped (PR #694) and
  established the "make the debt visible with the exact command" pattern, plus
  the principle that implicit destruction is wrong. The spec's regenerable-cache
  deletion is explicit and reported, not implicit — but that tension is open
  question 1 below.

## Open Questions

1. **The spec overrules the ticket's preferred pairing — confirm or reject.**
   The ticket ranks (1) *stop generating the junk* + (2) *report and offer* as
   "the pairing to beat". The spec ships (3) *classify by disposability* + (2),
   and declines (1). Reasoning: (1)+(2) never actually removes a worktree. (1)
   only reduces how often caches appear and covers nothing but the tooling we
   remember to redirect; (2) improves the message but deletes nothing. Under
   that pairing retire's documented promise stays broken, the `dev/code` context
   still has to be softened to "retire will usually refuse and tell you what to
   type", and accumulation continues at roughly today's rate. (3) is defensible
   as a *correction of the gate's predicate* rather than Coga judging the
   operator's files: retire already deletes the whole tracked working tree, and
   the four cache directories are recoverable by construction. If you disagree,
   the fallback is to ship section 2 (durable report) + the message split in
   section 1 and drop the regenerable classification — the PR shrinks to the
   reporting half and the context doc gets the softened promise instead.
2. **Constant or config?** The spec hardcodes `REGENERABLE_IGNORED_DIRS` in
   `branchcleanup.py`. The alternative is a `coga.toml` key (say
   `[retire] regenerable_ignored = [...]`) so a non-Python repo can set its own
   and Coga ships only a default. That answers the ticket's "Python-specific in
   a tool that is not" objection properly, at the cost of new config surface.
   Recommendation: constant now, config when a real non-Python consumer asks.
3. **Should the preserved-checkout note reach the retro task body?** Section 2
   of Proposed Shape says yes — otherwise the report is echoed to a terminal
   that immediately scrolls under the retro launch, which is most of why the
   current refusal is invisible. It is ~10 lines in `commands/retire.py` plus a
   test. Say so if you want the PR kept to `branchcleanup.py` + docs.
4. **`.venv/` and `.coga/` are deliberately *not* in the regenerable set.** Both
   are ignored, both would still preserve a checkout, and both are technically
   rebuildable — but expensively, and `.coga/` holds a vendored CLI and the
   per-launch worktrees. They get the force hint instead. Confirm that is the
   line you want.
