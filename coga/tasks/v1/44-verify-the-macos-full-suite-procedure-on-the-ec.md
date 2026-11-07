---
title: 44-Make Zach's Mac the macOS test machine and retire the EC2 Mac harness
status: draft
owner: zach
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills:
    - code/peer-review
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
step: 1 (implement)
---

## Description

Make Zach's Mac (to be recycled as the team's dedicated macOS test machine) the place where Coga's macOS full suite runs, and retire the EC2 Mac harness. EC2 Mac dedicated hosts bill a 24-hour minimum and need owner approval for each run. The owner decided on 2026-11-07 to drop them in favor of the owned test Mac.

Three parts, in one PR:

1. **Run and receipt.** On Zach's Mac, run the full suite at the full SHA of `origin/main` HEAD at run start. Use a fresh clone, uv, Python 3.11 (`uv sync --python 3.11 --extra test`), ripgrep, and a `nohup` pytest run that is polled rather than held open. Record a receipt with: full SHA, Mac model or chip, macOS version (`sw_vers`), Python version, the exact command, pass/skip/fail counts, and runtime. Record failures with test names and first errors; do not fix them here.
2. **Testing rules.** In `coga-dev/testing`, write the native macOS full-suite procedure that part 1 used, correcting it from what actually ran. Name the team's macOS test machine in place of the EC2 Mac host in: the macOS support threshold, the tier-2 platform-sensitive requirement, the tier-3 release requirement, and the harness overview. Keep "macOS is supported once its full suite passes on the macOS test machine" as an owner threshold. Do not declare macOS supported in this PR, even if the run is green; that is the owner's call on reading the receipt.
3. **Retire the EC2 Mac harness.** Delete `scripts/clean-install/aws-mac.sh`, `scripts/clean-install/macos-walk.sh`, and both copies of the macos-aws skill. Remove their entries from `tests/legacy_removal_inventory.txt` and `tests/test_packaging.py`, and their cases from `tests/test_clean_install_harness.py`. Update every live reference (listed in Context) so no link or instruction points at the removed files.

Done means the PR is merged with the receipt on the blackboard and in the PR. `rg -n 'macos-aws|aws-mac|macos-walk'` outside `docs/archive/`, `coga/tasks/` and `coga/log.md` finds nothing, the full Linux suite passes (including `tests/test_packaging.py` after both skill copies are deleted), and `coga validate` is clean.

## Context

### Owner decisions (2026-11-07)

- A native Windows receipt is **not** required for this PR. It deletes harness scripts, an EC2-only skill and their tests, and edits docs. No shipped runtime code or OS-dependent path changes. The Linux full suite is the gate. If review reads tier 2 differently, ask the owner rather than blocking.
- Zach's Mac is the native macOS run venue and becomes the team's dedicated macOS test machine. The EC2 Mac harness is retired outright, with no EC2 verification or follow-up.
- Losing the EC2 harness also loses the automated macOS **clean-install walk** (fresh machine → `pip install` → `coga init`). A reused Mac is not fresh. `v1/28-affordable-macos-testing-on-owned-macs-and-per-min` (blocked) owns fresh-install testing on owned Macs (disposable macOS VMs) and the comparison with per-minute hosted CI. Where the clean-install skill described the macOS walk, point to v1/28's scope as the open gap rather than inventing a replacement. v1/28's PR #976 (branch `owned-mac-clean-install`) is closed and built on `aws-mac.sh`/`macos-walk.sh`. Deleting both is accepted; v1/28 can recover the walk from git history. In the PR description, name the last commit that has them.
- The slug still says "ec" from the original EC2 scope. It is kept for references.

### Before deleting anything: AWS cleanup

An allocated EC2 Mac dedicated host keeps billing until it is released. `aws-mac.sh` keeps its state in the gitignored, machine-local `.coga/clean-install/<name>/resources.env`, which exists only on the checkout that ran it. A fresh clone on Zach's Mac has none.

Already checked during ticket authoring (2026-11-07), on the owner's Linux checkout: the only Mac run, `installer-mac-20261001`, used host `h-0833c01ac15e645ac`. It records `HOST_RELEASED=2026-10-02T01:20:21Z`. The remaining check is `aws ec2 describe-hosts --region us-east-1`, run by whoever holds the AWS credentials. Record its result on the blackboard. If any Mac host is still allocated, ask the owner before releasing it.

### Running on Zach's Mac

- **Launch the implement step on Zach's Mac** (`coga launch` from his checkout). The peer-review and open-pr steps can run anywhere.
- The starting procedure is the "Full suite at a commit" section of `src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/macos-aws/SKILL.md` (unverified). Run its step 2–3 command bodies locally, without the `aws-mac.sh ssh` wrapper. Record every substitution (for example, uv not at `~/.local/bin/uv`) and which prerequisites were already installed. Those notes become the corrected procedure in `coga-dev/testing`.
- **Never run `macos-walk.sh reset`** or any other step that removes the Command Line Tools on Zach's Mac.
- Use a fresh clone (for example `~/coga-work`), not Zach's working checkout.
- Right after the `nohup` start, write the start time, PID and SHA to the blackboard, so a resumed session can pick the run up. Confirm that no `pytest` process remains at the end. The run time on macOS is unknown; the Windows native run takes about 2 hours.
- The receipt SHA is `origin/main` HEAD at run start. The PR's own docs, script and test removals do not need a macOS re-run.

### Facts from coga-dev/testing (cited, not attached; this PR edits it)

`docs/contexts/coga-dev/testing/SKILL.md`, section "Verification tiers and receipts". Today:

- Tier 2 says "Once macOS is supported, also run it on macOS through the macOS AWS harness".
- Tier 3 says "on macOS (EC2 Mac host) once macOS is supported".
- The threshold says "macOS is supported once its full suite passes on the EC2 Mac host (owner's threshold). Until then, macOS receipts are not required, and a macOS run is informational."
- An earlier section (near the top) introduces the macOS AWS harness.
- The POSIX migration-runbook test needs `rg` on PATH. `TERM=dumb` keeps Typer output free of ANSI codes.

### Files to change

Package owners and their legacy live copies change together. AGENTS.md and `tests/test_packaging.py` require them to match, and require the inventory to list only existing pairs.

- Delete: `src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/macos-aws/SKILL.md` and `coga/skills/coga/testing/clean-install/macos-aws/SKILL.md`, plus `scripts/clean-install/aws-mac.sh` and `scripts/clean-install/macos-walk.sh`.
- Test bookkeeping. These are the only tests that pin these paths:
  - `tests/legacy_removal_inventory.txt`: delete the macos-aws line.
  - `tests/test_packaging.py`: delete the macos-aws path from `EXPECTED_BOOTSTRAP_RESOURCES`.
  - `tests/test_clean_install_harness.py`: delete the `aws_mac` fixture and every test that uses it or `macos-walk.sh` (including `test_macos_walk_provisions_and_pins_python_311`). Keep the shared install, release and Windows cases.
- Update references in:
  - the clean-install parent skill (`.../testing/clean-install/SKILL.md`, both copies);
  - `.../testing/clean-install/windows-aws/SKILL.md` (both copies);
  - `.../skills/coga/releasing/SKILL.md` (both copies; tier-3 macOS step). It ships to adopters, so say "the macOS test machine", never "Zach's Mac", and link to a named anchor in the new `coga-dev/testing` procedure section;
  - `coga/skills/coga/testing/clean-install/human-walk/SKILL.md` (it has no package owner, so only this copy changes);
  - `docs/README.md`;
  - `docs/contexts/coga-dev/testing/SKILL.md`.
- Leave historical mentions alone: `coga/tasks/**`, `coga/log.md`, `docs/archive/**`, and "PR #1046 (macOS harness)" in `docs/contexts/coga-dev/current-direction/SKILL.md`. `coga-dev/codebase` has no clean-install entry, so nothing to change there.

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

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
