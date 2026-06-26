---
slug: v2/audit-rules-md-usage-across-relay-and-decide-wheth
title: Audit rules.md usage across relay and decide whether to keep, gut, or remove
  it
status: draft
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
---

## Description

Audit how `relay-os/rules.md` (the "Global rules" prompt layer) is actually
used, then decide whether to keep it as-is, rewrite it with rules this repo
genuinely wants, or remove it entirely.

### Why this exists

`relay-os/rules.md` was not authored as considered policy. It is the default
file shipped in the `relay init` template (originated in the v1 POC) and was
committed wholesale in `ea7e94c` "Bootstrap relay-os/ for dogfooding". Its
current contents are boilerplate: "Never commit secrets / Always test before
merging / Ask before touching production data." The owner wants to audit
whether those rules earn their place in every composed prompt.

### Known facts (verified — do not re-derive)

- `rules.md` is composed as layer 3 ("Global rules") by `compose.py` and is
  inlined into every non-script task prompt by `relay launch`.
- It is **optional**: `compose.py:186` only appends the layer
  `if rules.is_file()`, so deleting or emptying the file degrades gracefully
  — no fail-loud, no broken composition.
- Path resolution: `paths.py` `rules_path()` → `<repo_root>/rules.md`.
- A packaged template copy lives at
  `src/relay/resources/templates/relay-os/rules.md`; `relay init --update`
  leaves the live `rules.md` untouched (it is user-owned), so live and
  template copies can legitimately diverge.

### Work

1. Confirm the composition behavior above (read `compose.py`, `paths.py`,
   and any tests touching the global-rules layer).
2. Judge each of the three current rules against the relay principles —
   does each one make the human think better, or is it noise that bloats
   every prompt? Cross-check against `relay/principles` and whether the
   rule is already enforced elsewhere (e.g. "always test before merging"
   vs. the dev workflows' test steps).
3. Recommend one of: **keep** (and why each rule earns its slot),
   **rewrite** (propose the rules this repo actually wants), or **remove**
   (delete `relay-os/rules.md`; decide whether the packaged template default
   also changes).
4. Write the recommendation to the blackboard. If the decision is a concrete
   edit/removal, that is a small follow-on change — flag whether it warrants
   its own PR or rides along here.

### Acceptance

- Blackboard carries a clear keep / rewrite / remove recommendation with
  per-rule reasoning grounded in `relay/principles`.
- The composition + optionality facts are confirmed (not assumed).
- If the human approves a change, the live `relay-os/rules.md` (and,
  separately considered, the packaged template) reflect it.

### Note

Workflow intentionally left unset — this is audit-first; pick a workflow
(or just `relay mark done` if it stays report-only) once the audit scope
is settled. Sibling ticket
`dev-loop-git-hygiene-lift-sync-with-main-into-code` deliberately does NOT
touch `rules.md`; keep the concerns separate.

## Context

- `src/relay/compose.py` (~line 184) — the global-rules composition layer.
- `src/relay/paths.py` — `rules_path()` resolution.
- `relay-os/rules.md` — the file under audit.
- `src/relay/resources/templates/relay-os/rules.md` — packaged default.
- `relay/principles` context — the filter for whether each rule earns its
  place.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
