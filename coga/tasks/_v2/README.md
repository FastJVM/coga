# `coga/tasks/_v2/` — the v2 wish list

A parked directory (see `coga/tickets`): Coga never lists, launches,
validates, or scans anything here. `ls` and git are the way to browse it.

## Owner parking decision — 2026-10-27

The owner retained the [numbered v1 queue](../v1/README.md) for first users,
including usage reports and commit/log work, and deferred the tickets below.
Microkernel cleanup, its demo, further context cleanup, and Dream fixes are
not v1 release gates. Existing designs, attachments, and lifecycle fields are
preserved as parked history; the pull-forward rules below still apply.

- [Add a failed terminal status](add-a-failed-terminal-status.md)
- [Add an Applying-a-batch-of-verdicts section to the v2 parking README](add-an-applying-a-batch-of-verdicts-section-to-the.md)
- [autoclose should be script only](autoclose-should-be-script-only.md)
- [Name cross-repo retire follow-ups with the repo that owns them](autofix/name-cross-repo-retire-follow-ups-with-the-repo-th/ticket.md)
- [Tear down launched sessions when mark done signal goes unobserved](autofix/tear-down-launched-sessions-when-mark-done-signal/ticket.md)
- [Autofix dedupe ignores closed autofix tickets](autofix-dedupe-ignores-closed-autofix-tickets.md)
- [Carry the apply-the-register-amendment step in a workflow](carry-the-apply-the-register-amendment-step-in-a-w.md)
- [coga chat without context and isolation for pure judgement a,nd eval](coga-chat-without-context-and-isolation-for-pure-j.md)
- [Count failed important alerts in recurring problems](count-failed-important-alerts-in-recurring-problem.md)
- [Dream runs a full documentation consistency audit once a month](dream-runs-a-full-documentation-consistency-audit.md)
- [Dream's own blackboard trips large-blackboard every run](dream-s-own-blackboard-trips-large-blackboard-ever.md)
- [Drop bundled-skill twin rows from the skill-update report](drop-bundled-skill-twin-rows-from-the-skill-update.md)
- [Gigantic refactor: move recurring recipes out of core](gigantic-refactor-move-recurring-recipes-out-of-co.md)
- [in init add a telemetry true message](in-init-add-a-telemetry-true-message.md)
- [Checkout exclusivity lock](launch-locks/checkout-exclusivity-lock/ticket.md)
- [Ticket ownership lock](launch-locks/ticket-ownership-lock/ticket.md)
- [make coga init initizalizess also already filled repo](make-coga-init-initizalizess-also-already-filled-r.md)
- [Make coga status an interactive control center](make-coga-status-an-interactive-control-center.md)
- [Audit and record the first-user ICP](marketing/1st-users/ticket.md)
- [Demo hackability: ask Claude to add a command live](marketing/demo-hackability-ask-claude-to-add-a-command-live.md)
- [Recruit first users](marketing/recruit-first-users.md)
- [Put into words why I would keep using Coga](marketing/why-i-would-keep-using-coga.md)
- [Match Dream report headings only in the blackboard](match-dream-report-headings-only-in-the-blackboard.md)
- [Decompose launch into substrate plus ticket orchestration](microkernel/launch-decomposition.md)
- [Move lifecycle verbs to ticket operations](microkernel/lifecycle-verbs-to-ticket-operations.md)
- [Classify read and report commands under the small-core rule](microkernel/read-report-commands-as-ticket-workflows.md)
- [Classify residual command surfaces](microkernel/residual-command-surfaces.md)
- [Classify support commands under the small-core rule](microkernel/support-commands-boundary.md)
- [Move work orchestration commands to tickets](microkernel/work-orchestration-commands-to-tickets.md)
- [Move the non-executable-script validate contract into a shipped user topic](move-the-non-executable-script-validate-contract-i.md)
- [Name unlaunched created periods when the recurring sweep stops early](name-unlaunched-created-periods-when-the-recurring.md)
- [Name where ticket checkout reservation receipts live in git-refresh](name-where-ticket-checkout-reservation-receipts-li.md)
- [open pr becomes detereminstici + mechanic (no check](open-pr-becomes-detereminstici-mechanic-no-check.md)
- [Record the two self-QA hazards from done-ticket blackboards](record-the-two-self-qa-hazards-from-done-ticket-bl.md)
- [A recurring template whose first step routes to the owner validates clean and fails every firing](recurring-template-whose-first-step-routes-to-the-owner.md)
- [Repair ticket referents when a referent is renamed or canceled](repair-ticket-referents-when-a-referent-is-renamed.md)
- [Repoint the launch topic chat occupancy guard owner to checkouts chat](repoint-the-launch-topic-chat-occupancy-guard-owne.md)
- [Report failed create syncs from named recurring launches](report-failed-create-syncs-from-named-recurring-la.md)
- [Rewrite the coga-dev current-direction native Windows entry after the core port](rewrite-the-coga-dev-current-direction-native-wind.md)
- [Route large-blackboard validate issues as state edits, not PR proposals](route-large-blackboard-validate-issues-as-state-ed.md)
- [Run launched agents in a resource-limited systemd scope](run-launched-agents-in-a-resource-limited-systemd.md)
- [Stop recommending control worktrees in the recurring refusal](run-recurring-agent-templates-off-the-control-bran.md)
- [Split launch preparation out of the git-refresh internals topic](split-launch-preparation-out-of-the-git-refresh-in.md)
- [Stop launch --prompt-report from sweeping Coga state](stop-launch-prompt-report-from-sweeping-coga-state.md)
- [Triage Dream eligibility drift in client templates](triage-dream-eligibility-drift-in-client-templates.md)
- [Triage open tickets whose premise Dream found satisfied or stale](triage-open-tickets-whose-premise-dream-found-sati.md)
- [Update this repo's coga.toml codex comment after the agents topic removal](update-this-repo-s-coga-toml-codex-comment-after-t.md)
- [validate-drift: empty-description — 23 title-only tickets need an author verdict](validate-drift-empty-description-23-title-only-tic.md)
- [validate-drift: stuck-in-progress — 11 in_progress tickets idle past threshold need an owner verdict](validate-drift-stuck-in-progress-11-in-progress-ti.md)
- [validate-drift: unfrozen-workflow — 11 hand-authored drafts carry an unfrozen workflow](validate-drift-unfrozen-workflow-11-hand-authored.md)
- [Verify Dream under codex on the real repo (first period after merge)](verify-dream-under-codex-on-the-real-repo-w40.md)
- [where have code review disappeared?](where-have-code-review-disappeared.md)

## What this is

A wish list of things someone wanted at some point, not a backlog. Each file
is a dated wish, not a spec. Files may be stale, name surfaces that no longer
exist, or contradict each other and `main` — that is fine. Nobody reconciles,
adjudicates, or cancels them while they sit here, and no verdict is ever due.
Do not "fix" a draft here to match the current repo.

Capture a wish with `coga create "_v2/<title>"`; a bare title is enough, and
`--description` is optional. Delete a wish that is no longer wanted with
`git rm`.

## Pulling a wish forward

Only through an explicit human decision. Then:

1. Run the premise check below against current `main`.
2. `git mv` the file out of `_v2/` into `coga/tasks/` (or `coga create` a
   fresh ticket that cites it), rewrite it against the current shape, and give
   it a workflow. From that point it is an ordinary ticket: it must pass
   `coga validate` and is visible to `coga status` and Dream.

### The premise check

The problem statement usually survives; the proposed implementation often
does not, because the surfaces it names keep moving. Four questions, in order:

1. **Does the subject still exist?** If what the wish asks you to build,
   document, or remove is already gone, drop it (`git rm`) instead of writing
   prose about a removed design.
2. **Do the surfaces it names still resolve?** Check every command, path, and
   field it names against current `main`, starting with the table below.
3. **Does the wish carry the substance it depends on?** A wish that points
   at another ticket's blackboard or body for its requirements may have lost
   them: that ticket can be retired and deleted. Recover the missing substance
   from git history with the
   [retired-task recipe in `coga/tickets/discovery`](../../../docs/contexts/coga/tickets/discovery/SKILL.md#where-tasks-live-and-how-they-are-named)
   (it covers the pre-rename `relay-os/tasks/` too) and inline it; never
   repoint the citation at a different live ticket. Citations kept only for
   provenance are fine.
4. **Has something else already delivered it?** Compare the target surface
   on current `main` with the wish's acceptance criterion, not its title. If
   it already ships, drop the wish; if only part shipped, pull forward only
   the remainder.

### Known-stale surfaces (the pre-rename cohort)

Most of this directory predates the `relay` → `coga` rename, and 46 of its
drafts still say `relay`. **The rename is not a find-and-replace.** Some names
carried over, some changed meaning, and some were deleted outright — so
mechanically rewriting `relay` to `coga` produces confident, wrong
instructions. Check each occurrence against this table:

| As written in a draft | Status today |
| --- | --- |
| `src/relay/` | Renamed — now `src/coga/`. |
| `relay-os/contexts/…` | Renamed — now `coga/contexts/…`. |
| `relay-os/workflows/<name>.md` | Check repo-local `coga/workflows/<name>.md` first; if absent, check `src/coga/resources/templates/coga/bootstrap/workflows/<name>.md`. This repo's `code/*` workflows are packaged-only: `coga/workflows/code/` does not exist. |
| `relay launch`, `relay recurring`, `relay status`, `relay bump` | Renamed — the `coga` equivalents exist. |
| `relay draft` | **Gone.** Ticket creation is `coga create` (raw draft) or `coga ticket` (authoring skill). |
| `relay panic` | **Replaced.** Use `coga block --task <slug> --reason "…"` for unresolved input; it records the ask, marks the task blocked, notifies the owner, and ends the session. |
| `mode:` ticket frontmatter (`script` / `auto` / `interactive`) | **Gone.** There is no `mode` or `recipe:` field. A directory-form ticket's exact sibling `ticket.py` is its headless deterministic half; without that file, launch selects the agent path. See `coga/script-tickets`. |
| Child `mode: script` tasks driven by a parent task | **Gone.** Put a ticket-owned deterministic phase in that selected ticket's exact sibling `ticket.py`, or invoke a stable package command explicitly through `coga run`; do not rebuild child-task mode orchestration. |
| `[secrets]` bulk-inject config block | **Gone.** Secrets are per-ticket `secrets:` frontmatter holding `op://vault/item/field` refs; see `coga/secrets`. |

This table is a starting point, not a guarantee of completeness — it was built
from the surfaces actually present in these drafts as of 2026-08-13. Treat any
other `relay`-era name the same way: verify it against `main` before acting on
it.
