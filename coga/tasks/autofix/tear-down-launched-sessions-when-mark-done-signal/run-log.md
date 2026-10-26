# Recurring sweep — 2026-10-26 10:16:08

- repo: coga
- mode: bare sweep
- templates scanned: 9
- tasks run: 9
- problems: 1

## Scan

```
address-pr-comments  ready (Mon 07:00)          launch
autoclose-merged     ready (Mon 08:00)          launch
blocker-reminders    ready (Mon 10:00)          launch
dream                ready (Mon 09:00)          launch
phone-home           ready (Mon 07:00)          launch
resolve-conflicts    ready (Mon 08:00)          launch
skill-update         ready (Mon 09:00)          launch
usage-report         ready (Mon 08:00)          launch
recurring/upstream-coga (clone): ran this period here
```

## Task outcomes

### recurring/address-pr-comments — completed

- template: `address-pr-comments`
- ticket status after the run: done

What the run wrote to its blackboard:

```


The blackboard is a notepad to be written to often as the human and agent works through a task.
```

### recurring/phone-home — completed

- template: `phone-home`
- ticket status after the run: done

What the run wrote to its blackboard:

```


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Phone home

Run 6: capture suppressed; receipt suppressed.
```

### recurring/autoclose-merged — completed

- template: `autoclose-merged`
- ticket status after the run: done

What the run wrote to its blackboard:

```


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Autoclose Sweep: retire follow-ups

Generated: 2026-10-26T17:18:33+00:00
Task: `recurring/autoclose-merged`

1 checkout(s) disposed of under the shared retire proofs (worktree removed, local and remote branch deleted where each proof admitted it):

- `windows-native/01-core-port-cli-and-test-suite-pass-on-native-window` "Core port: CLI and test suite pass on native Windows": branch `coga/windows-native-01-core-port-cli-and-test-suite-p-2e174f`

2 checkout(s) preserved — a proof refused; each stays on the worklist until a human acts:

- `blocks/06-collapse-state-publication-into-one-user-topic` (worklist backlog): branch `blocks-06-collapse-state-publication` — local 'blocks-06-collapse-state-publication' has unmerged work and no merged PR vouching for it — left in place. (`coga retire blocks/06-collapse-state-publication-into-one-user-topic`)
  - Branch cleanup: local 'blocks-06-collapse-state-publication' advanced past the merged PR head 55c24d2fe48f — preserving it.
  - Branch cleanup: local 'blocks-06-collapse-state-publication' has unmerged work and no merged PR vouching for it — left in place.
  - Branch cleanup: skipping remote origin/blocks-06-collapse-state-publication because the local branch remains.
  - Branch sweep: 'blocks-06-collapse-state-publication' has merged PR #1086 at 55c24d2fe48f, but the ref carries commits touching coga/skills/coga/ticket/finalize/SKILL.md, docs/README.md, docs/contexts/coga-dev/codebase/SKILL.md (+29 more) — left in place.
  - Branch cleanup: local 'blocks-06-collapse-state-publication' has unmerged work and no merged PR vouching for it — left in place.
- `blocks/08-trim-launch-prompt-and-workflow-topics` (worklist backlog): branch `coga/blocks-08-trim-launch-prompt-workflow` — local 'coga/blocks-08-trim-launch-prompt-workflow' has unmerged work and no merged PR vouching for it — left in place. (`coga retire blocks/08-trim-launch-prompt-and-workflow-topics`)
  - Branch cleanup: local 'coga/blocks-08-trim-launch-prompt-workflow' advanced past the merged PR head 61537ef1eed8 — preserving it.
  - Branch cleanup: local 'coga/blocks-08-trim-launch-prompt-workflow' has unmerged work and no merged PR vouching for it — left in place.
  - Branch cleanup: skipping remote origin/coga/blocks-08-trim-launch-prompt-workflow because the local branch remains.
  - Branch sweep: 'coga/blocks-08-trim-launch-prompt-workflow' has merged PR #1089 at 61537ef1eed8, but the ref carries commits touching coga/skills/code/open-pr/SKILL.md, docs/README.md, docs/contexts/coga-dev/codebase/gotchas/SKILL.md (+36 more) — left in place.
  - Branch cleanup: local 'coga/blocks-08-trim-launch-prompt-workflow' has unmerged work and no merged PR vouching for it — left in place.

## Autoclose Sweep: unanswered review threads

Generated: 2026-10-26T17:18:34+00:00
Task: `recurring/autoclose-merged`

1 auto-closed ticket(s) merged with a review thread that is unresolved, not outdated, and got no reply. Autoclose only names them — reading, resolving, or replying stays with a human:

- `windows-native/01-core-port-cli-and-test-suite-pass-on-native-window` "Core port: CLI and test suite pass on native Windows" — PR #1093:
  - `src/coga/branchsweep.py:1443` by @chatgpt-codex-connector: "P2 Badge Preserve non-UTF-8 Git ref and worktree names" — https://github.com/FastJVM/coga/pull/1093#discussion_r4362623990
```

### recurring/resolve-conflicts — completed

- template: `resolve-conflicts`
- ticket status after the run: done

What the run wrote to its blackboard:

```


The blackboard is a notepad to be written to often as the human and agent works through a task.
```

### recurring/usage-report — completed

- template: `usage-report`
- ticket status after the run: done

What the run wrote to its blackboard:

```


The blackboard is a notepad to be written to often as the human and agent works through a task.
```

### recurring/skill-update — completed

- template: `skill-update`
- ticket status after the run: done

What the run wrote to its blackboard:

```
[... truncated ...]
 human and agent works through a task.

## Skill Update

Generated: 2026-10-26T17:20:59+00:00
Command: `/home/n/.local/share/uv/tools/coga/bin/python -m coga.cli skill update --all --json --pr --pr-title 'Update Coga-managed skills'`
Task: `recurring/skill-update`

Result: 22 skill(s): 7 updated, 0 need follow-up, 15 skipped.
PR: https://github.com/FastJVM/coga/pull/1098

### Updated

- `google-agents-cli-adk-code`: `updated` (github) - updated by gh skill (google/agents-cli) aef7255c > 876b67f4 [v1.11.0]
- `google-agents-cli-deploy`: `updated` (github) - updated by gh skill (google/agents-cli) 3b814a38 > 3fd11023 [v1.11.0]
- `google-agents-cli-eval`: `updated` (github) - updated by gh skill (google/agents-cli) d8f4ffbb > 0f739661 [v1.11.0]
- `google-agents-cli-observability`: `updated` (github) - updated by gh skill (google/agents-cli) b6a9a90f > 15758239 [v1.11.0]
- `google-agents-cli-publish`: `updated` (github) - updated by gh skill (google/agents-cli) 5c2dd447 > 1f0af76b [v1.11.0]
- `google-agents-cli-scaffold`: `updated` (github) - updated by gh skill (google/agents-cli) 545a9274 > ccb2058b [v1.11.0]
- `google-agents-cli-workflow`: `updated` (github) - updated by gh skill (google/agents-cli) c0cd4975 > ee9e6b5b [v1.11.0]

### Skipped

- `code/address-pr-comments`: `skipped-bundled` (bundled) - repo copy of a package-bundled skill; it shadows the packaged copy and is maintained in this repo, so `coga skill update` leaves it alone
- `code/design`: `skipped-bundled` (bundled) - repo copy of a package-bundled skill; it shadows the packaged copy and is maintained in this repo, so `coga skill update` leaves it alone
- `code/implement`: `skipped-bundled` (bundled) - repo copy of a package-bundled skill; it shadows the packaged copy and is maintained in this repo, so `coga skill update` leaves it alone
- `code/open-pr`: `skipped-bundled` (bundled) - repo copy of a package-bundled skill; it shadows the packaged copy and is maintained in this repo, so `coga skill update` leaves it alone
- `code/review-design`: `skipped-bundled` (bundled) - repo copy of a package-bundled skill; it shadows the packaged copy and is maintained in this repo, so `coga skill update` leaves it alone
- `code/self-qa`: `skipped-bundled` (bundled) - repo copy of a package-bundled skill; it shadows the packaged copy and is maintained in this repo, so `coga skill update` leaves it alone
- `coga/autoclose/sweep`: `skipped-bundled` (bundled) - repo copy of a package-bundled skill; it shadows the packaged copy and is maintained in this repo, so `coga skill update` leaves it alone
- `coga/blockers/remind`: `skipped-bundled` (bundled) - repo copy of a package-bundled skill; it shadows the packaged copy and is maintained in this repo, so `coga skill update` leaves it alone
- `coga/branch-sweep/sweep`: `skipped-bundled` (bundled) - repo copy of a package-bundled skill; it shadows the packaged copy and is maintained in this repo, so `coga skill update` leaves it alone
- `coga/recurring/verify`: `skipped-bundled` (bundled) - repo copy of a package-bundled skill; it shadows the packaged copy and is maintained in this repo, so `coga skill update` leaves it alone
- `coga/releasing`: `skipped-bundled` (bundled) - repo copy of a package-bundled skill; it shadows the packaged copy and is maintained in this repo, so `coga skill update` leaves it alone
- `coga/show`: `skipped-bundled` (bundled) - repo copy of a package-bundled skill; it shadows the packaged copy and is maintained in this repo, so `coga skill update` leaves it alone
- `coga/testing/clean-install`: `skipped-bundled` (bundled) - repo copy of a package-bundled skill; it shadows the packaged copy and is maintained in this repo, so `coga skill update` leaves it alone
- `coga/ticket/finalize`: `skipped-bundled` (bundled) - repo copy of a package-bundled skill; it shadows the packaged copy and is maintained in this repo, so `coga skill update` leaves it alone
- `clarity`: `unchanged` (url) - upstream digest unchanged
```

### recurring/blocker-reminders — completed

- template: `blocker-reminders`
- ticket status after the run: done

What the run wrote to its blackboard:

```


The blackboard is a notepad to be written to often as the human and agent works through a task.
```

### recurring/dream — timed-out

- template: `dream`
- ticket status after the run: done
- note: liveness watchdog tore the session down before it signalled done

What the run wrote to its blackboard:

```
[... truncated ...]
ent-duplicate-session-usage-records-from-infla, record-the-two-self-qa-hazards-from-done-ticket-bl, repair-ticket-referents-when-a-referent-is-renamed, the three validate-drift-* owners themselves, verify-dream-under-codex-on-the-real-repo-w40, webhook-for-slack-is-public).
- validate-drift: unfrozen-workflow → validate-drift-unfrozen-workflow-11-hand-authored (20 members; 18 new since filed, incl. the commit-journal/*, microkernel/* and marketing drafts; see validate-drift section). Its recorded decision tag was dropped from coga/workflows by 4792e20df (owned by the same ticket), so no context-recorded decision applies this run.
- validate-drift: empty-description → validate-drift-empty-description-23-title-only-tic (6 members; 4 new: coga-chat-without-context-and-isolation-for-pure-j, in-init-add-a-telemetry-true-message, make-coga-init-initizalizess-also-already-filled-r, review-all-doc).
- Findings: windows-aws attended ssh -tt → windows-native/03-interactive-coga-launch-on-native-windows; recurring/templates run_reported → gigantic-refactor-move-recurring-recipes-out-of-co; coga-dev/testing CI reversal → windows-native/02-pr-ci-with-linux-and-windows-test-jobs (PR #1097); workflows decision tag → validate-drift-unfrozen-workflow-11-hand-authored; state-publication "commit it" → state-sync-published-unmerged-recurring-templates; checkout-cleanup foreign-linked wording → guard-foreign-linked-worktree-branch-cleanup; twin-splitting sweeps → stop-the-contexts-root-sweep-from-publishing-canon; ticket-prose PRs and `requires: pr` → add-an-applying-a-batch-of-verdicts-section-to-the (its PR #912 closed unmerged; stalled); knowledge sync step → carry-the-apply-the-register-amendment-step-in-a-w (draft branch carry-knowledge-amendments exists only in /home/n/Code/coga, unpushed); recurring-control declined checkout → run-recurring-agent-templates-off-the-control-bran; `--agent` self-review → where-have-code-review-disappeared.

Retirement debt (left on disk; `coga retire <slug>`):
- done+checkout (12): blocks/06-collapse-state-publication-into-one-user-topic (unlocks X5 → #1114), blocks/08-trim-launch-prompt-and-workflow-topics, blocks/09-trim-setup-and-extension-topics, document-the-remedy-for-a-bloated-blackboard-sibli, reuse-the-existing-control-worktree-for-recurring, service-recurring-from-a-temp-control-worktree-ins, validate-that-committed-skill-scripts-with-a-sheba, fix-parser-bugs-documented-in-pr-1055 (X9 → #1116), automate-checkout-setup-and-deduplicate-instructio (X7 → draft), context-audiences/02-move-coga-dev-contexts-out-of-the-shipped-set, launch-moves-the-checkout-to-main-before-and-after (X8 → #1114), windows-native/01-core-port-cli-and-test-suite-pass-on-native-window (X6 → #1115). The last five keep their `## Dev` branch only in a sibling clone (/home/n/Code/codex/coga or /home/n/Code/coga).
- canceled (32): retiring define-the-api-equivalent-cost-proxy-and-price-tab unlocks X10 (coga-dev/internals/usage-pricing declined-status note); nightly-auto-drain-run-for-ready-tickets unlocks X11 (coga/megalaunch declined unattended budget drain).

Human-needed:
- origin/main fails tests/test_packaging.py since e2d1c3362 ("Sync coga state", 10:53): a sweep from another session published an uncommitted coga/recurring/blocker-reminders/ticket.md edit without its packaged twin. That is the hazard owned by state-sync-published-unmerged-recurring-templates and stop-the-contexts-root-sweep-from-publishing-canon. Retro PRs #1099–#1106 report 29 passed / 1 failed for this reason only.
- Leftover Dream ops worktree (needed to run the closing commands outside the occupied primary): `git -C /home/n/Code/claude/coga worktree remove /home/n/Code/claude/.dream-retro-20261026T172253Z/dream-ops && git -C /home/n/Code/claude/coga branch -D dream/ops-20261026T172253Z && rmdir /home/n/Code/claude/.dream-retro-20261026T172253Z` (also remove `coga/coga.local.toml` copy first if the worktree refuses).
- Machine-local validator issues: none.
```

### recurring/branch-sweep — completed

- template: `branch-sweep`
- exit code: 0
- note: clone-scoped run for period 2026-10-26

What the run wrote to its blackboard:

```
— left in place.
- Branch sweep: 'docs/v2-batch-verdicts' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/dream-w40-testing-baseline (no merged PR).
- Branch sweep: 'dream/ops-20261026T172253Z' has a landed ref but is checked out in worktree '/home/n/Code/claude/.dream-retro-20261026T172253Z/dream-ops' — left in place.
- Branch cleanup: local 'dream/w44-blackboard-unblock-writer' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: local 'dream/w44-checkout-cleanup-wording' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: local 'dream/w44-code-skill-citations' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: local 'dream/w44-config-comments' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: local 'dream/w44-install-windows' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: local 'dream/w44-microkernel-placements' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: local 'dream/w44-pr-publication-gotchas' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: local 'dream/w44-sweep-docs' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: local 'dream/w44-topic-claims' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: local 'dream/w44-windows-aws-long-runs' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: skipping remote origin/fence-aware-section-splitter (no merged PR).
- Branch cleanup: skipping remote origin/fix-slack-requests-patch-target (no merged PR).
- Branch cleanup: skipping remote origin/fix/codex-peer-review-in-sandbox (no merged PR).
- Branch sweep: 'fix/retire-followup-owner' is recorded on a live ticket — left in place.
- Branch cleanup: local 'guard-reauthor-in-progress' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'install-walk-findings' is recorded on a live ticket — left in place.
- Branch sweep: 'marketing/readme-top' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/nicktoper-patch-1 (no merged PR).
- Branch sweep: 'owned-mac-clean-install' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/publish-off-control (no merged PR).
- Branch sweep: 'recurring-control-worktree' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/recurring-crlf-lease (no merged PR).
- Branch cleanup: skipping remote origin/recurring-ledger-from-log (no merged PR).
- Branch cleanup: skipping remote origin/retire-worklist-linked-only (no merged PR).
- Branch cleanup: local 'scrub-sa-token' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: 'self-qa-stale-ticket-and-state-side-effects' is recorded on a live ticket — left in place.
- Branch sweep: 'shebang-exec-check' has merged PR #800 at a02e2930511f, but the ref carries commits touching coga/skills/anthropic/skill-creator/eval-viewer/generate_review.py, coga/skills/clarity/scripts/validate_package.py, src/coga/resources/templates/coga/bootstrap/skills/coga/gmail/gmail.py (+1 more) — left in place.
- Branch cleanup: local 'shebang-exec-check' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: skipping remote origin/slack-important-alert (no merged PR).
- Branch cleanup: local 'split-ticket-contract' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: skipping remote origin/terminal-branch-cleanup (no merged PR).
- Branch cleanup: skipping remote origin/warn-on-bootstrap-unpublished-edits (no merged PR).
- Branch cleanup: skipping remote origin/wedge-ticket-admin-reproduction (no merged PR).
[branch-sweep] skipped-worktree-pinned: dream/ops-20261026T172253Z
```

## Sweep notes

- launching 8 due task(s) sequentially
