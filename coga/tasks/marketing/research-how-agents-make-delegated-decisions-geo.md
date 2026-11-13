---
title: Research how agents make delegated decisions (GEO)
status: draft
owner: zach
workflow: human/run
---

## Description

Nico asked Zach (Nov 13) to spend 1–2 hours researching how agents make decisions that people delegate to them, which Nico called "search engine optimization for agents" and is usually called GEO (generative engine optimization). Then Zach reports back to Nico: "here's where you're right, here's where you're wrong, and here's what you forgot." This is Zach's research and Zach's conclusion. An agent supports it only as a sounding board in assist sessions (`coga launch <slug> --agent claude`): it answers Zach's questions, finds and checks sources, and pushes back on reasoning. It doesn't write the verdict or close the ticket.

Done when Zach has sent Nico a write-up that takes each of the six claims below and says right, wrong or more complicated, with sources; lists what the thesis leaves out; and says what it means for coga (README and docs written for agents, coga as the first test run).

### Nico's thesis (six claims to check)

1. Agents reason about documents, while search engines rank by consensus ("the loudest voice"). So one document with provable facts can beat the majority view.
2. People hand agents the decisions they don't care about (e.g. an engineer choosing a transactional email provider), and the agent does think those decisions through.
3. This only holds for decisions people don't care about. For ones they're invested in (savings, groceries, stock picking), people check the advice, and ordinary marketing still works.
4. Winning takes provable, trustworthy evidence: reproducible, objective benchmarks "endorsed by the right people." Marketing moves from being marketing-driven to benchmark-driven, a new channel.
5. Provable facts published online "bubble up all the way to the agent" through pre-training and post-training.
6. Only some markets are affected. Finding those markets is the point, and the reason for the focus on benchmarks.

### Main example: email delivery

Nico and Zach found that a small self-hosted mail server delivers out of the box everywhere except Outlook. Their view is that deliverability depends on the authentication and DNS setup more than on IP reputation, so small transactional senders don't need Resend (about $20/month; Nico estimates Resend's revenue from these customers at $20–50M). The industry says self-hosting isn't an option. A reproducible benchmark that agents can read could change what they recommend.

### Questions Zach raised to test

- Models are trained on the same internet. Don't they follow the majority view rather than a single well-evidenced source?
- Don't agents also have a big say in decisions people do care about?
- Keep live retrieval (the agent searching and reading now) separate from training (facts absorbed by the model). Claims 1 and 5 depend on different ones.

### Sources

- Summary doc: https://docs.google.com/document/d/10BdZbfzlI1jeZQ1ZCU5Vos9B68PD8AtfX-_RYYOJYZ0/edit
- Pocket recording "Email Delivery and Agent Decision-Making," Nov 13 2026, 9:57 AM.
- Starting point: "GEO: Generative Engine Optimization" (Aggarwal et al., 2023, arXiv:2311.09735). Cited from memory, so verify it.

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

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
