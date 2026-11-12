---
title: Decide the Dream scans' corpus and fix the Known corpus limitation
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills:
    - code/peer-review
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
step: 3 (open-pr)
agent: claude
launch_generation: c3d02f4d-6574-4cac-98b4-118b353aaefe
---

## Description

Filed by Dream run recurring/dream, period 2026-W46 (run 20261112T051938Z), Phase 6 disposition. Finding from Phase 2 (ks-22, stale) and Phase 3 (ca-07, drift). Needs a human corpus decision, so it is a draft rather than a proposal PR.

Target: src/coga/resources/templates/coga/recurring/dream/ticket.md, section 'Known corpus limitation'. It says both scans exclude package-backed bootstrap/skills/** and that the knowledge scan owns tickets and coga/workflows/**. The scan skills (bootstrap/skills/bootstrap/dream/scan/knowledge-scan and contract-audit) instead tell coga-source runs to read src/coga/resources/templates/coga/bootstrap/{contexts,skills,workflows}/** and templates/coga/recurring/**. The 2026-W46 run followed the template body (the dispatch contract) and excluded bootstrap/skills/**, so ~300 KB of packaged skills went unscanned. Decide: include bootstrap/skills (sizing ~2 more shards per scan) and delete the limitation paragraph, or keep the exclusion and edit both scan skills to match. Then fix the losing side.

## Context

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: coga/decide-the-dream-scans-corpus

## Decision

Include package `bootstrap/skills/**` in both Dream scans; delete the
template's "Known corpus limitation" paragraph (the losing side). Reasons:
- The owner already decided it: the 2026-10-14 monthly-audit request (see
  commit 5c2caadca, ticket body) says Dream "should also lift the known
  corpus limitation that both scans exclude bootstrap/skills/**".
- The dream template's own Phase-scan step 2 says "In the Coga source repo
  apply no exclusion", and scan-protocol Rule B says "In the Coga source repo
  every Coga-owned file is in the corpus" — the paragraph contradicts both.
- After the package-definition cutover there is no live copy of packaged
  skills, so excluding them leaves ~300 KB of shipped skills with no scan.
- The paragraph's "knowledge scan owns tickets and coga/workflows/**" is also
  stale: the knowledge-scan skill adds package contexts/skills/workflows and
  recurring/** in coga-source runs.
Cost: ~303 KB of packaged skill Markdown ≈ 2 more 150 KB shards per scan,
within existing shard mechanics.

## Handoff (implement)

- Commit ac0591de3 on `coga/decide-the-dream-scans-corpus` (pushed) deletes the
  "### Known corpus limitation" section from
  `src/coga/resources/templates/coga/recurring/dream/ticket.md`. No scan-skill
  edit was needed: knowledge-scan and contract-audit already include the
  package `bootstrap/{contexts,skills,workflows}/**` and `recurring/**` in
  coga-source runs, so they are the winning side and own the corpus definition.
- No other topic, test, or README restates the exclusion (grep for
  "corpus limitation" / exclusion of bootstrap/skills across src, tests,
  docs/contexts, README.md found nothing).
- Pre-existing failures on origin/main (not caused by this change, reproduced
  on detached origin/main 46a376634): `test_packaging.py::test_context_navigation_has_no_broken_links`
  and both `test_git.py::test_final_package_edits_never_escape_a_mutating_cli_sweep`
  params. All come from README.md linking the deleted ticket
  `coga/tasks/document-the-remedy-for-a-bloated-blackboard-sibli.md`; already
  referenced by `make-retro-check-inbound-doc-links-before-deleting` and
  `correct-the-coga-workflows-topic-s-claim-that-init`.
- Next run's Dream should see ~2 more shards per scan; no code limits shard count.
- System `python` lacks `tomlkit`; tests ran with `.venv/bin/python`.

## Peer review

Codex direct independent review **completed** with no findings or must-fix
changes. Implement authorship is Claude per the implement handoff and the
commit's Claude Opus 5.5 co-author trailer; this fresh Codex session reviewed
the change rather than implementing it.

- Final reviewed head: `0d75ea99216f8a262a7561854416d3c209e502e4`.
  Reviewed base: `082c2fd3f4016812cd3e0eb9f2e2fb4481dc1225`.
- Read the eight-line deletion, surrounding Dream dispatch/index/sharding
  instructions, both scan skills, and scan-protocol Rules A/B. Both skills
  explicitly include packaged skills in source-repo scans; deleting the
  contradictory summary leaves one consistent corpus contract. Verified the
  earlier owner request in commit `5c2caadca`'s monthly-audit ticket body.
- No rendered UI or terminal interaction changed. A live Dream run was not
  performed; the next run must confirm actual scan coverage. Packaged skill
  Markdown totals 302,878 bytes across 31 files, consistent with the estimate.
- Rebased before review and full-suite testing. The final freshness fetch
  found three newer commits touching only another ticket and `coga/log.md`;
  rebased again and completed direct review on the final head/base above.
  Verified `src`, `tests`, `docs`, `README.md`, `AGENTS.md`, and `pyproject.toml`
  are identical to the full-suite-tested revision. Kept that receipt
  historical and ran the 22 Dream template tests on the final head rather
  than repeating the twelve-minute full suite for unrelated ticket/log state.
- Full suite: 3 failed, 4763 passed, 33 skipped on Linux x86_64, Python
  3.12.12. All three failures are the same missing README ticket link recorded
  by implement: navigation fails directly and inside both publication-test
  parameters. README and those tests are unchanged from the reproduced main
  baseline `46a376634`. Full output: `/tmp/coga-dream-peer-review-pytest.log`.
- Final branch is committed and pushed with one implementation commit ahead
  of main. Manual checkout returned to main. PR recommendation is `deep`
  because failed checks and the historical full-suite receipt must remain
  visible; the change itself has no unresolved review findings.

## PR

```yaml
title: Include packaged skills in Dream's scan corpus
author: claude
author_evidence: Implement handoff identifies a Claude Code session using claude-opus-5-5; the implementation commit also carries a Claude Opus 5.5 co-author trailer.
head: 0d75ea99216f8a262a7561854416d3c209e502e4
base: 082c2fd3f4016812cd3e0eb9f2e2fb4481dc1225
depth: deep
rationale: Bounded eight-line prose deletion with completed independent review and no findings, but the full suite has three pre-existing failures and its receipt predates the final unrelated ticket/log-only rebase.
implementation: Deletes the dream template's "Known corpus limitation" section so the template's own "apply no exclusion" rule, scan-protocol Rule B and the knowledge-scan and contract-audit skills consistently put package bootstrap/skills/** in both scans for the Coga source repo.
deviations: None. The scan skills already matched the chosen corpus, so only the template changed.
limitations: Not exercised by a live Dream run. Including the skills adds about 303 KB, roughly two more shards per scan. The full-suite receipt is historical after a final rebase that changed only another ticket and the log; Dream template checks passed on the final head.
files:
  src/coga/resources/templates/coga/recurring/dream/ticket.md: Remove the stale corpus-limitation section that excluded packaged skills from both scans.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: 0d75ea99216f8a262a7561854416d3c209e502e4
  base: 082c2fd3f4016812cd3e0eb9f2e2fb4481dc1225
  detail: Codex direct independent review completed on the final diff with no findings. Checked the dispatch contract, both scan skills, protocol ownership and sharding rules, and the earlier owner request. No interactive UI surface changed.
checks:
  - command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q
    status: failed
    head: 4bbeec862ef31638955054e7b8bf91674e6bd0d4
    base: 805fbf0493fa3c31626ce501ae1b84d8abba81cb
    detail: 3 failed, 4763 passed, 33 skipped in 723.42s on Linux x86_64 with Python 3.12.12. Navigation and both final-package-publication parameters fail on the existing README link to deleted document-the-remedy-for-a-bloated-blackboard-sibli.md. Implement reproduced these on main 46a376634; README and the affected tests are unchanged. Historical receipt before final ticket/log-only rebase.
  - command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q tests/test_dream_worker_templates.py
    status: passed
    head: 0d75ea99216f8a262a7561854416d3c209e502e4
    base: 082c2fd3f4016812cd3e0eb9f2e2fb4481dc1225
    detail: 22 passed in 0.21s on the final head. No source, test, or governing documentation changed in the final rebase; only another ticket and coga/log.md changed, so the full suite was not repeated.
  - command: git diff --check
    status: passed
    head: 0d75ea99216f8a262a7561854416d3c209e502e4
    base: 082c2fd3f4016812cd3e0eb9f2e2fb4481dc1225
    detail: No whitespace errors in the final branch diff.
```
