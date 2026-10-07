---
title: improve PR check
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 2 (peer-review)
agent: claude
launch_generation: 20416a3e-a368-4188-a7e6-0c3b243c0730
---

## Description

Make Coga-generated PRs clear enough for the owner to choose quickly between
merging without rereading, reading the description, and reviewing the diff in
detail. Titles should describe the actual change, identify the authoring and
reviewing agents, and indicate a recommended review depth; descriptions should
justify that recommendation, reproduce the ticket verbatim, explain the
implementation and any departures from the request, describe each changed file,
and report which tests ran and their results. Test requirements belong to the
applicable workflow: this change must not introduce a universal full-suite gate,
and skipped or unrun tests must be visible with a reason. Done means the normal
PR publication flow produces this presentation from actual task and change
evidence, with representative examples demonstrating all three review depths
and explicit reporting when tests or an independent review were not performed.

## Context

- The owner currently cannot choose a review depth from the PR list and has to
  open and investigate each PR. Make the title useful for that first decision,
  and put the short explanation at the top of the body. The recommendation is
  advisory; merging stays the owner's decision. Passing tests alone does not
  justify recommending that the owner skip review. Define the review-depth
  rubric before implementing formatting, with examples showing the evidence
  supporting each recommendation.
- Show actual author/reviewer identities, not simply the GitHub account used
  to publish. A configured agent or peer is not evidence that it performed
  the work: launch overrides and self-review exist. Report unavailable identity
  or absent independent review honestly. Keep the title readable; select a
  compact convention during implementation and show examples for review.
- Reproduce the ticket's title, Description, and Context as written at PR
  preparation time, in a clearly separated, preferably collapsible section.
  This is a snapshot of the requested work, not a paraphrase by the agent.
  Omit operational frontmatter and the blackboard, including the generated PR
  body itself. Keep the agent's commentary outside that snapshot, identifying
  what was delivered, any deviations, and remaining limitations.
- Explain every changed file using the actual PR diff against its base,
  including additions, deletions, and renames. A compact table is suitable;
  identical explanations may group files only if every path remains visible.
  Explain why each change belongs, not merely its diff statistics.
- Report the checks actually run, their commands and outcomes, and distinguish
  passed, failed, pending, and not run. Explain omissions or inapplicability;
  do not turn absent evidence into success. Preserve test obligations already
  imposed by the selected workflow. Broader test-policy redesign, mandatory
  full-suite execution for every PR, merge automation, and repository-wide
  GitHub branch-protection changes are outside this ticket.
  Tie test and review evidence to the published change; later edits must not
  inherit an unsupported claim that the current diff passed tests or review.
- Start with `open_pr._pr_body` and `open_pr.open_pr` in
  `src/coga/open_pr.py`, plus `tests/test_open_pr.py`. Currently the command
  uses the ticket title directly and prefers an agent-authored `## PR` body,
  then falls back to Description/title and appends the ticket closure marker.
  Keep deterministic extraction/formatting in the existing publication path;
  review-depth judgment and explanatory prose belong to the agent's preparation
  step. Missing evidence must remain legible in fallback output, too.
- Read the body-authoring instructions in `coga/skills/code/implement/SKILL.md`,
  `coga/skills/code/self-qa/SKILL.md`, `coga/skills/code/open-pr/SKILL.md`, and
  the bundled workflows under
  `src/coga/resources/templates/coga/bootstrap/workflows/code/`. Update the
  applicable instructions together so different code workflows produce the
  same presentation. Account for a rerun that finds an existing PR: the
  presentation must not silently remain stale after the prepared title/body
  changes, and intentional human edits must not be silently lost. Define how
  generated content is distinguished from human edits and verify both cases.
  General shortening of the shared implementation, publication, and review
  skills is separate maintenance and outside this ticket.
- `coga/internals/pr-publication`, at
  `docs/contexts/coga/internals/pr-publication/SKILL.md`, is cited rather than
  attached because it is an editing target. Read its introduction and
  "Checks, in order": publication already owns branch checks, push, PR reuse,
  and recording `pr:`; preserve those guarantees and the URL-only stdout
  contract while changing presentation. Update this owning topic and any
  affected skills/workflows together with their packaged twins. Use focused
  publication tests and the packaging twin check to verify the changes.

<!-- coga:blackboard -->

## Dev
branch: improve-pr-presentation

## Implementation plan

Owner approved the proposed convention in the attended session: `[merge|skim|deep · A:<actual author> R:<actual reviewer>] <actual change>`. Merge is advisory and needs small low-risk scope, completed independent review, applicable checks and no unresolved concerns; skim invites reading the rationale; deep covers risk or missing evidence. Self-review and unknown identities stay explicit.

Keep extraction/formatting in `src/coga/open_pr.py` (`_pr_body`, `open_pr`) and judgment/prose in preparation instructions. Bind evidence to head/base revisions, list every diff path, retain a verbatim title/Description/Context snapshot, and make missing tests/review explicit. Mark and fingerprint generated title/body; refresh untouched content on reruns, preserve external human notes, and refuse conflicting edits. Preserve publication gates and URL-only stdout. Update owning topic, applicable skills/workflows and twins; focused tests, full suite required by this implementation step, and fixture validation.

Actual implementing agent: Codex (session identity; ticket's configured `claude` is not evidence). No independent implementation review has run in this step.


## Implementation handoff

- Implemented and pushed `improve-pr-presentation` at `4b63afe49cd019b46ee97bd7492b1782df9fd052`; prepared diff base is `e1c9fcac385930fb12a80700b13fb44f6676fb78`. Actual implementing agent: Codex. No PR opened and no independent review run; peer-review is next.
- Owner approved the merge/skim/deep title convention before code changes. The owning publication topic now carries the rubric and representative examples for all three depths; agent instructions carry preparation, and the existing recipe owns deterministic rendering.
- Snapshot includes literal title/Description/Context and excludes operational metadata/blackboard. Current Git diff supplies every path, including both rename endpoints. Missing/stale evidence is explicit and conservative; no universal full-suite gate was introduced.
- Reruns refresh intact generated title/body, preserve external human notes, and refuse conflicting human/legacy edits before push; a second read catches edits during push. GitHub's remaining last-read/write race is documented.
- Verification on final rebased commit: full suite `3307 passed in 249.10s (0:04:09)`; example validation `ok_count: 4`, no issues. Focused publication/command/packaging checks before rebase: `.venv/bin/python -m pytest tests/test_open_pr.py tests/test_open_pr_command.py tests/test_packaging.py -q --disable-warnings` → `106 passed in 13.89s`; superseded for current-revision evidence by the final full suite. The first new regression run failed as expected before the implementation; a snapshot assertion then needed an exact heading match rather than the prefix of “Deviations”; final checks are green.
- All changed live skills/topic match their packaged twins. Example workflow updated and validated. No unresolved adjacent bug recorded. Limits: no live GitHub write in this step; legacy/conflicting presentation needs owner reconciliation; concurrent edits after the final GitHub read can still race.
- Next step: independently review the final diff, record the actual reviewer/session and covered head/base, apply any fixes, rerun required checks, and refresh `## PR` below without re-stamping older receipts. This initial preparation correctly recommends deep review and reports that independent review has not run.

## PR

```yaml
title: Show PR review depth and preserve human edits on reruns
author: codex
author_evidence: Codex implemented this branch in the attended session; the ticket configuration naming
  Claude was not used as authorship evidence.
head: 4b63afe49cd019b46ee97bd7492b1782df9fd052
base: e1c9fcac385930fb12a80700b13fb44f6676fb78
depth: deep
rationale: Changes publication evidence and overwrite behavior. The full suite passes, but independent
  review belongs to the next peer-review step and has not run; inspect this diff before merging.
implementation: Render a structured markdown/YAML preparation record into an advisory title, rationale,
  implementation/deviations, per-file reasons, checks and verbatim ticket snapshot. Match evidence to
  the feature commit and merge base. On reruns, refresh intact generated content and preserve human notes
  outside its digest-marked region.
deviations: None. Existing branch/auth/push/freshness/URL-only publication guarantees remain, and test
  obligations stay with the workflow. The full suite ran because this implementation step requires it.
limitations: No live GitHub PR was opened in this implementation step. Tests use real local Git and a
  fake gh. Human edits inside generated content and unmarked legacy PRs require reconciliation. GitHub
  title/body edits have no atomic compare-and-set, so a simultaneous edit after the last read can still
  race.
files:
  coga/skills/code/implement/SKILL.md: Capture actual implementing identity, exact check receipts and
    initial PR preparation, including workflows without code review.
  coga/skills/code/open-pr/SKILL.md: Consume prepared evidence, explain safe refresh and conflicts, and
    apply the review-in-flight gate only when the workflow ordered code review.
  coga/skills/code/self-qa/SKILL.md: Refresh preparation after fixes and distinguish self-review from
    independent review on a particular revision.
  docs/contexts/coga/internals/pr-publication/SKILL.md: Own the rubric, preparation schema, fallback behavior
    and generated-content conflict contract while retaining publication guarantees.
  example/coga/workflows/code/with-review.md: Keep the example publication step representative of the
    structured preparation and deterministic command.
  src/coga/open_pr.py: Format revision-bound preparation and the literal request; enumerate the actual
    diff; refresh intact generated content while preserving external human notes and refusing conflicts.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/pr-publication/SKILL.md: Ship the
    byte-identical owning publication topic and its rubric/schema.
  src/coga/resources/templates/coga/bootstrap/skills/code/implement/SKILL.md: Ship the byte-identical
    code/implement skill so installed repositories receive the same preparation instructions.
  src/coga/resources/templates/coga/bootstrap/skills/code/open-pr/SKILL.md: Ship the byte-identical code/open-pr
    skill so installed repositories receive the same preparation instructions.
  src/coga/resources/templates/coga/bootstrap/skills/code/self-qa/SKILL.md: Ship the byte-identical code/self-qa
    skill so installed repositories receive the same preparation instructions.
  src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md: Require implement-owned
    preparation and explicitly distinguish design approval from code review.
  src/coga/resources/templates/coga/bootstrap/workflows/code/with-review.md: Make the peer-review step
    prepare actual review/check receipts and explanatory prose after its final fixes and rebase.
  src/coga/resources/templates/coga/bootstrap/workflows/code/with-self-review.md: Point workflow framing
    at the shared preparation contract and honest self-review reporting.
  tests/test_open_pr.py: Exercise all three depths, actual identities, stale/missing verification, snapshot
    boundaries, added/deleted/renamed files, and safe PR refresh with real Git and fake gh.
review:
  kind: none
  status: not-run
  detail: Independent review is the next workflow step; no independent code review has run during implementation.
checks:
- command: PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest -q
  status: passed
  head: 4b63afe49cd019b46ee97bd7492b1782df9fd052
  base: e1c9fcac385930fb12a80700b13fb44f6676fb78
  detail: 3307 passed in 249.10s (0:04:09); includes focused publication tests and packaging twins on
    the final rebased commit.
- command: env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/codex/coga/src /home/n/Code/codex/coga/.venv/bin/python
    -m coga.cli validate --json
  status: passed
  head: 4b63afe49cd019b46ee97bd7492b1782df9fd052
  base: e1c9fcac385930fb12a80700b13fb44f6676fb78
  detail: 'Run from example/coga on the final rebased commit: ok_count 4, no issues.'
- command: git diff --check
  status: passed
  head: 4b63afe49cd019b46ee97bd7492b1782df9fd052
  base: e1c9fcac385930fb12a80700b13fb44f6676fb78
  detail: No whitespace errors.
- command: gh pr create
  status: not-run
  detail: This implementation step stops before PR creation; the later publication step owns it. Real-Git/fake-gh
    regression tests cover creation, refresh, draft readiness and refusal paths.
```
