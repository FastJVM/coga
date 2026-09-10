---
slug: make-sure-repo-clietn-don-t-edit-coga
title: make sure repo clietn don't edit coga
status: draft
owner: nicktoper
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow: code/design-then-implement
secrets: null
---

## Description

When Dream runs in a client repo — one that has Coga installed but is not the
Coga source repo (multiply, magicator) — it treats the installed Coga OS tree as
part of its own corpus and reports findings about Coga infrastructure. Those
findings are noise in the client repo: Phase 6 routes them to proposal PRs
against a repo that does not own the code they describe, and the client's real
backlog gets diluted.

Teach Dream to recognise it is not running in the Coga source repo and to keep
Coga-owned files out of its findings. What it does notice about Coga is not
discarded — it appends to a dedicated upstream file in the client repo, and a
new recurring job in the Coga repo sweeps configured client checkouts, reads
those files, and files real tickets here.

## Context

### Where the current behavior comes from

The Dream scan skills are written from inside the Coga source repo and never
distinguish Coga-owned files from the client's own:

- `src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/scan/scan-protocol/SKILL.md:8-9`
  calls both decide-half scans "read-only sweeps over **Coga's own** corpus".
- `.../scan/contract-audit/SKILL.md:55-74` audits `coga/` against
  `src/coga/resources/templates/coga/` — a pairing that only exists here.
- `.../scan/knowledge-scan/SKILL.md:47-53` defines the corpus as the configured
  contexts dir, `coga/skills/**`, and `coga/workflows/**`, with no notion of
  which tree owns them.

### The exclusion is a subset of `coga/`, not `coga/` itself

This is the trap, and an earlier draft of this ticket got it backwards. In a
client repo `coga/` is *also where the client's own knowledge lives* — `coga
init` seeds it and the client's contexts, skills, workflows, tasks, and log all
sit under it (`example/coga/` shows the shape). Since `knowledge-scan` defines
the corpus as exactly those directories, **excluding `coga/` wholesale would
exclude 100% of Dream's corpus** and Dream would find nothing at all.

What is actually Coga-owned in a client repo is a subset: `coga/contexts/coga/**`
(init installs the OS contexts, including `recurring/SKILL.md`), the shipped
`coga/recurring/<name>/` templates, `coga/.agent-skills/bootstrap/**`, `.coga/`,
and the Coga-authored sections of `CLAUDE.md` / `AGENTS.md`. Drawing that line
precisely is the hard part of this ticket.

### Precedent to generalise from

`knowledge-scan/SKILL.md:55-59` already solves the same shape of problem for
installer-managed skills:

> Installer-managed skills are **outside the corpus**. `coga/skills/` mixes
> repo-authored skills with upstream trees that `coga skill install` and `coga
> skill update` place and refresh wholesale. **The manifest's `ref` list in
> `src/coga/resources/managed-skills.toml` is the whole test.**

A manifest-driven "these paths are not yours" test is the model to extend —
Coga-installed OS files are the same category as installer-managed skills.
Prefer that over the narrower escape hatch at `contract-audit/SKILL.md:76` ("In
a downstream repo with no packaged source tree or explicit pair list, omit this
group"), which only covers the live/packaged twin comparison.

### The pieces of work

1. **Repo identity** — how Dream tells the Coga source repo from a client repo.
   Whatever signal is chosen must be stated once and reused, not re-derived per
   scan. `src/coga/` + `tests/test_packaging.py` is the obvious candidate but is
   also true of a fork or vendored copy; an explicit config marker may be more
   honest. Open for the design step.
2. **Exclusion** — in a client repo, Coga-owned paths (the subset above) leave
   the scan corpus and never reach `## Findings` or Phase 6 routing.
3. **Upstream capture** — Coga-infra observations append to a dedicated file in
   the client repo (proposal: `coga/upstream-coga.md`, append-only, one entry per
   observation carrying repo, date, and evidence path).
4. **Upstream processor** — a new recurring task here under `coga/recurring/`
   sweeps a configured list of client checkouts, reads each upstream file,
   creates Coga tickets for new entries, and watermarks what it processed so
   re-runs do not duplicate.

Direction is deliberately **Coga-repo-pulls**, not client-pushes: a client repo
then needs no credentials for this repo and no knowledge of where it lives. The
cost, accepted: the sweep only works on a machine that has every client checkout,
and the checkout list has to be maintained.

### Recurring-task facts the processor needs

Inlined rather than attaching the 52.6 KiB `coga/recurring` context, which would
have been 82% of this ticket's composed prompt while covering one of four pieces:

- A recurring task is `coga/recurring/<name>/ticket.md` with a cron `schedule:`
  in frontmatter; the directory name must not start with an underscore.
- The reserved sibling `ticket.py` is the deterministic half. `coga launch` runs
  it as `[sys.executable, "<task>/ticket.py"]` with no operands, copied into each
  period task and run headlessly before any agent phase.
- **The recurring task's own blackboard persists across every run and is where
  last-run cursors live** — that is the watermark mechanism, no new state file
  needed.
- Authoring path: create the directory by hand or `coga recurring promote`, then
  `coga validate --json`.
- A template may name any resolvable workflow and attach any resolvable contexts;
  there is no recurring-capable registry to register in.

`coga/recurring/blocker-reminders/` is the closest existing model — a one-step
workflow plus a `ticket.py` that scans, writes watermarks, and syncs through git.
Read it before designing the processor. Attach `coga/recurring` at the implement
step only if the design turns out to need the sweep or control-branch machinery.

### Constraints

- **The config key needs a core change, and that is expected here.**
  `src/coga/config.py:440` defines `_ALLOWED_LOCAL_SECTIONS = frozenset({"user",
  "agents", "notification", "git"})`, and `_reject_unknown_sections` (line 497)
  hard-fails on anything else — an unrecognised top-level key in
  `coga.local.toml` makes *every* coga command exit. So the checkout list is not
  documentation: it needs the section added to that frozenset, a parser, a
  dataclass field, and config tests. Config parsing is shared infra with many
  consumers, so this does not breach the microkernel rule.
- Agents may not edit `coga.toml` or `coga.local.toml`
  (`src/coga/resources/prompt.md:117`). Define the key and its shape, then ask
  the human to fill in the checkout paths. **The ticket cannot be verified
  end-to-end until they do** — treat that as a launch prerequisite, not a
  surprise at implement time.
- The processor's deterministic half goes in its sibling `ticket.py`, not
  `src/coga/`. Adding a recurring job is not by itself a reason to put code in
  core (`CLAUDE.md`, microkernel rule).
- **Packaging twins.** The Dream *scan* skills are bundled batteries with no live
  counterpart under `coga/skills/` — the packaged tree is the only copy, and
  `coga/.agent-skills/` is a generated, gitignored symlink view of it
  (`coga/.gitignore:13`). But `coga/recurring/dream/ticket.md` **is** an enforced
  twin of `src/coga/resources/templates/coga/recurring/dream/ticket.md`, and
  Phase 6 is defined there — editing one copy without the other fails
  `tests/test_packaging.py`. Decide explicitly whether the new upstream-processor
  template ships downstream at all; it only makes sense in this repo, so it
  likely needs to be unpackaged or listed in `INTENTIONALLY_DIVERGENT_TWINS`.
- Keep green: `tests/test_dream_skill_scripts.py`,
  `tests/test_dream_worker_templates.py`, `tests/test_dream_validate_drift.py`,
  `tests/test_packaging.py`, and the config tests.

### Verification

These tests pass today and will keep passing whether or not the change works, so
the design step must define acceptance beyond them. At minimum:

- A Dream run in a client repo produces zero findings naming Coga-owned paths,
  and a non-zero corpus (proving the exclusion did not empty the scan).
- The same run in this repo is unchanged.
- The processor turns a hand-written upstream file into tickets, and a second run
  over the same file creates none.

### Out of scope

- Changing what Dream considers a finding *within* the client's own product.
- Any transport requiring the client repo to reach into this one.
- Retrofitting upstream files for Dream runs that already happened.

### Related

`coga/tasks/dream-shouldn-t-touch-coga-in-coga-enabled-repo.md` is the same idea,
filed empty; canceled in favour of this ticket.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Evaluator review

Read cold, then every path, line number, quote, and test name verified against
the repo; scan skills, the recurring context, `code/with-review`, `config.py`,
and `init.py` all read.

### 1. Can an agent start from this cold?

Mostly yes, and it is unusually well-written for a fresh ticket: the Description
states the problem and the direction in two paragraphs, the Context names where
the current behavior comes from with citations, the three pieces are enumerated,
and there is an explicit Out of scope and a Related entry pointing at the ticket
being canceled. An agent would know what to do first.

Two things it does not say that the first hour will hit:

- **It never says which repos are the client repos**, beyond "(multiply,
  magicator)" in a parenthetical. There is no path to either checkout, no
  statement of whether they are on this machine, and no way to test the
  client-repo half. The recurring processor sweeps "a configured list of client
  repo checkouts" that does not exist yet and cannot be filled in by the agent
  (see the `coga.local.toml` point below). So the ticket's own acceptance is
  unverifiable as written — the agent can only write the mechanism and assert it.
- **There is no acceptance criteria or verification section.** For a change that
  is mostly prose edits to three SKILL.md files plus a new recurring job, "what
  does done look like" is not obvious. The Constraints section lists three tests
  to keep green, which is the closest thing, but those tests pass today and will
  keep passing whether or not the change works.

### 2. Workflow fit

`code/with-review` (implement → peer-review → open-pr → owner review) is a
reasonable *mechanical* fit — there is real code and real files — but it is a
poor fit for the **shape** of the work, and this is the ticket's biggest
structural problem.

Two of the three pieces are open design questions, not implementations:

- Piece 1 asks the implementer to *"Decide how Dream tells the Coga source repo
  from a client repo"* — the ticket proposes a signal but explicitly leaves the
  decision open.
- Piece 3 proposes a file format (`coga/upstream-coga.md`, append-only, entry
  shape), a transport direction, a config key, and a watermarking scheme — all
  as *proposals*.

`code/with-review`'s `implement` step runs `code/implement` and goes straight to
peer-review. The first reviewer of those four design decisions is the *other
agent* at peer-review, and the first human sight of them is the PR.
`coga/contexts/coga/current-direction/SKILL.md:84` says the design step is
skipped in favour of `code/with-review` "when the spec is already clear." Here it
is deliberately not clear — the ticket says "proposal:" and "whatever is chosen."
A design-first workflow, or splitting the design out, matches better.

Separately: `peer-review` resolves `assignee: other-agent`, which requires a
configured peer. Worth confirming the repo has two agent types wired before
launch, or the bump into peer-review fails loud.

### 3. Attached contexts — relevance and gaps

`coga/recurring` is genuinely the right context for piece 3; its own frontmatter
says "Attach to any ticket that adds or changes a recurring task." No argument
there.

But **two of the three pieces are Dream/scan work, and nothing is attached for
them.** There is no `coga/dream` context (checked — the contexts dir has 15
entries, none Dream). The Dream contract lives in `coga/recurring/dream/ticket.md`
(20 KB) and the three scan skills, and the ticket cites them by path but attaches
none. That is arguably fine — the agent can read them — but it means the one
attached context covers the *smallest* of the three pieces while consuming 82% of
the prompt.

Two contexts that should probably be attached instead of, or alongside, a trimmed
`recurring`:

- **`coga/extension-model`** (17.6 KiB) — the ticket's first Constraint is a
  microkernel argument ("not in `src/coga/`"), and this is the context that owns
  that rule. The ticket instead points at `CLAUDE.md`.
- **`coga/codebase`** (38.7 KiB) — owns source layout and the `RECIPES`/core
  boundary. Relevant because of the config finding in §7 below.

### 4. Is the attached context too broad?

**Yes, decisively.** `ticket_context` is 52.6 KiB of a 64.0 KiB prompt — **82%**,
against the 40% flag. The ticket's own body (description + context + blackboard)
is 4.3 KiB, about 6.7%. The agent reads eight times more about the recurring
subsystem than about the task.

`coga/contexts/coga/recurring/SKILL.md` broken down by section — 60 KB across 14
`##` sections:

| bytes | section |
|---|---|
| 17,025 | A recurring task is a ticket-format directory |
| 7,934 | The autofix loop closes the sweep |
| 6,118 | An `--all` child services an off-branch checkout from a temporary worktree |
| 4,855 | The creation contract |
| 4,423 | Description (the worked example) |
| 4,033 | Recurring runs start on the control branch |
| 3,819 | Gotchas |
| 3,322 | One operator owns recurring: the `owner` gate |
| 2,341 | Dropping a new recurring task |
| 1,976 | Extend recurring with a task-specific workflow |
| 1,589 | Dream is the recurring janitor |
| 1,023 | Last-run state lives in the recurring task's blackboard |
| 879 | REM is user-space recurring maintenance |
| 235 | What this context does NOT cover |

This ticket *adds one job*. It does not change the sweep, the scheduler, the
control-branch behaviour, the owner gate, the autofix loop, or off-branch `--all`
worktrees. Concretely, the facts it actually needs are about 5 KB:

1. A recurring task is `coga/recurring/<name>/ticket.md` with a cron `schedule:`
   in frontmatter; a non-underscore directory name.
2. The reserved sibling `ticket.py` is the deterministic half, run as
   `[sys.executable, "<task>/ticket.py"]` with no operands, copied into each
   period task and run headlessly before any agent phase. (Buried in the 17 KB
   section.)
3. The template's blackboard region persists across every run and is where
   last-run cursors live — this is *exactly* the ticket's watermark requirement,
   and it is the 1 KB section.
4. Authoring path: create the directory by hand or `coga recurring promote`, then
   `coga validate --json`.
5. A template may name any resolvable workflow and attach any resolvable
   contexts; there is no recurring-capable registry.

Copying those five facts into `## Context` and dropping the attachment would cut
the prompt from 64 KB to roughly 16 KB — a 75% reduction — with no loss of
anything the implementer needs. If you want to keep an attachment, keeping
`recurring` but adding `extension-model` and `codebase` on top would push the
prompt past 110 KB, which argues the other way: inline the facts.

### 5. Scope

**It bundles at least two tickets, arguably three.** The three pieces are not one
change:

- Pieces 1+2 (repo identity + exclusion) are prose edits to Dream's scan skills,
  verifiable in this repo, shipping in the package.
- Piece 3 is a **new subsystem**: a new file format in a foreign repo, a new
  config key requiring a `src/coga/config.py` change (see §7), a new recurring
  template with a `ticket.py`, a cross-repo filesystem sweep with
  idempotency/watermarking, and ticket creation from parsed external input. That
  is a full ticket on its own, and it is the half that cannot be tested without
  the client checkouts.

They also have different risk profiles and different reviewers. Piece 3 depends
on piece 1's identity rule but nothing else; splitting on that seam is clean.
Landing 1+2 alone already fixes the stated harm (noise in the client backlog);
piece 3 is the enhancement that preserves the signal.

### 6. Assumptions to question before launch

- **"The Coga OS tree (`coga/`, `.coga/`, and the installed package) is out of
  the scan corpus."** This is the assumption to push back hardest on — see §7, it
  is wrong as written and would break Dream in client repos.
- **Pull, not push.** The ticket says the direction was "decided deliberately
  over client-pushes" but gives no reason. Pull requires the Coga repo to know
  every client checkout path on every machine, and only ever runs on the machine
  that has them all. A push (client Dream opens an issue/PR upstream, or writes
  to a shared location) has no such coupling. The decision may be right; the
  ticket records it as settled without recording why, which is exactly what
  CLAUDE.md's "don't leave the durable explanation only in chat" warns against.
- **`coga/upstream-coga.md` as the filename.** It sits directly in the client's
  `coga/` root alongside `log.md` and `context.md`. Worth checking against
  `coga validate` and against the twin-derivation rule the ticket itself raises.
- **"Presence of `src/coga/` plus `tests/test_packaging.py`"** as the identity
  signal. This is true of the source repo but is also true of any *fork* or
  vendored copy, and false inside a `coga launch` worktree if the worktree is
  sparse. A `[layout]`-style explicit config marker, or the absence of
  `src/coga/resources/templates/`, may be more honest. The ticket wisely leaves
  this open, but see §2 — the workflow gives it no design step in which to be
  settled.
- **The three named tests are the only ones at risk.** Adding a config key breaks
  config tests; adding a `coga/recurring/upstream-*/` directory adds an enforced
  packaging twin and touches `tests/test_packaging.py`'s derived pair set and
  `coga validate`.

### 7. Factual claims — verification

**Correct:**

- `scan-protocol/SKILL.md:9` — verified. Line 9 reads `corpus.` as the wrap of
  "read-only sweeps over Coga's own / corpus" beginning on line 8; close enough
  that a reader lands on it.
- `contract-audit/SKILL.md` audits `coga/` against
  `src/coga/resources/templates/coga/` — correct (lines 55–74, the "copy
  divergence" shard).
- `knowledge-scan/SKILL.md` covers "every ticket and knowledge file" — correct
  (line 8).
- The escape-hatch **quote** is verbatim: "In a downstream repo with no packaged
  source tree or explicit pair list, omit this group."
- The Dream scan skills are bundled batteries with no live counterpart under
  `coga/skills/` — verified. `find coga -path '*dream/scan*'` outside
  `.agent-skills` returns nothing, and `tests/test_packaging.py:117-123`
  documents exactly this ("a packaged file with no live counterpart … is not a
  pair").
- `coga/.agent-skills/` is gitignored — verified, via `coga/.gitignore:13`, not
  the root `.gitignore`.
- All three named tests exist: `tests/test_dream_skill_scripts.py`,
  `tests/test_dream_worker_templates.py`, `tests/test_dream_validate_drift.py`.
- The base prompt forbids editing both config files — verified,
  `src/coga/resources/prompt.md:117`: "Do not edit `coga.toml` or
  `coga.local.toml`."
- The related ticket exists and is already `status: canceled` with an empty
  Description.
- Phase 6 routes findings to proposal PRs — verified,
  `coga/recurring/dream/ticket.md:163-164, 289-305`.

**Wrong or misleading:**

1. **The line number for the escape hatch is wrong.** The ticket cites
   `contract-audit/SKILL.md:63`. Line 63 is the middle of the `python -c` shell
   block. The quoted sentence is at **line 76**. Minor, but an agent that opens
   line 63 sees a shell command and may conclude the citation is stale.

2. **The exclusion rule in piece 2 is factually backwards and would break Dream
   in client repos.** The ticket says "the Coga OS tree (`coga/`, `.coga/`, and
   the installed package) is out of the scan corpus." But in a client repo,
   `coga/` is *also where the client's own knowledge lives* — `coga init` copies
   templates into `coga/` and the client's contexts, skills, workflows, tasks,
   and log all live under it (`example/coga/` shows exactly this shape:
   `contexts/email/`, `skills/infra/`, `workflows/code/`, `tasks/`). Meanwhile
   `knowledge-scan/SKILL.md:48-53` defines the corpus as precisely the configured
   contexts dir, `coga/skills/**`, and `coga/workflows/**`. Excluding `coga/`
   wholesale in a client repo excludes 100% of Dream's corpus — Dream would find
   nothing at all. What is actually Coga infra in a client repo is a *subset*:
   `coga/contexts/coga/**` (init installs all 15 OS contexts, including
   `recurring/SKILL.md`), the shipped `coga/recurring/<name>/` templates,
   `coga/.agent-skills/bootstrap/**`, `.coga/`, and the Coga-authored sections of
   `CLAUDE.md`/`AGENTS.md`. That distinction is the actual hard part of piece 2
   and the ticket states its opposite.

3. **An unstated fourth piece of work: the config key cannot be added without
   editing core.** The ticket says "define the key and ask the human to fill it
   in," implying the key is just documentation. It is not. `src/coga/config.py:440`
   defines `_ALLOWED_LOCAL_SECTIONS = frozenset({"user", "agents",
   "notification", "git"})` and `_reject_unknown_sections` (line 497) hard-fails
   on anything else — an unrecognized top-level key in `coga.local.toml` makes
   *every* coga command exit. So the implementer must add the section to that
   frozenset, write a parser and a dataclass field, and add config tests. This is
   legitimate shared infra, so it does not violate the microkernel rule, but it
   sits in tension with the ticket's Constraint that "Adding a recurring job is
   not a reason to put code in core," and an agent reading only the ticket will
   not expect it. There is also no precedent in the codebase for a multi-repo
   registry — nothing in `megalaunch.py` or elsewhere enumerates foreign
   checkouts, so this is genuinely new surface.

4. **The twin note is right for the scan skills but omits the one twin the work
   will actually hit.** The Constraint correctly says the scan skills have no
   twin, and correctly warns that new files under `coga/` that also ship as
   templates become enforced pairs. But it doesn't name the concrete case:
   `coga/recurring/dream/ticket.md` **is** an enforced twin
   (`src/coga/resources/templates/coga/recurring/dream/ticket.md` exists, 20 KB,
   and is not in `INTENTIONALLY_DIVERGENT_TWINS`). Since the Description itself
   calls out Phase 6, and Phase 6 is defined in that ticket.md, the implementer
   will almost certainly edit it — and must edit both copies byte-identically.
   Likewise, the new recurring template will need a packaged twin if it is to
   ship to client repos at all, which the ticket never addresses (does the
   *processor* ship downstream? it shouldn't — it only makes sense in the Coga
   repo, so it needs to be either not-packaged or explicitly divergent).

### Bottom line

Good ticket by fresh-ticket standards — real citations, explicit out-of-scope, an
honest Related. Four concrete things to change before launch: fix the
`coga/`-exclusion claim (it is inverted and would neuter Dream downstream); split
piece 3 into its own ticket; add the `config.py` work or drop the config key from
scope; and replace the 52.6 KiB `coga/recurring` attachment with about 5 KB of
inlined facts, which alone cuts the prompt by three quarters. The workflow choice
is the remaining open question — with four undecided design calls in the body,
`code/with-review` sends them all to peer-review sight-unseen.
