---
title: make dream run correctly under codex
status: in_progress
owner: nicktoper
contexts:
- dev/code
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (design)
agent: claude
---

## Description

Selecting `codex` for Dream is a config/flag matter (`coga dream --agent codex`
and `coga recurring --agent codex` already exist; a repo-wide default key is
ticket `dream-should-be-able-to-use-codex-instead-of-claud`). Whether Dream
then *works* under codex is untested: the Dream template has only ever run
under `claude`, and it leans heavily on delegating to subagents. Find what
breaks or degrades when Dream runs under `codex`, and fix the template/skills so
a codex run is as complete as a claude run.

Done when: a real `coga dream --agent codex` run (or the closest reproducible
equivalent the design step agrees on) completes every phase — validate-drift,
knowledge scan, contract audit, Retro pass, execute half — with its findings
routed to durable artifacts (PRs, draft tickets, markers) the same way a
claude run routes them; any agent-specific instruction in the Dream template or
its phase skills is either made agent-neutral or given a documented codex path;
the observed gaps and their fixes are recorded; `python -m pytest` passes and
`coga validate --json` is clean.

## Context

**Where Dream's instructions live.** The dispatch contract is the body of
`coga/recurring/dream/ticket.md` (packaged twin under
`src/coga/resources/templates/coga/`; byte-identity enforced by
`tests/test_packaging.py`). The phase skills ship packaged-only under
`src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/` (e.g.
`scan/knowledge-scan`, `scan/contract-audit`, `scan/scan-protocol`), plus
`retro/done-ticket`.

**Subagent dependence is the main risk.** The template's wording is already
agent-neutral ("delegate each shard to a subagent"), but the mechanics assume a
capable subagent primitive: Phases 2–3 shard the corpus into many subagents
whose result arrives only in their final message (the corpus is larger than one
agent can hold), and the Retro pass delegates to one subagent in an isolated
`git worktree add` checkout with an exact cwd. Establish first what codex
offers here (native subagents, `codex exec` sub-sessions, or nothing) and how
reliably it returns a final message — the design step should decide between
adapting the instructions and providing a codex-specific delegation recipe.
The prior done ticket `dream-phases-2-3-cannot-complete-scan-subagents-re`
documents how Phases 2–3 fail when shard subagents stop early; read it for the
failure signatures to check for.

**Agent config.** `[agents.codex]` in `coga/coga.toml` has `cli = "codex"`,
`file = "AGENTS.md"`, and a `discussion` flag but no `name_flag` or
`session_id_flag` — so session naming and usage-transcript recovery may differ
from claude runs; note any effect on Dream's run record, don't necessarily fix.

**Out of scope.** The default-agent config key (the sibling ticket above). REM
or other recurring templates — fix only what Dream needs, though note any
shared skill fix that obviously benefits them.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
