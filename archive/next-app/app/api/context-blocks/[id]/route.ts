import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';

export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const block = db.contextBlocks.getById(id);

    if (!block) {
      return NextResponse.json({ error: 'Context block not found' }, { status: 404 });
    }

    return NextResponse.json(block);
  } catch (error) {
    return NextResponse.json({ error: 'Failed to fetch context block' }, { status: 500 });
  }
}

export async function PATCH(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const body = await request.json();
    const block = db.contextBlocks.update(id, body);

    if (!block) {
      return NextResponse.json({ error: 'Context block not found' }, { status: 404 });
    }

    return NextResponse.json(block);
  } catch (error) {
    return NextResponse.json({ error: 'Failed to update context block' }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const deleted = db.contextBlocks.delete(id);

    if (!deleted) {
      return NextResponse.json({ error: 'Context block not found' }, { status: 404 });
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to delete context block' }, { status: 500 });
  }
}
