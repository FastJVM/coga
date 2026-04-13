import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';

export async function GET() {
  try {
    const tasks = db.tasks.getAll();
    return NextResponse.json(tasks);
  } catch (error) {
    return NextResponse.json({ error: 'Failed to fetch tasks' }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    const task = db.tasks.create({
      title: body.title,
      description: body.description,
      status: body.status || 'open',
      assignee: body.assignee || 'human',
      assignedTo: body.assignedTo,
      priority: body.priority || 'medium',
      contextBlocks: body.contextBlocks || [],
      createdBy: body.createdBy || 'you',
      tags: body.tags || [],
      dueDate: body.dueDate ? new Date(body.dueDate) : undefined,
      dependencies: body.dependencies || [],
      dependents: body.dependents || []
    });

    console.log(`[API] Created task: ${task.id} - ${task.title}`);
    return NextResponse.json(task, { status: 201 });
  } catch (error) {
    console.error('[API] POST task error:', error);
    return NextResponse.json({ error: 'Failed to create task' }, { status: 500 });
  }
}
