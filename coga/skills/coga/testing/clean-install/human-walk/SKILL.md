---
name: human-walk
description: Run an attended first-time install of Coga by a non-engineer on a fresh `cogatest` VM while an agent session on their normal account records findings. Covers walk rules, the record, what a walk can and cannot measure, and the fix-and-re-walk loop.
---

# Attended human install walk

The human counterpart of the automated harnesses
([Linux](https://github.com/FastJVM/coga/blob/main/coga/skills/coga/testing/clean-install/SKILL.md),
[macOS on AWS](https://github.com/FastJVM/coga/blob/main/coga/skills/coga/testing/clean-install/macos-aws/SKILL.md),
[Windows on AWS](https://github.com/FastJVM/coga/blob/main/coga/skills/coga/testing/clean-install/windows-aws/SKILL.md)).
Those prove the commands run. This walk shows what a first-time user hits:
waits with no feedback, confusing text, surprise popups or warnings, steps
they had to guess, and whether each step works. It rents no machines.

## Roles

- **The human** walks the install inside a fresh VM, following only the
  public README. They are usually not an engineer; that is the point.
- **The agent** runs on the human's normal account, in their Coga checkout,
  outside the VM. It never runs the install. It records what the human
  reports, answers when they are stuck, and fixes what fits the ticket.

Give the human the [operator guide](operator-guide.md) beside this skill. It
is written for them, in plain language, and the agent need not restate it.

## Before the walk

1. Prepare or reuse the VM per
   [coga/testing/fresh-vm](https://github.com/FastJVM/coga/blob/main/coga/skills/coga/testing/fresh-vm/SKILL.md),
   including the confirmed revert to bare and the baseline the human pastes
   in. Record the baseline under the walk's section of the record.
2. Write down which install source the walk uses: PyPI (`uv tool install
   coga`, what a real user gets) or `main` (see the fix loop). Record the
   resolved Coga version once it is installed.
3. Note what is already known to fail on this platform, from the ticket, so
   the human can stop there instead of fighting it.

## Walk rules

- **Docs only.** The human follows only what the README says. The agent helps
  only when they are stuck, and a hint they needed is itself a finding.
- **The first walk is the only cold one.** Once the human knows the answers the
  confusion this walk exists to catch is gone. If both a VM and a new user
  account will be used, walk the VM first.
- **The human does not fix things with tricks they know.** They paste the full
  error and one line of what they were doing.
- **Per step, record** the command typed or clicked, what they saw, what they
  expected, anything weird or slow, and whether they needed help. The operator
  guide carries the template.

## The record

Keep findings on the ticket's blackboard, under one section per walk (cold
walk, reproduction, verification). When dated walk evidence outgrows the
blackboard, move it verbatim to an attachment beside the ticket and leave a
numbered status list on the blackboard that points to it.

Each finding gets a number, a severity with its reason, the evidence (pasted
output, not paraphrase), the surface that owns the fix, and a status:
`fixed-in-PR`, `tracked-elsewhere` (name the ticket), or `open`. A finding
the walk confirmed says so; one read from the docs before walking is a
prediction until the walk reaches it.

`FastJVM/coga` is public: no account IDs, emails, keys, or personal host
details in the record.

## What a walk does not measure

- **Not timing.** The walk is conversational, with pauses to report and take
  breaks, so wall-clock times look like data without being data. Record a wait
  only as "nothing on screen for a long time" with what was running; take
  timing from the automated harnesses.
- **Not VM artifacts.** Typos in retyped out-of-band commands, host slowness,
  and missing clipboard are properties of the setup
  ([coga/testing/fresh-vm](https://github.com/FastJVM/coga/blob/main/coga/skills/coga/testing/fresh-vm/SKILL.md)
  lists them).
- **Not the leaked tools.** On a new user account, `git` and the Python floor
  are machine-wide; mark those steps "not a real test".

## Fix and re-walk

Finding, then PR, then merge, then re-walk the affected step on a fresh copy
(a new clone of the sealed macOS spare, the restored Windows snapshot, or a
new user account when the step does not depend on leaked tools).

`uv tool install coga` installs from PyPI, so a merged fix is not there until
a release. A re-walk of a merged fix installs from `main`:

```sh
uv tool install git+https://github.com/FastJVM/coga@main
```

and the finding records that it was checked against `main`, not a release.
Doc-only fixes need no reinstall. Name a re-walk on an untouched copy before
any fix lands a **reproduction**, and one after a fix a **verification**; only
the second can mark a finding fixed.

## Wrap-up

When the human says the walk is done, collect their notes and ask the guide's
three questions: the most annoying moment, where they would have given up,
and roughly how long it took overall (an impression, not timing evidence).
Then list every finding with its status and hand the open ones to the tickets
that own their surfaces.
