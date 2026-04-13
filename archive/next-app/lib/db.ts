import { Task, ContextBlock, TaskMessage } from './types';

// In-memory storage for MVP - can be replaced with a real database
let tasks: Map<string, Task> = new Map();
let contextBlocks: Map<string, ContextBlock> = new Map();
let initialized = false;

// Initialize with sample data
function initializeSampleData() {
  if (initialized) return; // Already initialized
  initialized = true;

  // Sample context blocks
  const paymentBlock: ContextBlock = {
    id: 'ctx-payment',
    name: 'Payment Processing',
    description: 'Context for payment and billing related tasks',
    content: `# Payment Processing Context

## Stripe Integration
- Always use Stripe API v1
- Handle webhook verification with endpoint secret
- Retry failed charges with exponential backoff (1s, 2s, 4s)

## Error Handling
- Log all transaction failures with transaction ID
- Notify user within 24 hours of charge failure
- Check blacklist status before retrying failed payments

## Testing
- Use Stripe test cards for development
- Always test webhook signature verification
- Test both success and failure paths`,
    category: 'backend',
    createdAt: new Date(),
    updatedAt: new Date(),
    reusableAcross: ['payment', 'billing', 'refund']
  };

  const frontendBlock: ContextBlock = {
    id: 'ctx-frontend',
    name: 'Frontend Development',
    description: 'Frontend patterns and best practices',
    content: `# Frontend Development Context

## Component Structure
- Keep components under 200 lines
- Use composition over props drilling
- Prop types should be defined at component top

## Testing
- Test user interactions, not implementation
- Use data-testid for reliable selectors
- Aim for 80%+ coverage on user-facing components

## Performance
- Profile before optimizing
- Code split at route boundaries
- Lazy load non-critical images`,
    category: 'frontend',
    createdAt: new Date(),
    updatedAt: new Date(),
    reusableAcross: ['frontend', 'ui', 'web']
  };

  contextBlocks.set(paymentBlock.id, paymentBlock);
  contextBlocks.set(frontendBlock.id, frontendBlock);

  // Sample task
  const sampleTask: Task = {
    id: 'task-1',
    title: 'Set up Stripe integration',
    description: 'Implement payment processing with Stripe. Need to handle webhook verification and set up retry logic for failed charges.',
    status: 'in-progress',
    assignee: 'agent',
    assignedTo: 'Claude Code',
    priority: 'high',
    contextBlocks: [paymentBlock.id],
    createdAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000), // 2 days ago
    updatedAt: new Date(Date.now() - 1 * 60 * 60 * 1000), // 1 hour ago
    createdBy: 'you',
    tags: ['backend', 'payment', 'critical'],
    messages: [
      {
        id: 'msg-1',
        author: 'agent',
        content: 'I\'ve reviewed the Stripe documentation. Ready to implement the webhook handler. Should I start with endpoint verification or the retry logic first?',
        timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000),
      },
      {
        id: 'msg-2',
        author: 'human',
        content: 'Start with webhook verification - the context block has the details on the endpoint secret pattern we use. Then implement retry with exponential backoff.',
        timestamp: new Date(Date.now() - 1 * 60 * 60 * 1000),
      }
    ]
  };

  tasks.set(sampleTask.id, sampleTask);
}

// Initialize on load
initializeSampleData();

// Task operations
export const db = {
  tasks: {
    create(task: Omit<Task, 'id' | 'createdAt' | 'updatedAt' | 'messages'>) {
      const id = `task-${Date.now()}`;
      const newTask: Task = {
        ...task,
        id,
        createdAt: new Date(),
        updatedAt: new Date(),
        messages: []
      };
      tasks.set(id, newTask);
      return newTask;
    },

    getAll() {
      return Array.from(tasks.values()).sort((a, b) => 
        b.updatedAt.getTime() - a.updatedAt.getTime()
      );
    },

    getById(id: string) {
      return tasks.get(id);
    },

    update(id: string, updates: Partial<Task>) {
      const task = tasks.get(id);
      if (!task) return null;
      
      const updated = {
        ...task,
        ...updates,
        updatedAt: new Date()
      };
      tasks.set(id, updated);
      return updated;
    },

    delete(id: string) {
      return tasks.delete(id);
    },

    addMessage(taskId: string, message: Omit<TaskMessage, 'id' | 'timestamp'>) {
      const task = tasks.get(taskId);
      if (!task) return null;

      const newMessage: TaskMessage = {
        ...message,
        id: `msg-${Date.now()}`,
        timestamp: new Date()
      };

      task.messages.push(newMessage);
      task.updatedAt = new Date();
      tasks.set(taskId, task);
      return newMessage;
    },

    getByStatus(status: string) {
      return Array.from(tasks.values()).filter(t => t.status === status);
    },

    getByAssignee(assignee: string) {
      return Array.from(tasks.values()).filter(t => 
        t.assignedTo === assignee || t.assignee === assignee
      );
    }
  },

  contextBlocks: {
    create(block: Omit<ContextBlock, 'id' | 'createdAt' | 'updatedAt'>) {
      const id = `ctx-${Date.now()}`;
      const newBlock: ContextBlock = {
        ...block,
        id,
        createdAt: new Date(),
        updatedAt: new Date()
      };
      contextBlocks.set(id, newBlock);
      return newBlock;
    },

    getAll() {
      return Array.from(contextBlocks.values()).sort((a, b) =>
        b.updatedAt.getTime() - a.updatedAt.getTime()
      );
    },

    getById(id: string) {
      return contextBlocks.get(id);
    },

    update(id: string, updates: Partial<ContextBlock>) {
      const block = contextBlocks.get(id);
      if (!block) return null;

      const updated = {
        ...block,
        ...updates,
        updatedAt: new Date()
      };
      contextBlocks.set(id, updated);
      return updated;
    },

    delete(id: string) {
      return contextBlocks.delete(id);
    },

    getByCategory(category: string) {
      return Array.from(contextBlocks.values()).filter(b => b.category === category);
    },

    getManyById(ids: string[]) {
      return ids.map(id => contextBlocks.get(id)).filter(Boolean) as ContextBlock[];
    }
  },

  // Health check and reset for development
  reset() {
    tasks.clear();
    contextBlocks.clear();
    initializeSampleData();
  }
};
