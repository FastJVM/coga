// Core types for the Relay ticketing system

export type TaskStatus = 'open' | 'in-progress' | 'blocked' | 'completed' | 'waiting';
export type TaskAssignee = 'human' | 'agent' | 'human-and-agent';

export interface ContextBlock {
  id: string;
  name: string;
  description: string;
  content: string;
  category: string; // e.g., 'payment', 'frontend', 'testing'
  createdAt: Date;
  updatedAt: Date;
  reusableAcross: string[]; // Task types this can be applied to
}

export interface TaskMessage {
  id: string;
  author: 'human' | 'agent';
  content: string;
  timestamp: Date;
  attachedContextBlocks?: string[]; // IDs of context blocks referenced
}

export interface Task {
  id: string;
  title: string;
  description: string;
  status: TaskStatus;
  assignee: TaskAssignee;
  assignedTo?: string; // Human name or agent name
  priority: 'low' | 'medium' | 'high' | 'critical';
  contextBlocks: string[]; // IDs of attached context blocks
  messages: TaskMessage[];
  createdAt: Date;
  updatedAt: Date;
  createdBy: string;
  dueDate?: Date;
  tags: string[];
  dependencies?: string[]; // Task IDs this depends on
  dependents?: string[]; // Task IDs that depend on this
}

export interface ProjectMetadata {
  name: string;
  description: string;
  defaultContextBlocks: string[];
  workflowStages: TaskStatus[];
}
