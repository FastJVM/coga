---
name: meta/dream
description: Scan the Relay repo for knowledge gaps, broken references, stale locks, and workflow patterns. Propose concrete fixes on the blackboard and summarize in Slack.
---

# Dream

Your job is to read the entire Relay repo and surface what's missing or drifting.
Write concrete proposals, not vague recommendations.

## Step 1 — Run the deterministic checker

Run:

```
python -m relay.validate --json > /tmp/relay-validate.json
```

Parse the JSON. Each issue has `kind`, `task`, `message`, and `severity`. Kinds:

- `missing-file` — a task is missing ticket.md/blackboard.md/log.md.
- `stale-lock` — a lock file is older than the configured threshold (likely a crashed agent).
- `invalid-status` — a ticket's status value isn't one of the allowed ones.
- `unknown-assignee` — assignee is not a known human or agent nickname.
- `broken-context` / `broken-skill` — a reference points to a file that doesn't exist.
- `stuck-active` — task is `active` but `log.md` hasn't been written to in a while.

For each error-severity issue: write a **Proposal** entry to the Findings section
of your own blackboard with a concrete remediation step (e.g. "delete stale lock
at path X", "reassign task Y to Pierre because claude2 is no longer used", etc.).

## Step 2 — Scan for knowledge gaps (this is the harder part)

Read every ticket (its body and blackboard). Compare against existing contexts,
skills, and workflows. Look for:

- **Context gaps** — patterns that repeat across multiple tickets but aren't
  captured in any context. Example: three different tickets mention "429 retry
  with Retry-After" and there's no `email/retry-patterns` context. Propose the
  missing context with a one-paragraph scope.
- **Skill gaps** — workflow steps with no `skill:` reference where blackboards
  show agents repeatedly asking the same questions. Propose a skill file with
  the boilerplate answers.
- **Workflow gaps** — groups of tickets that follow the same ad-hoc sequence
  without a named workflow. Propose the workflow name, steps, and which steps
  deserve skill refs.
- **Stale content** — a context or skill that contradicts what's in recent
  blackboards. Propose the specific edit (show old vs. new).

## Step 3 — Write proposals to the blackboard

Every proposal goes in the **Findings** section of *your* task's blackboard,
with this shape:

```
### Proposal: <short title>

**Kind:** context | skill | workflow | fix | staleness
**Target:** <file path or task id>

<one paragraph describing the proposed change>

<if it's a new file, include a draft of the content>
```

No proposal is too small. A human reviews and accepts or rejects — don't
pre-filter.

## Step 4 — Summarize for Slack

Call `relay feed --task <your-task-id> --message "<summary>"`. One line.
Example: `Dream scan: 3 broken refs, 2 context proposals, 1 stale lock.`

## Step 5 — Don't take action

Your role is to propose, not to edit files directly (outside of your own
blackboard). The human decides what to accept.
