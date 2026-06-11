---
title: init-questions
status: draft
mode: interactive
owner: zach
human: zach
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
---

## Description

Below is a 2 phase process meant to derive reusable knowledge. This knowledge becomes durable artifacts (contexts, rules, workflows, recurring, possibly skills) that Relay attaches to future tickets — so every agent starts already knowing the project instead of starting from zero.

Init Interview
(Runs only on the first `relay init` of a repository. It never triggers again — after that, `relay init --update` brings in changes.)

1. What is this repo for — what project or operation does it coordinate, and what does success look like? (Repo/relay-os/contexts)

2. What knowledge does this work depend on that an outsider couldn't get from reading the repo? 
(Repo/relay-os/contexts)

3. What rules should every agent always follow here? (e.g. "never push to main") (rules.md)

4. What work comes up repeatedly — and is any of it on a schedule? (Repo/relay-os/workflows...Repo/relay-os/recurring)

Once they answer all 4 questions, a setup ticket is auto-scaffolded for them, ready for `relay launch`.

Setup Ticket
1. Interview answers are added into the ticket (so the agent knows them)

2. Agent reads the user's repo

3. Agent creates workflows, contexts, recurring, (possibly skills) from the repo/ answers

4. Agent shows you the files it generated and you can sign-off, edit, etc.

Empty repo: the phase 1 questions are still asked, but since there's nothing to scan, artifacts are created from the answers alone. They are still shown to the human for review before landing.

Phase 2 is Relay building Relay. It uses the answers that the user gave in phase 1 + the information gained from scanning the repo (if there is one) to create durable artifacts (contexts, workflows, recurring, rules, possibly skills). These artifacts can then be called on and possibly attached when the user creates follow-up tickets. 

## Context

We found we were missing an easy opportunity for a new user to build reusable artifacts from installation — without it, relay-os starts empty and every future agent starts from zero. This fills that gap.
