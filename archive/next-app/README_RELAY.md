# Relay: A Blackboard for Humans and Agents

This is the foundation for **Relay** — a coordination system for managing parallel work between humans and AI agents.

Based on: Your boss's write-up describing the problems he faces coordinating work across Linear, markdown files, and GitHub.

## What This Is

A **v1 implementation** of the core concept: a shared surface where:
- Tasks live with full context (description, decision history, blockers)
- Context blocks (reusable knowledge) attach to tasks
- Humans and agents read/write to the same place
- No context bleeding between projects

## Quick Start

```bash
npm install
npm run dev
```

Visit `http://localhost:3000`

You'll see:
- A task board with one sample task (Stripe integration)
- Two context blocks (Payment Processing, Frontend Development)
- Full message thread showing how humans and agents coordinate

## The Core Problem

You keep losing the thread:
- **Across sessions**: Which context goes with which task?
- **Between agents**: Agent A designed the approach, Agent B coded it, Agent C tested it — who has the context?
- **Between tools**: Task in Linear, instructions in markdown, work in GitHub. No connection.

## The Solution: A Blackboard

One place where:
1. **Tasks** have status, history, and full conversation threads
2. **Context Blocks** are scoped knowledge (attached to relevant tasks only)
3. **Messages** record every action — human decisions, agent work, blockers
4. **Everyone** (humans and agents) reads from and writes to the same place

## Key Files

- [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) - Architecture and concepts
- [V2_ROADMAP.md](V2_ROADMAP.md) - How to build the MCP server and agent daemon

## What You Can Do Now (v1)

✅ Create tasks with title, description, priority, assignee type
✅ Attach context blocks to tasks
✅ Message in the task thread
✅ See full coordination history
✅ View context blocks library
✅ Change task status (Kanban board)

## What's Next (v2)

Build the agent integration layer:
1. **MCP Server** - Let Claude Code, Cursor, and other tools read/write Relay natively
2. **Local Agent Daemon** - Watches for assigned tasks, injects context, runs agents, writes back results
3. **Context Injection** - Agent gets exactly the context blocks attached to their task

See [V2_ROADMAP.md](V2_ROADMAP.md) for implementation details.

## The Philosophy

Everyone else is building:
- RAG pipelines trying to guess what context is relevant
- Vector databases and semantic search
- Complex agent orchestration frameworks

Relay bets the opposite: **Developers should own their context explicitly.** Not in a vector database, but in visible, editable blocks they control.

Context blocks are:
- **Explicit**: You decide what goes where
- **Reusable**: Write once, use across all tasks of that type
- **Scoped**: No noise from other projects
- **Curated**: Built up as a side effect of working

This keeps agents focused and humans in control.

## How It Scales

### Week 1 (now)
Start managing one task with context blocks. Get used to the workflow.

### Week 2-3
Build more context blocks for your recurring task types. Try attaching agents (via MCP).

### Month 2
Deploy the local agent daemon. Tasks auto-assigned to agents run automatically.

### Month 3+
Define recurring tasks. Monday morning: "Run tests" auto-creates with test context attached. Agent picks it up, runs, posts results. Cycle repeats.

Team workflows become:
1. Design once (what should this task type know?)
2. Encode once (write the context block)
3. Run forever (agents execute it repeatedly)

## Database

Currently uses in-memory storage (fine for development). For production, swap in:
- PostgreSQL + Prisma
- MongoDB
- Any database

The API layer is abstracted in `lib/db.ts`.

## Authentication & Multi-user

Current implementation is single-user. To make it multi-user:
1. Add authentication (next-auth, clerk, etc)
2. Add user/team ownership to tasks and context blocks
3. Add permissions (view, edit, assign)
4. Switch to persistent database

## Next Steps

1. Open `http://localhost:3000` and create a task
2. Read [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) to understand the architecture
3. Read [V2_ROADMAP.md](V2_ROADMAP.md) to plan the agent integration
4. Start building context blocks for your workflows
5. When ready, implement the MCP server (v2a)

---

**Built in response to**: "I keep losing the thread. I re-explain the same things. Agents don't coordinate with each other."

**The bet**: If you solve the coordination problem at the infrastructure level (a good blackboard), everything else gets easier.
