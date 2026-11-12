---
title: Make hands-on-trial cite the shared fresh-vm skill
status: done
owner: nicktoper
workflow:
  name: docs/with-review
  steps:
  - name: implement
    skills: []
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills: []
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
agent: claude
---

## Description

`coga/skills/competition-testing/hands-on-trial/SKILL.md` (proposed in PR
#1145) carries its own VM preparation steps. `coga/skills/coga/testing/fresh-vm/SKILL.md`
(proposed in PR #1153) is meant to be the single owner of VM preparation,
baseline capture, reuse, and cleanup for attended install walks and competitor
trials. Once both have merged to main, replace hands-on-trial's duplicated
VM-hygiene instructions with a citation of `coga/testing/fresh-vm`, so the
procedure has one owner per `coga/knowledge`.

Done when hands-on-trial points to fresh-vm for VM choice, preparation, baseline,
reuse, and cleanup, and restates no competing VM procedure. The trial-specific
guidance that fresh-vm does not own stays in hands-on-trial.

## Context

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

### Route: follow-up PR from main

Both PRs merged on 2026-11-04, in the opposite order to the plan: #1145
("New skill: hands-on competitor trial method") at 19:15 UTC, then #1153
("Add attended install-walk guidance with shared VM preparation", which adds
`coga/skills/coga/testing/fresh-vm/SKILL.md`) at 19:23 UTC. #1145 therefore
went in without the fresh-vm citation, so this ticket is the follow-up: branch
from current main and open its own PR. On main as of 2026-11-07,
hands-on-trial still has the **Fresh VM.** bullet in `## Setup`, the
"demand or a habit carried over" question, and the "cannot copy from the agent
session" text in the command relay.

### What to change

- Replace the VM-procedure parts of hands-on-trial with a link to fresh-vm.
  That covers the **Fresh VM.** bullet in `## Setup` ("Use a spare bare
  `cogatest` UTM machine, and have the human confirm which one at launch") and
  any VM reuse/cleanup steps. Use the same link form that
  `clean-install/human-walk` uses for fresh-vm.
- Remove restatements of facts that fresh-vm owns. Two are known now:
  separating steps the human installed from habit (fresh-vm `## Reusing a
  spare`), and the human being unable to copy from the agent session into the
  VM (fresh-vm `### Moving commands and evidence`) in the command-relay text.
  The relay artifact itself is trial-specific and stays.
- Keep the trial rules that fresh-vm does not own: install coverage starts at
  the bare machine's prerequisites, demands are recorded in order, earlier
  trials' write-ups are read first, and all laps run in the same VM and
  project directory (a `## Laps` rule, not VM hygiene). Read fresh-vm's final
  text to draw the line; the lists above are examples, not the boundary.
- Don't hard-code UTM/macOS in hands-on-trial. Let fresh-vm's "Choose the
  starting environment" pick the platform.
- Rule applied: `coga/knowledge` (`docs/contexts/coga/knowledge/SKILL.md`),
  cited, not attached. Read its one-owner rule ("one owner per fact; other
  surfaces summarize and link") and `## Attach or cite`. Neither skill file is
  attached either: one is edited, the other read once.
- No packaged twin: both skills are repo-local (nothing under
  `src/coga/resources/templates/coga/bootstrap/skills/competition-testing/` or
  `.../coga/testing/fresh-vm`), so `tests/test_packaging.py` does not pair them.
- Do not touch the competitor findings. `FastJVM/coga` is public, and
  hands-on-trial keeps findings out of the repo.

<!-- coga:blackboard -->

## Dev

pr: https://github.com/FastJVM/coga/pull/1188
branch: coga/competition-testing-make-hands-on-trial-cite-the-f50487


## Implementation

- Confirmed docs-only scope and the prepared feature checkout; the only entry
  dirt was this projected ticket. At entry, control had step 1 (`implement`)
  in progress. GitHub confirmed #1145 and #1153 merged and no PR for this branch.
- Read `coga/knowledge` (one owner per fact and attach-or-cite), both skills,
  and `clean-install/human-walk`. Use the latter's full GitHub link form.
- Replaced local VM setup and operator-habit guidance with the shared skill
  citation. Kept prerequisite coverage, ordered demands, earlier write-ups,
  and the same-VM/project lap rule as trial-specific guidance.
- Command relay remains a trial artifact. Its clipboard assumption and
  service-specific transfer route are replaced with a link to fresh-vm's
  `Moving commands and evidence`, which owns transfer with available tools.
- No packaged twin, runtime code, fixtures, or competitor findings changed.

## Verification

- `git diff --check` and `git diff --check origin/main...HEAD` passed.
- `git cat-file -e origin/main:coga/skills/coga/testing/fresh-vm/SKILL.md`
  passed; the cited file exists on fetched main.
- `rg -n '^### Moving commands and evidence$' coga/skills/coga/testing/fresh-vm/SKILL.md`
  found the section at line 81. A one-off Python link check also verified both
  destinations against fetched main, the section anchor, the matching
  `human-walk` link form, and the absence of packaged twins.
- Reviewed `git diff origin/main...HEAD -- coga/skills/competition-testing/hands-on-trial/SKILL.md`:
  only the setup and command-transfer passages changed; all other trial rules
  remain. No runtime or packaging tests were needed for this local prose edit.

## Peer review

- Passed with no must-fix findings and no source edits required. Reviewed the
  complete markdown diff against current main, the shared fresh-vm skill,
  human-walk's citation, and coga/knowledge's ownership rule.
- VM choice, preparation, baseline, reuse, cleanup, and command transfer now
  have one owner. Prerequisite coverage, ordered demands, earlier write-ups,
  the relay artifact, and same-VM/project laps remain trial-specific.
- Both new links resolve on fetched main, including the section anchor.
  Neither local skill has a packaged twin; no competitor findings changed.
- Recorded as self-review: Codex authored the implementation and runs this
  review session. The configured ticket agent does not establish authorship.
  Recommend skim; no independent review receipt exists.
- Pytest was not run: this is a pure prose edit with no code or fixture change.

## PR

```yaml
title: Cite shared fresh-VM guidance in hands-on trials
author: codex
author_evidence: The implementation handoff records Codex as author of 9dcdc6ef5db495cb75c899c7f5dbaf5087f19348,
  now rebased to the recorded head. This review session also runs Codex.
head: 20feaba3b8d4db8fd4fc927c5b223b5107ec5009
base: c00329d051a38dc4f320fc902d0d058703bc436a
depth: skim
rationale: Bounded prose change with verified links and preserved trial rules. Content review
  and link checks cover the change; skim because the review is self-review.
implementation: Hands-on-trial delegates VM choice, preparation, baseline, reuse, cleanup, and
  command transfer to fresh-vm. It removes the local VM procedure and clipboard/service assumptions
  while retaining prerequisite coverage, ordered demands, prior write-ups, the relay artifact,
  and the same-VM/project lap rule.
deviations: None.
limitations: 'No independent review receipt: Codex implemented and reviewed. No live VM trial
  was run; the diff changes citations and prose only.'
files:
  coga/skills/competition-testing/hands-on-trial/SKILL.md: Replace duplicated VM instructions
    with shared-skill citations while retaining the trial procedure.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 20feaba3b8d4db8fd4fc927c5b223b5107ec5009
  base: c00329d051a38dc4f320fc902d0d058703bc436a
  detail: Reviewed git diff origin/main...HEAD -- '*.md' ':!docs/archive/**' against fresh-vm,
    human-walk, and coga/knowledge. No must-fix findings; links, scope, trial rules, and absence
    of packaged twins verified.
checks:
- command: git diff --check origin/main...HEAD
  status: passed
  head: 20feaba3b8d4db8fd4fc927c5b223b5107ec5009
  base: c00329d051a38dc4f320fc902d0d058703bc436a
  detail: Passed; no whitespace errors.
- command: git cat-file -e origin/main:coga/skills/coga/testing/fresh-vm/SKILL.md
  status: passed
  head: 20feaba3b8d4db8fd4fc927c5b223b5107ec5009
  base: c00329d051a38dc4f320fc902d0d058703bc436a
  detail: Passed; the cited skill exists on fetched main.
- command: rg -n '^### Moving commands and evidence$' coga/skills/coga/testing/fresh-vm/SKILL.md
  status: passed
  head: 20feaba3b8d4db8fd4fc927c5b223b5107ec5009
  base: c00329d051a38dc4f320fc902d0d058703bc436a
  detail: Passed; the anchor heading is at line 81.
- command: git ls-tree -r --name-only HEAD -- src/coga/resources/templates/coga/bootstrap/skills/competition-testing
    src/coga/resources/templates/coga/bootstrap/skills/coga/testing/fresh-vm
  status: passed
  head: 20feaba3b8d4db8fd4fc927c5b223b5107ec5009
  base: c00329d051a38dc4f320fc902d0d058703bc436a
  detail: No entries; neither local skill has a packaged twin.
- command: |-
    python - <<'PY'
    from pathlib import Path
    import re, subprocess
    trial = Path('coga/skills/competition-testing/hands-on-trial/SKILL.md').read_text()
    walk = Path('coga/skills/coga/testing/clean-install/human-walk/SKILL.md').read_text()
    links = re.findall(r'\]\((https://github\.com/FastJVM/coga/blob/main/[^)]+)\)', trial)
    for link in links:
        rel, _, anchor = link.split('/blob/main/', 1)[1].partition('#')
        target = subprocess.check_output(['git', 'show', f'origin/main:{rel}'], text=True)
        if anchor:
            anchors = [re.sub(r'[^\w\- ]', '', heading.lower()).replace(' ', '-') for heading in re.findall(r'^#+ (.+)$', target, re.M)]
            assert anchor in anchors, link
        else:
            assert f'[coga/testing/fresh-vm]({link})' in walk
    print(f'{len(links)} GitHub links resolve on fetched main; section anchor and human-walk citation form verified.')
    PY
  status: passed
  head: 20feaba3b8d4db8fd4fc927c5b223b5107ec5009
  base: c00329d051a38dc4f320fc902d0d058703bc436a
  detail: Both GitHub links resolve on fetched main; the section anchor and human-walk citation
    form match.
- command: python -m pytest
  status: not-run
  detail: The docs peer-review workflow omits pytest for pure prose edits; no runtime code or
    fixtures changed.
```

## Handoff

- Reviewed and pushed branch head `20feaba3b8d4db8fd4fc927c5b223b5107ec5009` after rebasing
  the implementation commit `9dcdc6ef5db495cb75c899c7f5dbaf5087f19348` onto
  fetched main `c00329d051a38dc4f320fc902d0d058703bc436a`.
- Main's intervening changes were this ticket and the CLI log. Preserved and
  byte-verified the projected ticket; the feature diff is unchanged by rebase.
- No review-fix commit was needed. The branch diff contains only the skill;
  the projected ticket remains unstaged and is never committed to the branch.
- Ready for open-pr with current preparation and self-review/check receipts.
  No PR exists for this branch as of review; publication belongs to the next step.
- open-pr (2026-11-07): `coga open-pr` published PR #1188 at head
  `20feaba3b`; GitHub reports MERGEABLE / CLEAN, so no conflict resolution
  was needed. Ready for owner review.

---

## Blockers

- [x] [2026-11-02 21:51] [agent:claude] id=20261102T215124 Waiting on PR #1153 (fresh-vm) to merge, then the fresh-vm citation folded into PR #1145; cancel this ticket once #1145 merges with it
  resolved: [2026-11-07 14:15] [human:nicktoper] PR #1153 and #1145 both merged 2026-11-04; #1145 merged first without the fresh-vm citation, so this ticket proceeds as a follow-up PR from main.

- [x] [2026-11-03 14:38] [agent:claude] id=20261103T143857 Still waiting (checked 2026-11-03): PR #1153 (fresh-vm) and PR #1145 (hands-on-trial) are both OPEN and unmerged; neither skill is on main. Once #1153 merges, rebase #1145 and fold in the fresh-vm citation there, then cancel this ticket. Relaunch only if #1145 merges without the citation.
  resolved: [2026-11-07 14:15] [human:nicktoper] PR #1153 and #1145 both merged 2026-11-04; #1145 merged first without the fresh-vm citation, so this ticket proceeds as a follow-up PR from main.


---

## Blocker reminders

- 7891d747a9e1 last_reminded: 2026-11-03 10:44

- 07bc501bd134 last_reminded: 2026-11-05 08:55
