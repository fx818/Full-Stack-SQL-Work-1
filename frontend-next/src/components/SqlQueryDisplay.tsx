'use client';

import { useState } from 'react';
import { Copy, Check, Database, BarChart3 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SqlQueryDisplayProps {
  query: string;
  result?: string;
  className?: string;
}

export function SqlQueryDisplay({ query, result, className }: SqlQueryDisplayProps) {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(query);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy query:', err);
    }
  };

  return (
    <div className={cn('space-y-4', className)}>
      {/* SQL Query Section */}
      <div className="bg-gray-900 rounded-xl overflow-hidden border border-gray-800">
        <div className="flex items-center justify-between px-4 py-3 bg-gray-800 border-b border-gray-700">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-medium text-gray-300">Generated SQL Query</span>
          </div>
          <button
            onClick={copyToClipboard}
            className="flex items-center gap-1 px-2 py-1 text-xs text-gray-400 hover:text-white transition-colors rounded"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                Copy
              </>
            )}
          </button>
        </div>
        <div className="p-4">
          <pre className="text-sm text-green-400 font-mono whitespace-pre-wrap overflow-x-auto leading-relaxed">
            {query}
          </pre>
        </div>
      </div>

      {/* Results Section */}
      {result && (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
          <div className="flex items-center gap-2 px-4 py-3 bg-gray-50 border-b border-gray-200">
            <BarChart3 className="w-4 h-4 text-indigo-600" />
            <span className="text-sm font-medium text-gray-700">Query Results</span>
          </div>
          <div className="p-4">
            <pre className="text-sm text-gray-800 font-mono whitespace-pre-wrap overflow-x-auto leading-relaxed">
              {result}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
} 