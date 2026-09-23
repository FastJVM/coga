---
name: coga/principles
description: Coga's seven non-negotiable design constraints, derived from one root; use them to push back on changes that drift from the design intent.
---

# Coga principles

Most tools say **don't think**: delegate and forget. Coga's root is the
opposite: **don't don't think — think better.** The system exists to make human
judgment sharper, not absent, and to stay **yours**: legible, hackable, on your
disk.

The slogan alone is vague; the seven consequences below are the teeth. Each is
timeless, each can reject a change, and each names a receipt. When a change
makes one worse, push back.

## 1. Hackable — change anything directly

Every part of the system — base prompt, rules, contexts, skills, workflows —
changes by editing a file you own. You edit behavior; you do not request it.

**Forbids:** behavior you cannot edit (compiled binary, hosted service, plugin
fence); a config surface exposing only part of the logic.

**Receipt:** edit a context or other Coga markdown and the next `coga launch`
uses it — the short correction loop.

## 2. Agents do, humans think — offload the mechanizable

Judgment is the scarce resource. Route mechanizable steps to agents and
deterministic parts to scripts, so humans decide what matters, whether output
is right, and which rule was missing. Every operation is a text command or file
edit, so an agent can perform it as a human does.

**Forbids:** human-only operations (GUI-locked actions); making a human do work
an agent or script could do; a capability available only through a non-text
surface. A UI may view but never be the only way to act.

**Receipt:** the CLI and files are the whole surface. A ticket's reserved
`ticket.py` runs deterministic work before any agent phase, deduced rather than
declared; per-step `assignee` roles (`agent`/`other-agent`/`owner`) route work
([`coga/lifecycle`](../lifecycle/SKILL.md), [`coga/script-tickets`](../script-tickets/SKILL.md)).

## 3. Obvious — boring, standard, understandable

Markdown for knowledge and state, Python for determinism, SKILL.md for skills
and contexts. No database, DSL or exotic stack. Prefer the dumbest legible
mechanism; three similar lines beat an unexplainable abstraction. Reuse the OS
the operator knows — filesystem, Git, shell — instead of reimplementing it.

**Forbids:** proprietary formats; opaque cleverness; premature abstraction;
derived state that hides what a file says; a Coga command that reimplements
what `mkdir`, `mv`, `rm` or `git` already do.

**Receipt:** SKILL.md is the Claude Code / Codex format; validation and prompt
composition are plain file reads; task directories nest and move like any
directory ([`coga/tickets`](../tickets/SKILL.md)).

## 4. Memory via PR — compounding, human-gated, never opaque

Knowledge accumulates through human-reviewed diffs, not learned weights or a
hidden store. The system may find drift and **propose** a fix; the human
disposes.

**Forbids:** opaque, learned or auto-curated memory; the system changing its own
behavior on `main` without a human merge gate; silent knowledge updates.

**Receipt:** Dream proposes knowledge changes as reviewable PRs
([`coga/dream`](../dream/SKILL.md)). Sessions are stateless: the prompt is a
function of the files on disk now, so an edit between runs takes full,
inspectable effect. The blackboard is working memory; contexts are long-term
memory, merged by hand.

## 5. Yours — own the substrate, swap the vendors

State is plain files in your Git repository on your machine, with no hosted
backend, and agents are interchangeable.

**Forbids:** state in a hosted service you cannot inspect; lock-in to one model
vendor or a format only one vendor reads. Operational state stays local and
Git-backed; the bounded telemetry exception below does not host the OS.

**Receipt:** Git-backed markdown; Claude Code and Codex interchangeable through
`[agents.*]` and `other-agent` rotation ([`coga/agents`](../agents/SKILL.md));
`coga init` writes plain markdown and TOML into the repo — no venv, no second
CLI, nothing to un-rent.

> Owner reversal (2026-09-20, clarified 2026-09-22): permit default-on,
> opt-out weekly aggregate usage snapshots to measure product-market fit.
> Accept a small biased sample of repos with active operator sweeps, not an
> install count, and lost events without retries. The closed data boundary,
> development suppression and delivery contract belong to
> [`coga/telemetry`](../telemetry/SKILL.md). No per-command or
> agent/session/token instrumentation is authorized.

## 6. Fail loud — never a silent wrong answer

The worst failure is confident wrong output because something silently failed
to load. If a check costs a line and skipping it risks an unnoticed wrong
answer, check.

**Forbids:** swallowed errors; a missing context or skill dropped from the
prompt; a network, notification or script failure reported as success; a
read-only command (`status`, `show`, `validate`) that mutates state or touches
the network.

**Receipt:** a missing ref raises at composition; `coga validate` errors on
broken refs; notification and script failures surface; `coga block` returns a
task to a human instead of guessing.

## 7. Ticketed — every unit of work is a durable, directable task

Substantive work is a ticket: a Git-backed `ticket.md` with a blackboard and a
workflow, which the human directs, an agent resumes and the correction loop
later reads. This is not "everything is a ticket": reusable process stays a
skill, deterministic cores stay scripts, and CLI verbs operate on tickets.

**Forbids:** substantive work through an untracked side channel; a bespoke
command that performs task work instead of operating on a ticket;
machine-authored maintenance running loose instead of as a task.

**Receipt:** `coga create` / `coga ticket` scaffold work; `coga bump` advances
and logs steps; Dream, recurring runs and `retire` create real tasks (default
workflow `direct/body`) — no workflow-less active task is sanctioned.

## Not covered here

Stage posture with an expiry lives in `coga/project-stage` (local to the Coga
repository). The model of primitives and composition is
[`coga/architecture`](../architecture/SKILL.md). Market positioning is strategy,
not canon: `docs/contexts/marketing/strategy/SKILL.md`.
