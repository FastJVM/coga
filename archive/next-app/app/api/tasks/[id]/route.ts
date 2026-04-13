import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';

export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    console.log(`[API] GET /api/tasks/${id}`);
    const task = db.tasks.getById(id);
    
    if (!task) {
      console.log(`[API] Task ${id} not found. Available tasks:`, Array.from(db.tasks.getAll().map(t => t.id)));
      return NextResponse.json({ error: 'Task not found' }, { status: 404 });
    }
    
    console.log(`[API] Found task: ${task.title}`);
    return NextResponse.json(task);
  } catch (error) {
    console.error('[API] GET task error:', error);
    return NextResponse.json({ error: 'Failed to fetch task' }, { status: 500 });
  }
}

export async function PATCH(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const body = await request.json();
    const task = db.tasks.update(id, body);

    if (!task) {
      return NextResponse.json({ error: 'Task not found' }, { status: 404 });
    }

    return NextResponse.json(task);
  } catch (error) {
    return NextResponse.json({ error: 'Failed to update task' }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const deleted = db.tasks.delete(id);

    if (!deleted) {
      return NextResponse.json({ error: 'Task not found' }, { status: 404 });
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to delete task' }, { status: 500 });
  }
}

export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const body = await request.json();

    // Add message to task
    if (body.action === 'add-message') {
      const message = db.tasks.addMessage(id, {
        author: body.author,
        content: body.content,
        attachedContextBlocks: body.attachedContextBlocks
      });

      if (!message) {
        return NextResponse.json({ error: 'Task not found' }, { status: 404 });
      }

      return NextResponse.json(message);
    }

    return NextResponse.json({ error: 'Invalid action' }, { status: 400 });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to process request' }, { status: 500 });
  }
}
