'use client';

import { Task, TaskStatus } from '@/lib/types';
import TaskCard from './TaskCard';
import { useState } from 'react';
import NewTaskModal from './NewTaskModal';

interface TaskBoardProps {
  initialTasks: Task[];
}

const statusLabels: Record<TaskStatus, string> = {
  'open': 'Open',
  'in-progress': 'In Progress',
  'blocked': 'Blocked',
  'completed': 'Completed',
  'waiting': 'Waiting'
};

const statusOrder: TaskStatus[] = ['open', 'in-progress', 'blocked', 'waiting', 'completed'];

export default function TaskBoard({ initialTasks }: TaskBoardProps) {
  const [tasks, setTasks] = useState<Task[]>(initialTasks);
  const [isModalOpen, setIsModalOpen] = useState(false);

  console.log(`[TaskBoard] Rendered with ${tasks.length} tasks:`, tasks.map(t => `${t.id}:${t.title}`));

  const tasksByStatus = statusOrder.reduce((acc, status) => {
    acc[status] = tasks.filter(t => t.status === status);
    return acc;
  }, {} as Record<TaskStatus, Task[]>);

  const handleStatusChange = async (taskId: string, newStatus: TaskStatus) => {
    try {
      const response = await fetch(`/api/tasks/${taskId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      });
      
      if (response.ok) {
        const updatedTask = await response.json();
        setTasks(tasks.map(t => t.id === taskId ? updatedTask : t));
      }
    } catch (error) {
      console.error('Failed to update task status:', error);
    }
  };

  const handleTaskCreated = (newTask: Task) => {
    console.log('[TaskBoard] Task created:', newTask.id, newTask.title);
    setTasks([newTask, ...tasks]);
    setIsModalOpen(false);
  };

  const taskCounts = {
    total: tasks.length,
    active: tasks.filter(t => t.status !== 'completed').length,
    blockedCount: tasks.filter(t => t.status === 'blocked').length
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-slate-200 p-6 z-10">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-slate-900">Relay</h1>
              <p className="text-slate-600">A blackboard for humans and agents</p>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <div className="text-2xl font-bold text-slate-900">{taskCounts.total}</div>
                <div className="text-sm text-slate-600">{taskCounts.active} active</div>
              </div>
              {taskCounts.blockedCount > 0 && (
                <div className="px-3 py-2 bg-red-50 border border-red-200 rounded">
                  <div className="text-sm font-semibold text-red-700">{taskCounts.blockedCount}</div>
                  <div className="text-xs text-red-600">blocked</div>
                </div>
              )}
              <button
                onClick={() => setIsModalOpen(true)}
                className="px-4 py-2 bg-slate-900 text-white rounded-lg font-medium hover:bg-slate-800 transition-colors"
              >
                New Task
              </button>
            </div>
          </div>
        </div>

        {/* Kanban Board */}
        <div className="p-6">
          <div className="grid grid-cols-5 gap-6">
            {statusOrder.map(status => (
              <div key={status} className="flex flex-col">
                {/* Column Header */}
                <div className="mb-4">
                  <div className="flex items-center justify-between mb-2">
                    <h2 className="font-semibold text-slate-900">{statusLabels[status]}</h2>
                    <span className="text-xs font-medium text-slate-500 bg-slate-100 px-2 py-1 rounded">
                      {tasksByStatus[status].length}
                    </span>
                  </div>
                </div>

                {/* Tasks Column */}
                <div className="flex flex-col gap-3 flex-1">
                  {tasksByStatus[status].length === 0 ? (
                    <div className="text-center py-8 text-slate-400 text-sm">
                      No tasks
                    </div>
                  ) : (
                    tasksByStatus[status].map(task => (
                      <div
                        key={task.id}
                        onClick={(e) => {
                          e.preventDefault();
                          // Status change could be triggered here with a dropdown
                        }}
                      >
                        <TaskCard
                          task={task}
                          onStatusChange={handleStatusChange}
                        />
                      </div>
                    ))
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Modal */}
      {isModalOpen && (
        <NewTaskModal
          onClose={() => setIsModalOpen(false)}
          onTaskCreated={handleTaskCreated}
        />
      )}
    </div>
  );
}
