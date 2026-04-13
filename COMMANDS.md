# Relay CLI — Complete Command Reference

## Setup (one-time)

```bash
# Navigate to the Relay repo
cd ~/Desktop/ticketing-system

# Put relay on your PATH for this terminal session
export PATH="$PWD/cli:$PATH"

# Copy the local config template (if you haven't already)
cp relay.local.toml.example relay.local.toml
```

---

## relay create

Scaffold a new task directory with ticket.md, blackboard.md, and log.md.

**Required flags:**
```bash
relay create --project demo --title "My task title"
```

**All flags:**
```bash
relay create \
  --project demo \
  --title "My task title" \
  --workflow code/with-review \
  --assignee claude1 \
  --owner zach \
  --mode interactive \
  --context email/payment-flow \
  --context admin/bookkeeping
```

| Flag | What it does | Required? | Default |
|---|---|---|---|
| `--project` | Which project to create the task in | Yes | — |
| `--title` | Human-readable name | Yes | — |
| `--workflow` | Step sequence (frozen into the ticket) | No | No workflow (simple status task) |
| `--assignee` | Who does the work (agent nickname or human) | No | None |
| `--owner` | Who's accountable | No | Your user from relay.local.toml |
| `--mode` | `interactive`, `auto`, or `script` | No | `interactive` |
| `--context` | Attach a context block (repeatable) | No | None |

**Examples:**

```bash
# Simplest — just a title, no workflow, no context
relay create --project demo --title "Look into staging latency"

# Code task with workflow and context
relay create --project demo --title "Fix retry logic" --workflow code/with-review --assignee claude1 --context email/payment-flow

# Multiple contexts
relay create --project demo --title "Monthly books cleanup" --context admin/bookkeeping --context admin/tax-automation

# Auto mode — agent runs alone without human present
relay create --project demo --title "Weekly R&D scrape" --mode auto --assignee claude1

# Script mode — no agent, just runs a script
relay create --project admin --title "Run Xero reconciliation" --mode script --workflow admin/script

# Different workflow
relay create --project demo --title "LinkedIn post" --workflow content/post --assignee claude1
```

---

## relay status

Show all tasks across all projects, one line per task.

```bash
# Active tasks only (design, ready, active, paused)
relay status

# Include done, canceled, and failed tasks too
relay status --all
```

---

## relay launch

Compose the prompt from all context sources and start work on a task.
Task must be `active` before launching (unless using `--dry-run`).

```bash
# Dry-run — compose and preview without spawning anything
relay launch --task 006 --dry-run

# Real launch — spawns the agent or runs the script
relay launch --task 006
```

**What launch does behind the scenes:**

1. Reads the ticket's assignee → resolves to an agent type
2. Composes the prompt: protocol + mode block + rules + project context + ticket contexts + inline context + current step skill + blackboard
3. Writes the composed prompt to a temp file
4. Spawns the agent with the right CLI flags (or runs the script for script mode)
5. Logs the launch to log.md
6. Posts to Slack

**Before launching, the task must be active.** Edit ticket.md and change
`status: ready` to `status: active`, then save.

---

## relay step

Advance the task to the next workflow step. On the last step, marks
the task `done` automatically.

```bash
relay step --task 006
```

**Rules:**
- Task must be `active` (not ready, paused, or done)
- Task must have a workflow with steps
- Steps advance in order: 1 → 2 → 3 → 4 → done
- Each step transition is logged to log.md and posted to Slack

**In a real workflow, the agent calls this — not you.** You only call
it manually during testing or when acting on the agent's behalf.

---

## relay panic

Record a blocker and escalate to the task owner. Writes to the
blackboard's Blockers section and @mentions the owner in Slack.

```bash
relay panic --task 006 --reason "429 retry logic unclear, need decision on backoff ceiling"
```

**Both flags are required.** The reason should be specific and
actionable — the owner reads it to decide what to do.

**What panic does:**
1. Writes the reason under ## Blockers in blackboard.md
2. Logs the panic to log.md
3. Posts to Slack with @mention to the task owner

---

## relay feed

Post an FYI message to the shared Slack channel. No @mention — just
a line in the feed.

```bash
relay feed --task 006 --message "opened PR #142"
```

**Both flags are required.** Keep messages short — milestones, not
commentary.

---

## Manual operations (no CLI command — edit files directly)

### Change task status

Open ticket.md and edit the `status:` field. Valid values:

| Status | Meaning |
|---|---|
| `design` | Not ready — needs scoping or research |
| `ready` | In the pool — work can start |
| `active` | Someone is working on it |
| `paused` | Suspended — pick up later |
| `done` | Completed |
| `canceled` | Deliberately abandoned |
| `failed` | Work was attempted and did not succeed |

```bash
# Open a ticket to edit its status
open -e projects/demo/.relay/tasks/006-my-task/ticket.md
```

Change `status: ready` to `status: active` (or whatever transition
you need), save, close.

### Reassign a task

Open ticket.md and change the `assignee:` field.

```
assignee: claude1    →    assignee: claude2
assignee: claude1    →    assignee: zach
```

### Add or remove contexts from a task

Open ticket.md and edit the `contexts:` list.

```yaml
# Before
contexts:
  - email/payment-flow

# After — added a second context
contexts:
  - email/payment-flow
  - admin/bookkeeping
```

### Edit the blackboard

Open blackboard.md and write under the appropriate section heading:

```bash
open -e projects/demo/.relay/tasks/006-my-task/blackboard.md
```

- `## Plan` — current working plan
- `## Notes` — free space
- `## Findings` — discovered facts and results
- `## Blockers` — what's stalling progress
- `## Decisions` — rationale for choices made

### Read the audit trail

```bash
cat projects/demo/.relay/tasks/006-my-task/log.md
```

### Remove a task

Delete its directory:

```bash
# Remove a specific task
rm -rf projects/demo/.relay/tasks/006-my-task

# Remove ALL tasks in a project (careful!)
rm -rf projects/demo/.relay/tasks/*
```

### Remove a project's tasks but keep the project

```bash
rm -rf projects/demo/.relay/tasks/*
```

The project itself (config in relay.toml, path in relay.local.toml,
context.md in .relay/) stays intact.

---

## Available workflows

These are the step sequences you can attach with `--workflow`:

| Workflow | Steps | Use for |
|---|---|---|
| `code/with-review` | implement → pr → approve → merge | Code changes that need review |
| `code/autonomous` | implement → merge | Low-stakes code changes |
| `content/post` | draft → approve → publish | External content (LinkedIn, newsletters) |
| `admin/script` | run | Script-mode automations |

### To see what steps a workflow has:

```bash
cat workflows/code/with-review.md
cat workflows/content/post.md
cat workflows/code/autonomous.md
cat workflows/admin/script.md
```

---

## Available contexts

These are the domain knowledge blocks you can attach with `--context`:

| Context | What it covers |
|---|---|
| `email/payment-flow` | Stripe webhooks, retries, idempotency, rate limits |
| `admin/bookkeeping` | Brex unmapped transactions, Xero reconciliation, monthly scrapers |
| `admin/tax-automation` | IRC §41 R&D credit, Gusto tax forms |

### To see what a context contains:

```bash
cat contexts/email/payment-flow/SKILL.md
cat contexts/admin/bookkeeping/SKILL.md
cat contexts/admin/tax-automation/SKILL.md
```

Or browse them in Obsidian — they're all visible in the sidebar.

### To create a new context:

Create a folder under `contexts/` with a `SKILL.md` file inside:

```bash
mkdir -p contexts/infra/dns
```

Then create `contexts/infra/dns/SKILL.md` with this format:

```markdown
---
name: infra/dns
description: One-line description of when to attach this context.
---

# DNS — domain context

Your domain knowledge goes here. Write whatever an agent would
need to know about this topic.
```

After creating it, you can attach it to tasks with `--context infra/dns`.

---

## Available skills

Skills attach to workflow steps, not directly to tasks. These are
the process instructions available:

| Skill | Used by | What it covers |
|---|---|---|
| `infra/testing-conventions` | `code/with-review` step 1 | How to write tests |
| `admin/xero-reconcile` | `admin/script` step 1 | Xero reconciliation script |
| `meta/dream` | Recurring self-improvement task | Repo-wide knowledge gap scan |
| `meta/create-suggest` | Post-creation task helper | Suggest workflow/context/mode |

---

## Available projects

| Project | Type | Where tasks live |
|---|---|---|
| `demo` | local | `./projects/demo/.relay/tasks/` |
| `admin` | local | `./projects/admin/.relay/tasks/` |
| `rd-tax` | local | Not configured yet (commented out in relay.local.toml) |

---

## Quick reference — common workflows

### "I want to create a task and see what the agent would receive"

```bash
relay create --project demo --title "My task" --workflow code/with-review --assignee claude1 --context email/payment-flow
relay launch --task 007 --dry-run
```

### "I want to walk a task from start to finish"

```bash
relay create --project demo --title "My task" --workflow code/with-review --assignee claude1
# Edit ticket.md: change status: ready → status: active
relay step --task 007
relay step --task 007
relay step --task 007
relay step --task 007
# Task is now done
relay status --all
```

### "I want to see every task including completed ones"

```bash
relay status --all
```

### "I want to read a task's full history"

```bash
cat projects/demo/.relay/tasks/007-my-task/log.md
```

### "I want to see what contexts and workflows exist"

```bash
ls contexts/*/SKILL.md contexts/*/*/SKILL.md
ls workflows/*/*.md
```

### "I want to clean up and start fresh"

```bash
rm -rf projects/demo/.relay/tasks/*
relay status
```
