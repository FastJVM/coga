# Branch cleanup audit — 2026-10-05

Recorded: 2026-10-06T00:45:52+00:00

Audited checkout: `/home/n/Code/codex/coga`; remote: `FastJVM/coga`.
Ownership was read from supported Coga workspaces after refreshing control. PR history and live remote tips were queried from GitHub; stale remote-tracking refs were not used as branch inventory.
The snapshot contained 48 feature branch names (including this implementation), with 28 local and 22 remote refs. No GitHub settings were changed.

Deleted **24 local refs and 8 remote refs**, across 31 branch names, after rechecking the proofs and publishing/verifying their retirement archives. No checkout directory was removed.

## Branch dispositions

| Branch | Before: local / remote tip | Explicit owner at audit | PR | Outcome |
| --- | --- | --- | --- | --- |
| `attended-ticket-switch-recipe` | `d225a2ff130a99c4c49a89bc6ef6c7a9545674b0` / absent | `record-the-attended-ticket-switch-recipe-launch-do` (done) | [#910](https://github.com/FastJVM/coga/pull/910) merged | Deleted local. Archive: `retired/attended-ticket-switch-recipe@d225a2ff130a` |
| `branch-sweep-retired-tag-collision` | `3b3d1cb40256cdde3c559dc1fe67c995ecb79f07` / absent | `autofix/make-branch-sweep-retirement-survive-an-existing-r` (done) | [#937](https://github.com/FastJVM/coga/pull/937) merged | Deleted local. Archive: `retired/branch-sweep-retired-tag-collision` |
| `codex/retro-marketing-fix-installer-run-clean-installs-and-file-issues-knowledge` | `a4e8bd3e2e93138d88633cfe4898fabfa023f964` / absent | none | [#954](https://github.com/FastJVM/coga/pull/954) merged | Deleted local. Archive: `retired/codex/retro-marketing-fix-installer-run-clean-installs-and-file-issues-knowledge` |
| `codex/retro-recurring-branch-sweep-knowledge` | absent / `9b9e80d36a05cdce6c00993532c80c57c49899af` | none | [#859](https://github.com/FastJVM/coga/pull/859) merged | Deleted remote. Archive: `retired/codex/retro-recurring-branch-sweep-knowledge` |
| `daily-autoclose-branches` | `4be1b938711a66aea38828d97e2bf630008d136a` / absent | `run-the-landed-branch-sweep-daily-from-autoclose` (done) | [#898](https://github.com/FastJVM/coga/pull/898) merged | Deleted local. Archive: `retired/daily-autoclose-branches` |
| `doc-tmp-checkouts-ephemeral` | `ecaa9f2c7be783923c601d70803542f2ea04309b` / absent | `record-that-preserved-tmp-worktrees-do-not-survive` (done) | [#917](https://github.com/FastJVM/coga/pull/917) merged | Deleted local. Archive: `retired/doc-tmp-checkouts-ephemeral` |
| `docs/command-classification` | `7abde3019b56f72db44f653b56f79fa47f18c0fd` / absent | `settle-whether-megalaunch-is-the-only-unclassified` (done) | [#906](https://github.com/FastJVM/coga/pull/906) merged | Deleted local. Archive: `retired/docs/command-classification` |
| `docs/v2-batch-verdicts` | `e43251b3f6b377416382a280475541aa7120b610` / `e43251b3f6b377416382a280475541aa7120b610` | `add-an-applying-a-batch-of-verdicts-section-to-the` (in_progress) | [#912](https://github.com/FastJVM/coga/pull/912) closed | Preserved. 'docs/v2-batch-verdicts' is recorded on a live ticket — left in place. |
| `docs/w40-workflow-corrections` | `5b0515379eb51d7efa891e2975c51b0706a5e411` / absent | `apply-three-dream-w40-workflow-and-v2-readme-corre` (done) | [#934](https://github.com/FastJVM/coga/pull/934) merged | Deleted local. Archive: `retired/docs/w40-workflow-corrections` |
| `docs/w40-workflow-corrections-duplicate-d4dea0eee` | `d4dea0eeecd516bb32dbd03971ac05b79f44b68b` / absent | none | none found | Preserved. 'docs/w40-workflow-corrections-duplicate-d4dea0eee' preserved: no eligible PR head or landed local tip. |
| `dream-under-codex` | `7ea57bfbdb00e20c752816c379e606e1fad698be` / absent | `make-dream-run-correctly-under-codex` (done) | [#891](https://github.com/FastJVM/coga/pull/891) merged | Deleted local. Archive: `retired/dream-under-codex` |
| `dream-w40-doc-corrections` | `b6ce69362c7864208aea995fb5aac0c29dbf3583` / absent | `apply-three-dream-w40-skill-and-context-correction` (done) | [#933](https://github.com/FastJVM/coga/pull/933) merged | Deleted local. Archive: `retired/dream-w40-doc-corrections` |
| `dream-w40-notification-skill-docs` | `40abd83a833122a7beba723ce0deb1341a841433` / absent | `apply-three-dream-w40-notification-and-skill-manag` (done) | [#935](https://github.com/FastJVM/coga/pull/935) merged | Deleted local. Archive: `retired/dream-w40-notification-skill-docs` |
| `dream-w40-testing-baseline` | absent / `e01dfd73aea62da852c7b000a28630b8fa9a5c5c` | none | [#923](https://github.com/FastJVM/coga/pull/923) closed | Preserved. 'dream-w40-testing-baseline' preserved: no eligible PR head or landed local tip. |
| `dream-w41/checkout-disposal-docs` | absent / `acb6a05265e841021edf9dfc9fbe6970a5fc06a6` | none | [#959](https://github.com/FastJVM/coga/pull/959) merged | Deleted remote. Archive: `retired/dream-w41/checkout-disposal-docs` |
| `dream-w41/codebase-map-accuracy` | absent / `ec6c9830e5d47c8527a5689645c6d15b46776506` | none | [#957](https://github.com/FastJVM/coga/pull/957) merged | Deleted remote. Archive: `retired/dream-w41/codebase-map-accuracy` |
| `dream-w41/internals-doc-drift` | absent / `ceec9d14210bf89d1fe7c0d52ef93f25281ec778` | none | [#956](https://github.com/FastJVM/coga/pull/956) merged | Deleted remote. Archive: `retired/dream-w41/internals-doc-drift` |
| `dream-w41/notifications-phone-home-docs` | absent / `ede50d69e3b70b84898e8e9a41afef9df1a7d48d` | none | [#958](https://github.com/FastJVM/coga/pull/958) merged | Deleted remote. Archive: `retired/dream-w41/notifications-phone-home-docs` |
| `dream-w41/record-declined-decisions` | absent / `1affc8524cfa78c2944c9e78e8a45c22d496fb9e` | none | [#960](https://github.com/FastJVM/coga/pull/960) merged | Deleted remote. Archive: `retired/dream-w41/record-declined-decisions` |
| `edge-wheel-upgrades` | `2dd35eaceb257eae25e6699e48616f3ce621842e` / absent | `ship-edge-ticket-py-code-upgrades-with-the-wheel` (done) | [#938](https://github.com/FastJVM/coga/pull/938) merged | Deleted local. Archive: `retired/edge-wheel-upgrades` |
| `fix-authoring-publication` | `96f2a37c4391879554eb411cf91380fc987d43e1` / absent | `keep-agent-edits-to-contexts-and-skills-off-the-co` (done) | [#904](https://github.com/FastJVM/coga/pull/904) merged | Deleted local. Archive: `retired/fix-authoring-publication` |
| `fix-autoclose-clone-primary` | `9c74a60138a6b095c9dc787d5f4d44dde6ce149e` / absent | `autoclose-re-posts-another-clone-s-primary-checkou` (done) | [#939](https://github.com/FastJVM/coga/pull/939) merged | Deleted local. Archive: `retired/fix-autoclose-clone-primary` |
| `fix-recurring-git-hygiene` | `2b05e970538812e73fcb34ca298cf3fe49adc3fc` / absent | `fix-recurring-sweep-git-hygiene-blocked-task-escap` (done) | [#914](https://github.com/FastJVM/coga/pull/914) merged | Deleted local. Archive: `retired/fix-recurring-git-hygiene` |
| `fix/claude-synthetic-model` | `3e6fe25248e4338737f0e44d62bdcf975a6d3a4c` / absent | `stop-synthetic-from-claiming-a-claude-session-s-mo` (done) | [#916](https://github.com/FastJVM/coga/pull/916) merged | Deleted local. Archive: `retired/fix/claude-synthetic-model` |
| `fix/claude-usage-dedupe` | `a6661d2b657659a9f05f7ac74f3add683be1f304` / absent | `dedupe-claude-transcript-usage-by-message-id` (done) | [#947](https://github.com/FastJVM/coga/pull/947) merged | Deleted local. Archive: `retired/fix/claude-usage-dedupe` |
| `fix/codex-peer-review-in-sandbox` | absent / `c0521c085f62c37f5fe6be43da670699018f3746` | none | [#950](https://github.com/FastJVM/coga/pull/950) closed | Preserved. 'fix/codex-peer-review-in-sandbox' preserved: no eligible PR head or landed local tip. |
| `fix/phone-home-twin-exemption` | `04a258897d43d6d761007cc2d72cbc6cfb855b83` / absent | none | [#895](https://github.com/FastJVM/coga/pull/895) merged | Deleted local. Archive: `retired/fix/phone-home-twin-exemption` |
| `fix/retire-followup-owner` | absent / `7db37a31f76a20334f60b747ef60ced596805162` | `autofix/name-cross-repo-retire-follow-ups-with-the-repo-th` (draft) | [#870](https://github.com/FastJVM/coga/pull/870) closed | Preserved. 'fix/retire-followup-owner' is recorded on a live ticket — left in place. |
| `init-hosting-scaffold-empty` | `1f05535ba9f3ec1c168cf788768a2c7052e391ca` / absent | `coga-build-fails-after-init-on-a-github-scaffolded` (done) | [#902](https://github.com/FastJVM/coga/pull/902) merged | Deleted local. Archive: `retired/init-hosting-scaffold-empty` |
| `launch-marker-usage-match` | absent / `f7773d78cb6f2161502b4de21d8e0c53196d6081` | `match-concurrent-codex-sessions-to-their-launch-so` (in_progress) | [#961](https://github.com/FastJVM/coga/pull/961) open | Preserved. 'launch-marker-usage-match' is recorded on a live ticket — left in place. |
| `linux-clean-install-harness` | `1dd89deb9e66b8f76ceb746a0ff5dbe5862dd0ae` / absent | `marketing/fix-installer/linux-clean-install-harness` (done) | [#930](https://github.com/FastJVM/coga/pull/930) merged | Deleted local. Archive: `retired/linux-clean-install-harness` |
| `macos-clean-install-harness` | `d2cf99bc1818e929530f01ba20ebd25fa7d4cfb7` / absent | `marketing/fix-installer/macos-clean-install-harness-on-aws` (done) | [#943](https://github.com/FastJVM/coga/pull/943) merged | Deleted local. Archive: `retired/macos-clean-install-harness` |
| `nicktoper-patch-1` | absent / `cdc7b38d01e3bb3452018f40238d2ed5e37ed9e5` | none | none found | Preserved. 'nicktoper-patch-1' preserved: no eligible PR head or landed local tip. |
| `preserve-no-action-decisions` | `02433eb11bab07d64332d683c97a9e0afff09009` / absent | `preserve-owner-decisions-not-to-act-beyond-the-tic` (done) | [#918](https://github.com/FastJVM/coga/pull/918) merged | Deleted local. Archive: `retired/preserve-no-action-decisions` |
| `publish-off-control` | absent / `3af51afb30d42f4fc638951769900b69c001223f` | none | [#833](https://github.com/FastJVM/coga/pull/833) closed | Preserved. 'publish-off-control' preserved: no eligible PR head or landed local tip. |
| `recurring-crlf-lease` | absent / `a7b2e8d48a2f85f7b06451eecc55a10e5ee3dc50` | none | [#782](https://github.com/FastJVM/coga/pull/782) closed | Preserved. 'recurring-crlf-lease' preserved: no eligible PR head or landed local tip. |
| `recurring-ledger-from-log` | absent / `0a1b1bcedf748c2f64cf802ac2bad9051a3fb65d` | none | [#688](https://github.com/FastJVM/coga/pull/688) merged | Preserved. 'recurring-ledger-from-log' remote tip 0a1b1bcedf74 differs from the closed/merged PR head — remote preserved. 'recurring-ledger-from-log' preserved: no eligible PR head or landed local tip. |
| `release-0.4.0` | `0b007ef081da12a674129c2df81cdf43b06a58d1` / absent | none | none found | Preserved. 'release-0.4.0' has a landed ref but is checked out in worktree '/tmp/coga-release-0.4.0' — left in place. |
| `retire-worklist-linked-only` | absent / `916de0bc43eb7858092be9576dd9b69cc639ff6e` | none | [#849](https://github.com/FastJVM/coga/pull/849) closed | Preserved. 'retire-worklist-linked-only' preserved: no eligible PR head or landed local tip. |
| `retired-ticket-recovery` | `7e1d6f3b2cf3f921df0178004b2e540096dee184` / absent | `document-how-to-recover-a-retired-ticket-s-body-fr` (done) | [#893](https://github.com/FastJVM/coga/pull/893) merged | Deleted local. Archive: `retired/retired-ticket-recovery` |
| `shebang-exec-check` | absent / `a02e2930511f7af9fc7b51393e73b82f4ed6c944` | `validate-that-committed-skill-scripts-with-a-sheba` (done) | [#800](https://github.com/FastJVM/coga/pull/800) merged | Preserved. 'shebang-exec-check' recorded checkout '/home/n/Code/claude/coga-shebang-exec-check' is missing, unreadable, or owned by another clone — inspect in its owning repository. |
| `slack-important-alert` | absent / `b8b738fa2b6c668c4ab816593e98c730300e78c2` | none | [#578](https://github.com/FastJVM/coga/pull/578) closed | Preserved. 'slack-important-alert' preserved: no eligible PR head or landed local tip. |
| `split-ticket-contract` | absent / `c66b24e52994a283c6a2d855f07606a10634771a` | `define-the-split-a-ticket-mechanic-shared-by-code` (canceled) | [#889](https://github.com/FastJVM/coga/pull/889) closed | Preserved. 'split-ticket-contract' recorded checkout '/home/n/Code/coga' is missing, unreadable, or owned by another clone — inspect in its owning repository. |
| `stop-recurring-inactive` | `dd2f344a36a164d6f308560e16850f727e802f61` / absent | `stop-recurring-on-inactive-repo` (done) | [#905](https://github.com/FastJVM/coga/pull/905) merged | Deleted local. Archive: `retired/stop-recurring-inactive` |
| `terminal-branch-cleanup` | `d41518e2fa4b26535c0018feb4b67753b8890296` / absent | `clean-up-owned-branches-when-tickets-finish-or-are` (in_progress) | none found | Preserved. 'terminal-branch-cleanup' is the checked-out branch — left in place. |
| `usage-report-flow` | `fcef7899cfa99d6c8ab13a9628f49d4434474d0c` / `c9de296505e2b78bebf17387a1777019d89ce7f6` | `decide-whether-the-weekly-usage-report-belongs-on` (done) | [#944](https://github.com/FastJVM/coga/pull/944) closed | Deleted local, remote. Archive: `retired/usage-report-flow` |
| `v2-premise-adjudication` | absent / `c9b257f494eda97e1b3f5fe100cde7dd44a1e100` | `adjudicate-the-eight-premise-dead-v2-drafts` (canceled) | [#913](https://github.com/FastJVM/coga/pull/913) closed | Deleted remote. Archive: `retired/v2-premise-adjudication` |
| `wedge-ticket-admin-reproduction` | absent / `9d3007c7b0675dd23ee0fd551aa1e4d1995eb4b5` | none | [#876](https://github.com/FastJVM/coga/pull/876) closed | Preserved. 'wedge-ticket-admin-reproduction' preserved: no eligible PR head or landed local tip. |

## Decisions still needed

No abandonment was inferred for the following unresolved branches. The owner must identify still-wanted work and its live ticket, or provide an explicit disposition before manual cleanup. Re-running a sweep alone will not supply missing ownership or waive a source-change/checkout refusal.

- `docs/v2-batch-verdicts`: retained for its live owner. Finish or cancel the owning ticket only when its work has a disposition.
- `docs/w40-workflow-corrections-duplicate-d4dea0eee`: 'docs/w40-workflow-corrections-duplicate-d4dea0eee' preserved: no eligible PR head or landed local tip.
- `dream-w40-testing-baseline`: 'dream-w40-testing-baseline' preserved: no eligible PR head or landed local tip.
- `fix/codex-peer-review-in-sandbox`: 'fix/codex-peer-review-in-sandbox' preserved: no eligible PR head or landed local tip.
- `fix/retire-followup-owner`: retained for its live owner. Finish or cancel the owning ticket only when its work has a disposition.
- `launch-marker-usage-match`: retained for its live owner. Finish or cancel the owning ticket only when its work has a disposition.
- `nicktoper-patch-1`: 'nicktoper-patch-1' preserved: no eligible PR head or landed local tip.
- `publish-off-control`: 'publish-off-control' preserved: no eligible PR head or landed local tip.
- `recurring-crlf-lease`: 'recurring-crlf-lease' preserved: no eligible PR head or landed local tip.
- `recurring-ledger-from-log`: 'recurring-ledger-from-log' remote tip 0a1b1bcedf74 differs from the closed/merged PR head — remote preserved. 'recurring-ledger-from-log' preserved: no eligible PR head or landed local tip.
- `release-0.4.0`: 'release-0.4.0' has a landed ref but is checked out in worktree '/tmp/coga-release-0.4.0' — left in place.
- `retire-worklist-linked-only`: 'retire-worklist-linked-only' preserved: no eligible PR head or landed local tip.
- `shebang-exec-check`: 'shebang-exec-check' recorded checkout '/home/n/Code/claude/coga-shebang-exec-check' is missing, unreadable, or owned by another clone — inspect in its owning repository.
- `slack-important-alert`: 'slack-important-alert' preserved: no eligible PR head or landed local tip.
- `split-ticket-contract`: 'split-ticket-contract' recorded checkout '/home/n/Code/coga' is missing, unreadable, or owned by another clone — inspect in its owning repository.
- `wedge-ticket-admin-reproduction`: 'wedge-ticket-admin-reproduction' preserved: no eligible PR head or landed local tip.

## Earlier sweep candidates absent from this inventory

The ticket cited the sweep at `4c937f2d4`. These named candidates were absent from both this clone and the current remote before this cleanup; this audit did not delete them or infer the state of refs in other clones:

- `autoclose-retires-durable-home`
- `bloated-blackboard-remedy`
- `coga/skill-update`
- `guard-reauthor-in-progress`
- `recover-state-only-divergence`
- `recurring-control-worktree`
- `scrub-sa-token`

## Verification

Post-cleanup `git for-each-ref` and fresh `git ls-remote --heads --tags origin` confirmed all 24 deleted local refs and eight deleted remote refs absent, and all 31 archive tags present.

- `.venv/bin/python -m pytest -q`: 3,275 passed after rebasing onto `feb45858b`.
- `.venv/bin/python -m pytest tests/test_branchcleanup.py tests/test_branchsweep.py -q`: 146 passed after correcting the deletion diagnostic for closed PRs.
- `env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/codex/coga/src /home/n/Code/codex/coga/.venv/bin/python -m coga.cli validate --json` from `example/coga`: four valid tickets, no issues.
- Preview used `branchsweep.sweep_branches(..., dry_run=True)`. Application rechecked the 31 eligible names with `branches={...}, remove_worktrees=False`; its successful archive and deletion outcomes are recorded above.
- Recovery uses the recorded remote retirement tag with ordinary `git fetch origin tag <tag>` and `git switch -c <new-branch> <tag>`. The archive contract belongs to [dev/checkout-cleanup](../contexts/dev/checkout-cleanup/SKILL.md).

The application run began before a wording-only diagnostic correction: its low-level helper called authorized force-deletions “PR merged.” The PR state and terminal owner in this table distinguish the two closed-unmerged cases (`usage-report-flow`, `v2-premise-adjudication`); neither was represented as landed work by the eligibility proof.
