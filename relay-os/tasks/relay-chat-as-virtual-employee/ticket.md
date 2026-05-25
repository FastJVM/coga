---
title: relay chat as virtual employee
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/principles
- relay/current-direction
skills: []
workflow:
  name: dev/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
  - name: self-qa
    skills:
    - code/self-qa
  - name: pr
    skills:
    - code/open-pr
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

Use the **virtual-employee** framing as the positioning line for
`relay chat`. The companion ticket `virtual-employee` (PR #208)
rejects "virtual employee" as a Relay *primitive*; this ticket uses
it where it actually fits — UX positioning for the interactive
session that loads the repo's contexts and feels like talking to a
teammate who's been onboarded into the company.

Small doc PR via `dev/with-self-review`. Two surfaces:

1. **`relay-os/bootstrap/orient/ticket.md`** — reshape the
   Description to lead with the virtual-employee framing. The shim
   itself doesn't change; only the human-facing copy that explains
   what `relay launch bootstrap/orient` (aka `relay chat`) is *for*.
2. **`README.md`** — extend the Aliases section's `relay chat`
   description with the same positioning line so the README and the
   shim agree.

## Context

- **Why this framing fits `relay chat` specifically.** `relay chat`
  aliases to `relay launch bootstrap/orient`, which composes the
  canonical relay contexts (architecture, principles, cli) plus the
  repo's own contexts into the agent prompt. From the human's seat,
  that is functionally indistinguishable from talking to a coworker
  who's read the company handbook and the team docs. "Your virtual
  employee for this repo" is an honest description of that UX, even
  though the substrate is just stateless invocation + a composed
  prompt.
- **Why the rejection in the companion ticket doesn't conflict.**
  PR #208 declines `virtual-employee` as a *primitive* — no
  `[employees.*]` table, no memory-bearing role abstraction, no
  identity-bearing agent entry. It explicitly preserves the metaphor
  for UX positioning. This ticket is the first place that
  preservation cashes out. The two tickets draw the same line from
  opposite sides; the PR description should call that out so the
  reviewer reads them as a matched pair.
- **Shim sync — two copies, one change.** The bootstrap shim lives
  in two places that must stay identical:
  - `relay-os/bootstrap/orient/ticket.md` (live)
  - `src/relay/resources/templates/relay-os/bootstrap/orient/ticket.md` (packaged)
  Per `CLAUDE.md`'s sync rule, both must be updated in the same PR.
  The shim's own footer says "Don't edit this shim except to swap
  `assignee`" — that warning is aimed at *downstream* repos that
  vendored the shim; this PR is the *upstream* edit and is exactly
  where the framing change belongs.
- **Tone for the new copy.** Lead with the metaphor, then ground it
  in the substrate so a reader who clicks through doesn't feel
  oversold. Example shape (implementer's call on exact wording):

  > Your virtual employee for this repo — an agent that's loaded
  > the canonical relay contexts and the repo's own contexts, so
  > you can direct ad-hoc work without re-explaining the project.
  > Substrate is just a composed prompt over a stateless session;
  > there's no persistent identity, memory, or tenure. For
  > ticket-bound work, exit and `relay launch <slug>`.

  Keep the existing "stateless shim" / "no ticket, no workflow, no
  lock" mechanics in the body — the framing change is additive, not
  a rewrite.
- **README change shape.** The `### Aliases` section currently
  introduces the alias table with one line of context. Add a
  one-sentence positioning line for `chat` either as an inline
  comment in the toml block or as a one-liner above/below the block.
  The earlier `relay chat --agent codex` mention in the `relay
  launch` section doesn't need to change — that paragraph is about
  agent overrides, not about what chat *is*, and it lives under a
  different heading. One positioning line in `### Aliases` is
  sufficient; don't reach for the launch-section paragraph too.
- **Out of scope:**
  - Touching `[agents.*]` or `[aliases]` in `relay.toml`.
  - Introducing `[employees.*]`, `[personas.*]`, or any new
    primitive. The companion ticket exists precisely to prevent
    that drift.
  - Adding "virtual employee" language to ticket-bound workflows,
    `relay launch <slug>` copy, or any non-chat surface. The
    framing fits the *orient* shim specifically because it's the
    open-ended ad-hoc session; on ticket-bound work the
    abstraction over-promises.
  - `docs/vision.md` — PR #208 owns the vision.md clause for the
    *rejection* side of this line. No vision.md edits in this PR.
  - The commented-out `claude = …` / `codex = …` per-agent alias
    examples in the `### Aliases` toml block. They're scaffolding
    for downstream repos, not user-facing surfaces in this repo;
    don't add positioning copy to them.
  - `src/relay/resources/templates/CLAUDE.md` "Start here" section
    (the packaged downstream agent guide). It also mentions
    `relay launch bootstrap/orient` as the entry point, so a
    one-line nudge there would be coherent — but it's a separate
    audience (agents in downstream repos, not human readers of this
    repo) and worth a separate ticket if anyone wants it. Skip here.
- **PR shape** — one PR touching three files (the live shim, the
  packaged shim, and the README). The `self-qa` step is a re-read
  pass on wording — *not* a `/simplify` run on prose, which would
  mangle it (same caveat as the companion ticket). Worth flagging
  PR #208 in the PR description so the reviewer reads them as a
  matched pair.
