# Coga documentation

One library for people and agents. Every reusable topic is a file under
[`contexts/`](contexts): you read it here, and a ticket attaches the same
file by ref (`contexts: [coga/launch]`) to put it in an agent's prompt. A
link never loads anything — ticket contexts include exactly the refs listed.
How a fact picks its single home is [coga/knowledge](contexts/coga/knowledge/SKILL.md).

The library has two audiences. **User topics** under `coga/`
are needed to configure, launch, author, recover, or understand refusals in
any repo using Coga; they ship as bootstrap fallbacks. **Coga-dev topics**
under `coga-dev/` explain building, testing, releasing, or steering Coga
itself and stay local. Anything a shipped surface requires must be user
knowledge. [Context layout](contexts/coga/context-layout/SKILL.md#context-audiences)
owns the criterion; choose the set for the task before attaching topics.

The [next-release migration note](release-notes/context-audiences.md) lists
renamed refs and topics removed from the package.

Pages outside `contexts/` are for reading, never composed into prompts:
[`archive/`](#proposals-and-history) holds history, including dated
measurements and comparisons in [`archive/evidence/`](archive/evidence)
and unimplemented proposals in [`archive/design/`](archive/design).
Agent access to archives requires an explicit human request; see
[the archive access rule](contexts/coga-dev/archive-access/SKILL.md#archive-access).

## Start

1. [Install](contexts/coga/install/SKILL.md) the CLI.
2. [Set up a repo](contexts/coga/init/SKILL.md) — fresh, or a clone of one
   already using Coga.
3. [Take a first task](contexts/coga/first-task/SKILL.md) from draft to PR.
4. [Remove Coga](contexts/coga/uninstall/SKILL.md) if you need to.

New tickets include a field guide from the
[annotated template](../src/coga/resources/ticket.md).

## Understand

- The three concepts, as the [project README](../README.md#key-concepts)
  defines them: a [ticket](contexts/coga/tickets/SKILL.md) (one piece of
  work, disposable once done), a [context block](contexts/coga/knowledge/SKILL.md)
  (a durable fact with one owning file), and a
  [workflow](contexts/coga/workflows/SKILL.md) (the steps for one kind of
  work).
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
  [Dream](../coga/recurring/dream/ticket.md).
- Team sync: [Git state overview](contexts/coga/sync/SKILL.md),
  [notifications](contexts/coga/notifications/SKILL.md)
  ([producers](contexts/coga/notifications/producers/SKILL.md),
  [failures](contexts/coga/notifications/failures/SKILL.md)),
  [coga-important](contexts/coga/important/SKILL.md),
  [usage records](contexts/coga/usage/SKILL.md),
  [state publication](contexts/coga/state-publication/SKILL.md).

- Publication: [PRs](contexts/coga/pr-publication/SKILL.md)
  ([preparation](contexts/coga/pr-publication/preparation/SKILL.md),
  [existing PRs](contexts/coga/pr-publication/existing-pr/SKILL.md));
  [human assists](contexts/coga/human-assist/SKILL.md);
  [state authoring](contexts/coga/state-publication/authoring/SKILL.md) and
  [sweep recovery](contexts/coga/state-publication/sweep/SKILL.md).
- Extending and recovering a repo: [extension choices](contexts/coga/extension-model/SKILL.md),
  [edge code and forks](contexts/coga/edge-code/SKILL.md),
  [agent sandboxes](contexts/coga/sandboxes/SKILL.md).

- Code-task conventions: [checkouts](contexts/coga/checkouts/SKILL.md)
  ([launch boundary](contexts/coga/checkouts/launch-boundary/SKILL.md),
  [sandbox clone](contexts/coga/checkouts/sandbox-clone/SKILL.md)),
  [design history](contexts/coga/blackboard/SKILL.md#superseded-designs),
  [checkout cleanup](contexts/coga/checkout-cleanup/SKILL.md)
  ([terminal owners](contexts/coga/checkout-cleanup/terminal-owners/SKILL.md),
  [branch sweep](contexts/coga/checkout-cleanup/branch-sweep/SKILL.md)).

## Develop Coga

The local-only Coga-dev set and the skills used by Coga maintainers:

- [Design principles](contexts/coga-dev/principles/SKILL.md),
  [patterns](contexts/coga-dev/patterns/SKILL.md), and the
  [microkernel boundary](contexts/coga-dev/microkernel/SKILL.md).
- [Internals index](contexts/coga-dev/internals/SKILL.md) for concurrency,
  publication transactions, recurring admission, and activity capture.
- [Codebase](contexts/coga-dev/codebase/SKILL.md) source map and
  [gotchas](contexts/coga-dev/codebase/gotchas/SKILL.md).
- [Weekly telemetry](../coga/recurring/phone-home/ticket.md) (opt-out) and its
  [operator runbook](../coga/recurring/phone-home/operations.md) for release
  verification, read-back and deletion.
- [Testing](contexts/coga-dev/testing/SKILL.md) and the clean-install skills
  ([Linux](../coga/skills/coga/testing/clean-install/SKILL.md),
  [macOS on AWS](../coga/skills/coga/testing/clean-install/macos-aws/SKILL.md),
  [Windows on AWS](../coga/skills/coga/testing/clean-install/windows-aws/SKILL.md)),
  [packaging](contexts/coga-dev/packaging/SKILL.md),
  [release skill](../coga/skills/coga/releasing/SKILL.md).
- This repo's posture (dated, local to this repo):
  [current direction](contexts/coga-dev/current-direction/SKILL.md),
  [project stage](contexts/coga-dev/project-stage/SKILL.md).

## Product and positioning

- [Design principles](contexts/coga-dev/principles/SKILL.md) — philosophy and design principles.
- [README](../README.md) — current public presentation.

## Proposals and history

- [Retired marketing contexts](archive/marketing-contexts-2026-10-15/README.md) —
  planning behind the README, idea piece and launch.

- Archived evidence (read the date and scope on each page before reusing a
  claim): [agent memory landscape](archive/evidence/agent-memory-landscape-2026-10-13.md),
  [velocity](archive/evidence/velocity.md),
  [admin and patent flexibility](archive/evidence/admin-and-patent-flexibility-2026-09-12.md),
  [Claude cache TTL survey](archive/evidence/claude-cache-ttl-survey.md),
  [macOS clean-install runs](archive/evidence/macos-clean-install-runs-2026-10.md),
  [Dream under codex scratch runs](archive/evidence/dream-under-codex-scratch-runs-2026-09.md).
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
