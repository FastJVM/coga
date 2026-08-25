---
slug: move-cogacontext-to-roodoc-so-its-easier-for-human
title: move cogacontext to roodoc so its easier for human
status: done
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- dev/code
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
---

## Description

Make the location of the repo's contexts directory tunable in `coga.toml`
instead of hardcoded at `<repo_root>/contexts` (i.e. `coga/contexts/`). The
goal is human ergonomics: contexts are hand-edited prose, but they are buried
inside the machine-owned `coga/` tree, which makes them hard for a human to
find and hard to reach from the tools they actually edit docs in. A repo should
be able to say "my contexts live in `docs/contexts/`" and have every part of
coga follow.

Proposed spelling — a new top-level table, `[layout] contexts = "docs/contexts"`.
The name is not sacred; change it if something reads better, but decide it
before writing code rather than leaving it to the diff.

Scope is **contexts only**. Skills stay where they are — they are process
knowledge for agents and are not meant to be hand-edited by humans, so they get
no knob.

Done looks like: the setting points the contexts directory somewhere outside
`coga/`; `coga launch` composes from it, `coga validate` resolves refs against
it, `coga create`/`coga ticket` accept refs from it, and **the git state sweep
and authoring sync actually track files there** (see "The git sync fork" — this
is the part most likely to be missed and the part that decides whether the
feature works at all). Local-first resolution over the bundled
`bootstrap/contexts/` batteries is unchanged. With the setting unset the
behavior is byte-identical to today.

## Context

### Where the path is built today

`src/coga/paths.py:120` and `:124` are the **only** two places the local
contexts path is constructed:

```python
def context_path(cfg, ref):  return cfg.repo_root / "contexts" / ref / "SKILL.md"
def context_dir(cfg, ref):   return cfg.repo_root / "contexts" / ref
```

This was verified by grepping every `contexts` literal and every
`cfg.repo_root /` join across `src/coga/`; no other module builds the path.
Every consumer routes through `resolve_context_path` / `context_resolution_paths`
(`compose.py:201,203`, `validate.py:757,763`, `create.py:84`), so the resolver
is the single seam.

Note `context_dir` (`paths.py:123`) has **no callers** in `src/coga/` — only its
`__all__` export at `paths.py:203`. Prefer deleting it over threading a knob
through dead code.

### Fail loud — the default is silent corruption

`resolve_context_path` (`paths.py:135`) tries the local path and **falls back to
the packaged bootstrap contexts** on a miss. So if the new setting points at a
typo'd or nonexistent directory, nothing errors: `coga/architecture` quietly
resolves to the packaged copy and every repo-local context silently vanishes
from composed prompts.

Per coga's fail-loud principle this **must be a hard error at config load** —
assert the configured directory exists and is a directory, and reject absolute
paths and `..` escapes that leave the checkout. Keep the local-first fallback
for individual refs (that is how bundled batteries work); the thing that must
not be silent is a misconfigured *directory*. Decide explicitly whether
`coga validate` also carries this check, or whether config load alone is enough.

### Layout: there are two, and the anchor must work in both

Do **not** assume `Config.repo_root` is always the `coga/` directory. That is
true only in the **nested layout**. `find_repo_root` (`config.py:173`) accepts
any directory containing `coga.toml`, and
`src/coga/workspace_discovery.py:22-39` documents that the scan root is
recognized by its `coga.toml` alone, "whatever its name". The **root layout**,
where the coga root *is* the checkout root, is why `git.py:125-134` maintains
`_ROOT_LAYOUT_COGA_PATHS` at all. `config.py:131` (`repo_root.name == "coga"`)
is a display-name heuristic, not a layout guarantee.

So "resolve relative to the project root" is undefined in the root layout. Pick
an anchor that is well-defined in both — the recommended one is the **checkout
(git worktree) root**, which makes `docs/contexts` mean `<checkout>/docs/contexts`
under either layout — and require the resolved path to stay inside the checkout.
Write the chosen rule down in the config docs; it is the part a reader will get
wrong.

### The git sync fork — decide this before writing code

This is the ticket's real risk, not a line to update.

`_coga_state_pathspecs` (`src/coga/git.py:2144-2148`):

```python
def _coga_state_pathspecs(root: Path, coga_root: Path) -> list[str]:
    rel = _relative_to_root(root, coga_root)
    if rel != ".":
        return [rel]
    return list(_ROOT_LAYOUT_COGA_PATHS)
```

`_ROOT_LAYOUT_COGA_PATHS` — the tuple containing `"contexts"` at `git.py:128` —
is used **only in the root layout**. In the ordinary nested layout the pathspec
collapses to the single directory `coga`. The moment contexts move to
`docs/contexts/`, they fall entirely outside coga's git state sweep: agent edits
to contexts stop being committed and synced.

The same defect sits in authoring, which hardcodes `cfg.repo_root / root_name`:
`snapshot_authoring_files` (`authoring.py:47-56`, over `AUTHORING_SYNC_DIRS` at
`:23`) and `support_paths` (`authoring.py:95-99`).

There are only two ways out, and one of them is not acceptable here:

1. **Make the pathspecs config-derived** in *both* branches of
   `_coga_state_pathspecs` (and teach `_relative_to_root` to handle a contexts
   dir that is a *sibling* of `coga_root`, not a child), and do the same for the
   two authoring helpers. **This is the required direction.**
2. Constrain the setting to stay under `repo_root` — rejected, because it
   defeats the entire stated goal of reaching `docs/`.

### Config plumbing

`coga.toml` parsing is allowlist-based at two levels, and a new top-level table
needs the **section** allowlist, not the per-table key allowlists:

- Top-level sections: `_ALLOWED_SHARED_SECTIONS` at **`config.py:368-379`**,
  enforced by `_reject_unknown_sections`/`_reject_unknown_keys` at
  `config.py:430` (helper defined at `config.py:340`). A new `[layout]` table
  must be registered here or config load rejects it.
- Per-table keys: the `_ALLOWED_*_KEYS` frozensets at `config.py:386-413` —
  add one for the new table's keys.

`Config` is a frozen dataclass (`config.py:75`); store the **resolved** contexts
directory as a field so callers read it off `cfg` instead of recomputing the
join. This belongs in shared `coga.toml` (a repo-layout fact), not
`coga.local.toml`.

### Other consumers that assume the layout

Behavioral (code and executable agent instructions), beyond the resolver:

- `src/coga/commands/init.py:462` — `copy_fresh_templates` copies the packaged
  tree, which contains a real `contexts/` subtree, into the new `coga/`. So
  `coga init` *materializes* contexts at the hardcoded location; with the knob
  set in a scaffolded `coga.toml` a fresh repo diverges on day one.
- `src/coga/commands/init.py:220` — the AGENTS.md / CLAUDE.md body `coga init`
  **writes into every new repo** says "override them with local files under
  `coga/contexts/coga/`". Generated output, not documentation.
- `src/coga/commands/update.py:43-45` — `_LEGACY_COGA_GITIGNORE_ENTRIES`
  hardcodes `contexts/coga/architecture`, `contexts/coga/principles`,
  `contexts/coga/cli`.
- `.../bootstrap/skills/bootstrap/dream/scan/contract-audit/SKILL.md:16` —
  instructs an agent to audit `coga/contexts/**/SKILL.md`. A hardcoded glob in
  an executable instruction; a relocated dir makes the audit silently scan
  nothing.
- `src/coga/validate.py:755` and `src/coga/create.py:84` — ref resolution gates.

Deliberately **not** on this list: `ticket.py:45,170`, `create.py:187`,
`validate.py:94,587,591`, `recurring.py:712,863,937`, `config.py:534`. Those are
the ticket-frontmatter *key* named `contexts`, unrelated to the directory.

Grep `contexts` across `src/coga/` yourself before declaring this done; the list
above is a starting point, not a proof of completeness.

### Prose that becomes conditionally wrong

Roughly 25 sites across 20 files state "contexts live at `coga/contexts/`". They
need to say "the configured contexts directory, `coga/contexts/` by default":

`src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md:40,150,833`;
`.../contexts/coga/cli/SKILL.md:45`; `.../skills/bootstrap/ticket/SKILL.md:121,229`;
`.../skills/retro/done-ticket/SKILL.md:86,224,246,302`; `.../skills/browser/dochub/SKILL.md:16`;
live twins `coga/contexts/coga/architecture/SKILL.md:40,150,833` and
`coga/skills/browser/dochub/SKILL.md:16`; `src/coga/resources/retire.md:29`;
docs `docs/concepts.md:11,12,102,223,224`, `docs/development.md:100`,
`docs/getting-started.md:80`, `docs/cli-extension-audit.md:12,49`,
`docs/vision.md:8`, `docs/migrating-to-coga.md:73`.

Per `CLAUDE.md`, shipped contexts/templates exist in two copies — the live repo
copy under `coga/` and the packaged copy under
`src/coga/resources/templates/coga/` — and both must stay in sync. Note the
two-copy rule applies to `architecture` and `browser/dochub`; `bootstrap/ticket`
and `coga/cli` are **packaged-only** (there is no live `coga/skills/bootstrap/`),
so don't go looking for live twins of those.

If the prose sweep starts crowding out the code change, split it into a
follow-up ticket rather than shipping a half-done sweep — but say so on the
blackboard, don't just drop it.

### Coverage is the risk, so review for coverage

A diff review structurally cannot catch a *missed* consumer, because a missed
consumer produces no diff. At the `peer-review` step, do not just read the diff:
independently re-run the `contexts` grep across `src/coga/`, `docs/`, and both
template trees, and check the result against the audit lists above.

### The tradeoff this ticket accepts

Coga's posture is one obvious, legible layout. A tunable path adds a second
convention: every error message, doc, and skill naming a concrete path becomes
conditionally wrong, and validate/sync gain a dimension. Two cheaper
alternatives were considered and **rejected by the owner**: (1) leave the code
alone and add a `docs/contexts.md` index or symlink; (2) a one-time move to a
fixed root-level `contexts/`, no knob. The knob was chosen deliberately for
flexibility across repos. Given that, spend the effort on keeping the *default*
path indistinguishable from today and on making messages and docs **derive** the
path rather than hardcode it — that is what keeps the added dimension from
degrading legibility.

### Out of scope

- Permanently moving this repo's own contexts. Ship the knob; whether `coga`
  itself adopts it is a separate call.
- Any change to skills (`coga/skills/`), tasks, or workflows locations.
- Changing how the bundled `bootstrap/contexts/` batteries are resolved.

### Verification

`python -m pytest` and `coga validate --json` with the setting unset must be
unchanged from today.

Then exercise the non-default path for real, because a unit test will not touch
git sync or authoring: point *this* repo's `coga.toml` at a relocated contexts
directory, move the files, and confirm green on the full suite,
`coga validate --json`, `coga launch <slug> --prompt-report` (composition
resolves local contexts, not the packaged fallback), and a git state sweep that
actually picks up an edit to a relocated context file — **then revert**. Add an
end-to-end test covering a non-default directory (resolve → compose → validate →
sync); `example/coga/` is the seeded fixture for end-to-end behavior.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
pr: https://github.com/FastJVM/coga/pull/704
branch: layout-contexts-dir
worktree: /tmp/coga-layout-contexts-peer.YrKIJA

## Decisions (implement step)

- **Spelling:** `[layout] contexts = "docs/contexts"` — kept as proposed. A new
  top-level `[layout]` table registered in `_ALLOWED_SHARED_SECTIONS`, with its
  own `_ALLOWED_LAYOUT_KEYS = {"contexts"}`. Shared `coga.toml` only (repo-layout
  fact), not `coga.local.toml`.
- **Anchor: the git checkout root**, found by walking up from `repo_root` for a
  `.git` entry (dir or worktree file). This is the one anchor well-defined in
  both layouts, per the ticket's Context. `docs/contexts` therefore means
  `<checkout>/docs/contexts` under the nested *and* root layouts. Tradeoff
  accepted: a monorepo-nested coga (`tools/ops/coga/`) must spell the full
  `tools/ops/docs/contexts` rather than `docs/contexts`.
- **Fail loud at config load** when the key is set: reject absolute paths,
  reject `..`/symlink escapes out of the checkout, reject a missing or
  non-directory target, and reject the case where no `.git` checkout root
  exists to anchor against. Unset key = no checks run at all, so default
  behavior is byte-identical.
- **Config surface:** `Config.contexts_dir: Path | None = None` (the resolved
  override) plus a `contexts_root` property returning
  `contexts_dir or repo_root / "contexts"`. Optional-with-default keeps every
  existing `Config(...)` construction (`managed_skills.py`, `tests/test_git.py`)
  working untouched; callers read `cfg.contexts_root`.
- **Git sync fork (direction 1, as required):** `_coga_state_pathspecs` becomes
  config-derived — takes `cfg`, substitutes the real contexts path for the
  literal `"contexts"` entry in the root-layout tuple, and appends a sibling
  contexts pathspec in the nested layout when it is not already covered by the
  `coga` spec. Same for `authoring.snapshot_authoring_files` / `support_paths`,
  which now iterate resolved roots instead of `cfg.repo_root / name`.

## Verification (implement step)

Default unset — byte-identical, as required:

- `python -m pytest`: 1810 passed, 1 skipped, **3 failed**. All three fail
  identically on `main` at 3600a6fe (verified by running them against main's
  `src/`): `test_autoclose.py::test_recipe_preflights_live_summary_before_closing`
  and two `test_recurring.py` malformed-sweep-ledger tests. Pre-existing and
  unrelated to this change.
- `coga validate --json` on `example/coga/` and on this repo, run against
  main's `src/` and the branch's `src/`: **identical output** modulo the
  `generated_at` timestamp.

Non-default path, exercised for real against this repo (contexts moved to
`docs/contexts/`, `[layout] contexts = "docs/contexts"`):

- `coga validate --json`: **identical** to the default-layout run — every
  context ref still resolves.
- `resolve_context_path`: `dev/code`, `coga/architecture`, and
  `coga/principles` all resolved to `docs/contexts/...`, **not** to the
  packaged bootstrap copies. This is the silent-corruption case the ticket
  called out, and it is covered.
- `coga launch <slug> --prompt-report`: composed the `ticket_context`
  `dev/code` layer at 8.4 KiB from the relocated directory.
- git state sweep: `_coga_state_pathspecs` returned `['coga', 'docs/contexts']`
  and `_changed_paths_under` picked up an edit to
  `docs/contexts/coga/codebase/SKILL.md`. The sibling contexts directory is
  inside the sweep.

Then reverted. See the incident below.

## Incident — the verification recipe lands the relocation on `main`

**Recording this because the ticket's own "Verification" section tells the next
agent to do exactly what caused it.** "Point *this* repo's `coga.toml` at a
relocated contexts directory, move the files, and confirm green on
... `coga validate --json`, `coga launch <slug> --prompt-report` ... — **then
revert**" cannot be followed as written. Every Coga CLI command fires the
catch-all `sync_coga_state` sweep at its dispatch boundary, and that sweep is
precisely the machinery this ticket widens. So the *first* `coga validate` run
after the relocation committed the move plus the `[layout]` key as
`e93307ac "Sync coga state"` and landed it on `origin/main` — and the pull-back
then relocated the primary checkout's working tree too. There is no window in
which the experiment is only local; the revert step comes too late by design.

Recovery, already done: `12ff7c1a Revert "Sync coga state"` on `main`, pushed.
`git diff 3600a6fe..12ff7c1a -- coga/ docs/contexts src/coga/resources` is
empty, so main's content is exactly what it was before. The feature branch was
reset back to `3600a6fe` and the relocation undone in the worktree, leaving only
the intended change. No history was rewritten; the accident and its revert are
both visible in `main`'s log.

Next time, run that experiment with `[git] enabled = false` in
`coga.local.toml`, or in a throwaway clone — never in a checkout whose sweep
can reach the real remote. Worth folding into the ticket's Verification section
before anyone repeats it.

## What changed

Code:

- `config.py` — new `[layout]` table (`_ALLOWED_SHARED_SECTIONS` +
  `_ALLOWED_LAYOUT_KEYS`), `_parse_layout` validator, `find_checkout_root`,
  `Config.contexts_dir` field + `Config.contexts_root` property.
- `paths.py` — `context_path` reads `cfg.contexts_root`; dead `context_dir`
  deleted (no callers, per the ticket).
- `git.py` — `_coga_state_pathspecs(root, cfg)` is config-derived in both
  branches, with a `_pathspec_covers` helper. Nested layout appends the
  contexts spec only when `coga` does not already cover it; root layout
  *substitutes* the real path for the literal `"contexts"` entry, so a vacated
  default directory stops being swept as Coga state.
- `authoring.py` — new `authoring_sync_roots(cfg)`; `snapshot_authoring_files`
  and `support_paths` resolve off config instead of `cfg.repo_root / name`.

Tests: `tests/test_layout_contexts.py` (new end-to-end: resolve → create →
compose → validate → sync against a relocated directory, plus a default-layout
control), plus focused cases in `test_config.py` (9), `test_git.py` (2, one per
layout), `test_authoring.py` (1), `test_paths.py` (1 new + 2 stubs updated for
the new `contexts_root` accessor).

Docs/contexts: a new "The contexts directory is relocatable" section in the
`coga/architecture` context (both copies) documenting the checkout-root anchor
and the fail-loud rules; `[layout]` added to its unknown-key allowlist
paragraph; `docs/concepts.md` gained the human-facing explanation.

## Deliberately deferred — prose sweep follow-up

The ticket allows splitting the ~25-site prose sweep. I did the sites where
being wrong *changes behavior*, and deferred the rest. Done here:

- Executable agent instructions whose hardcoded globs would silently scan
  nothing after a relocation: `bootstrap/dream/scan/contract-audit/SKILL.md`,
  `bootstrap/ticket/SKILL.md` (both the `ls` enumeration and the new-context
  path), `retro/done-ticket/SKILL.md`, `browser/dochub/SKILL.md`, Dream's
  `knowledge-scan`, the onboarding workflow, and the packaged `coga-build`
  ticket.
- General-rule statements: `architecture` (3 sites), `principles`,
  `codebase`, `sync`, packaged `coga/cli`, `docs/concepts.md` local-first
  paragraph, and the AGENTS.md/CLAUDE.md guide generated by `coga init`.

Deferred to a follow-up ticket, with reasons:

- `docs/migrating-to-coga.md:12,73` — a historical rename table describing what
  the v1→v2 migration did. Accurate as history; rewording it would falsify it.
- `docs/concepts.md:11,223`, `docs/development.md:100`,
  `docs/cli-extension-audit.md:12`, `docs/cli-extension-external-surface.md:6`,
  `README.md:70-71` — these link to or name *this repo's own* context files at
  their real current path. They are correct, not conditionally wrong, unless
  and until coga adopts the knob itself (explicitly out of scope here).
- `src/coga/commands/update.py:43-45` — `_LEGACY_COGA_GITIGNORE_ENTRIES` are
  literal historical strings older versions wrote into `coga/.gitignore`, used
  only to dedupe them away. Layout-independent history; changing them would
  break the cleanup.
- `coga/contexts/coga/project-stage/SKILL.md:21` — "Moving `contexts/` to live
  next to tasks would be fine if..." is live product posture that this ticket
  partly answers. It needs an owner's judgment call, not a mechanical reword.

## Peer review findings

`codex review --base main` reported eight release-blocking coverage/safety gaps;
all are fixed on the branch:

- unsafe broad roots are rejected, including the checkout root, a root that
  contains the Coga root, symlinked components, and Git pathspec metacharacters;
- the dispatch-boundary sweep reloads live config, so an agent relocation made
  during the command cannot publish `coga.toml` without its new context tree;
- relocation sync finds the last historical tree where the former root was
  active, carries its tracked deletions even when config landed earlier, and
  does not adopt unrelated files later left there;
- stranded-product detection excludes both the current and control-base
  context roots when the feature branch itself contains a relocation;
- configured roots and real context files must be Git-reproducible, while a
  contexts-local `.gitignore` keeps `_template` scaffolding ignored after a
  manual move;
- `coga uninstall` resolves and removes an external configured contexts tree
  before deleting `coga.toml`, while broken config warns and avoids guessing a
  destructive target; and
- the canonical sync/architecture contracts and generated orientation guide
  now describe the config-derived state boundary and lifecycle behavior.

The independent coverage grep across `src/coga/`, `docs/`, the live Coga tree,
and packaged templates additionally caught the Dream knowledge scan,
onboarding workflow, packaged `coga-build` ticket, `principles`/`codebase`
copies, and uninstall lifecycle. Remaining concrete `coga/contexts` strings are
explicit default examples, links to this repo's current files, or historical
migration/cleanup literals.

The branch was unconditionally rebased onto `origin/main` at `cc0d7b72`. Review
fixes are committed as `49d2f395` and `30ce90e0`; the clean branch was pushed
to `origin/layout-contexts-dir`.

## Verification (peer-review step)

- `.venv/bin/python -m pytest`: **1921 passed**.
- `env -u SLACK_WEBHOOK_URL coga validate --json` in `example/coga/`: **3 ok,
  no issues**.
- Repository-root `coga validate --json` still reports the existing unrelated
  draft-ticket errors recorded on `main`; the implement step already compared
  default-layout output against `main` and found it identical modulo timestamp.
- `git diff --check`: clean; live/packaged-copy and executable-instruction
  coverage tests pass inside the full suite.

## PR

Summary: Add `[layout] contexts` as a checkout-root-relative, fail-loud way to
relocate human-authored contexts, and carry that configured root through
resolution, composition, validation, authoring, init/uninstall, Git sync, and
the shipped behavioral guidance. The default layout remains unchanged.

Test plan: `python -m pytest` (1921 passed); `coga validate --json` on the seeded default-layout fixture (3 ok, no issues); relocated-context end-to-end and Git-history regressions are included in the suite.
