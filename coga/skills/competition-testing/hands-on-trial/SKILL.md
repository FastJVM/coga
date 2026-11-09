---
name: competition-testing/hands-on-trial
description: Run a hands-on trial of a competing agent-workflow tool with a human in a fresh VM. Covers the shared trial task, laps that test learning claims, a bare-model control, the entry-log and command-relay artifacts, and the Drive write-up. Findings never enter this public repo.
---

# Hands-on competitor trial

A human installs a competing tool and runs a real task through it. The agent
keeps notes, discusses what the human sees, and prepares the write-up inputs.
The ticket names the tool, the claims to test, and the owner. This skill
covers how the trial runs.

## Boundaries

- **The human runs the tool; the agent does not.** Findings come from the
  human's screenshots and notes. A plausible paragraph the human did not
  observe is a failure. Do not draft findings for a lap that has not run.
- **Nothing about the competitor enters this repo.** `FastJVM/coga` is
  public. Do not commit trial output, competitor notes, or the scratch
  project. Findings stay in the owner's Drive docs. The ticket blackboard
  holds only pointers: doc links, lap state, decisions about how the trial
  runs, and whether the share happened.
- Follow the human's lead on what to look at next. This is information
  gathering, not a staged project. Decide what to compare across tools once
  the write-ups exist. Do not start a cross-tool matrix mid-trial.

## Setup

- **Fresh VM.** Follow
  [coga/testing/fresh-vm](https://github.com/FastJVM/coga/blob/main/coga/skills/coga/testing/fresh-vm/SKILL.md)
  for VM choice, preparation, baseline capture, reuse, and cleanup.
- **Install coverage.** Start at the machine's prerequisites (the agent CLI
  itself and anything else the bare machine demands), not at the tool's own
  install command. Record each demand in order.
- **Read the earlier trials' write-ups before install.** Their prerequisite
  chains and standing results are the baseline.
- **Shared trial task.** Every trial builds the same small product, so a bad
  plan is obvious to a human who knows the correct design. Keep the product
  name the earlier trials used, in a per-tool project directory.
- **Same first prompt.** Hand the tool the same description an earlier tool
  got, verbatim, including its known gaps and typos. Do not repair it and do
  not pre-answer the tool's questions. "Did it find the real gaps" is only a
  fair head-to-head from the same starting line.

## Laps

When the tool claims that captured learnings make later work better, a single
build exercises only the write half of that claim. Run one full pass of the
tool's loop per feature of the trial task, in the same VM and the same
project directory, so stored learnings survive and later laps can read them
back. Start each lap in a fresh agent session: a later lap run in the earlier
lap's conversation recalls everything from that history, so it would look the
same with no stored learnings at all. Tools rarely say to restart, so tell the
human before each lap. Watch whether stored learnings visibly change later planning output,
and whether what was captured was worth capturing. Record where the tool
stores learnings, its default location, and whether that setting can be
discovered. Plan at least one lap where a stored learning and the existing
code disagree, because that lap settles attribution. A trial that stops
early should say which claim is left without evidence.

Run any hands-off or unattended mode last, on a new feature in the same
codebase, so it is judged against the hand-driven laps. Keep the scratch
project without a Git remote so an unattended mode stays local and cannot
push or open PRs.

## Controls

Every tool in this space is prompt files over the same model. When the tool
asks a sharp question or catches a gap, give the same input to the bare model
with no plugin before crediting the tool. What a tool controls is whether it
asks, when, in what format, and with what posture. Record an observation as
unattributed until the control has run.

## Artifacts

Keep two published artifacts. The entry log is for the human to read back
before recording conclusions. The command relay is for pasting.

- **Running entry log.** Numbered entries in the order things happened, each
  tagged worked, friction, question closed, or reads-against-Coga. It is not
  the deliverable and not a draft of it.
- **Command relay.** Put every command or prompt the human should run in the
  relay, never only in chat. Follow the shared VM skill's
  [command and evidence guidance](https://github.com/FastJVM/coga/blob/main/coga/skills/coga/testing/fresh-vm/SKILL.md#moving-commands-and-evidence)
  to make the artifacts available in the guest.

Record both artifact URLs on the blackboard. Republish from the same source
path to keep each URL.

## Write-up and close

The human records their conclusions after the trial, for example as a voice
recording. A later session summarizes that recording into a separate Drive doc
in the competitors folder, matching the register of the earlier write-ups.
The recording carries the human's conclusions. The session notes carry how
the trial got there. If the available Drive tools cannot edit an existing Doc,
draft Markdown for the human to paste, and never replace a doc that holds the
screenshots.

Installer findings that also apply to Coga's own install route to the ticket
that owns Coga's install commands, not into the write-up alone.

At close, record on the blackboard which laps ran, which were stopped and
what that leaves unanswered, the deliverable link, and the share. Share by
named account rather than link-sharing, and check the doc's permissions
before saying the share happened.
