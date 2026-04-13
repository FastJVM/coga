# Relay - Task Coordination System

A foundation for coordinating work between humans and AI agents. This is **v1** of the Relay system, focused on the core blackboard: a shared surface where tasks, context, and conversation threads live.

## What's Included

### Core Components
- **Task Board**: Kanban-style view of tasks organized by status (Open, In Progress, Blocked, Waiting, Completed)
- **Task Details**: Full conversation threads with message history and attached context blocks
- **Context Blocks Library**: Reusable, scoped bundles of knowledge and process
- **Task Management**: Create, update, and track tasks across the team

### Data Models

#### Task
- Title and description
- Status (open, in-progress, blocked, waiting, completed)
- Priority (low, medium, high, critical)
- Assignee type (human, agent, human-and-agent) and name
- Message thread for the full conversation history
- Attached context blocks
- Tags and metadata

#### ContextBlock
- Name and description
- Category (e.g., payment, frontend, testing)
- Content (the actual knowledge/process)
- Reusable across (which task types it applies to)
- Full edit history

### API Routes
- `GET/POST /api/tasks` - List and create tasks
- `GET/PATCH/DELETE /api/tasks/[id]` - Task operations
- `POST /api/tasks/[id]` - Add messages to task thread
- `GET/POST /api/context-blocks` - List and create context blocks
- `GET/PATCH/DELETE /api/context-blocks/[id]` - Context block operations

## Running Locally

```bash
npm run dev
```

Visit `http://localhost:3000` to see the task board.

## Sample Data

The system comes with sample data:
- One task: "Set up Stripe integration" (in-progress, assigned to Claude Code)
- Two context blocks: Payment Processing and Frontend Development
- Shows how tasks attach context blocks and maintain message threads

## Next: Building Towards v2

The write-up mentions three phases:

### v1 ✅ **Current: Basic Blackboard**
- Task board
- Context blocks
- Message threads
- Agent-agnostic API

### v2: Local Agent Daemon
A daemon running on the user's machine that:
- Watches Relay tasks for assignments
- Pulls attached context blocks
- Calls agents via MCP with scoped context
- Writes results back to the blackboard
- Turns Relay from passive (agents check when they choose) to active (Relay runs the work)

To implement v2, you'll need:
1. **MCP Server implementation** - Create an MCP server that exposes task operations
2. **Agent runner** - A daemon process that polls for tasks and orchestrates agent calls
3. **Context injection** - Automatically include relevant context blocks when calling agents

### v3: Recurring Tasks & Automation
- Tasks that auto-create on schedules
- Automated context block attachment
- Continuous background agent work
- Team workflows become self-running

## Key Concepts from the Write-up

### The Blackboard
All agents and humans read from and write to the same place. No context bleeding between projects. No guessing about what information is relevant.

### Context Blocks
The core insight: developers should own what their agents know. Rather than RAG pipelines trying to guess, context blocks are:
- **Explicit**: You decide what information goes with which task type
- **Reusable**: Write once, use across many tasks
- **Curated**: Built up as a side effect of doing work
- **Scoped**: No noise from unrelated projects

### Message Threads
Every action (human decision, agent work, blocker, resolution) is recorded in the task's conversation. Full context history without switching tools.

## Architecture Notes

### Storage
Currently using in-memory storage (`lib/db.ts`). For production, replace with:
- PostgreSQL + Prisma
- MongoDB
- Any database with proper transactions

### Client/Server
- **Server**: Next.js API routes + in-memory storage
- **Client**: React components with client-side state management
- Can be easily extended to work with external databases, authentication, real-time updates

### Scaling to Multiple Users
Current implementation is single-user. To add multi-user support:
1. Add authentication
2. Add user/team ownership to tasks and context blocks
3. Add permissions (who can edit, who can view)
4. Use a persistent database instead of in-memory

## Extending the System

### Add Authentication
```tsx
// Use a library like next-auth or clerk
// Add user context to API routes
// Filter tasks by user/team
```

### Add Real-time Updates  
```tsx
// Use WebSockets or Server-Sent Events
// Broadcast task updates to watching clients
// Show when other team members are working on tasks
```

### Implement MCP Server
```typescript
// Create an MCP server that exposes:
// - read:task
// - write:task
// - list:tasks
// - read:context-block
// This allows Claude Code, Cursor, etc. to interact with Relay
```

### Add Block Extraction
LLM reads task description and suggests reusable context blocks:
```typescript
// When creating a task, optionally:
// 1. Send task description to Claude
// 2. Ask it to extract domain knowledge
// 3. Suggest new context blocks
// 4. Let human review and save
```

## File Structure

```
app/
  ├── api/
  │   ├── tasks/
  │   │   ├── route.ts          # List and create tasks
  │   │   └── [id]/
  │   │       └── route.ts       # Task operations and messages
  │   └── context-blocks/
  │       ├── route.ts          # List and create blocks
  │       └── [id]/
  │           └── route.ts       # Block operations
  ├── tasks/
  │   └── [id]/
  │       └── page.tsx          # Task detail view
  ├── context-blocks/
  │   └── page.tsx             # Blocks library view
  ├── page.tsx                 # Main task board
  └── layout.tsx
components/
  ├── TaskBoard.tsx            # Kanban board
  ├── TaskCard.tsx             # Task card component
  ├── TaskDetail.tsx           # Task detail view
  ├── TaskModal.tsx            # Modal for creating tasks
  └── ContextBlockPreview.tsx  # Context block display
lib/
  ├── types.ts                 # TypeScript types
  └── db.ts                    # Storage layer
```

## Why This Approach

The write-up explains that most solutions overengineer this. Relay is deliberately low-tech:
- No RAG pipelines guessing what context is relevant
- No vector databases
- No complex orchestration frameworks
- Just: a task list, scoped instructions, and a shared surface

The complexity is in the domain knowledge (what belongs in each context block), not the infrastructure.

## Next Steps

1. ✅ Build the foundation (done)
2. Run locally and create some tasks
3. Add more context blocks for your workflows
4. Build the MCP server (for v2)
5. Create the local agent daemon (for v2)
6. Add authentication and multi-user support
7. Deploy and start coordinating with your team

---

Built with the philosophy from the Relay write-up: **Keep humans in control, give agents focus, and make the coordination layer the thing that's hard to leave.**
