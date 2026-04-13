# Quick Start Guide - Relay v1

Get up and running with the task coordination system.

## 1. Start the Development Server

```bash
cd /Users/zach2179/Desktop/ticketing-system
npm install  # if you haven't already
npm run dev
```

Open http://localhost:3000 - you should see a task board.

## 2. Explore the Sample Data

The board comes with:
- **1 Task**: "Set up Stripe integration" (in-progress, assigned to Claude Code)
- **2 Context Blocks**: "Payment Processing" and "Frontend Development"

### Explore the task:
1. Click on the "Set up Stripe integration" card
2. You'll see:
   - Task details (priority, assignee, created date)
   - Full message thread (human and agent messages)
   - Attached context blocks (on the right)
   - Stats about messages and blocks

### Understand the context block:
1. In the task detail view, expand the "Payment Processing" context block
2. See the actual content: Stripe integration info, retry logic, error handling
3. This context block would automatically be shared with any agent working on this task

## 3. Create Your First Task

1. Click **"New Task"** button (top right of board)
2. Fill in:
   - **Title**: Something specific ("Implement JWT auth" or "Add dark mode toggle")
   - **Description**: What needs to happen and why
   - **Priority**: low/medium/high/critical
   - **Assignee Type**: human/agent/human-and-agent
   - **Assigned To**: Your name or agent name
   - **Tags**: Comma-separated (e.g., "backend, authentication, urgent")
3. Click "Create Task"
4. Task appears in the "Open" column

## 4. Move the Task Around

1. In the task list view, there are 5 columns: Open, In Progress, Blocked, Waiting, Completed
2. Click on a task card → it opens the detail view
3. In the detail view, the **Status** dropdown lets you change where it is
4. Try: Open → In Progress → Waiting → In Progress → Completed

Watch the statistics at the top: "Total active" counts all tasks not in Completed.

## 5. Have a Conversation in the Thread

1. Open a task
2. Scroll to the **Thread** section
3. In the message box at the bottom, type something like:
   - "Need to check if we have CORS configured"
   - "Tried the API endpoint, got 401 response"
   - "Added the middleware fix suggested above"
4. Click "Send Message"
5. Your message appears in the thread

**Key insight**: This is where all coordination happens. Not Slack, not GitHub issues. Here. Full history, full context.

## 6. Understand Context Blocks

Context blocks are reusable chunks of knowledge. The system comes with:

### Payment Processing Block
- Category: backend
- Contains: Stripe API info, webhook patterns, retry logic, error handling
- Reusable across: payment, billing, refund tasks

### Frontend Development Block
- Category: frontend
- Contains: Component structure patterns, testing approach, performance notes
- Reusable across: frontend, ui, web tasks

### Why blocks?
When you assign a task to an agent, the attached context blocks go too. Agent gets exactly what it needs, no noise from other projects.

## 7. View All Context Blocks

1. From anywhere, go to http://localhost:3000/context-blocks
2. See all blocks organized by category
3. More blocks = better agent coordination

## 8. Typical Workflow

### Scenario: You're stuck on a backend task

1. **Create a task**: "Debug intermittent 500 errors in user service"
2. **Assign to**: An agent (Claude Code or your chosen agent)
3. **Attach context**: Backend patterns, logging conventions, error code reference
4. **Add initial message**: "Started debugging. Checked recent logs. Agent, try reprouting with these debug flags: ..."
5. **Agent sees the task**: (when v2 is built) Reads the context block, sees your message, starts investigating
6. **Agent replies**: "Reproduced it. The issue is X. Tried solution Y. Stuck on Z."
7. **You add context**: "Ah, for Z you need to check the database migration history. That's in the context block now."
8. **Agent tries again**: Now has the info it needs
9. **Task completes**: "Fixed! Here's the commit."

### Without Relay:
- You write Slack message to agent
- Agent reads Slack (when?)
- You forgot to mention the migration history
- Agent gets stuck, asks you
- You reply in 8 hours
- Loop repeats

### With Relay:
- Task is the source of truth
- Context blocks are pre-attached
- Agent reads task once, has everything
- Human can see exactly where agent is stuck
- Human can update context blocks when patterns emerge
- Next agent with same type of task has better context

## 9. Try Assigning Different Types

Create a few tasks with different configurations:

**Human task**: "Review design mockups"
- Assignee: Human
- Assigned to: Your name
- Context: Design system block

**Agent task**: "Run automated tests"
- Assignee: Agent
- Assigned to: "Test Runner" (or whatever you call your agent)
- Context: Testing conventions block

**Collaborative task**: "Implement payment gateway"
- Assignee: Human & Agent
- Assigned to: "Claude + You"
- Context: Payment block
- Message thread shows back-and-forth

## 10. Before Moving to v2

Create at least 5 tasks and answer:
- ✅ Did the task board feel like a better place for coordination than email/Slack?
- ✅ Did context blocks make sense? Would you reuse them?
- ✅ Did the message thread capture the decision-making process?
- ✅ Can you see how an agent would benefit from reading the context block?

If yes to all, v2 (agent integration) will 10x the value.

## Common Questions

**Q: Why not just use Linear/Jira/Asana?**
A: Those are built for human teams. Agent integration is a checkbox. Relay builds agents as first-class workers from day one.

**Q: How is this different from a note with Slack thread?**
A: Context blocks are structured and reusable. Slack is ephemeral. A context block written once can help 100 agents with 100 tasks.

**Q: When should I create a context block vs just message?**
A: Message: "I just tried X and it didn't work."
Context block: "Here's how we always approach X" (that pattern will come up again)

**Q: What happens when the agent does the task wrong?**
A: You see it in the thread. Message the agent what went wrong. Update the context block so next time it's clearer. Context compounds over time.

## Next: Building v2

Once you're comfortable with v1, read:
1. [V2_ROADMAP.md](V2_ROADMAP.md) - The plan
2. [CLAUDE.md](CLAUDE.md) - Instructions for agents working on the code

v2 brings:
- MCP server (agents can read/write Relay natively)
- Local daemon (tasks auto-assigned to agents, context auto-injected)
- Integration with Claude Code, Cursor, etc.

Then v3: recurring tasks that run themselves.

---

**Key Insight from the write-up**: The problem isn't intelligence. It's infrastructure. Give agents the right context and a place to coordinate, and they stop being blockers and become multipliers.

Start using Relay now. Get familiar with the workflow. Then automate it.
