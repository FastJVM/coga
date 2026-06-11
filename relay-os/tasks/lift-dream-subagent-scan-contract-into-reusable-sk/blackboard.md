The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: dream-scan-skills
worktree: /tmp/relay-dream-scan-skills

## Implementation notes

Created prompt-only scan skill contracts for:

- `bootstrap/dream/scan/knowledge-scan`
- `bootstrap/dream/scan/contract-audit`

Trimmed both Dream recurring ticket copies so Phase 2/3 delegate to those
skills and keep only the phase framing plus `## Findings` handoff.

Important packaging detail: `relay-os/bootstrap/` is generated/ignored in this
source checkout. The committed durable skill files are under
`src/relay/resources/templates/relay-os/bootstrap/skills/bootstrap/dream/scan/`;
`relay init --update` materializes them into `relay-os/bootstrap/`. I also
materialized ignored live copies in `/tmp/relay-dream-scan-skills` for local
parity checks, but they are not staged.

Verification:

- `cmp` confirmed live and packaged Dream recurring tickets match.
- `cmp` confirmed ignored live scan skills and packaged scan skills match in the
  feature worktree.
- `rg` confirmed the new scan skills have no `script:` and no
  `## Known Skill Contract`.
- `PYTHONPATH=/tmp/relay-dream-scan-skills/src python -m relay.cli validate --task lift-dream-subagent-scan-contract-into-reusable-sk --json`
  passed with 1 ok and no issues.
- `PYTHONPATH=/tmp/relay-dream-scan-skills/src python -m pytest` passed:
  624 passed, 1 skipped.
- Full `relay validate --json` is not clean in this checkout before/aside from
  this change: it reports pre-existing draft/workflow issues and missing
  generated bootstrap skills in the fresh worktree. The targeted task validation
  above is clean.

Follow-up still out of scope: Phase 3's contract-audit corpus globs
`relay-os/contexts/**` and `relay-os/skills/**`, not
`relay-os/bootstrap/skills/**`, so it still will not audit the bundled Dream
skills that define it. This ticket intentionally did not widen that audit
surface.

Workflow-state note: the ticket was still `draft` when implementation started,
so the first `relay bump` refused. I activated it with `relay mark active`;
that updated the ticket but git sync hit the sandboxed `.git/index.lock` write
restriction. I also corrected `agent:` / `assignee:` from `claude` to `codex`
because Codex implemented this step; otherwise `other-agent` would resolve the
peer-review step back to Codex instead of Claude.

## Ticket refinement (2026-06-09, pre-launch)

Human flagged the ticket looked obsolete. Verified it is NOT — the two skill
files don't exist yet and the Phase 2/3 contract is still inlined verbatim in
`relay-os/recurring/dream/ticket.md` (lines ~82–145). Packaged mirror currently
byte-identical to live.

Fixed one real drift: the ticket originally specified skill paths under
`bootstrap/dream/scan/...` rooted at a top-level `relay-os/skills/`. The real
dream-skills root is `relay-os/bootstrap/skills/bootstrap/dream/` (where
`tasks/validate-drift` and `tasks/cleanup-orphan-markers` live). Corrected the
target paths to `relay-os/bootstrap/skills/bootstrap/dream/scan/<name>/SKILL.md`,
referenced as `bootstrap/dream/scan/<name>`.

Folded the evaluator's three tightenings into acceptance: (a) skills are
prompt-only (no `script:` / `## Known Skill Contract`), validate-drift is the
wrong shape to copy; (b) replaced the unverifiable "identical Dream rerun"
acceptance with a content-equivalence diff check; (c) packaged-mirror sync now
covers the two new skill files, not just the recurring ticket body.

Possible follow-up (out of scope here): Phase 3 contract-audit globs
`relay-os/contexts/**` and `relay-os/skills/**`, which don't cover
`relay-os/bootstrap/skills/…` — so the audit doesn't read the dream skills that
define it. Pre-existing (the `tasks/` skills are already outside it). Noted in
ticket ## Context.

## Evaluator review

The packaged templates mirror `bootstrap/skills/bootstrap/dream/tasks/` but the ticket's acceptance only requires syncing the recurring `ticket.md`, not the new skill files. That's a gap. I have everything I need.

---

**Evaluation: lift-dream-subagent-scan-contract-into-reusable-sk**

**1. Description clarity — mostly clear, one ambiguity.**
An agent with no context could start. The intent ("lift the two inlined subagent contracts into reusable SKILL.md files, then trim the Dream body to reference them") is unambiguous, and the two target skill paths are spelled out literally. The source-line range (82–145) is approximately correct — Phase 2 starts at line 82 and Phase 3's contract ends at line 144, so that pointer is accurate. The one soft spot: the ticket never states what a *prompt* (non-script) SKILL.md should contain for frontmatter. The only shape reference given (validate-drift) is a `script:` skill with a `## Known Skill Contract` block tuned for script workers; the new skills are subagent-prompt skills with no script. An agent may wrongly copy the `script:`/`## Known Skill Contract` shape. Confirmed there are many prompt-only SKILL.md files in the repo (e.g. `relay-os/contexts/**`, `relay-os/skills/google-agents-cli-*`) that would be a better shape reference — the ticket points at the wrong archetype.

**2. Workflow fit — appropriate.** `code/with-review` (implement → peer-review → open-pr → review) fits: this is a file-authoring + template-edit change that produces a reviewable PR, and the dream disposition convention itself scaffolds gap tickets with exactly this workflow. Good match.

**3. Scope — reasonable, single ticket.** Two sibling skill files of the same shape plus one template trim (mirrored to the packaged copy). It is cohesive and bounded; not multiple tickets' worth.

**4. Path/convention claim — CONFIRMED CORRECT, with one caveat.**
- Existing dream skills do live under `relay-os/bootstrap/skills/bootstrap/dream/` — verified: `tasks/validate-drift/` and `tasks/cleanup-orphan-markers/` are present, with `name:` frontmatter `bootstrap/dream/tasks/<name>`. So the reference convention (`bootstrap/dream/scan/<name>` → `…/bootstrap/dream/scan/<name>/SKILL.md`) is consistent with the established `tasks/` segment. The proposed `scan/` segment is a clean parallel.
- The warning "do NOT create under a top-level `relay-os/skills/`" is well-founded: that tree exists and holds unrelated imported skills.
- `scan/` does not exist yet (correct — it's to be created).
- **Caveat (latent contradiction, worth flagging):** Dream's own Phase 3 contract audit (lines 116–117 of the source) audits `relay-os/contexts/**/SKILL.md` and `relay-os/skills/**/SKILL.md`. The new scan skills live under `relay-os/bootstrap/skills/…`, which is outside both globs — so the contract audit will not audit the very skills that define it. Whether that's intended or a gap is unstated; the ticket should acknowledge it.

**5. "A Dream rerun behaves identically (same findings on the same fixture)" — UNDERSPECIFIED / not verifiably actionable.**
This is the weakest acceptance criterion. Problems:
- No fixture is named. There is no seeded Dream-run fixture identified, and the knowledge scan / contract audit are subagent reads over the *live repo corpus*, not a deterministic script with a golden output. "Same findings" is not reproducible — an LLM subagent will not emit byte-identical findings run to run even with no change.
- The change is a pure refactor of prose *into* a referenced skill; there's no cheap way to actually execute a full Dream run as part of review (it deletes done tickets, opens PRs). An agent cannot realistically "rerun Dream" to verify.
- Realistic intent is probably "the lifted skill text is content-equivalent to what was inlined, so the contract the subagent receives is unchanged." That should be the acceptance: a diff showing the taxonomy/corpus/output-shape text is preserved verbatim (or with only the framing trimmed), not a behavioral rerun. As written, a future agent cannot check this and will either skip it or invent a fixture.

**6. Assumptions to question / missing items.**
- **Packaged skill copy not in scope (likely a miss).** The acceptance syncs only `recurring/dream/ticket.md` to its packaged mirror. But the packaged tree *does* mirror `bootstrap/skills/bootstrap/dream/tasks/` (verified present under `src/relay/resources/templates/…`). The two new skill files almost certainly also need packaged copies, or the trimmed recurring body will reference skills that don't exist in the shipped package — exactly a "referenced artifact missing" drift the audit is meant to catch. The ticket should require mirroring the new SKILL.md files too, not just the ticket.md.
- **Provenance unverifiable.** The ticket says this came from "Dream-2026-W21 knowledge scan as gap G1," but no such artifact is on disk (no `*W21*` file; no G1 marker found in dream blackboards). Not blocking, but the cited evidence can't be inspected by the picking-up agent.
- **Frontmatter shape unspecified for prompt skills** (see #1) — the single most likely source of an inconsistent result.
- **"preserve the per-phase delegation framing and the `## Findings` handling downstream"** is good guidance, but it leaves a judgment call about how much of the ~60 lines stays inline vs. moves into the skill. Reviewer and implementer could disagree on where the line is; a one-sentence rule ("the body keeps only the delegate-to-subagent sentence + Findings write target; everything classificatory moves to the skill") would remove that ambiguity.

**Bottom line:** Paths and convention are correct and the scope is right-sized; safe to launch after tightening three things — (a) point the implementer at a *prompt* SKILL.md as the shape reference, not the script-skill validate-drift; (b) replace the "identical Dream rerun" acceptance with a content-equivalence diff check; (c) add the two new skill files to the packaged-mirror sync requirement.

## Peer review + open PR (claude, 2026-06-10)

Peer-reviewed the implemented diff (step 2). **Verdict: clean pass.**
- Two prompt-only skills (`knowledge-scan`, `contract-audit`) with correct
  `name:`/`description:` frontmatter, no `script:`, no `## Known Skill
  Contract` — the right shape per eval point (a).
- Phase 2/3 prose lifted content-equivalent into the skills; both recurring
  ticket copies (live + packaged) trimmed to "delegate to
  `bootstrap/dream/scan/<name>`" + `## Findings` handoff. Packaged mirror
  includes the two new skill files (eval point c satisfied).
- Known limitation (contract-audit globs don't cover `bootstrap/skills/**`,
  so the audit can't see the skills that define it) is documented and
  intentionally out of scope.

Branch was forked from day-old main; rebuilt cleanly on current main with ONLY
the 5 substantive files (skills + both dream templates + tests) so the PR can't
revert main's bump history. Force-pushed (user-authorized) `dream-scan-skills`.

Verification on the rebuilt branch:
- `python -m pytest` → 636 passed.
- `tests/test_dream_worker_templates.py` → 9 passed.

PR: https://github.com/FastJVM/relay/pull/333
