# Branch backlog audit under the terminal-owner rules

Evidence recorded 2026-10-05 (US Pacific) for the
[terminal-owner rule](../contexts/dev/checkout-cleanup/SKILL.md#terminal-owners-and-closed-prs)
introduced by `clean-up-owned-branches-when-tickets-finish-or-are`. These are
point-in-time observations of the `/home/n/Code/coga` clone and `origin`;
the topic keeps only the durable rule.

## Starting state

Rechecked before acting: GitHub had one open PR (#961,
`launch-marker-usage-match`) and `delete_branch_on_merge=false`. After
`git fetch --prune`, this clone had 24 local feature branches and `origin`
had 22. Ownership was read with `branchsweep._terminal_owners`, live pins
with `_live_ticket_branches`, and local refs were judged with
`merged_pr_verdict` (closed PRs only for terminal-owned branches).

## Cleared by the new sweep code

Running `coga run branch-sweep` from the feature branch archived each tip as
`retired/<branch>` on `origin` before deleting it:

- Local refs with a merged PR at the exact head, or patch-equivalent to it:
  `branch-sweep-cherry-pick`, `branch-sweep-retired-tag-collision`,
  `docs/w40-workflow-corrections`, `dream-w40-doc-corrections` (archived as
  `retired/dream-w40-doc-corrections@d6860337ee52`, because the plain name
  already held other history), `fix-autoclose-clone-primary`,
  `init-offers-dependency-installs`, `knowledge-ticket-links-at-retirement`,
  `macos-clean-install-harness`, `phone-home-record-failure-caller`,
  `skill-digest-skip-local-artifacts`, `uninstall-uv-tool`.
- Remote ref at its merged head: `shebang-exec-check` (#800).
- Released by the new rule: local `v2-premise-adjudication`. PR #913 was
  closed unmerged at this exact tip, and the owner ticket
  `adjudicate-the-eight-premise-dead-v2-drafts` is canceled.

Between the audit and the run, another process removed the remote refs of
`v2-premise-adjudication`, the five `dream-w41/*` branches and
`codex/retro-recurring-branch-sweep-knowledge`, publishing their
`retired/<branch>` tags. The `/home/n/Code/codex/coga` clone holds local
`retired/dream-w41/*` tags, consistent with its own daily sweep. The actor
for `v2-premise-adjudication` was not identified; its archive tag holds the
closed head.

## Kept by the rules: owner-approved for manual removal

The rules cannot release any of these. The owner approved deleting all of
them after archiving each tip, but the agent's tool permissions refused the
destructive step. They stay until the owner runs the removal.

- Closed unmerged PR; the owner ticket was terminal but has since been
  deleted, so no ownership record remains: `usage-report-flow` (#944; owner
  `decide-whether-the-weekly-usage-report-belongs-on`, done 2026-10-01),
  `split-ticket-contract` (#889; owner
  `define-the-split-a-ticket-mechanic-shared-by-code`, canceled "Won't do"),
  `slack-important-alert` (#578; owner
  `coga-important/add-coga-slack-important`, done 2026-07-17). The first two
  were also pinned by this ticket's own description.
- Closed unmerged PR that no ticket ever recorded, with the remote still at
  the closed head: `dream-w40-testing-baseline` (#923),
  `fix/codex-peer-review-in-sandbox` (#950), `publish-off-control` (#833),
  `recurring-crlf-lease` (#782), `retire-worklist-linked-only` (#849). Also
  the local review copies `pr849` and `pr870`, at the closed heads of #849
  and #870.
- No PR at all: `clean-install-merge`, `nicktoper-patch-1`,
  `wip/numbered-drain-order-stale-base`.
- Merged PR, but the ref carries unreviewed source commits:
  `launch-normalizes-checkout` (#909, about 40 paths beyond the merged head),
  `linux-clean-install-harness` (#930, 5 paths), `recurring-ledger-from-log`
  (remote past merged head of #688). The agent recommended keeping these;
  the owner chose removal with archive.

## Kept: live ticket

`carry-knowledge-amendments`, `docs/v2-batch-verdicts` (closed #912),
`fix/retire-followup-owner` (closed #870), `launch-marker-usage-match` (open
#961), `recover-state-only-divergence` (merged #948 but pinned), and the
ticket's own `terminal-branch-cleanup`.
