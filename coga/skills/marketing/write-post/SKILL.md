---
name: marketing/write-post
description: The procedure for writing one post in the Coga launch series — brief, thesis stress-test, outline, draft, craft pass, claim check, prepared replies, channel sequencing — and the gates that stop it shipping early. Attach to any marketing/post-* ticket alongside the marketing/plan and marketing/positioning contexts.
---

# Write a Coga launch post

This is the **order of work** for one post in the launch series, and the gates
that block it. It owns sequence and gates only.

Everything about *content* lives in two contexts, and this file defers to both:

- `marketing/plan` — which post this is, its beats, the phasing, the writing
  rules, the claim-discipline rationale, the channel tactics.
- `marketing/positioning` — the spine, the audience, the voice, the honest
  limits, the competitive framing, and the pinned strategic fork.

Read both before step 1. When this file and a context disagree about *what to
say*, the context wins. Never restate a context's content here; cite it.

## Entry condition

A `marketing/post-*` ticket exists and names exactly one post. If you cannot
name, from `marketing/plan`, which post number this is and which phase it sits
in, you are not briefed — that is step 1's job, not something to discover in
step 5.

**Fork A is pinned.** It is an owner decision recorded in
`marketing/positioning` ("The strategic fork"). Write to it. Do not re-derive
it, re-argue it, or reopen it inside a post ticket; changing the fork is an
owner decision taken elsewhere.

## The division of labour with `clarity`

`coga/skills/clarity/SKILL.md` is an imported general prose-craft skill
(upstream `addyosmani/clarity`, MIT) with four modes: **co-write**, **rewrite**,
**review**, **lint**. Its co-write mode runs an author interview and builds a
piece from scratch — the same slot steps 1–4 below occupy. The split is
therefore a decision, not something clarity's design hands over:

- **Steps 1–4 are this skill's.** Do not enter clarity in co-write mode. Coga's
  posts are not open interviews: the two marketing contexts already fix the
  brief, audience, voice, and any required arc, and the source material is a
  repo you can read. Co-write mode would re-derive decisions already made, and
  two skills would fight over the same job.
- **Step 5 is clarity's.** Hand the finished draft to its **rewrite** mode,
  then its **review** mode, then its **lint** mode. That is the craft pass, and
  this skill does not duplicate a line of it.
- **One exception, and only one.** `references/interview.md` has a short "If a
  draft already exists" probe — three questions for passages with no support or
  authorship behind them. Step 4 may use that probe on a specific weak beat.
  That is a gap-filler; it is not a mode switch into co-write.

**Invoke clarity by name, never by slash command.** `docs/with-review` rotates
peer-review to `other-agent`, which may be Codex, and the import pruned
clarity's `commands/` directory — so `/clarity-rewrite` does not exist in this
repo and would not be understood by every agent that runs this skill. Invoke it
by reading `coga/skills/clarity/SKILL.md`, following the named mode's
instructions, and loading the reference files that mode lists. Resolve every
relative `references/` or `scripts/` path against `coga/skills/clarity/`.

---

## Step 1 — Brief

**Do:** From `marketing/plan`, write down the post number, its phase, its one
idea, and any material the plan explicitly excludes from that post. From
`marketing/positioning`, write down the reader and the register.

**Exit:** One paragraph on the blackboard naming: post number, the single idea,
the reader, the excluded material, and the channel set for this phase. If the
single idea needs two sentences to state, it is two posts — say so on the
blackboard and ask the owner which one this ticket is.

**Blocks step 2** until the single idea is one sentence.

## Step 2 — Stress-test the thesis

**Do:** Before outlining, argue against the post's own thesis. Write the
strongest real objection a skeptical reader in the tribe would raise, and the
strongest real limitation of Coga that bears on *this* post's idea. Draw the
limitations from `marketing/positioning`'s "Honest limits" — do not invent
softer ones, and do not invent a weak opponent to defeat.

**Exit:** The objection and the limitation are written down, each with a
decision beside it: **answered in the post**, **conceded in the post**, or
**out of scope for this post and why**. "Answered" requires naming where.

**Blocks step 3** until every objection carries one of those three decisions.
An objection with no decision is a hole the comment section will find.

## Step 3 — Outline against the beats

**Do:** Turn the structure `marketing/plan` supplies into an outline. For post
1, that is the five-beat arc. For a later post, use that phase's stated angle,
exclusions, and evidence or receipt requirements; do not silently reuse post
1's arc. If the plan does not supply enough structure, record the gap and ask
the owner rather than inventing a new post. Attach to every beat or section the
real, checkable material the plan requires.

Apply source requirements only to the post and plan version where they appear;
a condition attached to one post is not a series-wide default.

For post 3, attach the required token and time-to-first-edit receipts to the
outline or blackboard as **private source support**. Use them to test whether
the premise survives and to identify the exact context and repository question
whose understanding was reused. They are not draft copy: do not outline a
measured delta or quote a receipt value. The permitted essay form is the
concrete mechanism — name what the context already answered on a later session
— without saying it was faster or used fewer tokens. Publishing that measured
comparison would require the owner to move the ticket into the proof-post
regime.

**Exit:** Every planned beat or section has real, checkable support attached,
and any missing structure has been resolved. A section carrying only a
generalization is not outlined yet.

**Blocks step 4** while any required beat or section is generic, a required
source is absent, or the plan does not yet define a workable structure.

## Step 4 — Draft

**Do:** Write the post in the voice the contexts define. Where a beat wants
material you do not have, do not invent it — leave `[TK: specific question]`
and carry it forward.

**Exit:** A complete draft with no unresolved `[TK]`. Resolve each one from a
real source, or cut or reframe the passage so it no longer depends on missing
material. If owner input is necessary, escalate under the current session
conduct and wait; recording the question does not satisfy this exit condition.
If a beat is weak on support or authorship, run clarity's three-question probe
from `references/interview.md` against that beat before escalating.

**Blocks step 5** while any `[TK]` remains. Never close one by writing a
plausible detail.

## Step 5 — Craft pass (clarity)

**Do:** Hand the draft to `coga/skills/clarity/SKILL.md`:

1. **rewrite** mode — it loads `coga/skills/clarity/references/edit.md`;
   because this is an authored essay it also loads
   `coga/skills/clarity/references/longform.md`, and because the register is
   marketing it also loads `coga/skills/clarity/references/medium.md`.
2. **review** mode — a critique, no rewriting.
3. **lint** mode — `coga/skills/clarity/scripts/strip_markdown.py` writes a
   stripped copy of the draft, and
   `coga/skills/clarity/scripts/prose_stats.py` reads that copy. Treat every
   hit as a prompt to reread the passage, never as a target to optimize.

Apply clarity's rewrite; take its review findings as findings, not orders. Its
safeguards are Coga's rules already generalized, so they should not fight the
contexts. Where they do, the contexts win and you say so on the blackboard.

**Exit:** Rewrite applied, review findings each either fixed or dismissed with
a reason, lint output read.

**Blocks step 6** until clarity's review has actually been run. Skipping it
because the draft "reads fine" is the failure this handoff exists to prevent.

## Step 6 — Claim-discipline check

**Do:** Read the publishable post once looking only for figures. For each
number, ask whether it appears as a *result*. This check applies to the post,
not to private source attachments on its outline or blackboard.

**The stop rule:** if any figure appears as a result, **stop** — the post has
graduated into the proof-post regime (pre-registration, recomputability), which
this ticket is not running. Cut the figure or escalate to the owner. Do not
drift into that regime by accident.

The reasoning behind the rule, and the one ratio Coga does publish and why it
is exempt, are in `marketing/plan`'s "Claim discipline". Read it there; this
step is the check, not the argument.

For post 3, keep the required receipts attached as support, including their
values. In the post itself, use only the non-result form from step 3: the exact
context and question it cached. Do not publish the values, a delta, or an
unquantified measured outcome such as "it was faster" or "it used fewer
tokens". If the receipts undermine the premise, cut or reframe the claim; do
not make contrary evidence disappear to pass this gate.

**Exit:** Zero figures stated as results in the publishable post, all required
private receipts remain attached to their source notes, and the post's honest
caveat is *in the post* rather than deferred to a FAQ.

**Blocks step 7** while any result-shaped figure survives.

## Step 7 — Prepared replies

**Do:** Write out the replies to the objections this post will draw, before it
ships, in full sentences. `marketing/plan` carries the four standing replies
for post 1; a later post inherits those that still apply and needs new ones
written for the objections *its* idea raises. Step 2's objection list is the
input — anything you decided was "out of scope for this post" is exactly what
arrives in the comment section.

**Exit:** Every objection from step 2, plus the standing replies that apply,
has a written reply.

**This gate blocks shipping.** A post does not go out until the prepared
replies are written. Never improvise one in-thread.

## Step 8 — Channel sequencing

**Do:** Publish in the order `marketing/plan`'s phase section sets, with
per-channel URLs into the blog so attribution works without telemetry.
An optional channel omitted from that phase does not block the post; once it
is chosen, its stated position in the sequence is binding.

**Two hard orderings, both blocking:**

- **Blog first.** The blog is the canonical hub; every other channel points at
  it.
- **Bookface precedes HN**, by a few days. Friendly fire hardens the post and
  YC readers arrive in the HN thread already convinced. Submitting to HN before
  the Bookface read has happened is out of order — hold the submission.

Before any HN submission, reread `marketing/plan`'s "Distribution tactics" and
verify its current submission-form, title, upvote, retry, and founder-presence
rules. Those tactics are context, not duplicated here. Any mismatch blocks the
submission.

**Exit:** Published in the plan's order, with every channel-specific gate
satisfied.

---

## The gates, in one list

A post is blocked from moving forward while any of these is true:

1. The single idea does not fit in one sentence. (step 1)
2. An objection or honest limitation has no answer/concede/out-of-scope
   decision. (step 2)
3. Any planned beat or section lacks real, checkable support. (step 3)
4. Any `[TK]` remains unresolved. (step 4)
5. Clarity's review mode has not been run on the draft. (step 5)
6. A figure appears as a result in the publishable post. (step 6)
7. The prepared replies are not written. (step 7)
8. HN would go out before Bookface, or the blog is not live first. (step 8)

## What this skill does NOT cover

- What the post says — the beats, the voice, the audience, the excluded
  material: `marketing/plan` and `marketing/positioning`.
- Why the claim-discipline rule exists and which ratio is exempt:
  `marketing/plan`, "Claim discipline".
- The pinned fork and the competitive framing: `marketing/positioning`.
- General prose craft — mode selection, the editing pass, the anti-generic
  safeguards, the prose-stat scripts: `coga/skills/clarity/SKILL.md`.
- The proof-post regime: shelved in `marketing/plan` under "Later, gated".
