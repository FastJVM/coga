'use server';

import TaskBoard from '@/components/TaskBoard';
import { db } from '@/lib/db';

export default async function Home() {
  const tasks = db.tasks.getAll();
  
  return <TaskBoard initialTasks={tasks} />;
}
