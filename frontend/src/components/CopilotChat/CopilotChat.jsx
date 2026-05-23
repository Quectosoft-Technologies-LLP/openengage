// src/components/CopilotChat/CopilotChat.jsx
import React, { useState, useRef, useEffect } from 'react';
import { useCopilot } from '../../hooks/useCopilot';
import ReactMarkdown from 'react-markdown';
import { Bot, User, Send, Loader2, Zap, X, Minimize2, Maximize2 } from 'lucide-react';
import clsx from 'clsx';

const AGENT_COLORS = {
  campaign_strategy:  'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
  lead_scoring:       'bg-violet-500/20 text-violet-300 border-violet-500/30',
  email_copywriter:   'bg-sky-500/20 text-sky-300 border-sky-500/30',
  segmentation:       'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  analytics_analyst:  'bg-amber-500/20 text-amber-300 border-amber-500/30',
};

const AGENT_LABELS = {
  campaign_strategy: '📋 Campaign Strategy',
  lead_scoring:      '⚡ Lead Scoring',
  email_copywriter:  '✉️ Email Copywriter',
  segmentation:      '🎯 Segmentation',
  analytics_analyst: '📊 Analytics Analyst',
};

const QUICK_PROMPTS = [
  "Create a nurture campaign for SaaS leads",
  "Write 3 subject lines for a demo invite",
  "Segment contacts who visited pricing page",
  "Explain why lead score dropped this week",
  "Analyze last campaign's open rate",
];

export default function CopilotChat({ sessionId = 'default', onClose }) {
  const { messages, isThinking, connected, send, clear } = useCopilot(sessionId);
  const [input, setInput] = useState('');
  const [minimized, setMinimized] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (!input.trim()) return;
    send(input.trim());
    setInput('');
  };

  return (
    <div className={clsx(
      'fixed bottom-6 right-6 z-50 flex flex-col rounded-2xl shadow-2xl border border-gray-700 bg-gray-950 transition-all duration-300',
      minimized ? 'w-72 h-14' : 'w-[440px] h-[620px]'
    )}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 bg-gray-900 rounded-t-2xl">
        <div className="flex items-center gap-2">
          <div className={clsx('w-2 h-2 rounded-full', connected ? 'bg-emerald-400 animate-pulse' : 'bg-red-400')} />
          <Bot className="w-4 h-4 text-brand-400" />
          <span className="text-sm font-semibold text-gray-100">OpenEngage Copilot</span>
        </div>
        <div className="flex items-center gap-1.5">
          <button onClick={() => setMinimized(m => !m)} className="p-1 hover:bg-gray-700 rounded-lg text-gray-400">
            {minimized ? <Maximize2 className="w-3.5 h-3.5" /> : <Minimize2 className="w-3.5 h-3.5" />}
          </button>
          {onClose && (
            <button onClick={onClose} className="p-1 hover:bg-gray-700 rounded-lg text-gray-400">
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {!minimized && (
        <>
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 && (
              <div className="text-center py-8">
                <Zap className="w-10 h-10 text-brand-500 mx-auto mb-3" />
                <p className="text-gray-400 text-sm mb-4">Ask me anything about your campaigns</p>
                <div className="space-y-2">
                  {QUICK_PROMPTS.map(p => (
                    <button key={p} onClick={() => send(p)}
                      className="block w-full text-left text-xs px-3 py-2 rounded-xl bg-gray-800/60 hover:bg-gray-800 text-gray-300 transition-all border border-gray-700/50">
                      {p}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map(msg => (
              <div key={msg.id} className={clsx('flex gap-3', msg.role === 'user' && 'flex-row-reverse')}>
                {/* Avatar */}
                <div className={clsx('flex-shrink-0 w-7 h-7 rounded-xl flex items-center justify-center text-xs',
                  msg.role === 'user' ? 'bg-brand-600' : 'bg-gray-700')}>
                  {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4 text-brand-300" />}
                </div>

                <div className={clsx('max-w-[85%] rounded-2xl px-4 py-3 text-sm',
                  msg.role === 'user'     && 'bg-brand-600/20 border border-brand-500/30 text-gray-100',
                  msg.role === 'assistant'&& 'bg-gray-800 border border-gray-700 text-gray-200',
                  msg.role === 'thinking' && 'bg-violet-900/20 border border-violet-700/30 text-violet-300 italic',
                )}>
                  {msg.role === 'thinking' && (
                    <div className="flex items-center gap-2 mb-1">
                      <Loader2 className="w-3 h-3 animate-spin" />
                      <span className="text-xs font-medium">Thinking...</span>
                    </div>
                  )}
                  {msg.agent && AGENT_LABELS[msg.agent] && (
                    <div className={clsx('badge border mb-2 text-xs', AGENT_COLORS[msg.agent])}>
                      {AGENT_LABELS[msg.agent]}
                    </div>
                  )}
                  <ReactMarkdown className="prose prose-invert prose-sm max-w-none">
                    {msg.content}
                  </ReactMarkdown>
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="p-3 border-t border-gray-800">
            <div className="flex items-end gap-2">
              <textarea
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }}}
                placeholder="Ask about campaigns, emails, leads..."
                rows={2}
                className="input flex-1 resize-none text-sm py-2"
              />
              <button onClick={handleSend} disabled={!input.trim() || !connected}
                className="btn-pri p-2.5 disabled:opacity-40 disabled:cursor-not-allowed">
                {isThinking ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              </button>
            </div>
            <button onClick={clear} className="text-xs text-gray-500 hover:text-gray-400 mt-1.5 transition-all">
              Clear conversation
            </button>
          </div>
        </>
      )}
    </div>
  );
}
