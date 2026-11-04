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

Read the [operator guide](operator-guide.md) and give it to the human. It
owns the participant's walk rules, report template, and wrap-up questions;
this skill owns the helper's record and fix loop.

## Before the walk

1. Prepare or reuse the VM per
   [coga/testing/fresh-vm](https://github.com/FastJVM/coga/blob/main/coga/skills/coga/testing/fresh-vm/SKILL.md),
   including the confirmed return to bare when reusing a VM. Record the
   baseline under the walk's section of the record.
2. Follow the ticket's install source and completion criteria. For a normal
   first-user walk, use PyPI (`uv tool install coga`); for a merged fix, see
   the fix loop. A release-check ticket may instead require a candidate wheel
   and a completed first task. Record the installed version and, for a source
   or wheel install, the resolved commit and wheel hash when applicable.
3. Note what is already known to fail on this platform, from the ticket, so
   the human can stop there instead of fighting it.

## The record

Keep findings on the ticket's blackboard, under one section per walk (cold
walk, reproduction, verification). When dated walk evidence outgrows the
blackboard, move it verbatim to an attachment beside the ticket and leave a
numbered status list on the blackboard that points to it.

Each finding gets a number, a severity with its reason, the evidence (exact
output or screenshots), the surface that owns the fix, and a status:
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
- **Not a fresh-machine prerequisite test on a new account.** Apply the
  machine-wide tool exclusions in the shared VM skill.

## Fix and re-walk

Finding, then PR, then merge, then re-walk the affected step on a fresh copy
(a new clone of the sealed macOS spare, the restored Windows snapshot, or a
new user account when the step does not depend on leaked tools).

`uv tool install coga` installs from PyPI, so verify that the tested release
contains the fix. For a merged fix not yet released, use `main` unless the
ticket specifies another candidate:

```sh
uv tool install git+https://github.com/FastJVM/coga@main
```

The finding records the resolved commit and that it was checked against
`main`, not a release; a package version alone cannot distinguish main commits.
Doc-only fixes need no reinstall. Name a re-walk on an untouched copy before
any fix lands a **reproduction**, and one after a fix a **verification**; only
the second can mark a finding fixed.

## Wrap-up

When the human reaches the ticket's completion criteria or stops the walk,
collect their notes and the guide's wrap-up answers. List every finding with
its status, record any untested steps, and hand the open findings to the
tickets that own their surfaces. A stopped walk does not satisfy an incomplete
release check.
