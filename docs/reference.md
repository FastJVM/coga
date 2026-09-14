# Command guide

The canonical command-behavior reference is the
[`coga/cli` context](../src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md).
This page helps you find it by task; command arguments, flags, and lifecycle
rules live there. For the syntax supported by your installed version, run
`coga --help` and `coga <command> --help`.

## Set up a repository

Use `coga init` to prepare Coga in a Git repository or finish local setup after
cloning a repo that already uses it. Use `coga uninstall` to remove its
footprint. Read [Getting started](getting-started.md) for the onboarding path
and the [setup reference](../src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md)
for the command contracts.

## Author and direct work

`coga create` drafts a ticket; `coga ticket` guides its authoring. `coga launch`
starts or resumes its work. `coga mark`, `coga bump`, `coga block`, and
`coga unblock` express lifecycle decisions and handoffs. Consult the
[ticket command reference](../src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md)
for each transition's conditions, and [Concepts](concepts.md) for the model.

## Inspect the workspace

`coga status`, `coga show`, `coga usage`, and `coga validate` expose current
work, history, recorded usage, and structural diagnostics. The
[inspection reference](../src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md)
describes their scope and options.

## Run queues and maintenance

`coga megalaunch` services selected work, while `coga recurring` runs recurring
templates. `coga dream`, `coga autoclose`, and `coga retire` support maintenance
and completed work. `coga run` invokes the fixed recipe registry. Read the
[queue and maintenance reference](../src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md)
for admission and completion rules, or [Operations](operations.md) for a tour.

## Manage skills and integrations

`coga skill` manages project skills. `coga slack` sends an explicit FYI and
`coga secret` exposes the human-facing secret lookup. The
[integration reference](../src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md)
owns their contracts; [Operations](operations.md) explains their place in daily
work.
