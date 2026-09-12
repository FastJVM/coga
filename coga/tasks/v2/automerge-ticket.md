---
title: automerge ticket
status: paused
owner: nicktoper
agent: claude
contexts:
- dev/code
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

Add a new workflow `code/optimistic-merge` that mirrors `code/with-review`
(implement → peer-review by the *other* agent → open-pr) but replaces the
final human `review` step with an **agent** step that merges the PR
optimistically. The premise is speed: most reviewed-and-peer-checked
changes are fine, so an agent merges them without waiting on the human,
and the human stays a post-hoc safety net to catch and revert the rare
mess-up. This is the inverse of the existing `autoclose-merged` recurring
sweep (the `coga autoclose` alias), which only marks a ticket `done` after a
human merges; here an agent does the merging.

## Context

**Premise re-checked 2026-09-12** by `four-parked-tickets-carry-premises-that-have-since`.
The subject was never built and the workflow it mirrors still exists, so the ticket
stands — but every file location and command below was rewritten against the current
tree. The `## Evaluator review` on the blackboard verified the *old* layout; treat its
"correct and verified" packaging claim as stale.

**Mirror, don't reinvent.** Copy the shape of
`src/coga/resources/templates/coga/bootstrap/workflows/code/with-review.md`. Keep
steps 1–3 identical, including their `requires:` gates: `implement`
(`code/implement`, `requires: branch`), `peer-review` (`assignee: other-agent`, which
resolves to the main agent's configured peer — see `src/coga/bump.py`), `open-pr`
(`code/open-pr`, `requires: pr`; the `coga open-pr` recipe already refuses a branch
with unsafe drift from the control branch). Only the final step changes.

**Where the files go — this is the inverted part.** The `code/` workflow namespace
**is** shipped in the packaged template, and only there: the three `code/*`
workflows live under `src/coga/resources/templates/coga/bootstrap/workflows/code/`
and the live tree has no `coga/workflows/code/` directory. Per `coga/architecture`,
a repo-local `coga/workflows/<ref>.md` *overrides* the bundled
`bootstrap/workflows/<ref>.md`, so a live copy would sit in the override layer, not
beside its siblings. Therefore:

- the workflow is `src/coga/resources/templates/coga/bootstrap/workflows/code/optimistic-merge.md`
  with **no** live twin;
- the new skill is `src/coga/resources/templates/coga/bootstrap/skills/code/merge-pr/SKILL.md`
  **and** its live twin `coga/skills/code/merge-pr/SKILL.md`, because the other
  `code/*` skills have live twins and `tests/test_packaging.py` requires every
  packaged/live pair to be byte-identical.

**New final step = agent merge.** Replace the `review` step
(`assignee: owner`, `code/address-pr-comments`) with `assignee: agent` (by this
point `open-pr` has routed back to the main agent, so the merging agent is the
original author; that's fine). This needs the **new skill** `code/merge-pr` —
`code/open-pr` cannot be reused: its remit is the deterministic push/open/record
command, and its worked case (PR #723, in that skill) records the owner's precedent
that merging without a returned review is the failure mode to avoid. The merge skill
should: read `pr:` from the blackboard `## Dev` section (the `dev/code` convention,
attached as a context); require the `## Peer review` note to record that the review
**returned** (the same evidence `code/open-pr` gates on); require the verification
gate below; run `gh pr merge`; then run `coga mark done <slug>` itself. A failed
gate is a hard stop: `coga block --task <slug> --reason "…"` (the successor of the
old `panic` command), not a note-and-bump.

**Verification gate — re-examine before implementing.** The recorded decision was
"CI gate = required (hard stop)". This repo has **no PR test job**: the only GitHub
Actions workflow is the publish-only `release.yml`, so `gh pr checks` has nothing to
report (see `no-context-records-the-ci-posture-publish-only-rel`, which records this
in `coga/codebase`). Until `v2/minimal-ci-run-pytest-on-prs-and-tags` ships, "green"
can only mean the local gate — `python -m pytest` and `coga validate --json` run from
the rebased feature checkout — and the skill must say so explicitly rather than
naming a check that does not exist.

**Human safety net = loud post.** The owner is cc'd on every broadcast by being
`owner:`; the `watchers:` field was removed with the simplified ticket format (#784)
and is not available. The load-bearing mechanism is a **live** Slack post on merge:
`coga slack --task <slug> --message "merged <pr-url> — revert if wrong"` so the owner
can review post-hoc and revert fast. The merge is optimistic; safety is fast
visibility, not a blocking gate.

**Decisions already made (don't re-litigate):** name = `code/optimistic-merge`;
verification gate = required, hard stop; safety net = loud live post on merge. The
only decision reopened above is *what* the gate checks, because the remote check it
assumed does not exist.

**Scope / out of scope.** One packaged workflow file, one skill in two copies, plus a
short human-facing section in the workflow body documenting the optimistic-merge
step (mirror how `with-review.md` documents `## review`; note that a step declaring
`skills:` does not compose its inline section). No Python/CLI changes are expected;
if the merge step needs new CLI support, that is a separate ticket — block and
surface it rather than expanding scope here. Markdown-only, so validate with
`python -m pytest` (the packaging twin test) and `coga validate --json` plus a
read-through; do not run this ticket's own workflow under the new workflow.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Bootstrap notes

Ticket filled by `bootstrap/ticket` (interactive, with nick).

Subject: add `code/optimistic-merge` workflow — mirrors `code/with-review`
(implement → peer-review → open-pr) but the final human `review` step is
replaced by an **agent** step that merges the PR optimistically. Human stays
a post-hoc safety net.

Human decisions (AskUserQuestion):
- Workflow name: `code/optimistic-merge` (avoids collision with the existing
  `relay automerge` auto-bump command).
- Safety net: "Both" (watcher + loud post) — narrowed during write to **loud
  live post** as the load-bearing mechanism, since the owner is already cc'd
  on broadcasts by being `owner:` (watcher self-add is redundant). See ticket.
- CI gate: required (hard stop / `panic` on red).
- This ticket runs under: `code/with-review`.

Key design facts captured in ticket `## Context`:
- New skill needed: `relay-os/skills/code/merge-pr/SKILL.md` (open-pr can't be
  reused — it says merging is the human's job).
- Merge step `assignee: agent` (coder; open-pr flipped back to coder).
- Merge skill overrides open-pr's "bump anyway on red CI" → here red CI = panic.
- Don't rely on `relay automerge` auto-bump as a backstop (only fires on final
  step, which the merge step already is) — call `relay mark done` directly.
- `code/` workflow namespace is NOT in the packaged template
  (`src/relay/resources/templates/relay-os/`), so no dual-copy sync needed.
- Attached context: `dev/code` (the `## Dev` / `pr:` blackboard convention the
  merge skill reads).

## Evaluator review

I have everything I need. Here is my cold-read critique.

---

**1. Clarity / can an agent start cold?**

Yes, mostly. The Description plus the "Mirror, don't reinvent" framing give a clear mental model: copy `with-review.md`, keep steps 1–3, replace step 4. The contrast with the existing `relay automerge` (auto-bump after human merge vs. agent-does-the-merging) is well drawn and pre-empts the obvious confusion. An implementer would know what to build. The main gap is that the ticket tells the agent to put the merge logic in a new skill but doesn't specify the workflow file's frontmatter precisely — e.g. it never says what `assignee:` the final step gets (it says "an agent step" but `with-review`'s coder is `agent`; after `open-pr` flips back to coder, is the merge done by the coder or the peer?). That's left to inference.

**2. Workflow fit (`code/with-review`).**

This is the clearest weakness. The work is "write two markdown files" (a workflow + a skill). Running it under `code/with-review` means: implement → peer-review by the *other* agent → open-pr → human review. That is a heavyweight code-change workflow applied to authoring a couple of prose/markdown files. Steps like `code/implement`, `python -m pytest`, "is the PR mergeable vs main," and Codex peer-review of a diff are awkward overkill for adding two `.md` files with no Python. There are no tests to run for a markdown-only change. It's usable but mismatched in shape; a lighter workflow (or design-then-implement) would fit better. Note also the ironic recursion: this ticket sits in `code/with-review`, whose final human-review step is exactly what the new workflow proposes to remove.

**3. Contexts (none attached; facts in `## Context`).**

`contexts: []` and `skills: []` are both empty, and the durable facts are pasted into prose. The implementer will want at least two contexts wired in that they'll otherwise have to find by hand:
- the `dev/code` context (the `pr:` / `## Dev` blackboard convention) — referenced by name but not attached;
- the `architecture` context, which is where `watchers`, `other-agent`, and step/assignee resolution are actually defined.

Missing facts the implementer will wish were here: the field is `watchers` (plural list), not `watcher` (the ticket says "watcher" singular twice) — and crucially, **this ticket's own frontmatter has no `watchers:` field at all**, so the "ensure owner is also a watcher" instruction has no worked example to copy. Also missing: the exact name of the `dev/code` context file, and a pointer to `src/relay/bump.py` where `other-agent` resolution lives.

**4. Scope.**

Reasonable and well-bounded for the core ask (one workflow file + one skill). The explicit "out of scope / separate ticket if CLI support is needed" clause is good discipline. However it quietly bundles **two non-trivial new behaviors** that aren't free markdown:
- "ensure the ticket's `owner` is also a `watcher`" — there's no mechanism shown for a workflow/skill to *mutate* the ticket's `watchers` field; a skill is prose instructions to an agent, so this becomes a manual edit step the agent must perform each run, not a workflow property. That's underspecified and may be the seed of a real feature.
- "require CI green and `relay panic` if red" — fine as prose, but note it directly contradicts the reused `code/open-pr` skill, which says to blackboard a CI failure and **bump anyway**. The new merge step inverts that policy; the implementer needs to be aware they're overriding, not inheriting.

So: not multiple tickets' worth, but two soft assumptions hiding inside a "just markdown" framing.

**5. Assumptions to question before launch.**

Most of the design holds up against the actual primitives — I verified:
- `relay slack --task --message` exists and is the **live** path (cc's owner + watchers); the ticket's claim is accurate. Good.
- `other-agent` resolves and exactly two agents (`claude`, `codex`) are configured, so step 2 works as claimed. Good.
- `relay panic` and `relay mark done` exist. Good.
- The packaged-template claim is **correct and verified**: `src/relay/resources/templates/relay-os/workflows/` has only `browser/` and `_template.md`, no `code/`. So "no dual-copy sync" holds. The ticket's "but confirm before assuming" hedge is unnecessary caution here, but harmless.

Assumptions that are shaky:
- **"the existing `relay automerge` auto-bump will close the ticket"** — false as a fallback for *this* workflow. `auto_bump_one`/`auto_bump_merged` only bump a ticket that is **on its final step** (`_on_final_step`). In the new workflow the agent-merge *is* the final step, and the agent is told to `relay mark done` itself. So automerge auto-bump is essentially redundant here, not a safety net — and if the agent merges but is *not* yet on the final step, automerge will deliberately ignore it ("mid-workflow merges stay alone"). The ticket's "don't rely on the hook, run mark done yourself" instruction is right, but the framing that automerge backstops it is misleading.
- **owner = watcher self-cc**: `relay slack`/`post` already pass `owner=ticket.owner` and cc the owner inline regardless of watchers. The owner is *already* notified by virtue of being owner. Adding the owner to `watchers` may be redundant — worth confirming the post path doesn't already cover the stated goal before building machinery for it.
- **"`gh pr merge` then the task is done"**: no check that the merging agent has push/merge rights, branch-protection allowing a non-human merge, or that `gh pr checks` exists and is wired — these are environment assumptions the ticket asserts but doesn't ground.
- **field name**: `watcher` (singular, as written) is not the schema field; it's `watchers`. Minor but will trip a literal implementer.

Net: the core idea is implementable with existing primitives, but two of its load-bearing claims (automerge as backstop; owner-as-watcher as the safety mechanism) are partly redundant or inaccurate, the workflow choice is heavier than the work, and the empty `contexts`/`skills` push real lookup burden onto the implementer.

---

(Note: the ticket was revised after this review to address points 1, 3, 4, and 5 —
final-step `assignee: agent` now specified; `dev/code` attached + `architecture`/`bump.py`
pointers added; `watcher`→`watchers` corrected and the self-cc redundancy called out;
automerge-backstop framing fixed; CI-gate override of open-pr made explicit; markdown-only
"no pytest" caveat added. Point 2 — workflow heaviness — left as-is per nick's choice of
`code/with-review`.)

## Premise re-check (2026-09-12)

Rewritten by `four-parked-tickets-carry-premises-that-have-since` (Dream 2026-W36
finding, shard `ks-10`). What changed since the bootstrap notes and evaluator review
above were written:

- The packaging claim inverted: `code/*` workflows now ship **only** in the packaged
  `bootstrap/workflows/code/` tree; there is no live `coga/workflows/code/`. The
  evaluator's "correct and verified — no `code/`" line described the pre-rename
  layout and is stale.
- Pre-rename surfaces mapped: `relay-os/` → packaged `bootstrap/` (workflows) or
  `coga/` + packaged twin (skills); `relay panic` → `coga block`; `relay slack` →
  `coga slack` (still the live path); `relay automerge` → the `autoclose-merged`
  sweep / `coga autoclose` alias; `src/relay/bump.py` → `src/coga/bump.py`.
- `watchers:` no longer exists (removed with the simplified ticket format, #784);
  the owner cc is the whole safety-net audience.
- `code/open-pr` no longer carries a "blackboard the CI failure and bump anyway"
  policy, so the "deliberate override" framing is moot; and the repo has no PR test
  job at all, so the CI gate must be restated as the local `pytest` + `coga validate`
  gate until `v2/minimal-ci-run-pytest-on-prs-and-tags` exists.
- New precedent to respect: the PR #723 worked case in `code/open-pr` — the owner
  chose to hold the review gate when a review returned after merge. The merge skill
  gates on the returned `## Peer review` note for that reason.

The recorded human decisions (name, hard-stop gate, loud post) were kept; only the
gate's *check* was reopened, because the remote check it assumed does not exist.
