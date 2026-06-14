---
title: relay-onboarding
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

Create a short, welcoming onboarding doc — **"Relay Onboarding"** — that takes a
brand-new user from nothing to their first launched piece of work in as few
steps as possible. The audience has never used Relay, so the tone is concrete
and every step has a copy-pasteable command. The deliverable is a Google Doc
(via the `docs/create-google-doc` workflow). It supersedes the earlier "Getting
Started with Relay — Your First Five Commands" doc, which had too many steps and
documented commands that no longer exist (`relay project`, and `relay setup` run
twice).

## Context

This is an intro/onboarding journey, **not** a command reference — every extra
step loses users, so keep it to the minimal happy path and leave power-user
commands out entirely. Behavior is verified against
`src/relay/commands/{setup,launch}.py`.

The whole flow is three steps:

1. **Install the CLI.** Install once from source — cloning alone isn't enough;
   the `pip install -e .` is what puts the `relay` command on your PATH:

   ```
   git clone https://github.com/FastJVM/relay && cd relay && pip install -e .
   ```

   Keep it to exactly this — no PyPI / `pip install relay-os` mention.

2. **Set up your repo — `relay setup`.** In a *separate* folder for your work
   (not the relay clone), run `relay setup`. In one run it creates your Relay OS
   in that folder, interviews you about what the repo is for (generating starter
   contexts/rules/workflows for you to sign off on), then offers to plan your
   first project into an ordered set of draft tickets. One command, one run;
   safe to re-run (it resumes where it left off).

3. **Start the work — `relay launch "<ticket>"`.** Composes the ticket's context
   and starts an agent working it. Launching auto-activates a draft, so this one
   command takes a ready ticket to work actually happening.

Out of scope — do not include, they add steps a new user doesn't need: there is
no `relay project` command (planning lives inside `relay setup`), and
`relay create` / `relay ticket` are power-user commands. The Google Doc's title
is "Relay Onboarding".
