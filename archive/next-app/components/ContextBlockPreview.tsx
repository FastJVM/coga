'use client';

import { ContextBlock } from '@/lib/types';
import { useState } from 'react';

interface ContextBlockPreviewProps {
  block: ContextBlock;
}

export default function ContextBlockPreview({ block }: ContextBlockPreviewProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="border border-slate-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 bg-slate-50 hover:bg-slate-100 flex items-center justify-between transition-colors"
      >
        <div className="text-left">
          <div className="font-semibold text-slate-900 text-sm">{block.name}</div>
          <div className="text-xs text-slate-500 mt-1">{block.category}</div>
        </div>
        <span className="text-slate-400">{isExpanded ? '▼' : '▶'}</span>
      </button>

      {isExpanded && (
        <div className="p-4 bg-white border-t border-slate-200 max-h-48 overflow-y-auto">
          <p className="text-xs text-slate-600 mb-2">{block.description}</p>
          <div className="bg-slate-50 p-3 rounded overflow-x-auto">
            <pre className="text-xs text-slate-700 font-mono whitespace-pre-wrap break-words">
              {block.content}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
