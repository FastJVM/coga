# Coga documentation

The [project README](../README.md) explains what Coga is and shows the
workflow. This index is for finding the details: using Coga in a repository,
understanding its files and commands, or contributing to Coga itself.

## Start

1. [Get started](../README.md#get-started) — install Coga and check prerequisites.
2. [Set up a repo](../src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md) — fresh, or a clone already using Coga.
3. [Take a first task](../src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md) from draft to PR.
4. [Remove Coga](../src/coga/resources/templates/coga/bootstrap/contexts/coga/uninstall/SKILL.md) if you need to.

The project README's Get started section is the only install path. The
native Windows boundary is in
[coga/launch](../src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md#phases-and-routing).

## Understand

Coga keeps work readable and editable across agent sessions. Its
[building blocks](../README.md#what-lives-in-your-repo) are
[tickets](../src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/SKILL.md) for units of work,
[contexts](../src/coga/resources/templates/coga/bootstrap/contexts/coga/knowledge/SKILL.md) for lasting knowledge,
[workflows](../src/coga/resources/templates/coga/bootstrap/contexts/coga/workflows/SKILL.md) for steps and review gates,
and [history](../coga/log.md) for recorded transitions.

- [Architecture](../src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md) — the model and the
  correction loop.
- Working with tickets: [discovery](../src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/discovery/SKILL.md),
  [authoring](../src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/authoring/SKILL.md),
  [lifecycle](../src/coga/resources/templates/coga/bootstrap/contexts/coga/lifecycle/SKILL.md), and
  [blackboard](../src/coga/resources/templates/coga/bootstrap/contexts/coga/blackboard/SKILL.md).
- [Prompt composition](../src/coga/resources/templates/coga/bootstrap/contexts/coga/prompt-composition/SKILL.md) — what an
  agent receives; [knowledge placement](../src/coga/resources/templates/coga/bootstrap/contexts/coga/knowledge/SKILL.md) —
  which context belongs with a task.
- The [annotated ticket template](../src/coga/resources/ticket.md) explains
  the fields in new tickets.

## Operate

- Commands: the [CLI index](../src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md) points each command
  at its owning topic.
- Configuration: [coga.toml and local config](../src/coga/resources/templates/coga/bootstrap/contexts/coga/configuration/SKILL.md),
  [directory layout](../src/coga/resources/templates/coga/bootstrap/contexts/coga/context-layout/SKILL.md),
  [secrets](../src/coga/resources/templates/coga/bootstrap/contexts/coga/secrets/SKILL.md).
- Running work: [launch](../src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md),
  [script tickets](../src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md),
  [megalaunch queue](../src/coga/resources/templates/coga/bootstrap/contexts/coga/megalaunch/SKILL.md).
- Recurring jobs: [overview](../src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/SKILL.md),
  [templates](../src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/templates/SKILL.md),
  [scheduling](../src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md)
  ([inactivity](../src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/inactivity/SKILL.md)),
  [delegation](../src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/delegation/SKILL.md),
  [autofix](../src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/autofix/SKILL.md),
  [period tasks](../src/coga/resources/templates/coga/bootstrap/contexts/coga/period-task/SKILL.md),
  [Dream](../src/coga/resources/templates/coga/recurring/dream/ticket.md).
- Team sync: [Git state overview](../src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md),
  [notifications](../src/coga/resources/templates/coga/bootstrap/contexts/coga/notifications/SKILL.md)
  ([producers](../src/coga/resources/templates/coga/bootstrap/contexts/coga/notifications/producers/SKILL.md)),
  [coga-important](../src/coga/resources/templates/coga/bootstrap/contexts/coga/important/SKILL.md), and
  [usage records](../src/coga/resources/templates/coga/bootstrap/contexts/coga/usage/SKILL.md).

- Publication: [PRs](../src/coga/resources/templates/coga/bootstrap/contexts/coga/pr-publication/SKILL.md)
  ([preparation](../src/coga/resources/templates/coga/bootstrap/contexts/coga/pr-publication/preparation/SKILL.md));
  [human assists](../src/coga/resources/templates/coga/bootstrap/contexts/coga/human-assist/SKILL.md);
  [state publication and recovery](../src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md).
- Extending and recovering a repo: [extension choices](../src/coga/resources/templates/coga/bootstrap/contexts/coga/extension-model/SKILL.md),
  [edge code and forks](../src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/SKILL.md),
  [agent sandboxes](../src/coga/resources/templates/coga/bootstrap/contexts/coga/sandboxes/SKILL.md).

- Code-task conventions: [checkouts](../src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md)
  ([launch boundary](../src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/launch-boundary/SKILL.md),
  [sandbox clone](../src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/sandbox-clone/SKILL.md)),
  [design history](../src/coga/resources/templates/coga/bootstrap/contexts/coga/blackboard/SKILL.md#superseded-designs),
  [checkout cleanup](../src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/SKILL.md)
  ([terminal owners](../src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/terminal-owners/SKILL.md),
  [branch sweep](../src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/branch-sweep/SKILL.md)).

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
- [Weekly telemetry](../src/coga/resources/templates/coga/recurring/phone-home/ticket.md) (opt-out) and its
  [operator runbook](../src/coga/resources/templates/coga/recurring/phone-home/operations.md) for release
  verification, read-back and deletion.
- [Testing](contexts/coga-dev/testing/SKILL.md) and the clean-install skills
  ([Linux](../src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/SKILL.md),
  [macOS on AWS](../src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/macos-aws/SKILL.md),
  [Windows on AWS](../src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/windows-aws/SKILL.md),
  [attended human walk](../coga/skills/coga/testing/clean-install/human-walk/SKILL.md)
  on a [fresh VM](../coga/skills/coga/testing/fresh-vm/SKILL.md)),
  [packaging](contexts/coga-dev/packaging/SKILL.md),
  [release skill](../src/coga/resources/templates/coga/bootstrap/skills/coga/releasing/SKILL.md).
- This repo's posture (dated, local to this repo):
  [current direction](contexts/coga-dev/current-direction/SKILL.md),
  [project stage](contexts/coga-dev/project-stage/SKILL.md).

## How this library works

The same Markdown topics are read by people and can be attached to agents'
prompts. A ticket attaches a
context by its ref (for example, `contexts: [coga/launch]`); a Markdown
link is only navigation and does **not** load that topic into the prompt.

There are two audiences. [User topics](../src/coga/resources/templates/coga/bootstrap/contexts/coga/) under `coga/`
describe what an adopting repository needs to run Coga and ship as packaged
fallbacks. [Coga-dev topics](contexts/coga-dev/) under `coga-dev/`
describe Coga's implementation and stay in this source repository.
[Context layout](../src/coga/resources/templates/coga/bootstrap/contexts/coga/context-layout/SKILL.md#context-audiences)
defines the boundary; [knowledge placement](../src/coga/resources/templates/coga/bootstrap/contexts/coga/knowledge/SKILL.md)
defines where facts belong. For older context refs, see the
[migration note](release-notes/context-audiences.md). Shipped definitions are
owned by the package and resolved local-first; the
[package-definitions note](release-notes/package-definitions.md) covers
recurring selection, state carriers and migrating an existing repo. This
source repo uses those package owners directly; there is no second user-topic
tree under `docs/contexts/`. Its local topics are the Coga-dev library above.

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
