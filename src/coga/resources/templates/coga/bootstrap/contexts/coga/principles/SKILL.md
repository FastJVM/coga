---
name: coga/principles
description: The non-negotiables for coga, as one root and its consequences. The Pirsig filter — when in doubt, choose the option that makes the human think better. Use to push back on changes that drift from the design intent.
---

# Coga principles

Most tools say **don't think** — delegate the work and forget it. Coga's bet is the opposite:

> **Don't don't think. Think better.**

The tool exists to make your judgment *sharper, not absent* — and to keep the
system **yours**: legible, hackable, on your disk, not rented from a vendor.

Everything below is a **consequence** of that one root. Each is timeless (it
doesn't change with stage or scale), each can *reject* a change, and each has a
**receipt** — the feature that proves we mean it. When a proposed change makes
any of these worse, push back hard.

The filter: **does this make the human think better?** Then check the
consequence that applies — is it still hackable? did we make the human do
mechanizable work? is it still obvious? does memory stay human-gated? is it
still yours? does it still fail loud?

A warning about the root: "think better" alone is vague — almost anything can be
rationalized as thinking better. **The consequences are the teeth.** Filter on
them concretely, not on the slogan.

---

## 1. Hackable — you can change anything, directly

Better thinking is useless if you can't act on it, so every part of the system
is yours to change immediately by editing a file you own: the base prompt,
rules, contexts, skills, workflows. No hidden logic, no vendor-controlled config
surface, **no plugin API that gates what you may touch.** You don't *request*
behavior; you *edit* it. Modification is direct, not plugin-mediated — you change
the actual files the system runs on, not a sandboxed extension point.

**Forbids:** behavior that lives somewhere you can't edit (a compiled binary, a
hosted service, a plugin fence); a config surface that exposes only part of the
logic.

**Receipt:** edit any markdown under `coga/` → the next `coga launch` uses
it. The ~2-minute correction loop: see a mistake → edit the context → commit →
next run is fixed.

## 2. Agents do, humans think — offload everything mechanizable

The human's scarce resource is judgment. Don't spend it on doing. Route every
mechanizable step to an agent (and crystallize the deterministic part to a
script), so human attention concentrates on what only judgment can settle:
what's worth doing, whether the output is right, what rule was missing. The
agent is a first-class operator — any workflow step's `assignee` can be an agent
or a human, interchangeably — because every operation is a text command or a
file edit, which an agent does exactly as a human does.

**Forbids:** a human-only operation (a GUI-locked action, anything not
expressible as a command + file); making a human do work an agent or script
could do; a capability exposed *only* through a non-text surface. A UI may
*view* (read-only) but never be the only way to *do* something — the absence of
a webUI is this principle holding, not a missing feature.

**Receipt:** the CLI + files are the whole surface, no webUI; the two modes — `agent` for agent judgment and `script` for deterministic Python — route work to the right substance; per-step `assignee` (`agent`/`other-agent`/`human`)
chains a task across operators in one `coga launch`.

## 3. Obvious — boring, standard, immediately understandable

You can only think well about what you instantly grasp, so the materials are
deliberately unexciting: **markdown** for knowledge and state, **Python** for
determinism, the standard **SKILL.md** format for skills and contexts. No
database, no DSL, no exotic stack. A clever mechanism that buys opacity is the
bug, not the feature — prefer the dumbest legible version. Three similar lines
beat an abstraction whose purpose you couldn't explain to a new hire in one
sentence. This extends to the substrate underneath: **reuse the OS the operator
already knows — the filesystem, git, the shell — rather than reimplementing a
worse version of it inside Coga.** A concept that the directory tree already
expresses gets no Coga machinery; you operate it with `mkdir` / `mv` / `rm` /
`git`, the verbs a shell-fluent operator already has in their hands. That
reuse is a large part of why Coga is powerful for that operator: there is no
second, lesser vocabulary to learn.

**Forbids:** a proprietary format; a clever/opaque mechanism where a boring
legible one would do; premature abstraction; derived/denormalized state that
hides what a file already says; a bespoke Coga command that reimplements
something the filesystem, git, or the shell already does well.

**Receipt:** the whole substrate is markdown + Python + SKILL.md. SKILL.md *is*
the Claude Code / Codex format (Anthropic's `skill-creator` is vendored
verbatim, not reinterpreted). `coga validate` and the prompt composition are
plain file reads. Task directories nest like any directory — a task is a
`ticket.md` directory at any depth under `tasks/`, organized with `mkdir` /
`mv` / `rm`. `coga status <dir>` is a thin read-only filter over that tree,
not a new abstraction on top of it.

## 4. Memory via PR — thinking compounds, human-gated, never opaque

Better thinking must *accumulate* — so you don't re-think the same thing — but
it must never become the automatic, opaque memory that would *replace* thinking.
So knowledge compounds through human-reviewed diffs, not learned weights or a
hidden store. The system reads its own execution history, finds where its
knowledge drifted from reality, and **proposes** the fix; the human disposes.

**Forbids:** opaque/learned/auto-curated memory; the system editing its own
behavior on `main` without a human merge gate; silent knowledge updates.

**Receipt:** **Dream** (`coga/recurring/dream/`) reads tickets + blackboards,
classifies drift, and opens **proposal PRs** — "propose, human disposes."
the blackboard region (in `ticket.md`) is working memory; `contexts/` is long-term memory, merged by
hand. The correction loop is the human instance of this; Dream is the agent
instance. (Sessions are stateless — the prompt is a pure function of the files on
disk now, never a carried-over session — which is what makes an edit between runs
take effect, totally and inspectably.)

## 5. Yours — own the substrate, swap the vendors

You can't think better about a black box you rent. The substrate is yours: plain
files in your git repo, on your machine, no hosted backend. And no single model
vendor owns you — agents are interchangeable.

**Forbids:** moving state into a hosted service you can't inspect; lock-in to one
model vendor; a format only one vendor can read. **No phoning home — no
telemetry, usage tracking, or install ping, not even anonymized or opt-out.**
Coga sends nothing about you or your repo anywhere; product signals come from
public surfaces (PyPI/GitHub) you can read too, never from instrumenting the
operator's machine.

**Receipt:** git-backed markdown, local by default, no cloud. Nothing in Coga
makes a network call you didn't initiate. `claude` ↔ `codex` interchangeable
(`[agents.*]` in `coga.toml`, `other-agent` rotation across workflow steps).
`coga init` vendors the CLI into your repo. SKILL.md is an open standard.

> Considered and rejected (2026-06): an opt-out anonymous install ping (3
> fields, no PII) to gauge product-market fit. Even with loud disclosure and a
> one-line disable it cuts against this principle — users don't want to be
> tracked, and a tool that phones home isn't fully *yours*. Use the PyPI/GitHub
> estimate instead.

## 6. Fail loud — surface every failure, never silent-wrong-answers

You can't think about a problem you can't see. The worst failure is an agent
confidently producing wrong output because a context or skill silently failed to
load. If the cost of a check is one line and the cost of skipping it is "wrong
answer and nobody knows," always check.

**Forbids:** swallowing errors; a missing context/skill silently dropped from
the prompt; a network/Slack/script failure that returns success; a read-only
command (`status`, `show`, `validate`) that mutates state or hits the network as
a side effect of reading.

**Receipt:** missing context/skill → raise; `coga validate` errors on broken
refs; Slack/script failures surface (and log), never swallowed; `coga block`
hands a blocked task back to a human rather than guessing.

## 7. Ticketed — every unit of work is a durable, directable task

Better thinking needs something to think *about* and something that survives the
session. So every substantive unit of work is a **ticket** — a git-backed
`ticket.md` with a blackboard (working memory) and a workflow (its steps) —
never an untracked side-channel action that vanishes when the process exits. The
ticket is what the human directs, what an agent resumes, what the team sees, and
what the correction loop later reads. Work you can't point at is work you can't
think about, hand off, or fix.

This is not "everything is a ticket." Reusable *process* stays a **skill**, its
deterministic core a **script**, and the CLI verbs (`launch`, `bump`, `status`)
*operate on* tickets rather than being work themselves. The rule bites on
**work**: a substantive change, decision, or task gets a ticket — it does not get
done as a bespoke command, a loose branch, or an agent action that leaves no
recoverable trace.

**Forbids:** doing substantive work through an untracked side channel (a one-off
command that mutates the repo with no ticket/blackboard/log; an agent change that
leaves no resumable trace); a bespoke Coga command that performs task-work
instead of operating on a ticket; machine-authored maintenance that runs loose
instead of as a real task.

**Receipt:** `coga create` / `coga ticket` scaffold every unit of work as a
`ticket.md`; the blackboard persists state between stateless sessions and
`coga bump` advances + logs each step; even machine-authored work (Dream,
`recurring`, `retire`) creates a real task with the `direct/body` workflow
rather than running loose — there is no sanctioned workflow-less active task.

---

## What this context does NOT cover

- **Stage-specific posture** (e.g. "no backwards compat needed") — has an expiry
  date; lives in `coga/project-stage`.
- **The mental model of how coga works** — primitives, composition, locking —
  see `coga/architecture`.
- **Market positioning** (no-moat / taste / "think better ≠ keep thinking" /
  absorption-vs-imposition) — that's strategy, not canon; it lives in
  `docs/market-thesis.md`. Keep positioning out of the principles.
