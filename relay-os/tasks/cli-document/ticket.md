---
title: cli-document
status: in_progress
mode: interactive
owner: zach
human: zach
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: docs/create-google-doc
  steps:
  - name: preflight
    skills: []
    assignee: agent
  - name: draft
    skills: []
    assignee: agent
  - name: revise
    skills: []
    assignee: agent
step: 2 (draft)
---

## Description

Create a short, one-page, well-structured document that walks a brand-new
Relay user through the handful of CLI commands they need to start getting
value right away — from setting up a repo to launching their first piece of
work. The audience is someone who has never used Relay, so the tone is
welcoming and concrete, with a copy-pasteable example for each command. The
deliverable is a Google Doc (via the `docs/create-google-doc` workflow);
Zach will finalize the wording manually after the draft.

## Context

This is a getting-started journey, not a full command reference — cover
only the commands below, in order, with a sentence or two and a
copy-pasteable example each. Behavior is verified against
`src/relay/commands/{setup,project,create,ticket,launch}.py`.

Prerequisite (step 0 in the doc): the reader must already have the `relay`
CLI installed, so the doc should open with a one-line install step —
`pip install relay-os` (README documents `pip install -U relay-os` as the
published update path) — before the flow below.

The intended flow, framed as three stages (set up → plan → launch):

1. **Set up the repo — `relay setup`.** Make an empty folder for your work
   (e.g. `~/Desktop/<name>`), `cd` into it, and run `relay setup`. There is
   **no git clone** — `relay` is a CLI you install once, and `relay setup`
   scaffolds the Relay OS into the current folder (it runs `relay init` for
   you if needed), records your name, then launches an interactive interview
   that asks what your repo is for and scans it, generating starter Relay OS
   artifacts — contexts, rules, workflows, and any recurring tasks — for you
   to review and sign off on. (Note: setup scaffolds your Relay OS; it does
   *not* hand you work tickets to start on — those come from stage 2 below.)
   Safe to re-run — it resumes where it left off.

2. **Plan a project — `relay project`.** If you have a project in mind, run
   `relay project`. An agent interviews you about what the project is trying
   to accomplish and scaffolds an ordered set of draft tickets from your
   answers.

3. **Or capture a standalone task — `relay create "<task title>"`.** If you
   just have individual tasks rather than a whole project, this scaffolds a
   single draft ticket to track one. (No interview — quick scaffolding.)

4. **Flesh out a ticket — `relay ticket "<task title>"`.** Walks you through
   adding a description, context, and workflow to a draft via a guided agent
   interview, so the ticket is ready to launch.

5. **Start the work — `relay launch "<task title>"`.** Composes the ticket's
   context and starts an agent working the task. Launching auto-activates a
   draft, so this is the single command that takes a ready ticket to work
   actually happening.

Framing note: this was described as the "3 most important commands" but is
five commands; the natural shape is three stages — **set up → plan (project
or task) → launch** — with `relay project` / `relay create` as the two
branches of stage two.
