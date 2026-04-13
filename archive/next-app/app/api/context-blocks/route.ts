import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const category = searchParams.get('category');

    let blocks;
    if (category) {
      blocks = db.contextBlocks.getByCategory(category);
    } else {
      blocks = db.contextBlocks.getAll();
    }

    return NextResponse.json(blocks);
  } catch (error) {
    return NextResponse.json({ error: 'Failed to fetch context blocks' }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const block = db.contextBlocks.create({
      name: body.name,
      description: body.description,
      content: body.content,
      category: body.category,
      reusableAcross: body.reusableAcross || []
    });

    return NextResponse.json(block, { status: 201 });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to create context block' }, { status: 500 });
  }
}
