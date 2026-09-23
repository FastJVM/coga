# Coga documentation

One library for people and agents. Every reusable topic is a file under
[`contexts/`](contexts/): you read it here, and a ticket attaches the same
file by ref (`contexts: [coga/launch]`) to put it in an agent's prompt. A
link never loads anything — a task gets exactly the refs it lists. How a
fact picks its single home is [coga/knowledge](contexts/coga/knowledge/SKILL.md).

Pages outside `contexts/` are for reading, never composed into prompts:
[`evidence/`](#evidence-and-positioning) (dated measurements and
comparisons), [`design/`](#proposals-and-history) (unbuilt proposals), and
[`archive/`](#proposals-and-history) (history).

## Start

1. [Install](contexts/coga/install/SKILL.md) the CLI.
2. [Set up a repo](contexts/coga/init/SKILL.md) — fresh, or a clone of one
   already using Coga.
3. [Take a first task](contexts/coga/first-task/SKILL.md) from draft to PR.
4. [Remove Coga](contexts/coga/uninstall/SKILL.md) if you need to.

## Understand

- [Principles](contexts/coga/principles/SKILL.md) — the seven constraints.
- [Architecture](contexts/coga/architecture/SKILL.md) — the model, the
  correction loop, and a map of every topic.
- The work unit: [tickets](contexts/coga/tickets/SKILL.md),
  [lifecycle](contexts/coga/lifecycle/SKILL.md),
  [workflows](contexts/coga/workflows/SKILL.md),
  [blackboard](contexts/coga/blackboard/SKILL.md).
- What the agent sees: [prompt composition](contexts/coga/prompt-composition/SKILL.md),
  [session conduct](contexts/coga/session-conduct/SKILL.md),
  [knowledge placement](contexts/coga/knowledge/SKILL.md).

## Operate

- Commands: the [CLI index](contexts/coga/cli/SKILL.md) points each command
  at its owning topic.
- Configuration: [coga.toml and local config](contexts/coga/configuration/SKILL.md),
  [directory layout](contexts/coga/context-layout/SKILL.md),
  [agents](contexts/coga/agents/SKILL.md),
  [secrets](contexts/coga/secrets/SKILL.md).
- Running work: [launch](contexts/coga/launch/SKILL.md),
  [script tickets](contexts/coga/script-tickets/SKILL.md),
  [megalaunch queue](contexts/coga/megalaunch/SKILL.md).
- Recurring jobs: [overview](contexts/coga/recurring/SKILL.md),
  [templates](contexts/coga/recurring/templates/SKILL.md),
  [scheduling](contexts/coga/recurring/scheduling/SKILL.md),
  [delegation](contexts/coga/recurring/delegation/SKILL.md),
  [autofix](contexts/coga/recurring/autofix/SKILL.md),
  [period tasks](contexts/coga/period-task/SKILL.md),
  [Dream](contexts/coga/dream/SKILL.md).
- Team sync: [Git state overview](contexts/coga/sync/SKILL.md),
  [notifications](contexts/coga/notifications/SKILL.md)
  ([producers](contexts/coga/notifications/producers/SKILL.md),
  [failures](contexts/coga/notifications/failures/SKILL.md)),
  [coga-important](contexts/coga/important/SKILL.md),
  [usage records](contexts/coga/usage/SKILL.md),
  [weekly telemetry](contexts/coga/telemetry/SKILL.md) (opt-out, and the
  [operator runbook](telemetry.md) for release verification, read-back and
  deletion),
  [reusable patterns](contexts/coga/patterns/SKILL.md).
- Browser work: [API first](contexts/browser/api-first/SKILL.md),
  [DOM-backed runners](contexts/browser/dom-backed/SKILL.md).

Internals — exact guarantees, for changing or debugging Coga:
[launch internals index](contexts/coga/launch-internals/SKILL.md)
([agent spawn](contexts/coga/internals/agent-spawn/SKILL.md),
[human assist](contexts/coga/internals/human-assist/SKILL.md),
[assist publication](contexts/coga/internals/assist-publication/SKILL.md),
[launch claims](contexts/coga/internals/launch-claims/SKILL.md),
[claim recovery](contexts/coga/internals/claim-recovery/SKILL.md),
[PR publication](contexts/coga/internals/pr-publication/SKILL.md));
recurring ([admission](contexts/coga/internals/recurring-admission/SKILL.md),
[control](contexts/coga/internals/recurring-control/SKILL.md),
[temporary worktrees](contexts/coga/internals/recurring-temp-worktrees/SKILL.md));
Git state ([publication](contexts/coga/internals/state-publication/SKILL.md),
[regressions](contexts/coga/internals/git-regressions/SKILL.md),
[refresh](contexts/coga/internals/git-refresh/SKILL.md),
[union merges](contexts/coga/internals/spool-merge/SKILL.md));
[activity capture](contexts/coga/internals/activity-capture/SKILL.md).

## Develop

- [Codebase](contexts/coga/codebase/SKILL.md) source map and
  [gotchas](contexts/coga/codebase/gotchas/SKILL.md).
- [Extension model](contexts/coga/extension-model/SKILL.md) — core versus
  edge, aliases, recipes. [Skill management](contexts/coga/skill-management/SKILL.md).
- [Testing](contexts/coga/testing/SKILL.md),
  [packaging](contexts/coga/packaging/SKILL.md),
  [releasing](contexts/coga/releasing/SKILL.md).
- Code-task conventions: [overview](contexts/dev/code/SKILL.md),
  [checkouts](contexts/dev/checkouts/SKILL.md),
  [the `## Dev` record](contexts/dev/dev-record/SKILL.md),
  [design history](contexts/dev/design-history/SKILL.md),
  [checkout cleanup](contexts/dev/checkout-cleanup/SKILL.md).
- This repo's posture (dated, local to this repo):
  [current direction](contexts/coga/current-direction/SKILL.md),
  [project stage](contexts/coga/project-stage/SKILL.md),
  [roadmap](contexts/coga/roadmap/SKILL.md).

## Evidence and positioning

- [Product vision](contexts/product/vision/SKILL.md) — purpose, audience,
  bet, limits.
- Marketing: [map](contexts/marketing/map/SKILL.md),
  [positioning](contexts/marketing/positioning/SKILL.md),
  [strategy](contexts/marketing/strategy/SKILL.md),
  [plan](contexts/marketing/plan/SKILL.md),
  [distribution](contexts/marketing/distribution/SKILL.md).
- Dated evidence (read the date and scope on each page before reusing a
  claim): [velocity](evidence/velocity.md),
  [usage comparison](evidence/usage-comparison.md),
  [build vs adopt](evidence/build-vs-adopt.md),
  [why switch](evidence/why-switch-to-coga.md),
  [pitch evaluation](evidence/pitch-evaluation.md),
  [continuity](evidence/continuity-comparison.md),
  [human-centred comparison](evidence/human-centered-comparison.md),
  [research-work comparison](evidence/research-work-comparison.md),
  [research replacement trial](evidence/research-replacement-trial.md),
  [adoption trial](evidence/adoption-trial.md),
  [upkeep audit](evidence/upkeep-audit.md).

## Proposals and history

- Unbuilt designs: [CLI extension audit](design/cli-extension-audit.md),
  [CLI external surface](design/cli-external-surface.md).
- Archive: [origins](archive/origins.md),
  [market landscape](archive/market-landscape.md),
  [superseded decisions](archive/superseded-decisions.md),
  [launch programs](archive/launch-programs/README.md),
  [Relay → Coga migration](archive/relay-migration.md).
- [Context migration record](context-migration.md) — old paths and refs,
  where each went, and the cutover.
- Team-specific: [Google Drive MCP](contexts/docs/gdrive-mcp/SKILL.md)
  (dated 2026-06).
