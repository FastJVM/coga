# Relay Implementation Roadmap

This document outlines the path from the current v1 foundation to a full agent coordination system.

## v1: Core Blackboard ✅ CURRENT

**Mission**: Create a shared surface where all coordination happens.

**What's done**:
- Task board with status tracking
- Context blocks library
- Message threads
- REST API for all operations

**Key achievement**: The blackboard works as a ground truth. Humans and agents (when connected) will read from and write to the same place.

**When to move to v2**: Once you have a few tasks created and understand how context blocks work.

---

## v2: Local Agent Daemon

**Mission**: Make Relay active instead of passive. Agents check Relay constantly, pick up assigned work, and send results back.

### Phase v2a: MCP Server

Build an MCP (Model Context Protocol) server that lets Claude Code, Cursor, and other compatible agents read/write to Relay.

#### Key operations to expose:

```typescript
// Read operations
read_task(id: string) -> Task
list_tasks(filter?: { status, assignee, tag }) -> Task[]
read_context_block(id: string) -> ContextBlock

// Write operations  
update_task_status(id: string, status: TaskStatus) -> Task
add_message(taskId: string, content: string, author: "agent") -> TaskMessage
flag_blocked(taskId: string, reason: string) -> Task
```

#### Implementation structure:
```
mcp/
├── server.ts           # MCP server setup
├── tools.ts            # Tool definitions (read, write operations)
├── handlers.ts         # Handler functions for each tool
└── types.ts            # Type definitions
```

#### To implement:
1. Use `@modelcontextprotocol/sdk` npm package
2. Define tools that correspond to your API endpoints
3. Each tool maps to an API call (auth as needed)
4. Test with Claude Code first (simplest integration)

### Phase v2b: Local Agent Daemon

A daemon that runs in the background and orchestrates agent work.

```typescript
// Basic loop
while (true) {
  const tasks = await relay.listTasks({ status: "open", assignedTo: "agent" });
  
  for (const task of tasks) {
    const blocks = await relay.getContextBlocks(task.contextBlockIds);
    const prompt = buildPrompt(task, blocks);
    
    const result = await callAgent(prompt);
    
    await relay.addMessage(task.id, result, "agent");
    await relay.updateTaskStatus(task.id, result.suggestedStatus);
  }
  
  await sleep(30000); // Check every 30 seconds
}
```

#### Structure:
```
agent/
├── daemon.ts           # Main loop
├── orchestrator.ts     # How to call agents
├── prompt-builder.ts   # Context + task -> prompt
└── config.ts           # Settings (which agents, polling interval, etc)
```

#### Key decisions:
- **Polling vs webhooks**: Start with polling (simpler). Upgrade to webhooks later.
- **Which agent?**: CLI agents (Claude via CLI or API) are easiest. Browser-based agents harder.
- **Context size**: Combine task description + all context blocks. Watch token usage.
- **Result handling**: Agent writes back status, messages, and flagged blockers

### Implementation order for v2:

1. **MCP Server** (easier, more reusable)
   - Test with Claude Code
   - Claude Code now has MCP built-in
   - Can read/write Relay natively

2. **Local Daemon** (more complex, more powerful)
   - Runs in background
   - Picks up work automatically
   - No manual prompt crafting

---

## v3: Recurring Tasks & Team Automation

**Mission**: Encode team workflows so they run themselves.

### What this looks like:

```typescript
// Define a recurring task
const recurringTask = {
  title: "Daily deliverability check",
  schedule: "0 9 * * MON-FRI", // 9am weekdays
  assignee: "agent",
  contextBlocks: ["email-diagnostics", "escalation-rules"],
  onComplete: (result) => {
    if (result.severity === "critical") {
      notify("team@company.com", result);
    }
  }
};

// System creates task, agent picks it up, runs diagnostics, posts results
// No human intervention needed
```

### To implement:

1. **Scheduler**: Use node-cron or similar
2. **Task auto-creation**: When scheduled time arrives, create task
3. **Notification system**: Route results to right people
4. **Feedback loop**: If agent gets something wrong, human fixes it and updates context block

### Example: Email Deliverability Checks

From the write-up:
- Weekly task: "Run deliverability diagnostics for domains"
- Attached context: "How to check SPF/DKIM/DMARC, how to read blacklist results, when to escalate"
- Agent runs checks, posts results in thread
- If novel issue found, human adds to context block for next run

---

## Implementation Priorities

### Must-have for v1 → v2:
- ✅ Task board works
- ✅ Context blocks can be created and attached
- ✅ Message threads work
- [ ] Add authentication (if multi-user)
- [ ] Persistent database (replace in-memory)

### Must-have for v2a (MCP):
- [ ] MCP server package
- [ ] Authentication token system (agents need to authenticate to Relay)
- [ ] Tool definitions for read/write
- [ ] Testing in Claude Code

### Must-have for v2b (Daemon):
- [ ] Agent integration (CLI or API)
- [ ] Polling loop
- [ ] Error handling (agent fails, network fails, etc)
- [ ] Logging (what did the agent do?)

### Must-have for v3:
- [ ] Scheduler
- [ ] Task template system
- [ ] Notification system
- [ ] Runbook/playbook system (predefined workflows)

---

## Quick Implementation Guide

### Start with v2a (MCP Server)

**Why?** Easier than the daemon, immediately gives you MCP access.

```bash
# 1. Add MCP dependencies
npm install @modelcontextprotocol/sdk

# 2. Create mcp/server.ts
# - Initialize MCP server
# - Define tools (list_tasks, read_task, add_message, etc)
# - Map tools to your API calls

# 3. Test in Claude Code
# - Open Claude Code
# - Enable MCP
# - Add your MCP server
# - Try: "Read the list of tasks from Relay"
```

**Minimal example**:
```typescript
// mcp/server.ts
import { Server } from "@modelcontextprotocol/sdk/server/index.js";

const server = new Server({
  name: "relay",
  version: "1.0.0",
});

// Define list_tasks tool
server.setRequestHandler(ListResourcesRequestSchema, async () => ({
  resources: [{
    uri: "relay://tasks",
    name: "tasks",
    mimeType: "application/json",
  }],
}));

server.setRequestHandler(ReadResourceRequestSchema, async (req) => {
  if (req.params.uri === "relay://tasks") {
    const tasks = await fetch("http://localhost:3000/api/tasks").then(r => r.json());
    return {
      contents: [{
        uri: req.params.uri,
        mimeType: "application/json",
        text: JSON.stringify(tasks),
      }],
    };
  }
});

// Start server...
```

Then you can ask Claude Code: *"Show me the highest priority items from Relay"* and it works.

### Then build v2b (Daemon)

```typescript
// daemon.ts
async function runDaemon() {
  console.log("Relay agent daemon started");
  
  while (true) {
    try {
      // Get unassigned or assigned-to-agent tasks
      const tasks = await fetch("http://localhost:3000/api/tasks")
        .then(r => r.json())
        .then(tasks => tasks.filter(t => 
          t.status === "open" && t.assignee === "agent"
        ));
      
      for (const task of tasks) {
        console.log(`[${task.id}] Starting: ${task.title}`);
        
        // Get context blocks
        const blocks = await Promise.all(
          task.contextBlocks.map(id =>
            fetch(`http://localhost:3000/api/context-blocks/${id}`).then(r => r.json())
          )
        );
        
        // Build prompt
        const prompt = `
Task: ${task.title}
Description: ${task.description}

Context:
${blocks.map(b => `## ${b.name}\n${b.content}`).join("\n\n")}

Please work on this task and report back what you did and what you found.
`;
        
        // Call Claude
        const result = await callClaude(prompt);
        
        // Write back to Relay
        await fetch("http://localhost:3000/api/tasks/${task.id}", {
          method: "POST",
          body: JSON.stringify({
            action: "add-message",
            author: "agent",
            content: result
          })
        });
        
        console.log(`[${task.id}] Complete`);
      }
      
      // Wait before next check
      await sleep(30000);
    } catch (e) {
      console.error("Daemon error:", e);
      await sleep(5000);
    }
  }
}

runDaemon();
```

---

## Validation Metrics (from the write-up)

After building v2, measure if it's working:

1. **Are agents actually picking up tasks?** Check the message thread - agent messages should appear
2. **Is context reaching the agent?** Agent should reference context block information in responses
3. **Are multiple agents working in parallel?** Assign tasks to different agents, both should execute
4. **Is the team retaining it after week 3?** Usage should stick, not drop off

If yes to all four, you have a working v2 and can move to v3 (automating recurring work).

---

## Questions to Answer as You Build

- **Authentication**: How do agents authenticate to your Relay instance? API key? OAuth? Token?
- **Rate limiting**: Should there be limits on how fast agents can poll/update?
- **Context size**: What's your token budget? How many context blocks per task?
- **Error handling**: What happens if an agent fails? Does it retry? Get reassigned?
- **Audit trail**: Do you need to log every agent action for compliance?

Start simple, add constraints when needed.
