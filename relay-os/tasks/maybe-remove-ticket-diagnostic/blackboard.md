# maybe-remove-ticket-diagnostic — implement step

## Findings (recon, 2026-06-10)

- Ticket says the live copy is `relay-os/skills/eval/ticket-diagnostic/`; actual
  path is `relay-os/bootstrap/skills/eval/ticket-diagnostic/`. That live copy is
  **gitignored** (bootstrap/ is laid down by `relay init` from the package), so
  deleting it is local cleanup, not a commit.
- The git-tracked copy is
  `src/relay/resources/templates/relay-os/bootstrap/skills/eval/ticket-diagnostic/SKILL.md`.
- `ticket-diagnostic` is the **only** skill under `eval/` in both trees — removal
  empties the `eval/` namespace entirely.
- References found (repo-wide grep over .md/.py/.toml):
  - `tests/test_packaging.py:16` — entry in `EXPECTED_BOOTSTRAP_RESOURCES`;
    asserts the real packaged file exists and ships in the wheel. **Must change.**
  - `pyproject.toml:51` — comment listing ticket-diagnostic as an example of a
    SKILL.md-only dir. **Comment edit.**
  - `tests/test_init.py` (many lines) — all uses are **synthetic fixture data**
    (`_seed_fake_clone` / `_seed_fake_upstream_for_update` write their own
    eval/ticket-diagnostic SKILL.md); no test reads the real packaged skill.
    Tests pass either way.
  - `tests/test_skill_manager.py:508-567` — same: synthetic fixtures only.
  - `relay-os/recurring/digest/blackboard.md` — historical digest artifact; leave.
  - No contexts/ or docs/ references exist.
- Live `relay-os/.agent-skills/eval/ticket-diagnostic` symlink exists (gitignored,
  regenerated/pruned by init); remove locally alongside the live copy.
- `.relay/` vendored copies are gitignored build artifacts; refreshed by
  `relay init --update`, not touched by hand.

## Plan (pending human review)

1. `git worktree add ../relay-remove-ticket-diagnostic -b remove-ticket-diagnostic main`
2. In the worktree: delete packaged
   `src/relay/resources/templates/relay-os/bootstrap/skills/eval/` (whole dir —
   ticket-diagnostic is its only child).
3. `tests/test_packaging.py`: drop the eval/ticket-diagnostic entry from
   `EXPECTED_BOOTSTRAP_RESOURCES`.
4. `pyproject.toml`: drop "ticket-diagnostic" from the example-list comment.
5. Open question for human: rewrite the synthetic eval/ticket-diagnostic fixtures
   in test_init.py / test_skill_manager.py to a different skill name, or leave
   them (they don't depend on the real skill)? Leaning leave-as-is to keep the
   diff scoped; the names are arbitrary fixture data.
6. Run `python -m pytest`; commit.
7. In the primary checkout (not committed): delete live
   `relay-os/bootstrap/skills/eval/` and `relay-os/.agent-skills/eval/` symlink dir.
8. `relay bump maybe-remove-ticket-diagnostic`.

## Dev

branch: remove-ticket-diagnostic
worktree: /Users/zach2179/Desktop/relay-remove-ticket-diagnostic

## Decisions

- Human approved plan 2026-06-10; chose to leave the synthetic
  eval/ticket-diagnostic fixture names in test_init.py /
  test_skill_manager.py as-is (arbitrary fixture data, keeps diff scoped).

## Implement step — done

Committed on `remove-ticket-diagnostic` as 8ba9d693
("Remove bundled eval/ticket-diagnostic skill"), 4 files,
+2/-76:

- Deleted packaged
  `src/relay/resources/templates/relay-os/bootstrap/skills/eval/ticket-diagnostic/SKILL.md`
  (whole `eval/` namespace — it was the only skill there).
- `tests/test_packaging.py`: dropped the eval entry from
  `EXPECTED_BOOTSTRAP_RESOURCES`.
- `tests/test_init.py`: recon correction — `relay init` lays the bootstrap
  battery down from the *real* package resources (the fake_clone only fakes the
  CLI clone), so `test_init_into_empty_dir` and
  `test_init_links_skills_into_agent_dirs` did assert on the real skill and
  failed after removal. Dropped the eval assertions; nested-namespace symlink
  coverage now rides on `relay/calendar-reminder` (already a real nested
  bundled skill). Synthetic fixture mentions left untouched per decision.
- `pyproject.toml`: removed ticket-diagnostic from the build-comment example
  list.

Verification: `python -m pytest` in the worktree — **635 passed, 0 failed**.
(No repo dev venv exists; created throwaway `.venv-test` in the worktree with
`pip install -e ".[test]"` + `google-api-python-client google-auth-oauthlib` —
the test extra doesn't cover the two Google skill test modules' imports.
Possible follow-up ticket: add the google client libs to the `test` extra so a
clean-checkout `pytest` collects.)

Live gitignored copies removed in the primary checkout (not a commit):
`relay-os/bootstrap/skills/eval/` and `relay-os/.agent-skills/eval/`.
`relay-os/.relay/` vendored copies left alone — refreshed by `relay init
--update`.

No push, no PR — that's the next step.
