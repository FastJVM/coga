# Coga documentation

One library for people and agents. Every reusable topic is a file under
[`contexts/`](contexts/): you read it here, and a ticket attaches the same
file by ref (`contexts: [coga/launch]`) to put it in an agent's prompt. A
link never loads anything — ticket contexts include exactly the refs listed.
How a fact picks its single home is [coga/knowledge](contexts/coga/knowledge/SKILL.md).

Pages outside `contexts/` are for reading, never composed into prompts:
[`archive/`](#proposals-and-history) holds history, including dated
measurements and comparisons in [`archive/evidence/`](archive/evidence/)
and unimplemented proposals in [`archive/design/`](archive/design/).

## Start

1. [Install](contexts/coga/install/SKILL.md) the CLI.
2. [Set up a repo](contexts/coga/init/SKILL.md) — fresh, or a clone of one
   already using Coga.
3. [Take a first task](contexts/coga/first-task/SKILL.md) from draft to PR.
4. [Remove Coga](contexts/coga/uninstall/SKILL.md) if you need to.

## Understand

- The three concepts, as the [project README](../README.md#key-concepts)
  defines them: a [ticket](contexts/coga/tickets/SKILL.md) (one piece of
  work, disposable once done), a [context block](contexts/coga/knowledge/SKILL.md)
  (a durable fact with one owning file), and a
  [workflow](contexts/coga/workflows/SKILL.md) (the steps for one kind of
  work).
- [Design principles](contexts/coga/principles/SKILL.md) — philosophy and design principles.
- [Architecture](contexts/coga/architecture/SKILL.md) — the model, the
  correction loop, and a map of every topic.
- The work unit: [tickets](contexts/coga/tickets/SKILL.md)
  ([discovery](contexts/coga/tickets/discovery/SKILL.md),
  [authoring](contexts/coga/tickets/authoring/SKILL.md),
  [ownership](contexts/coga/tickets/ownership/SKILL.md)),
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
  [scheduling](contexts/coga/recurring/scheduling/SKILL.md)
  ([ledger](contexts/coga/recurring/scheduling/ledger/SKILL.md),
  [inactivity](contexts/coga/recurring/scheduling/inactivity/SKILL.md),
  [failures](contexts/coga/recurring/scheduling/failures/SKILL.md)),
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
  [reusable patterns](contexts/coga/patterns/SKILL.md).

Internals — exact guarantees, for changing or debugging Coga:
[launch internals index](contexts/coga/launch-internals/SKILL.md)
([agent spawn](contexts/coga/internals/agent-spawn/SKILL.md),
[human assist](contexts/coga/internals/human-assist/SKILL.md),
[assist publication](contexts/coga/internals/assist-publication/SKILL.md),
[launch claims](contexts/coga/internals/launch-claims/SKILL.md),
[claim recovery](contexts/coga/internals/claim-recovery/SKILL.md),
[PR publication](contexts/coga/internals/pr-publication/SKILL.md):
[preparation](contexts/coga/internals/pr-publication/preparation/SKILL.md),
[existing PR](contexts/coga/internals/pr-publication/existing-pr/SKILL.md));
recurring ([admission](contexts/coga/internals/recurring-admission/SKILL.md),
[control](contexts/coga/internals/recurring-control/SKILL.md),
[temporary worktrees](contexts/coga/internals/recurring-temp-worktrees/SKILL.md));
Git state ([publication](contexts/coga/internals/state-publication/SKILL.md):
[publish](contexts/coga/internals/state-publication/publish/SKILL.md),
[sweep](contexts/coga/internals/state-publication/sweep/SKILL.md),
[authoring](contexts/coga/internals/state-publication/authoring/SKILL.md);
[regressions](contexts/coga/internals/git-regressions/SKILL.md),
[refresh](contexts/coga/internals/git-refresh/SKILL.md),
[union merges](contexts/coga/internals/spool-merge/SKILL.md));
[activity capture](contexts/coga/internals/activity-capture/SKILL.md).

## Develop

- [Codebase](contexts/coga/codebase/SKILL.md) source map and
  [gotchas](contexts/coga/codebase/gotchas/SKILL.md).
- [Extension model](contexts/coga/extension-model/SKILL.md) — core versus
  edge, aliases, recipes. [Skill management](contexts/coga/skill-management/SKILL.md).
- [Weekly telemetry](contexts/coga/telemetry/SKILL.md) (opt-out) and its
  [operator runbook](contexts/coga/telemetry/operations/SKILL.md) for release
  verification, read-back and deletion.
- [Testing](contexts/coga/testing/SKILL.md) and its clean-install harnesses
  ([Linux](contexts/coga/testing/clean-install/SKILL.md),
  [macOS on AWS](contexts/coga/testing/clean-install/macos-aws/SKILL.md)),
  [packaging](contexts/coga/packaging/SKILL.md),
  [releasing](contexts/coga/releasing/SKILL.md).
- Code-task conventions: [overview](contexts/dev/code/SKILL.md),
  [checkouts](contexts/dev/checkouts/SKILL.md)
  ([launch boundary](contexts/dev/checkouts/launch-boundary/SKILL.md),
  [sandbox clone](contexts/dev/checkouts/sandbox-clone/SKILL.md)),
  [the `## Dev` record](contexts/dev/dev-record/SKILL.md),
  [design history](contexts/dev/design-history/SKILL.md),
  [checkout cleanup](contexts/dev/checkout-cleanup/SKILL.md)
  ([proofs](contexts/dev/checkout-cleanup/proofs/SKILL.md),
  [foreign ownership](contexts/dev/checkout-cleanup/foreign-ownership/SKILL.md),
  [terminal owners](contexts/dev/checkout-cleanup/terminal-owners/SKILL.md),
  [branch sweep](contexts/dev/checkout-cleanup/branch-sweep/SKILL.md)).
- This repo's posture (dated, local to this repo):
  [current direction](contexts/coga/current-direction/SKILL.md),
  [project stage](contexts/coga/project-stage/SKILL.md).

## Product and positioning

- [Design principles](contexts/coga/principles/SKILL.md) — philosophy and design principles.
- Marketing: [map](contexts/marketing/map/SKILL.md),
  [positioning](contexts/marketing/positioning/SKILL.md),
  [strategy](contexts/marketing/strategy/SKILL.md),
  [plan](contexts/marketing/plan/SKILL.md).

## Proposals and history

- Archived evidence (read the date and scope on each page before reusing a
  claim): [agent memory landscape](archive/evidence/agent-memory-landscape-2026-10-13.md),
  [velocity](archive/evidence/velocity.md),
  [admin and patent flexibility](archive/evidence/admin-and-patent-flexibility-2026-09-12.md),
  [Claude cache TTL survey](archive/evidence/claude-cache-ttl-survey.md),
  [macOS clean-install runs](archive/evidence/macos-clean-install-runs-2026-10.md).
- Archived, unimplemented design: [CLI external surface](archive/design/cli-external-surface.md).
- Archive: [origins](archive/origins.md),
  [market landscape](archive/market-landscape.md),
  [superseded decisions](archive/superseded-decisions.md),
  [launch programs](archive/launch-programs/README.md),
  [Relay → Coga migration](archive/relay-migration.md),
  [browser automation](archive/browser-automation.md),
  [Google Doc workflow](archive/create-google-doc-workflow.md),
  [roadmap](archive/roadmap.md),
  [marketing distribution](archive/marketing-distribution.md),
  [context migration record](archive/context-migration.md),
  [CLI extension audit](archive/cli-extension-audit.md),
  [Google Drive MCP observations](archive/gdrive-mcp.md),
  [positioning before the README reset](archive/positioning-before-readme-2026-10-13.md).
- Archived evidence from the September pitch and build-versus-adopt research:
  [usage comparison](archive/evidence/usage-comparison.md),
  [build vs adopt](archive/evidence/build-vs-adopt.md),
  [why switch](archive/evidence/why-switch-to-coga.md),
  [pitch evaluation](archive/evidence/pitch-evaluation.md),
  [continuity](archive/evidence/continuity-comparison.md),
  [human-centred comparison](archive/evidence/human-centered-comparison.md),
  [research-work comparison](archive/evidence/research-work-comparison.md),
  [research replacement trial](archive/evidence/research-replacement-trial.md),
  [adoption trial](archive/evidence/adoption-trial.md),
  [upkeep audit](archive/evidence/upkeep-audit.md),
  [independent-clone incident](archive/evidence/independent-clone-worklist-2026-09.md),
  [branch cleanup audit](archive/evidence/branch-cleanup-audit-2026-10-05.md).
