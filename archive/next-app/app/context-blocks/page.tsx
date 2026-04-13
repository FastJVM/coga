'use server';

import { db } from '@/lib/db';
import Link from 'next/link';

export default async function ContextBlocksPage() {
  const blocks = db.contextBlocks.getAll();

  const groupedByCategory = blocks.reduce((acc, block) => {
    if (!acc[block.category]) {
      acc[block.category] = [];
    }
    acc[block.category].push(block);
    return acc;
  }, {} as Record<string, typeof blocks>);

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="bg-white border-b border-slate-200 p-6">
          <Link href="/" className="text-sm text-slate-600 hover:text-slate-900 mb-4 inline-block">
            ← Back to board
          </Link>
          <h1 className="text-3xl font-bold text-slate-900">Context Blocks Library</h1>
          <p className="text-slate-600 mt-2">Reusable knowledge and process blocks for your team</p>
        </div>

        {/* Content */}
        <div className="p-6">
          {Object.entries(groupedByCategory).length === 0 ? (
            <div className="bg-white rounded-lg border border-slate-200 p-8 text-center">
              <p className="text-slate-600">No context blocks yet. Create your first one when setting up a task.</p>
            </div>
          ) : (
            <div className="space-y-8">
              {Object.entries(groupedByCategory).map(([category, categoryBlocks]) => (
                <div key={category}>
                  <h2 className="text-xl font-semibold text-slate-900 mb-4 capitalize">{category}</h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {categoryBlocks.map(block => (
                      <div key={block.id} className="bg-white rounded-lg border border-slate-200 p-6">
                        <h3 className="font-semibold text-slate-900 mb-2">{block.name}</h3>
                        <p className="text-sm text-slate-600 mb-3">{block.description}</p>
                        
                        <div className="bg-slate-50 p-3 rounded mb-4 max-h-32 overflow-y-auto">
                          <pre className="text-xs text-slate-700 font-mono whitespace-pre-wrap break-words">
                            {block.content.substring(0, 300)}
                            {block.content.length > 300 ? '...' : ''}
                          </pre>
                        </div>

                        {block.reusableAcross.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {block.reusableAcross.map(tag => (
                              <span key={tag} className="text-xs bg-slate-100 text-slate-700 px-2 py-1 rounded">
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
