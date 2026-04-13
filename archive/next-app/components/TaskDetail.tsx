'use client';

import { Task, ContextBlock } from '@/lib/types';
import { useState, useEffect } from 'react';
import Link from 'next/link';
import ContextBlockPreview from './ContextBlockPreview';

interface TaskDetailProps {
  taskId: string;
}

export default function TaskDetail({ taskId }: TaskDetailProps) {
  const [task, setTask] = useState<Task | null>(null);
  const [contextBlocks, setContextBlocks] = useState<ContextBlock[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [newMessage, setNewMessage] = useState('');
  const [isSubmittingMessage, setIsSubmittingMessage] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState<string>('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        console.log(`[TaskDetail] Fetching task: ${taskId}`);
        const taskResponse = await fetch(`/api/tasks/${taskId}`);
        console.log(`[TaskDetail] Response status:`, taskResponse.status);
        
        if (taskResponse.ok) {
          const taskData = await taskResponse.json();
          console.log(`[TaskDetail] Got task:`, taskData);
          setTask(taskData);
          setSelectedStatus(taskData.status);

          // Fetch associated context blocks
          if (taskData.contextBlocks && taskData.contextBlocks.length > 0) {
            console.log(`[TaskDetail] Fetching ${taskData.contextBlocks.length} context blocks`);
            const blockPromises = taskData.contextBlocks.map((blockId: string) =>
              fetch(`/api/context-blocks/${blockId}`)
                .then(r => {
                  if (!r.ok) throw new Error(`Failed to fetch block ${blockId}`);
                  return r.json();
                })
                .catch(e => {
                  console.error(`Failed to fetch block ${blockId}:`, e);
                  return null;
                })
            );
            const blocks = await Promise.all(blockPromises);
            const validBlocks = blocks.filter(Boolean);
            console.log(`[TaskDetail] Got ${validBlocks.length} blocks`);
            setContextBlocks(validBlocks);
          }
        } else {
          console.error(`[TaskDetail] Task not found. Status: ${taskResponse.status}`);
        }
      } catch (error) {
        console.error('[TaskDetail] Error fetching task:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [taskId]);

  const handleStatusChange = async (newStatus: string) => {
    if (!task) return;

    try {
      const response = await fetch(`/api/tasks/${taskId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      });

      if (response.ok) {
        const updatedTask = await response.json();
        setTask(updatedTask);
        setSelectedStatus(updatedTask.status);
      }
    } catch (error) {
      console.error('Failed to update task status:', error);
    }
  };

  const handleAddMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!task || !newMessage.trim()) return;

    setIsSubmittingMessage(true);
    try {
      const response = await fetch(`/api/tasks/${taskId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'add-message',
          author: 'human',
          content: newMessage
        })
      });

      if (response.ok) {
        const message = await response.json();
        setTask({
          ...task,
          messages: [...task.messages, message],
          updatedAt: new Date()
        });
        setNewMessage('');
      }
    } catch (error) {
      console.error('Failed to add message:', error);
    } finally {
      setIsSubmittingMessage(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-slate-600">Loading task...</div>
      </div>
    );
  }

  if (!task) {
    return (
      <div className="min-h-screen bg-slate-50 p-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-slate-900 mb-2">Task not found</h1>
          <Link href="/" className="text-slate-600 hover:text-slate-900">
            Back to board
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-6xl mx-auto">
        {/* Header with Back Button */}
        <div className="bg-white border-b border-slate-200 p-6">
          <Link href="/" className="text-sm text-slate-600 hover:text-slate-900 mb-4 inline-block">
            ← Back to board
          </Link>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-bold text-slate-900 mb-2">{task.title}</h1>
              <p className="text-slate-600">{task.description}</p>
            </div>
            <select
              value={selectedStatus}
              onChange={(e) => handleStatusChange(e.target.value)}
              className="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900 font-medium"
            >
              <option value="open">Open</option>
              <option value="in-progress">In Progress</option>
              <option value="blocked">Blocked</option>
              <option value="waiting">Waiting</option>
              <option value="completed">Completed</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-6 p-6">
          {/* Main Content - Messages */}
          <div className="col-span-2 space-y-6">
            {/* Task Metadata */}
            <div className="bg-white rounded-lg border border-slate-200 p-6">
              <h2 className="font-semibold text-slate-900 mb-4">Task Details</h2>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs font-medium text-slate-500 uppercase">Priority</div>
                  <div className="mt-1 text-sm font-semibold text-slate-900">
                    {task.priority.charAt(0).toUpperCase() + task.priority.slice(1)}
                  </div>
                </div>
                <div>
                  <div className="text-xs font-medium text-slate-500 uppercase">Assignee</div>
                  <div className="mt-1 text-sm font-semibold text-slate-900">
                    {task.assignedTo || 'Unassigned'}
                  </div>
                </div>
                <div>
                  <div className="text-xs font-medium text-slate-500 uppercase">Type</div>
                  <div className="mt-1 text-sm font-semibold text-slate-900">
                    {task.assignee}
                  </div>
                </div>
                <div>
                  <div className="text-xs font-medium text-slate-500 uppercase">Created</div>
                  <div className="mt-1 text-sm font-semibold text-slate-900">
                    {new Date(task.createdAt).toLocaleDateString()}
                  </div>
                </div>
              </div>
            </div>

            {/* Messages Thread */}
            <div className="bg-white rounded-lg border border-slate-200 p-6">
              <h2 className="font-semibold text-slate-900 mb-4">Thread</h2>

              <div className="space-y-4 mb-6 max-h-96 overflow-y-auto">
                {task.messages.length === 0 ? (
                  <div className="text-center text-slate-500 py-8">
                    No messages yet. Start the conversation.
                  </div>
                ) : (
                  task.messages.map(message => (
                    <div
                      key={message.id}
                      className={`p-4 rounded-lg border ${
                        message.author === 'agent'
                          ? 'bg-blue-50 border-blue-200'
                          : 'bg-slate-50 border-slate-200'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-semibold text-slate-900">
                          {message.author === 'agent' ? '🤖 Agent' : '👤 You'}
                        </span>
                        <span className="text-xs text-slate-500">
                          {new Date(message.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      <p className="text-slate-700">{message.content}</p>
                    </div>
                  ))
                )}
              </div>

              {/* New Message Form */}
              <form onSubmit={handleAddMessage} className="space-y-3 border-t border-slate-200 pt-4">
                <textarea
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  placeholder="Add a message or update on this task..."
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
                  rows={3}
                />
                <button
                  type="submit"
                  disabled={isSubmittingMessage || !newMessage.trim()}
                  className="px-4 py-2 bg-slate-900 text-white rounded-lg font-medium hover:bg-slate-800 disabled:bg-slate-400 transition-colors"
                >
                  {isSubmittingMessage ? 'Sending...' : 'Send Message'}
                </button>
              </form>
            </div>
          </div>

          {/* Sidebar - Context Blocks & Info */}
          <div className="space-y-6">
            {/* Tags */}
            {task.tags.length > 0 && (
              <div className="bg-white rounded-lg border border-slate-200 p-6">
                <h3 className="font-semibold text-slate-900 mb-3">Tags</h3>
                <div className="flex flex-wrap gap-2">
                  {task.tags.map(tag => (
                    <span key={tag} className="px-3 py-1 bg-slate-100 text-slate-700 rounded-full text-sm">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Context Blocks */}
            {contextBlocks.length > 0 && (
              <div className="bg-white rounded-lg border border-slate-200 p-6">
                <h3 className="font-semibold text-slate-900 mb-4">Context Blocks</h3>
                <div className="space-y-3">
                  {contextBlocks.map(block => (
                    <ContextBlockPreview key={block.id} block={block} />
                  ))}
                </div>
              </div>
            )}

            {/* Quick Stats */}
            <div className="bg-white rounded-lg border border-slate-200 p-6">
              <h3 className="font-semibold text-slate-900 mb-3">Stats</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-600">Messages</span>
                  <span className="font-semibold text-slate-900">{task.messages.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600">Context Blocks</span>
                  <span className="font-semibold text-slate-900">{contextBlocks.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600">Last Updated</span>
                  <span className="font-semibold text-slate-900">
                    {new Date(task.updatedAt).toRelativeTime?.() || 'recently'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
