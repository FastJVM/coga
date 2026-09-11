---
title: 'Installer-managed skills: the local-adaptation guard misses github-backed
  packs'
status: draft
owner: nicktoper
agent: claude
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
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
step: 1 (implement)
---

## Description

Two facts about the seven installer-managed `google-agents-cli-*` packs that
no context records, both of which change how a reader should treat those trees.

**1. The local-adaptation guard covers url-sourced skills only.** In
`src/coga/skill_manager.py`, `installed_digest` is computed only when
`metadata.get("source_type") == "url"`, so the `dirty_existing_skill` refusal on
install ("has local adaptations; rerun with --force to overwrite") and the
update-side `skipped-local-adaptation` / `conflict` results in
`_update_url_skill_dir` apply to url-sourced skills alone. Every entry in
`src/coga/resources/managed-skills.toml` is `source_type = "github"`, and
`_update_gh_backed_skills` simply delegates `gh skill update --dir <root> --all`
with no digest comparison and no Coga-side guard. So a local edit to any
`google-agents-cli-*` file is silently overwritable by the weekly skill-update
job, while the identical edit to a url-sourced skill raises a conflict. Neither
`coga/contexts/coga/codebase/SKILL.md` nor `coga/contexts/coga/extension-model/SKILL.md`
records the asymmetry.

**2. Nothing records why those packs are in this repo at all.** They are ~250 KB
of Google Cloud / ADK agent-development guidance, all seven materialized into
`coga/.agent-skills/` — the view Claude Code and Codex are pointed at — so every
session in this repo carries their descriptions, one of which
(`google-agents-cli-workflow`) self-describes as "Always active". Yet no ticket,
context, recurring job or workflow in the repo does ADK work: a case-insensitive
sweep of `coga/tasks`, `coga/contexts`, `coga/recurring` and `docs` for ADK or
agents-cli turns up only provenance and cleanup tickets about managing the packs
themselves. The presumable reason — dogfooding `coga skill install` / `update`
against a real remote source — is a good one and is written down nowhere, so a
future cleanup pass could read them as dead weight and delete the only
end-to-end exercise of that path.

## Context

Both belong in the installer-managed bullet of
`coga/contexts/coga/codebase/SKILL.md` (with its enforced packaged twin):

- state that installer-managed github-backed skills are read-only in-repo —
  fix them upstream or convert to a hand-vendored namespaced copy with
  attribution — because Coga's local-adaptation guard does not cover that path;
- state why the packs are kept, so their purpose survives a cleanup sweep.

A third, closely related item is already routed into a Dream proposal PR this
run (the counter-instruction that a pack's own `uvx google-agents-cli setup`
refresh instructions are inert in a Coga repo). Check that PR before editing the
same bullet, and fold rather than conflict.

Verify the `skill_manager.py` behavior yourself before writing — describe what
the code does, not this summary.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
