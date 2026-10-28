# Coga documentation

The [project README](../README.md) explains what Coga is and shows the
workflow. This index is for finding the details: using Coga in a repository,
understanding its files and commands, or contributing to Coga itself.

## Start

1. [Get started](../README.md#get-started) — install Coga and check prerequisites.
2. [Set up a repo](contexts/coga/init/SKILL.md) — fresh, or a clone already using Coga.
3. [Take a first task](contexts/coga/first-task/SKILL.md) from draft to PR.
4. [Remove Coga](contexts/coga/uninstall/SKILL.md) if you need to.

For installation alternatives, troubleshooting, and platform boundaries, see
the [installation reference](contexts/coga/install/SKILL.md). The project README
is the primary first-install path.

## Understand

Coga keeps work readable and editable across agent sessions. Its
[building blocks](../README.md#what-lives-in-your-repo) are
[tickets](contexts/coga/tickets/SKILL.md) for units of work,
[contexts](contexts/coga/knowledge/SKILL.md) for lasting knowledge,
[workflows](contexts/coga/workflows/SKILL.md) for steps and review gates,
and [history](../coga/log.md) for recorded transitions.

- [Architecture](contexts/coga/architecture/SKILL.md) — the model and the
  correction loop.
- [Finding tickets](contexts/coga/tickets/discovery/SKILL.md) and
  [writing them](contexts/coga/tickets/authoring/SKILL.md) —
  [lifecycle](contexts/coga/lifecycle/SKILL.md) and
  [blackboard](contexts/coga/blackboard/SKILL.md).
- [Prompt composition](contexts/coga/prompt-composition/SKILL.md) — what an
  agent receives; [knowledge placement](contexts/coga/knowledge/SKILL.md) —
  which context belongs with a task.
- The [annotated ticket template](../src/coga/resources/ticket.md) explains
  the fields in new tickets.

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
  ([inactivity](contexts/coga/recurring/scheduling/inactivity/SKILL.md)),
  [delegation](contexts/coga/recurring/delegation/SKILL.md),
  [autofix](contexts/coga/recurring/autofix/SKILL.md),
  [period tasks](contexts/coga/period-task/SKILL.md),
  [Dream](../coga/recurring/dream/ticket.md).
- Team sync: [Git state overview](contexts/coga/sync/SKILL.md),
  [notifications](contexts/coga/notifications/SKILL.md)
  ([producers](contexts/coga/notifications/producers/SKILL.md)),
  [coga-important](contexts/coga/important/SKILL.md),
  [usage records](contexts/coga/usage/SKILL.md),
  [state publication](contexts/coga/state-publication/SKILL.md).

- Publication: [PRs](contexts/coga/pr-publication/SKILL.md)
  ([preparation](contexts/coga/pr-publication/preparation/SKILL.md));
  [human assists](contexts/coga/human-assist/SKILL.md);
  [state publication and recovery](contexts/coga/state-publication/SKILL.md).
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

If you want to change Coga, start with [Contributing](../CONTRIBUTING.md).
The local-only Coga-dev topics and maintainer skills cover implementation:

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

## How this library works

The same Markdown topics are read by people and can be attached to agents'
prompts. Topics live under [`contexts/`](contexts/). A ticket attaches a
context by its ref (for example, `contexts: [coga/launch]`); a Markdown
link is only navigation and does **not** load that topic into the prompt.

There are two audiences. [User topics](contexts/coga/) under `coga/`
describe what an adopting repository needs to run Coga and ship as packaged
fallbacks. [Coga-dev topics](contexts/coga-dev/) under `coga-dev/`
describe Coga's implementation and stay in this source repository.
[Context layout](contexts/coga/context-layout/SKILL.md#context-audiences)
defines the boundary; [knowledge placement](contexts/coga/knowledge/SKILL.md)
defines where facts belong. For older context refs, see the
[migration note](release-notes/context-audiences.md).

## Proposals and history

These are historical documents, **not current instructions**. Dated evidence
and earlier decisions can be useful, but agents must not read or search the
archive without an explicit human request
([archive access rule](contexts/coga-dev/archive-access/SKILL.md#archive-access)).

- [Archived evidence](archive/evidence/) — dated investigations, comparisons,
  and test results.
- [Archived designs](archive/design/) — proposals that may never have shipped.
- [Other history](archive/) — origins, prior positioning, migrations, and
  retired plans; see the [superseded decisions](archive/superseded-decisions.md)
  and [context migration record](archive/context-migration.md) for those topics.
