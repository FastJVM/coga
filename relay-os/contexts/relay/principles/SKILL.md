---
name: relay/principles
description: Non-negotiables for relay. The Pirsig filter — when in doubt, choose the option that scores higher on these. Use to push back on changes that drift from the design intent.
---

# Relay principles

Timeless. These don't change with stage or scale. If a proposed
change makes any of these worse, push back hard.

## Markdown-first, git-backed, locally operated

Every artifact is a markdown file in a git repo on the user's
machine. No database, no server, no cloud. Git is the sync layer
(v1 — explicitly acceptable for ≤5-person teams). The user can
`grep`, `cat`, `vim`, and diff anything without learning a tool.

Corollary: no proprietary file formats. SKILL.md is the SKILL.md
that Claude Code and Codex use. Frontmatter is YAML. Bodies are
markdown.

## Legibility over cleverness

A human reading any single file should understand what it means
without needing to run the system. State is on disk in a form a
person can read. Computed/derived state is a code smell — if
something can be inferred from files, infer it; don't store a
denormalized copy.

## Short human correction loop

The user must be able to interrupt, edit, and resume. The
blackboard exists for this. Manual edits to ticket.md / blackboard
/ contexts are first-class — no audit hooks, no "you changed this
outside the tool" warnings.

## Fail loud, never silent-wrong-answers

The worst failure mode is an agent confidently producing wrong
output because a context or skill silently failed to load.

- Missing context → raise.
- Missing skill → raise.
- Network error posting to Slack → surface, don't swallow.

If the cost of a check is one line of code and the cost of skipping
it is "agent gives wrong answer and nobody knows," always check.

## Read-only commands stay read-only

A command whose name and shape promise a read (`status`, `show`,
`validate`, `--prompt-report`) must not mutate ticket state, shell
out to network services, or swallow errors as a side effect of
reading. Users `grep` and pipe these commands; they expect a fast,
deterministic, filesystem-only read. A read that quietly bumps a
ticket, posts to Slack, or no-ops on a missing `gh` is exactly the
silent-wrong-answer shape `fail loud` exists to prevent — and it
makes the command network-dependent and slow on top of that.

Catch-up work (auto-bumping on a merged PR, refreshing remote state)
belongs in an explicit command (`relay automerge`), a git hook
(`post-merge`), or a recurring task — surfaces that announce they
mutate state and surface their own failures. Don't bolt it onto a
read.

## Classical mode (Pirsig)

Build the thing well. Understand each part. Resist accumulating
abstractions whose purpose you couldn't explain to a new hire in
one sentence. When something feels gnarly, the design is wrong —
fix the design, don't add a layer to hide it.

## No premature abstraction

Three similar lines is better than a clever abstraction. We're
still discovering what the right shape is; abstractions calcify
the wrong shape. Inline first; extract only when the third real
caller appears.

## What this context does NOT cover

- Stage-specific posture like "no backwards compat needed" — that
  lives in `relay/project-stage` because it has an expiry date.
- The mental model of how relay works — see `relay/architecture`.
