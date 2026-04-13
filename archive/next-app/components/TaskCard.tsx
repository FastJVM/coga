'use client';

import { Task, TaskStatus } from '@/lib/types';
import Link from 'next/link';

interface TaskCardProps {
  task: Task;
  onStatusChange: (taskId: string, status: TaskStatus) => void;
}

const statusColors: Record<TaskStatus, string> = {
  'open': 'bg-slate-100 text-slate-700',
  'in-progress': 'bg-blue-100 text-blue-700',
  'blocked': 'bg-red-100 text-red-700',
  'completed': 'bg-green-100 text-green-700',
  'waiting': 'bg-yellow-100 text-yellow-700'
};

const priorityColors: Record<string, string> = {
  'low': 'text-slate-500',
  'medium': 'text-blue-600',
  'high': 'text-orange-600',
  'critical': 'text-red-600'
};

export default function TaskCard({ task, onStatusChange }: TaskCardProps) {
  return (
    <Link href={`/tasks/${task.id}`}>
      <div className="bg-white rounded-lg border border-slate-200 p-4 hover:shadow-md transition-shadow cursor-pointer">
        <div className="flex items-start justify-between mb-2">
          <h3 className="font-semibold text-slate-900 flex-1">{task.title}</h3>
          <span className={`px-2 py-1 rounded text-xs font-medium ${statusColors[task.status]}`}>
            {task.status}
          </span>
        </div>

        <p className="text-sm text-slate-600 mb-3 line-clamp-2">{task.description}</p>

        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className={`text-xs font-medium ${priorityColors[task.priority]}`}>
              {task.priority.charAt(0).toUpperCase() + task.priority.slice(1)}
            </span>
            {task.assignedTo && (
              <span className="text-xs bg-slate-100 text-slate-700 px-2 py-1 rounded">
                {task.assignedTo}
              </span>
            )}
          </div>
        </div>

        {task.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-2">
            {task.tags.slice(0, 3).map(tag => (
              <span key={tag} className="text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded">
                {tag}
              </span>
            ))}
            {task.tags.length > 3 && (
              <span className="text-xs text-slate-500">+{task.tags.length - 3}</span>
            )}
          </div>
        )}

        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>{task.messages.length} messages</span>
          <span>{task.contextBlocks.length} context blocks</span>
        </div>
      </div>
    </Link>
  );
}
