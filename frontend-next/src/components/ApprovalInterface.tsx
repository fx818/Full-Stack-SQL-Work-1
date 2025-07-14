'use client';

import { useState } from 'react';
import { Check, X, RefreshCw, AlertTriangle } from 'lucide-react';
import { SqlQueryDisplay } from './SqlQueryDisplay';

interface ApprovalInterfaceProps {
  query: string;
  question: string;
  resolvedQuestion: string;
  onApprove: (feedback?: string) => void;
  onRegenerate: (feedback: string) => void;
  onCancel: () => void;
}

export function ApprovalInterface({
  query,
  question,
  resolvedQuestion,
  onApprove,
  onRegenerate,
  onCancel,
}: ApprovalInterfaceProps) {
  const [feedback, setFeedback] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleApprove = async () => {
    setIsLoading(true);
    try {
      await onApprove(feedback);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegenerate = async () => {
    setIsLoading(true);
    try {
      await onRegenerate(feedback);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-2xl p-6">
      <div className="flex items-start gap-3 mb-6">
        <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
          <AlertTriangle className="w-5 h-5 text-blue-600" />
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 mb-1">Query Approval Required</h3>
          <p className="text-sm text-gray-600">
            Please review the generated SQL query before execution. This ensures safe database operations.
          </p>
        </div>
      </div>

      {/* Question Context */}
      <div className="mb-6 p-4 bg-white rounded-xl border border-gray-200">
        <div className="space-y-3">
          <div>
            <p className="text-sm font-medium text-gray-700 mb-1">Original Question:</p>
            <p className="text-gray-900 font-medium">{question}</p>
          </div>
          {resolvedQuestion !== question && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-1">Resolved Question:</p>
              <p className="text-gray-900 font-medium">{resolvedQuestion}</p>
            </div>
          )}
        </div>
      </div>

      {/* SQL Query Display */}
      <SqlQueryDisplay query={query} className="mb-6" />

      {/* Feedback Input */}
      <div className="mb-6">
        <label htmlFor="feedback" className="block text-sm font-medium text-gray-700 mb-2">
          Feedback (optional)
        </label>
        <textarea
          id="feedback"
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          placeholder="Provide feedback to improve the query... (e.g., 'Add more specific filters', 'Include additional columns')"
          className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-gray-900 placeholder-gray-500"
          rows={3}
        />
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={handleApprove}
          disabled={isLoading}
          className="flex-1 flex items-center justify-center gap-2 bg-green-600 text-white px-4 py-3 rounded-xl hover:bg-green-700 focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
        >
          <Check className="w-4 h-4" />
          {isLoading ? 'Approving...' : 'Approve & Execute'}
        </button>

        <button
          onClick={handleRegenerate}
          disabled={isLoading || !feedback.trim()}
          className="flex-1 flex items-center justify-center gap-2 bg-blue-600 text-white px-4 py-3 rounded-xl hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
        >
          <RefreshCw className="w-4 h-4" />
          {isLoading ? 'Regenerating...' : 'Regenerate'}
        </button>

        <button
          onClick={onCancel}
          disabled={isLoading}
          className="flex items-center justify-center gap-2 bg-gray-600 text-white px-4 py-3 rounded-xl hover:bg-gray-700 focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
        >
          <X className="w-4 h-4" />
          Cancel
        </button>
      </div>

      {/* Help Text */}
      <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
        <p className="text-sm text-blue-800">
          <strong>Tip:</strong> You can provide feedback to improve the query, then regenerate it, or approve it as-is for execution.
        </p>
      </div>
    </div>
  );
} 