'use client';

import { User, Bot } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChatMessageProps {
  content: string;
  type: 'user' | 'bot';
  timestamp?: string;
}

export function ChatMessage({ content, type, timestamp }: ChatMessageProps) {
  const isUser = type === 'user';

  return (
    <div className={cn(
      'flex gap-4',
      isUser ? 'justify-end' : 'justify-start'
    )}>
      <div className={cn(
        'flex gap-4 max-w-3xl',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}>
        {/* Avatar */}
        <div className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
          isUser 
            ? 'bg-gradient-to-br from-blue-600 to-indigo-600' 
            : 'bg-gradient-to-br from-gray-500 to-gray-600'
        )}>
          {isUser ? (
            <User className="w-4 h-4 text-white" />
          ) : (
            <Bot className="w-4 h-4 text-white" />
          )}
        </div>
        
        {/* Message Content */}
        <div className={cn(
          'rounded-2xl px-4 py-3 shadow-sm max-w-full',
          isUser
            ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white'
            : 'bg-white text-gray-900 border border-gray-200'
        )}>
          <div className="text-sm leading-relaxed whitespace-pre-wrap">
            {content}
          </div>
          {timestamp && (
            <div className={cn(
              'text-xs mt-2',
              isUser ? 'text-blue-100' : 'text-gray-500'
            )}>
              {timestamp}
            </div>
          )}
        </div>
      </div>
    </div>
  );
} 