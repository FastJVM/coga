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

Scope is **contexts only**. Skills stay where they are — they are process
knowledge for agents and are not meant to be hand-edited by humans, so they get
no knob.

Done looks like: a new `coga.toml` setting points the contexts directory
somewhere else; `coga launch` composes from it, `coga validate` resolves refs
against it, `coga ticket`/`coga create` accept refs from it, and the
authoring/git sync paths track it. Local-first resolution over the bundled
`bootstrap/contexts/` batteries is unchanged. Defaults are unchanged, so a repo
that sets nothing keeps working exactly as today.

## Context

### Where the path is built today

`src/coga/paths.py:120` and `:124` are the *only* two places the local contexts
path is constructed:

```python
def context_path(cfg, ref):  return cfg.repo_root / "contexts" / ref / "SKILL.md"
def context_dir(cfg, ref):   return cfg.repo_root / "contexts" / ref
```

Everything that resolves a context ref goes through `resolve_context_path`
(`paths.py:136`), which tries the local path first and falls back to
`bootstrap_context_path` (the packaged batteries under
`src/coga/resources/templates/coga/bootstrap/contexts/`). That local-first
fallback must not change — only the local half moves.

### The repo_root gotcha

`Config.repo_root` is the **`coga/` directory**, not the project root
(`config.py:131` keys off `repo_root.name == "coga"` to derive the project
name). So `docs/` is a *sibling* of `repo_root`, not a child. A knob whose whole
point is to reach `docs/contexts/` therefore has to resolve relative to the
project root (or accept an explicit relative-to-project path), not blindly join
onto `repo_root`. Decide and document which anchor the setting uses, and reject
absolute paths and `..` escapes that leave the project.

### Config plumbing

`coga.toml` parsing is allowlist-based — unknown keys are rejected, so the new
setting must be registered, not just read. See the `_ALLOWED_*_KEYS` frozensets
around `config.py:386-413` and `_reject_unknown_keys`. `Config` is a frozen
dataclass (`config.py:75`); add the resolved directory as a field there so
callers read it off `cfg` rather than recomputing the join. Shared `coga.toml`
is the right home (it is a repo-layout fact, not machine-specific), so it does
not belong in `coga.local.toml`.

### Other places that assume the layout

Changing `paths.py` alone is not enough. At minimum, audit and update:

- `src/coga/authoring.py:23` — `AUTHORING_SYNC_DIRS = ("tasks", "contexts", "skills")`
  and the `for root_name in ("contexts", "skills")` loop at `:95`.
- `src/coga/git.py:128` — the tracked-path list.
- `src/coga/validate.py` — context ref resolution (`:755`) and any
  directory-walking that enumerates contexts.
- `src/coga/create.py:84` — `resolve_context_path` gate on unknown contexts.
- Error-message prose that hardcodes the old path, e.g. `config.py:579` points
  at `coga/contexts/coga/architecture/SKILL.md`.

Grep for the string `"contexts"` across `src/coga/` before declaring this done;
the list above is a starting point, not a proof of completeness.

### Docs and templates that state the convention

Per `CLAUDE.md`, shipped contexts/templates exist in two copies — the live repo
copy under `coga/` and the packaged copy under
`src/coga/resources/templates/coga/`. Both need to stay in sync. Any doc,
context, or skill that tells a reader "contexts live at `coga/contexts/`" now
needs to say "at the configured contexts directory, `coga/contexts/` by
default" — including the `bootstrap/ticket` skill's own survey step, which
tells the bootstrap agent to `ls coga/contexts/*/`.

### The tradeoff this ticket accepts

Coga's stated posture is one obvious, legible layout. A tunable path adds a
second layout convention: every error message, doc, and skill that names a
concrete path becomes conditionally wrong, and validate/sync gain a dimension.
Two cheaper alternatives were considered and **rejected** by the owner:

1. Leave the code alone and add a `docs/contexts.md` index or symlink.
2. A one-time move to a fixed root-level `contexts/`, no knob.

The knob was chosen deliberately for flexibility across repos. Given that, the
implementation should spend its effort on keeping the *default* path
indistinguishable from today and on making messages/docs derive the path rather
than hardcode it — that is what keeps the added dimension from degrading
legibility.

### Out of scope

- Moving this repo's own contexts. Ship the knob; whether `coga` itself sets it
  is a separate call.
- Any change to skills (`coga/skills/`), tasks, or workflows locations.
- Changing how the bundled `bootstrap/contexts/` batteries are resolved.

### Verification

`python -m pytest`, plus `coga validate --json` both with the setting unset
(default path) and with it pointed at a relocated directory. Add a test that
covers a non-default contexts directory end-to-end (resolve → compose →
validate); `example/coga/` is the seeded fixture for end-to-end behavior.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
