---
title: Autonomy-triage context + move tier workflows to autonomy/ namespace
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude1
assignee: claude1
contexts: []
skills: []
workflow:
  name: dev/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 2 (self-qa)
---

## Source method

This ticket encodes the method from **"Audit, Test, Automate: how we decide
what AI can own"**
(https://deviantabstraction.com/2026/06/02/audit-test-automate-how-we-decide-what-ai-can-own/).
The post is the canonical rubric — do not re-derive it.

Its three stages map onto Relay as:

- **Audit** — the periodic human practice of inventorying tasks. **Out of scope
  here.**
- **Test** — the per-task 3-Question Test that decides how much AI can own. **This
  is what the `autonomy/triage` context encodes.**
- **Automate** — the chosen tier workflow actually does (or redesigns) the work.

## Description

Every ticket should be tested for *how much* of it AI can own: if a task can run
unattended, it should. We capture that decision once as a reusable, callable
**context**, `autonomy/triage` (the "Test" stage). The intent is to run it at
impl-ready (not at ticket-definition time) — but **that wiring is the follow-up
ticket, not this one.** This ticket only ships the rubric and the tiers it sorts
into; no timing behavior changes here.

This is **general, not browser-specific** — it applies to any ticket.

**`autonomy/triage` is a distinct concern from `build-automation`'s triage.**
build-automation's `triage-tier` is a browser-specific, often-obvious human call
about failure radius for a task already committed to as a SaaS automation. The
`autonomy/triage` test is the general, upstream *eval* of whether AI should own a
task at all (and how much). They are **not** the same rubric and are **not**
merged here — build-automation's triage logic is left untouched by this ticket.

## The 3-Question Test (context body — canonical source)

A task may be delegated to AI only if it passes all three. The questions, from
the post:

1. **Publicly documented?** Is the task somewhat public / conventional, so the
   LLM likely already knows the domain? (Private, idiosyncratic work → leans
   human.)
2. **Conventional result acceptable?** Is average/conventional quality good
   enough — i.e. it is *not* a source of competitive advantage? (If it needs
   above-average, differentiating quality → it fails this question.)
3. **Verifiable, or bounded failure?** Can you directly verify the output —
   **or**, if not, is the **failure radius** bounded (what's the worst that
   happens if it fails, and can it be undone)?

The verification rule from the post applies throughout: *never spend more time
reviewing the AI's work than a human would have spent doing it.*

## The four tiers

The test sorts a task into one of four tiers (this **resolves** the earlier
open "is there a fourth tier?" — yes: **assist-only**):

- **fully-automated** — all three pass and the failure radius is low. Runs
  unattended, no human in the loop.
- **assist-only** — fails Q2 (needs above-average / differentiating quality). The
  AI assists, but a **human owns the result**. The work is not delegated
  end-to-end.
- **human-verify** — verifiable-or-bounded but with medium/high failure radius.
  The agent runs end to end, stops before the irreversible step, and the human
  reviews and fires.
- **human-only** — structurally unverifiable **and** high failure radius (or Q1
  fails outright). A human performs it; the agent only supports (read-only).

## Tier → Relay primitives mapping

The tier is expressed through **workflow step `assignee` roles** — the human is
in the loop exactly when a step is assigned to a human (`agent` / `owner` /
`human` / `other-agent`, resolved at each `relay bump`). A human gate *is* a
human-assigned step; there is no separate "gate" flag.

- **fully-automated** → no human-assigned step; every step `assignee: agent`.
- **assist-only** → the producing step is `assignee: agent` but the **owning /
  delivering** step is human-assigned; the agent's output is an input the human
  finishes and owns. (New shape — see deliverable 2.)
- **human-verify** → a human-assigned step (`assignee: human`) at/before
  the irreversible action; mirror the existing human-verify tier workflow.
  (`assignee` takes one role token, not a slash.)
- **human-only** → acting steps human-assigned, agent steps read-only support
  (the existing human-only tier workflow).

`mode` is **orthogonal** and must not be conflated with the tier. `mode`
(`interactive`/`auto`/`script`) controls how the agent CLI process is launched,
not whether a human is in the loop. Note: **`mode: auto` is currently disabled**
at launch (hard-bails); **`mode: script` is the live unattended path**. So
"fully-automated = `mode: auto`" is not true today.

## Scope — this is the "ship the rubric first" split

This ticket ships the **callable rubric (context) + the four tier workflows**
(three moved to `autonomy/`, plus the new `assist-only`), and updates
`build-automation`'s moved tier paths. The actual *wiring* of the test into the
impl-ready path — a triage step seeded into `_template` and the general workflows
— is the **risky general-path rollout, split to a follow-up ticket** (see
"Follow-up (not here)"). So: this ticket creates the rubric and the tiers it
sorts into; the follow-up makes every ticket run it.

## What to build

1. **`relay-os/contexts/autonomy/triage/SKILL.md`** — the context: the 3-Question
   Test + the four tiers (what each *means*: the decision criteria and failure
   radius) + the verification rule. **Domain knowledge only, no process** — so
   the tier→`assignee` realization is **not** spelled out here; the context gets
   at most a one-line pointer ("each tier is realized as a workflow's
   human-assigned steps — see the `autonomy/` tier workflows"). The full
   tier→assignee mapping lives in the tier workflows, not the context. Under a
   page, `autonomy/` namespace, mimic `relay-os/contexts/_template/`, cite the
   source post.
2. **Move the tier workflows to a neutral namespace, and add `assist-only`.** The
   three existing tier workflows are domain-generic despite living under
   `browser/`. Move them to `autonomy/` so they mirror the context namespace, and
   add the new fourth:
   - `relay-os/workflows/browser/human-only.md` → `autonomy/human-only.md`
   - `relay-os/workflows/browser/human-verify.md` → `autonomy/human-verify.md`
   - `relay-os/workflows/browser/fully-automated.md` → `autonomy/fully-automated.md`
   - **new** `relay-os/workflows/autonomy/assist-only.md` — see spec below.

   **Move mechanism (must follow):** `git mv` each live file (preserve history),
   then update its `name:` field (`browser/<tier>` → `autonomy/<tier>`). For the
   packaged mirror under `src/relay/resources/templates/relay-os/workflows/`,
   **delete the old `browser/` copies and add the `autonomy/` ones** (don't leave
   duplicates). Workflow resolution is **path-based** (`workflow:` field →
   `workflows/<name>.md`); the `name:` frontmatter is display-only, not used to
   locate the file — so a stale `name:` mis-*displays* in the composed prompt, it
   does not mis-bind. Still update **all** `name:` fields (live + packaged) for
   correctness/legibility. Update prose references — notably
   `browser/build-automation`'s
   `triage-tier` and `emit-and-launch` (lines ~25, ~29). The bare-word tier
   cross-refs inside the tier workflows (e.g. "downgrade to human-only") need **no
   change** — the words are unchanged. `browser/build-automation` itself stays
   under `browser/`.

   **`assist-only` workflow spec** — it fails the test on **Q2 (quality), not
   feasibility**, so it must **not** inherit `prerequisites-and-handoff` /
   `dry-run-or-downgrade` (those are feasibility/flakiness steps; the task *is*
   machine-feasible). And because it's a **quality** axis, orthogonal to the
   feasibility downgrade ladder, assist-only is **not** a downgrade target of
   fully-automated/human-verify. Steps:
   - `agent-produces` (`assignee: agent`) — agent drafts the deliverable.
   - `human-owns-and-finishes` (`assignee: human`) — human edits it to
     differentiating quality and owns the result. (Single role token — siblings
     `human-verify`/`human-only` use `assignee: human`; do **not** write
     `owner/human` with a slash, which fails `validate`.)
   - `report-to-relay` (`assignee: agent`) — record outcome, bump.
   Also give it a `description:` frontmatter line in the sibling tiers' style
   (one triage-framed sentence).
3. **Update `browser/build-automation`'s tier paths only.** This ticket does
   **not** touch build-automation's triage logic — it's a different decision (see
   Description). The *only* edit is repointing its tier references from
   `browser/<tier>` to `autonomy/<tier>` in `triage-tier` and `emit-and-launch`
   (lines ~25, ~29), because the files moved. Its 3-outcome failure-radius
   routing stays exactly as-is; it does **not** reference `autonomy/triage` and
   does **not** gain an `assist-only` branch (a quality-differentiated task isn't
   a SaaS automation build, so assist-only is out of its domain).
   - **Not** wired into `bootstrap/ticket` — the decision is impl-ready, not
     authoring-time. Authoring no longer triages.

## Follow-up (not here)

A separate ticket wires the test into the **general** authoring/impl path: a thin
triage step, backed by `autonomy/triage`, seeded into `relay-os/workflows/_template.md`
and added to the primary general workflows (`code/*`, `dev/*`, …) so *every*
ticket gets the test at impl-ready. Carved out because it touches the general
workflow surface broadly and deserves its own review.

**File this follow-up as a `draft` before closing this ticket.** Until it lands,
`autonomy/triage` and `autonomy/assist-only` are correct-but-unreferenced library
artifacts (normal for contexts/workflows — they're attached/selected by tickets,
not called by code). Filing the follow-up bounds that orphan window and gives the
files a tracked consumer.

## Build rules — assertion check only, no change expected

The two automation build rules (**dry-run before live**, **easy downgrade** to a
more protective tier) already exist in the tier workflows'
`dry-run-or-downgrade` step (verified). **Not a deliverable.** The build agent
confirms they're still present and that the new `assist-only` workflow is
consistent with them; it does not re-add or edit them.

## Also proposed (not in this ticket)

- **`dochub-form-fill` skill** — DocHub form completion, fully automatable via
  Playwright **except** signature-box placement (a deliberate coordinate-based
  exception to the DOM-backed rule). Its own ticket.

## Seed sync

Keep live + packaged copies in sync per CLAUDE.md
(`src/relay/resources/templates/relay-os/`) for **every** touched file under the
packaged tree: the new `autonomy/triage` context, the four `autonomy/` tier
workflows (three moved — delete the old `browser/` packaged copies — plus the new
`assist-only`), and the edited `browser/build-automation`. Default: sync all.

## Done check (verification — `dev/with-self-review`'s self-qa won't supply this)

The code-diff self-qa tools no-op on markdown moves, so the real done-check is
explicit:

- `relay validate --json` passes (CLAUDE.md's prescribed check after workflow
  changes).
- `grep -rn "browser/\(human-only\|human-verify\|fully-automated\)" relay-os src`
  returns **no** stale references (only `browser/build-automation` and intended
  prose remain).
- All four tier workflows load with the correct `autonomy/<tier>` `name:` (live +
  packaged); no duplicate `browser/` copies remain in the packaged tree.
- A second grep for **bare-word** tier names (eyeball the hits): the only
  intended bare-word survivor is `tasks/browser-automation/ticket.md` "three run
  tiers (fully-automated / human-verify / human-only)" — **leave it**, it's
  correct (build-automation stays 3-outcome; the words are namespace-agnostic).

**Pre-verified during authoring (record, re-confirm if the tree changed):** no
ticket binds `workflow:` to any moved tier (so no `workflow:` field needs
repointing); no test references the tier names; `validate.py` enumerates no tier
whitelist. The move is path-safe.

## Open questions

- None blocking. Resolved: namespace → `autonomy/`; fourth tier → `assist-only`;
  general rollout → follow-up; build-automation triage is a **separate concern**,
  left untouched except for moved tier paths.
