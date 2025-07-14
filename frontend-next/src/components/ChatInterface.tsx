'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, RefreshCw, Users, Activity, Database, Settings, LogOut, MessageSquare, Bot, FileText } from 'lucide-react';
import { ChatMessage } from './ChatMessage';
import { SqlQueryDisplay } from './SqlQueryDisplay';
import { ApprovalInterface } from './ApprovalInterface';
import { apiService } from './api';
import { useAuth } from '../contexts/AuthContext';
import { useRouter } from 'next/navigation';

interface Message {
  id: string;
  content: string;
  type: 'user' | 'bot';
  timestamp: string;
  query?: string;
  result?: string;
}

interface ApprovalData {
  question: string;
  resolved_question: string;
  query: string;
  state_hex: string;
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentStateHex, setCurrentStateHex] = useState<string | null>(null);
  const [currentApprovalData, setCurrentApprovalData] = useState<ApprovalData | null>(null);
  const [lastExecutedQuery, setLastExecutedQuery] = useState<{
    query: string;
    result: string;
    question: string;
    resolved_question: string;
  } | null>(null);
  const [showRegenerateOption, setShowRegenerateOption] = useState(false);
  const [showSidebar, setShowSidebar] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const { user, logout } = useAuth();
  const router = useRouter();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Focus input on mount
    inputRef.current?.focus();
  }, []);

  const addMessage = (content: string, type: 'user' | 'bot', query?: string, result?: string) => {
    const newMessage: Message = {
      id: Date.now().toString(),
      content,
      type,
      timestamp: new Date().toLocaleTimeString(),
      query,
      result,
    };
    setMessages(prev => [...prev, newMessage]);
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || !user || isLoading) return;

    const userInput = inputValue.trim();
    setInputValue('');
    addMessage(userInput, 'user');
    setIsLoading(true);

    try {
      const response = await apiService.sendQuery({
        username: user.username,
        question: userInput,
      });

      setIsLoading(false);

      if ('state_hex' in response) {
        // This is an ApprovalResponse - SQL query needs approval
        setCurrentStateHex(response.state_hex);
        setCurrentApprovalData({
          question: response.question,
          resolved_question: response.resolved_question,
          query: response.query,
          state_hex: response.state_hex,
        });
        addMessage(response.answer, 'bot');
      } else {
        // This is a QueryResponse - immediate chat response
        addMessage(response.answer, 'bot');
        if (response.query) {
          addMessage('', 'bot', response.query, response.result);
        }
      }
    } catch (error) {
      setIsLoading(false);
      console.error('API Error:', error);
      
      let errorMessage = "Connection failed. Please check: ";
      if (error instanceof Error) {
        if (error.message.includes('fetch')) {
          errorMessage += "• Is the API server running on http://localhost:8001? • Are there any CORS issues?";
        } else if (error.message.includes('HTTP')) {
          errorMessage += `• Server returned: ${error.message}`;
        } else {
          errorMessage += `• ${error.message}`;
        }
      }
      
      addMessage(errorMessage, 'bot');
    }
  };

  const handleApproveQuery = async (feedback?: string) => {
    if (!currentStateHex) return;

    setIsLoading(true);

    try {
      const response = await apiService.approveQuery({
        state_hex: currentStateHex,
        feedback: feedback || '',
      });

      setIsLoading(false);
      setCurrentStateHex(null);
      setCurrentApprovalData(null);
      addMessage(response.answer, 'bot');
      
      if (response.query) {
        addMessage('', 'bot', response.query, response.result);
        setLastExecutedQuery({
          query: response.query,
          result: response.result,
          question: response.question,
          resolved_question: response.resolved_question,
        });
        setShowRegenerateOption(true);
      }
    } catch (error) {
      setIsLoading(false);
      console.error('API Error:', error);
      addMessage("Error executing approved query.", 'bot');
    }
  };

  const handleRegenerateQuery = async (feedback: string) => {
    if (!currentStateHex) return;

    setIsLoading(true);

    try {
      const response = await apiService.regenerateQuery({
        state_hex: currentStateHex,
        feedback,
      });

      setIsLoading(false);
      setCurrentStateHex(response.state_hex);
      setCurrentApprovalData({
        question: response.question,
        resolved_question: response.resolved_question,
        query: response.query,
        state_hex: response.state_hex,
      });
    } catch (error) {
      setIsLoading(false);
      console.error('API Error:', error);
      addMessage("Error regenerating query.", 'bot');
    }
  };

  const handleMemoryCommand = async (command: string) => {
    if (!user) return;

    setIsLoading(true);

    try {
      const response = await apiService.handleMemoryCommand({
        username: user.username,
        command,
      });

      setIsLoading(false);

      if (response.success) {
        addMessage(response.message, 'bot');
        if (response.data) {
          addMessage(JSON.stringify(response.data, null, 2), 'bot');
        }
      } else {
        addMessage(response.message, 'bot');
      }
    } catch (error) {
      setIsLoading(false);
      console.error('API Error:', error);
      addMessage("Error executing memory command.", 'bot');
    }
  };

  const handleSystemCommand = async (command: string) => {
    setIsLoading(true);

    try {
      let response: unknown;
      let message = '';

      switch (command) {
        case '/health':
          response = await apiService.checkHealth();
          const healthResponse = response as import('./api').HealthResponse;
          const status = healthResponse.status === 'healthy' ? '✅ Healthy' : '❌ Unhealthy';
          const dbStatus = healthResponse.database_connected ? '✅ Connected' : '❌ Disconnected';
          const supabaseStatus = healthResponse.supabase_connected ? '✅ Connected' : '❌ Disconnected';
          message = `System Health: ${status}\nDatabase: ${dbStatus}\nSupabase: ${supabaseStatus}\nTimestamp: ${healthResponse.timestamp}`;
          break;

        case '/users':
          response = await apiService.getAllUsers();
          const usersResponse = response as import('./api').UsersResponse;
          if (usersResponse.success) {
            const usersList = usersResponse.users.join(', ');
            message = `Active Users (${usersResponse.total_users}): ${usersList}`;
          } else {
            message = "Error retrieving users.";
          }
          break;

        case '/schema':
          response = await apiService.getDatabaseSchema();
          if (response) {
            message = "Database Schema:\n" + JSON.stringify(response, null, 2);
          } else {
            message = "Error retrieving database schema.";
          }
          break;

        case '/clear':
          if (!user) break;
          if (confirm("Are you sure you want to clear your memory?")) {
            response = await apiService.clearUserMemory(user.username);
            const clearResponse = response as { success: boolean; message: string };
            if (clearResponse.success) {
              message = clearResponse.message;
            } else {
              message = "Error clearing memory.";
            }
          }
          break;

        default:
          message = `Unknown command: ${command}`;
      }

      setIsLoading(false);
      addMessage(message, 'bot');
    } catch (error) {
      setIsLoading(false);
      console.error('API Error:', error);
      addMessage("Error executing system command.", 'bot');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  return (
    <div className="h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <div className={`fixed inset-y-0 left-0 z-50 w-80 bg-white border-r border-gray-200 transform transition-transform duration-300 ease-in-out ${showSidebar ? 'translate-x-0' : '-translate-x-full'} lg:relative lg:translate-x-0 lg:z-auto`}>
        <div className="flex flex-col h-full">
          {/* Sidebar Header */}
          <div className="p-6 border-b border-gray-200">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-xl flex items-center justify-center">
                <Database className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-gray-900">SQL Agent</h1>
                <p className="text-sm text-gray-600">AI Database Assistant</p>
              </div>
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              {user?.username}
            </div>
          </div>

          {/* Sidebar Content */}
          <div className="flex-1 p-6 space-y-4">
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-3">Quick Commands</h3>
              <div className="space-y-2">
                <button
                  onClick={() => handleMemoryCommand('/history')}
                  className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  📚 Conversation History
                </button>
                <button
                  onClick={() => handleMemoryCommand('/entities')}
                  className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  🏷️ Known Entities
                </button>
                <button
                  onClick={() => handleMemoryCommand('/summary')}
                  className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  📝 Conversation Summary
                </button>
              </div>
            </div>

            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-3">System</h3>
              <div className="space-y-2">
                <button
                  onClick={() => handleSystemCommand('/health')}
                  className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  🏥 System Health
                </button>
                <button
                  onClick={() => handleSystemCommand('/users')}
                  className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  👥 Active Users
                </button>
                <button
                  onClick={() => handleSystemCommand('/schema')}
                  className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  📋 Database Schema
                </button>
                <button
                  onClick={() => handleSystemCommand('/clear')}
                  className="w-full text-left px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                >
                  🗑️ Clear Memory
                </button>
              </div>
            </div>
          </div>

          {/* Sidebar Footer */}
          <div className="p-6 border-t border-gray-200">
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <LogOut className="w-4 h-4" />
              Sign Out
            </button>
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setShowSidebar(!showSidebar)}
                className="lg:hidden p-2 text-gray-500 hover:text-gray-700 transition-colors"
              >
                <Settings className="w-5 h-5" />
              </button>
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
                  <Bot className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-lg font-semibold text-gray-900">Chat</h1>
                  <p className="text-sm text-gray-600">
                    {user ? `Logged in as ${user.username}` : 'Not logged in'}
                  </p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleSystemCommand('/health')}
                className="p-2 text-gray-500 hover:text-gray-700 transition-colors"
                title="Check system health"
              >
                <Activity className="w-5 h-5" />
              </button>
              <button
                onClick={() => handleSystemCommand('/users')}
                className="p-2 text-gray-500 hover:text-gray-700 transition-colors"
                title="Show all users"
              >
                <Users className="w-5 h-5" />
              </button>
              <button
                onClick={() => handleSystemCommand('/schema')}
                className="p-2 text-gray-500 hover:text-gray-700 transition-colors"
                title="Show database schema"
              >
                <FileText className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 && (
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-gradient-to-br from-blue-100 to-indigo-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <MessageSquare className="w-8 h-8 text-blue-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Welcome to SQL Agent
              </h3>
              <p className="text-gray-600 mb-6 max-w-md mx-auto">
                I&apos;m your AI-powered database assistant. Ask me questions about your data, and I&apos;ll help you generate SQL queries and analyze your database.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto">
                <div className="bg-white p-4 rounded-xl border border-gray-200">
                  <h4 className="font-medium text-gray-900 mb-2">💬 Natural Language</h4>
                  <p className="text-sm text-gray-600">Ask questions in plain English</p>
                </div>
                <div className="bg-white p-4 rounded-xl border border-gray-200">
                  <h4 className="font-medium text-gray-900 mb-2">🔒 Safe Execution</h4>
                  <p className="text-sm text-gray-600">Human approval for database changes</p>
                </div>
                <div className="bg-white p-4 rounded-xl border border-gray-200">
                  <h4 className="font-medium text-gray-900 mb-2">🧠 Smart Memory</h4>
                  <p className="text-sm text-gray-600">Remembers your conversation context</p>
                </div>
                <div className="bg-white p-4 rounded-xl border border-gray-200">
                  <h4 className="font-medium text-gray-900 mb-2">⚡ Quick Commands</h4>
                  <p className="text-sm text-gray-600">Use /history, /health, /users, /schema</p>
                </div>
              </div>
            </div>
          )}

          {messages.map((message) => (
            <div key={message.id}>
              <ChatMessage
                content={message.content}
                type={message.type}
                timestamp={message.timestamp}
              />
              {message.query && (
                <SqlQueryDisplay query={message.query} result={message.result} />
              )}
            </div>
          ))}

          {/* Approval Interface */}
          {currentStateHex && currentApprovalData && (
            <ApprovalInterface
              query={currentApprovalData.query}
              question={currentApprovalData.question}
              resolvedQuestion={currentApprovalData.resolved_question}
              onApprove={handleApproveQuery}
              onRegenerate={handleRegenerateQuery}
              onCancel={() => {
                setCurrentStateHex(null);
                setCurrentApprovalData(null);
              }}
            />
          )}

          {/* Regenerate Option */}
          {showRegenerateOption && lastExecutedQuery && (
            <div className="bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-3">
                <RefreshCw className="w-5 h-5 text-green-600" />
                <span className="font-medium text-green-800">Query Executed Successfully</span>
              </div>
              <p className="text-sm text-green-700 mb-3">
                You can regenerate this query with different parameters or ask a new question.
              </p>
              <button
                onClick={() => setShowRegenerateOption(false)}
                className="text-sm text-green-600 hover:text-green-700 font-medium"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Loading Indicator */}
          {isLoading && (
            <div className="flex items-center gap-3 text-gray-500">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-100 to-indigo-100 rounded-full flex items-center justify-center">
                <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
              </div>
              <span className="text-sm">AI is thinking...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="bg-white border-t border-gray-200 p-6">
          <div className="max-w-4xl mx-auto">
            <div className="flex gap-4">
              <div className="flex-1">
                <textarea
                  ref={inputRef}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask me anything about your database... (e.g., 'Show me all users', 'What are the top 10 products?', '/history', '/schema')"
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-gray-900 placeholder-gray-500"
                  rows={2}
                  disabled={isLoading}
                />
              </div>
              <button
                onClick={handleSendMessage}
                disabled={!inputValue.trim() || isLoading}
                className="px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl hover:from-blue-700 hover:to-indigo-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg flex items-center gap-2"
              >
                <Send className="w-4 h-4" />
                Send
              </button>
            </div>
            
            {/* Quick Commands */}
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                onClick={() => handleMemoryCommand('/history')}
                className="text-xs px-3 py-1 bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
              >
                /history
              </button>
              <button
                onClick={() => handleMemoryCommand('/entities')}
                className="text-xs px-3 py-1 bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
              >
                /entities
              </button>
              <button
                onClick={() => handleMemoryCommand('/summary')}
                className="text-xs px-3 py-1 bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
              >
                /summary
              </button>
              <button
                onClick={() => handleSystemCommand('/health')}
                className="text-xs px-3 py-1 bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
              >
                /health
              </button>
              <button
                onClick={() => handleSystemCommand('/schema')}
                className="text-xs px-3 py-1 bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
              >
                /schema
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 