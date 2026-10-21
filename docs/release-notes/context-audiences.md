# Context audiences — next release

Coga now ships only contexts needed to operate Coga in an adopting repo.
User topics remain under `coga/` and `dev/`. Development topics move to
`coga-dev/` in Coga’s own source library and are absent from the wheel.
The [audience criterion](../contexts/coga/context-layout/SKILL.md#context-audiences)
explains the boundary.

This is a clean break: no aliases, redirects, or stub topics. Update ticket
`contexts:` lists and instructions before using the new package. A removed
ref without a repo-local copy fails validation, creation, and composition;
existing repo-local overrides remain repo-owned. A development topic is
available only from a checkout that authors it, never as a package fallback.

## Renamed user topics

These new refs continue to ship. Old spellings below are migration history,
not usable references.

| Previous ref | Shipped ref |
| --- | --- |
| `coga/internals/human-assist` | `coga/human-assist` |
| `coga/internals/pr-publication` | `coga/pr-publication` |
| `coga/internals/pr-publication/existing-pr` | `coga/pr-publication/existing-pr` |
| `coga/internals/pr-publication/preparation` | `coga/pr-publication/preparation` |
| `coga/internals/state-publication/authoring` | `coga/state-publication/authoring` |
| `coga/internals/state-publication/sweep` | `coga/state-publication/sweep` |

## Split topics

| Previous topic | Shipped user knowledge | Local-only development knowledge |
| --- | --- | --- |
| `coga/testing` | `coga/sandboxes` — restrictions and grants | `coga-dev/testing` — suite, test environments, receipts |
| `coga/packaging` | `coga/edge-code` — shims, upgrades, forks; `coga/context-layout` — distribution and overrides | `coga-dev/packaging` — twins and wheel construction |
| `coga/extension-model` | Same ref — repo extension choices, recipes, aliases | `coga-dev/microkernel` — core placement and migrations |
| `coga/knowledge` | Same ref — fact ownership, attach versus cite | `coga-dev/archive-access` — this repo’s archive rule |
| `coga/internals/state-publication` | `coga/state-publication` — roots, eligibility, publication hazard | `coga-dev/internals/state-publication` — invariants and machinery |

The supporting `edge-code-upgrades.md` moves from the packaging topic to
`coga/edge-code/edge-code-upgrades.md`.

## Development topics removed from the package

Every target below is local-only. The two posture topics were already
local-only; they are renamed with the rest of the development audience.
The local-only remainders of all five split topics above also do not ship.

| Previous ref | Local-only ref |
| --- | --- |
| `coga/codebase` | `coga-dev/codebase` |
| `coga/codebase/gotchas` | `coga-dev/codebase/gotchas` |
| `coga/current-direction` | `coga-dev/current-direction` |
| `coga/internals/activity-capture` | `coga-dev/internals/activity-capture` |
| `coga/internals/agent-spawn` | `coga-dev/internals/agent-spawn` |
| `coga/internals/assist-publication` | `coga-dev/internals/assist-publication` |
| `coga/internals/claim-recovery` | `coga-dev/internals/claim-recovery` |
| `coga/internals/git-refresh` | `coga-dev/internals/git-refresh` |
| `coga/internals/git-regressions` | `coga-dev/internals/git-regressions` |
| `coga/internals/launch-claims` | `coga-dev/internals/launch-claims` |
| `coga/internals/recurring-admission` | `coga-dev/internals/recurring-admission` |
| `coga/internals/recurring-control` | `coga-dev/internals/recurring-control` |
| `coga/internals/recurring-temp-worktrees` | `coga-dev/internals/recurring-temp-worktrees` |
| `coga/internals/spool-merge` | `coga-dev/internals/spool-merge` |
| `coga/internals/state-publication/publish` | `coga-dev/internals/state-publication/publish` |
| `coga/launch-internals` | `coga-dev/internals` |
| `coga/patterns` | `coga-dev/patterns` |
| `coga/principles` | `coga-dev/principles` |
| `coga/project-stage` | `coga-dev/project-stage` |

The principles reading list moves with its parent and no longer ships.
Maintainer release and clean-install skills retain their existing names and
distribution; this change concerns contexts. Job contracts already moved to
their recurring tickets or skills are not recreated as contexts.

After updating refs, run `coga validate --json` in the adopting repo.
