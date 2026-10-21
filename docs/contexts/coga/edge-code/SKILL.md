---
name: coga/edge-code
description: Wheel-owned edge implementations, repo shims, upgrades, and explicit local forks.
---

# Using wheel-owned edge code

## Wheel-owned edge implementations

`src/coga_edge/` ships beside `src/coga/` in the **same distribution**, with
one version and install transaction, no extra dependency, registry or CLI.
Edge modules may import shared `coga` infrastructure; core never
imports edge implementations. Repo shims select the implementation. `coga_edge/__init__.py`
has no eager job imports or side effects.

A repo-owned `ticket.py` may import a stable module `main` and return its exit
code. Init seeds that shim; recurring creation copies its bytes. On the next
process invocation it uses the installed implementation, even if the template
script later changes or disappears. The shim contains no job logic or duplicate
completion. A missing module is an ordinary script failure, never a fallback.
Installing a wheel does not discover or rewrite repositories. Legacy full
copies adopt the shim once through the
[reviewed migration procedure](edge-code-upgrades.md); until then they retain
their old code. Markdown, schedules, workflows and shim-contract changes still
need reviewed repo edits.

Ordinary Python attachments have the same shipping option: a worker has a
direct module entry point invoked explicitly by instructions, or a plain named
attachment shim. Only the reserved `ticket.py` participates in automatic
execution and recurring copying. There is no general dispatcher or additional
attachment discovery/copying.

Default period tasks freeze the shim, not its imported implementation. Retain
the exact wheel artifact/hash and repo revision for reproducibility; a version
string alone cannot distinguish unreleased main-branch builds. Running
processes are not promised hot upgrades.

### Explicit local forks

A full implementation replacing either template or period `ticket.py` is
repo-owned. New periods copy the template fork; existing periods retain their
own script. Neither installation nor launch overwrites, merges or bypasses it.
Editing a wrapper that still imports the default is not an implementation fork.
A fork stops receiving upstream fixes and must remain compatible with the
shared core it imports; restoring the stock shim rejoins wheel updates.

Phone-home's complete module is deliberately forkable: it imports only stdlib
and shared `coga.*`, never relative or sibling edge modules, and carries both
normal and private `--worker` dispatch behind `__main__`. Its worker executes
that same file, including when copied to a local fork. Preserve these constraints
when refactoring it. The migration procedure includes source inspection and
copy commands; do not run production telemetry to find its source.
