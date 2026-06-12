The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: autoclose-merged
worktree: /tmp/relay-autoclose-merged
pr: https://github.com/FastJVM/relay/pull/347

## Peer review notes (codex, 2026-06-11)

- Ran `codex review --base main` from `/tmp/relay-autoclose-merged`.
  The first sandboxed run failed with `Read-only file system (os error 30)`;
  reran outside the sandbox with approval. Result: no must-fix findings.
- No code changes were made in peer review; branch `autoclose-merged` remains
  clean at commit `3538671`.
- Verification in `/tmp/relay-autoclose-merged`:
  - `PYTHONPATH=/tmp/relay-autoclose-merged/src python -m pytest -q` -> 672
    passed, 1 skipped.
  - `PYTHONPATH=/tmp/relay-autoclose-merged/src python -m relay.validate
    --task recurring-task-check-ticket-done --json` -> clean.

## Implement notes (codex, 2026-06-11)

- Commit `3538671` on branch `autoclose-merged` adds the daily
  `recurring/autoclose-merged/` script template, one-step
  `autoclose-merged/sweep` workflow, and `relay/autoclose/sweep` script skill.
- The script calls the existing `relay.automerge.auto_bump_merged(cfg,
  quiet=False)` directly. No second sweep implementation and no unused wrapper
  function were added; existing `relay automerge` and launch-freshness callers
  remain live for the follow-up ticket.
- Installed repos get the skill through the package-backed
  `bootstrap/skills/relay/autoclose/sweep/` copy. The Relay source checkout has
  the matching local `relay-os/skills/relay/autoclose/sweep/` copy so validation
  works without depending on a generated `relay-os/bootstrap/` tree.
- Verification in `/tmp/relay-autoclose-merged`:
  - `PYTHONPATH=/tmp/relay-autoclose-merged/src python -m pytest -q` -> 672
    passed, 1 skipped.
  - `PYTHONPATH=/tmp/relay-autoclose-merged/src python -m pytest
    tests/test_autoclose_sweep.py tests/test_automerge.py
    tests/test_recurring.py tests/test_init.py tests/test_packaging.py -q` ->
    162 passed, 1 skipped.
  - `PYTHONPATH=/tmp/relay-autoclose-merged/src python -m relay.validate
    --task recurring-task-check-ticket-done --json` -> clean.
  - Full `relay validate --json` from the feature worktree still fails on
    pre-existing repo task-state drift unrelated to this branch (for example
    `relay-crm` missing `docs/gdrive-mcp` and
    `split-context-to-doc-user-accessible-and-editable` missing `step:`).

## Bootstrap decisions (nick, interactive, 2026-06-11)

- **Discovery:** `relay automerge` already implements the merged→done sweep
  (`src/relay/automerge.py` `auto_bump_merged`): final-step + `pr:` under
  `## Dev` + PR merged on GitHub → `relay mark done`. Gap is purely that
  nothing runs it on a schedule.
- **Approach (Q1):** port + rename — make a daily recurring task the *sole*
  trigger for the sweep; retire the standalone command.
- **Closure (Q2):** auto-mark-done (keep existing behavior; broadcasts spool
  into the digest).
- **Trigger surface (Q3):** recurring task is the **sole** trigger. Remove
  explicit command + launch-freshness check. (Hook already gone — see
  evaluator.) Settles the `drift-…-auto-bump-merged` draft.
- **Workflow:** `code/with-review`.
- **Re-baseline after cold review:** only TWO live removals remain (CLI
  command, launch-freshness `auto_bump_one`); the post-merge git hook is
  already removed and `relay status` already stopped calling the sweep.

## Evaluator review

**Headline: one of the three named removal sites is already removed. The ticket is built on a stale premise and must be reconciled with its own drift draft before launch.**

### 1. Can a cold agent start from this alone?
Mostly yes for the *constructive* half. The ticket is unusually well-scaffolded: it names the source function (`auto_bump_merged`), the mirror trio (`digest/ticket.md` + `digest/flush` skill + `digest/post` workflow — all three confirmed to exist), the schedule rationale (8am before 9am digest so closures land in the same digest), and the PR-link convention. A new agent could build the recurring task.

Gaps/ambiguities:
- **"Add the matching one-step workflow (mirror `digest/post`)"** — but `digest/ticket.md` reuses `workflow: digest/post`. The ticket doesn't say whether to create a new `autoclose-merged/post.md` or reuse `digest/post`. Minor, but unspecified.
- **The rename** ("rename `automerge.py` / its public surface to match the new framing") is hand-waved — no target name given, and `auto_bump_merged`/`auto_bump_one`/`pr_state`/`parse_pr_url` are in `__all__` with external importers. An agent has to invent the new name and chase imports.
- **No acceptance criteria** as a checklist — the body is prose. The work is implied across Description + Context but never enumerated as "done when."

### 2. Does `code/with-review` (no design step) fit?
**No — it should have a design step, or the design questions should be resolved before launch.** Two genuinely open design decisions are buried in the ticket:
- The `mode: script` recurring sweep calls `gh` for every candidate ticket. The digest mirror it copies does **not** make network calls — it drains a local spool. Running `gh pr view` per-ticket inside a `mode: script` recurring run (which the recurring context notes runs under a "temporary mode=auto recurring freeze") is a new pattern, not a copy of digest. Whether a network-touching script step is safe under that freeze is an unanswered design question.
- The rename/public-surface reshaping touches `__all__` + multiple importers and overlaps a live decision (below). That's design, not just implement.

`with-review` is implement → peer-review → open-pr → human review. The peer-review step would be the first time anyone sanity-checks the script-vs-network and rename decisions — too late.

### 3. Are the attached contexts right?
- `relay/recurring` — correct and necessary (the constructive half lives there). Good fit.
- `dev/code` — correct; owns the `pr:` convention the sweep parses.
- **Missing:** the ticket's own Context section says docs in **`relay/sync`** and the **cli context** must be updated, yet neither is attached. The removal/doc-update half of the work has no context support. At minimum `relay/sync` should be attached given the digest-spool interaction (automerge done events spool into the digest — `commands/digest.py:4` and the digest ticket both reference "automerge done").
- Nothing attached is over-broad-enough to demote to a copied fact.

### 4. Is the scope one ticket?
**No — it bundles five loosely-coupled deliverables:** (a) new recurring task, (b) logic port + module rename, (c) three trigger removals, (d) doc/context updates across sync+cli+README in both the live and packaged `relay-os/` trees, (e) reconciling/closing **two** other drafts (`drift-status-still-calls-auto-bump-merged-after-mo` and `remove-the-post-merge-automerge-git-hook`). Each of (a), (b), (c) is independently shippable. This is at least 2-3 tickets. The "settle the drift draft" item especially is a *decision*, not a code change, and shouldn't ride inside an implementation ticket.

### 5. Wrong assumptions to question before launch
- **`auto_bump_merged`/`auto_bump_one` work as claimed — confirmed.** `automerge.py` lines 161–198: `auto_bump_merged` walks `list_tasks`, gates on `active`/`in_progress` + final-step + `pr:` under `## Dev`, checks `gh pr view ... state == "MERGED"`, calls `mark_done`. `auto_bump_one` is the single-ticket form. The docstring scope (final-step only, mid-workflow left alone) is accurate. No correction needed here.

- **Removal site 1 — `relay automerge` CLI command: REAL.** `cli.py:79` registers it; `commands/automerge.py` is the thin wrapper calling `auto_bump_merged(quiet=False)`.

- **Removal site 2 — `auto_bump_one` in `launch.py`: REAL.** `launch.py:160` inside the pre-launch freshness check (lines 152–168). Confirmed.

- **Removal site 3 — the `init`-installed post-merge git hook: ALREADY REMOVED. This is the ticket's central wrong assumption.** `init.py` no longer *installs* a post-merge hook — it only contains `_remove_post_merge_hook` (lines 693–728), which *prunes* stale Relay-owned symlinks on `init --update`. The docstring states plainly: *"Relay no longer ships or installs a post-merge hook (automerge is an explicit-only surface)."* The only `symlink_to` in init (line 671) wires **skills**, not hooks. The `bootstrap/hooks/post-merge` file still exists on disk but is dead — nothing symlinks it into `.git/hooks/`. So the ticket's task 3 bullet "Remove the `init`-installed post-merge git hook... Update `relay init` so fresh repos no longer install it" describes work that was **already done in a prior PR**.

- **Corroborating drift evidence:** the ticket claims it "settles the `drift-status-still-calls-auto-bump-merged-after-mo` draft." Reading that draft shows the surface has *already moved* underneath this ticket: PR #254 removed the `status` side-effect (confirmed — `status.py:73` is now just a comment). The drift draft's "remaining triggers" list is {explicit, hook, launch-freshness} — but the hook is already gone in init, so even the drift draft is itself stale. The actual current trigger surface is just **{explicit `relay automerge`, launch-freshness check}** — two, not three.

**Net:** before launch, re-baseline the ticket against current `main`. The real remaining removals are only **two** (CLI command + launch-freshness), plus possibly deleting the now-dead `bootstrap/hooks/post-merge` file and the vestigial `_remove_post_merge_hook` migration. The "remove the init hook install" framing should be struck. The doc references (`with-review.md:82` still tells humans to "run `relay automerge` explicitly," and `automerge.py`'s docstring still claims "Two callers") will also drift once the CLI command is removed — those are additional update sites the ticket doesn't name.

### Post-review reconciliation (applied to ticket)
- Removal list corrected to TWO live sites + dead-artifact cleanup (hook already gone).
- `relay/sync` added to attached contexts.
- Doc-drift sites named (`with-review.md` review step, `automerge.py` docstring); rename guidance + importer-chase added.
- "Done when" checklist added.
- Mode note added (script + `gh` is what `relay automerge` already does; the freeze is about agent buffering, not network).
- NOT split into multiple tickets per evaluator §4: nick chose this as one consolidation move. Flagged to human as an open option.

## Split + git cleanup (nick, 2026-06-11)

- **Split applied** (nick chose to split, dependency-ordered):
  - `recurring-task-check-ticket-done` — narrowed to the *additive* half:
    create the daily `mode: script` recurring task `autoclose-merged/` +
    factor the sweep into a shared function. No removals.
  - `retire-standalone-relay-automerge-triggers-recurri` (new) — the
    *removal* half: drop the `relay automerge` command + launch-freshness
    check, rename the module, clean dead hook artifacts, update docs,
    reconcile the `drift-…-auto-bump-merged` + hook drafts. **Depends on the
    first landing.**
- **Deleted** redundant empty drafts `recurring-task-check-ticket-done-2`
  and `autoclose-merged` (the task draft; the recurring task reuses the name
  under `relay-os/recurring/`, different path).
- **Resolved a pre-existing stuck git state** (4 `UU` files from a failed
  `relay` autostash pop, `Updated upstream` vs `Stashed changes`):
  - `dream/log.md`, `relay-dev-update/log.md` — union (append-only ledgers).
  - `digest/blackboard.md` — union both spool blocks (events disjoint; no
    double-post).
  - `relay-dev-update/blackboard.md` — took `last_commit: df63188` (advanced
    cursor) over the `8e0ab9c` "first run" fallback.
  - `git add`ed all 4 → unmerged state cleared; `relay validate` exits 0,
    CLI unblocked. NB: 3 stale `autostash` entries remain in `git stash
    list` (harmless clutter; left for nick to drop if wanted). None of the
    above is committed yet — `relay` commits failed during the stuck state;
    files are correct on disk.
