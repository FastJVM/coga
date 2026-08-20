---
slug: move-cogacontext-to-roodoc-so-its-easier-for-human
title: move cogacontext to roodoc so its easier for human
status: draft
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
  - dev/code
skills: []
workflow: code/with-review
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
