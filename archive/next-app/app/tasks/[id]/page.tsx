'use client';

import TaskDetail from '@/components/TaskDetail';
import { use } from 'react';

export default function TaskPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <TaskDetail taskId={id} />;
}
