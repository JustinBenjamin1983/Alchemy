/**
 * AIChatPanel - Collapsible panel for AI conversations about findings
 *
 * Features:
 * - Chat interface for asking questions about findings/DD
 * - Context-aware (shows current finding context)
 * - Message history with user/assistant roles
 * - Collapsible design for flexible workspace
 */

import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage, Finding } from './types';

// Icons
const SendIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
  </svg>
);

const BrainIcon = ({ className }: { className?: string }) => (
  <svg className={`w-5 h-5 ${className || ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
  </svg>
);

const UserIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
  </svg>
);

const ChevronDownIcon = ({ isOpen, className }: { isOpen: boolean; className?: string }) => (
  <svg className={`w-5 h-5 transition-transform ${isOpen ? 'rotate-180' : ''} ${className || ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
  </svg>
);

const DocumentIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

interface AIChatPanelProps {
  ddId: string;
  runId: string | null;
  selectedFinding?: Finding | null;
  messages: ChatMessage[];
  onSendMessage: (message: string, context?: { findingId?: string; documentId?: string }) => void;
  isLoading?: boolean;
  isExpanded: boolean;
  onToggleExpand: () => void;
}

// Suggested questions based on context
const SUGGESTED_QUESTIONS = {
  finding: [
    'Explain this finding in more detail',
    'What are the potential consequences?',
    'How does this compare to market standard?',
    'What should we ask the counterparty about this?'
  ],
  general: [
    'Summarise the key risks in this DD',
    'What are the deal-breakers identified?',
    'Are there any unusual clauses?',
    'What documents are we missing?'
  ]
};

// Message bubble component
const MessageBubble: React.FC<{ message: ChatMessage }> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
        isUser
          ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
          : 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400'
      }`}>
        {isUser ? <UserIcon /> : <BrainIcon />}
      </div>
      <div className={`flex-1 max-w-[80%] ${isUser ? 'text-right' : ''}`}>
        <div className={`inline-block px-4 py-2 rounded-lg ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100'
        }`}>
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        </div>
        {message.finding_id && (
          <div className={`mt-1 text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1 ${isUser ? 'justify-end' : ''}`}>
            <DocumentIcon />
            <span>Re: Finding</span>
          </div>
        )}
        <div className={`mt-1 text-xs text-gray-400 dark:text-gray-500 ${isUser ? 'text-right' : ''}`}>
          {new Date(message.timestamp).toLocaleTimeString('en-GB', {
            hour: '2-digit',
            minute: '2-digit'
          })}
        </div>
      </div>
    </div>
  );
};

export const AIChatPanel: React.FC<AIChatPanelProps> = ({
  ddId,
  runId,
  selectedFinding,
  messages,
  onSendMessage,
  isLoading = false,
  isExpanded,
  onToggleExpand
}) => {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    if (isExpanded) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isExpanded]);

  // Focus input when expanded
  useEffect(() => {
    if (isExpanded) {
      inputRef.current?.focus();
    }
  }, [isExpanded]);

  const handleSend = () => {
    if (!inputValue.trim() || isLoading) return;

    onSendMessage(inputValue, {
      findingId: selectedFinding?.id,
      documentId: selectedFinding?.document_id
    });
    setInputValue('');
  };

  const handleSuggestedQuestion = (question: string) => {
    onSendMessage(question, {
      findingId: selectedFinding?.id,
      documentId: selectedFinding?.document_id
    });
  };

  const suggestions = selectedFinding ? SUGGESTED_QUESTIONS.finding : SUGGESTED_QUESTIONS.general;

  return (
    <div className="bg-white dark:from-gray-900 border-t-2 border-gray-300 dark:border-gray-600 shadow-[0_-4px_12px_-4px_rgba(0,0,0,0.1)]">
      {/* Header - Always visible, clickable to expand/collapse */}
      <button
        onClick={onToggleExpand}
        className="w-full h-12 px-4 flex items-center justify-between bg-alchemyPrimaryNavyBlue hover:bg-alchemyPrimaryNavyBlue/90 transition-all duration-200 hover:shadow-lg"
      >
        <div className="flex items-center gap-2">
          <BrainIcon className="text-white" />
          <span className="font-medium text-white">Ask AI</span>
          {selectedFinding && (
            <span className="text-xs text-white/70 bg-white/20 px-2 py-0.5 rounded">
              Context: {selectedFinding.title.substring(0, 30)}...
            </span>
          )}
          {messages.length > 0 && (
            <span className="text-xs text-white bg-white/20 px-2 py-0.5 rounded">
              {messages.length} messages
            </span>
          )}
        </div>
        <ChevronDownIcon isOpen={isExpanded} className="text-white" />
      </button>

      {/* Expanded Content - Expands in place, adds height to container */}
      {isExpanded && (
        <div className="h-72 flex flex-col border-t border-gray-100 dark:border-gray-800">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
            {messages.length === 0 ? (
              <div className="text-center py-6">
                <BrainIcon />
                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                  Ask questions about this Due Diligence analysis
                </p>
                {/* Suggested questions */}
                <div className="mt-4 flex flex-wrap justify-center gap-2">
                  {suggestions.slice(0, 3).map((q, i) => (
                    <button
                      key={i}
                      onClick={() => handleSuggestedQuestion(q)}
                      className="px-3 py-1.5 text-xs bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition-all duration-200 hover:scale-105 hover:shadow-md border border-gray-200 dark:border-gray-700 shadow-sm"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {messages.map((msg) => (
                  <MessageBubble key={msg.id} message={msg} />
                ))}
                {isLoading && (
                  <div className="flex gap-3">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400">
                      <BrainIcon />
                    </div>
                    <div className="flex-1">
                      <div className="inline-block px-4 py-2 rounded-lg bg-gray-100 dark:bg-gray-800">
                        <div className="flex items-center gap-2">
                          <div className="flex gap-1">
                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                          </div>
                          <span className="text-xs text-gray-500 dark:text-gray-400">Thinking...</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* Input */}
          <div className="flex-shrink-0 px-4 py-3 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/30">
            <div className="flex items-center gap-2">
              <input
                ref={inputRef}
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder={selectedFinding
                  ? `Ask about "${selectedFinding.title.substring(0, 30)}..."`
                  : 'Ask a question about this DD...'
                }
                disabled={isLoading}
                className="flex-1 px-3 py-2 text-sm border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-alchemyPrimaryNavyBlue focus:border-transparent disabled:opacity-50"
              />
              <button
                onClick={handleSend}
                disabled={!inputValue.trim() || isLoading}
                className="flex items-center justify-center w-10 h-10 bg-alchemyPrimaryNavyBlue text-white rounded-lg hover:bg-alchemyPrimaryNavyBlue/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 hover:scale-105 hover:shadow-md"
              >
                <SendIcon />
              </button>
            </div>
            <div className="mt-2 flex items-center justify-between">
              <div className="flex flex-wrap gap-1">
                {suggestions.slice(0, 2).map((q, i) => (
                  <button
                    key={i}
                    onClick={() => handleSuggestedQuestion(q)}
                    disabled={isLoading}
                    className="px-2 py-1 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-all duration-200 hover:scale-105 disabled:opacity-50"
                  >
                    {q}
                  </button>
                ))}
              </div>
              <span className="text-xs text-gray-400 dark:text-gray-500">
                Powered by Claude
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
