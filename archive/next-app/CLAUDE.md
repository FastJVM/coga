# CLAUDE.md - Relay Project Context

You are helping build **Relay**, a coordination system for humans and AI agents.

## The Problem We're Solving

The creator keeps losing the thread when coordinating work:
- 4 tickets in flight (one he's working on, two with agents, one waiting)
- Can't remember which agent is stuck on what
- Re-explains the same context across sessions
- Task info spread across Linear, markdown files, GitHub

## What We Built (v1)

A task board where:
1. **Tasks** have full conversation threads (what was decided, what was tried, blockers)
2. **Context blocks** are reusable bundles of knowledge (attached to tasks, not guessed by RAG)
3. **Everyone** (human and agent) reads from and writes to the same place

## Codebase Layout

```
app/
  api/tasks/              # Task CRUD + messaging
  api/context-blocks/     # Context block management
  tasks/[id]/            # Task detail page
  context-blocks/        # Context blocks library
  page.tsx               # Main task board (Kanban)

components/
  TaskBoard.tsx          # Kanban board view
  TaskDetail.tsx         # Task conversation view
  TaskCard.tsx           # Individual task
  ContextBlockPreview.tsx # Context block display

lib/
  types.ts               # Task, ContextBlock types
  db.ts                  # Storage (in-memory for now, replace with DB)
```

## Key Concepts

### Task Model
```typescript
{
  id: string
  title: string
  description: string
  status: "open" | "in-progress" | "blocked" | "waiting" | "completed"
  assignee: "human" | "agent" | "human-and-agent"
  assignedTo?: string // "Claude Code", "you", etc
  priority: "low" | "medium" | "high" | "critical"
  
  // The conversation thread
  messages: [{ author, content, timestamp }]
  
  // Attached knowledge
  contextBlocks: string[] // IDs of context blocks
  
  // Metadata
  tags: string[]
  createdAt: Date
  updatedAt: Date
}
```

### Context Block Model
```typescript
{
  id: string
  name: string
  category: string // "payment", "frontend", "testing"
  description: string
  content: string // The actual knowledge/process
  reusableAcross: string[] // Which task types use this
}
```

## When Working on Tasks

1. **Read SYSTEM_DESIGN.md** - Full architecture explanation
2. **Read V2_ROADMAP.md** - What comes next (MCP server, agent daemon)
3. **Reference the types** - `lib/types.ts` is authoritative
4. **Use the API** - All state goes through `/api/tasks` and `/api/context-blocks`

## Building Features

### Adding a new task status
1. Update `TaskStatus` in `lib/types.ts`
2. Add it to the kanban columns in `TaskBoard.tsx`
3. Update status dropdown in `TaskDetail.tsx`

### Adding context block management
1. Create a modal/form for editing context blocks
2. POST to `/api/context-blocks`
3. Update the task's `contextBlockIds` when attaching

### Adding agent integration (v2)
1. Build MCP server in `mcp/` folder
2. Expose tools: `list_tasks`, `read_task`, `add_message`, `update_task_status`
3. Build daemon in `agent/` folder that polls tasks and calls agents

## Important Notes

**This is deliberately low-tech:**
- No RAG pipelines
- No vector databases
- No semantic search
- No complex orchestration

Resources go into **domain knowledge** (good context blocks), not infrastructure.

**When you get stuck on a task:**
1. Write what you tried in the message thread
2. A human will see what blocked you and add context
3. Next time, that context block exists for all future tasks

**For testing:**
Sample data in `lib/db.ts` has:
- One task: "Set up Stripe integration"
- Two context blocks: Payment Processing, Frontend Development

## Your Job

Work backwards from the goal: users should feel that losing Relay would disrupt their workflow. That happens when:
1. Tasks accumulate context blocks (a library of domain knowledge)
2. Agents actually use the context when working
3. The conversation thread is richer than scattered Slack messages

## Next Phase (v2)

Build the agent integration:
- **MCP Server**: Let Claude Code read/write tasks natively
- **Local Daemon**: Watch for work, inject context, call agents, write results back

When that's done, agents become first-class workers on the blackboard.

---

**Philosophy**: Programming is becoming context management. Give agents the exact context they need, keep humans in control, build the coordination layer that's hard to leave.

Check V2_ROADMAP.md for implementation details.
