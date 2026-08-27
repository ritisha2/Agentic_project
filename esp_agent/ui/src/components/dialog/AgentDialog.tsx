'use client';

import React, { useState, useRef, useEffect } from 'react';
import { runAgentStreamQuery } from '@/lib/api';
import {
  MarkdownBlock,
  PlotlyChartBlock,
  StatusBannerBlock,
  AdvisoryActionCardBlock,
  PlotlyChartData,
} from './GenerativeUIBlocks';
import MessageComposer from '@/components/workspace/MessageComposer';
import {
  Bot,
  Maximize2,
  Minimize2,
  X,
  Sparkles,
  ChevronDown,
  ChevronUp,
  RotateCcw,
  Zap,
} from 'lucide-react';

export interface ChatMessage {
  id: string;
  sender: 'user' | 'agent';
  timestamp: string;
  textDelta?: string;
  statusMessage?: { stage: string; text: string };
  advisory?: any;
  chart?: PlotlyChartData;
}

export interface AgentDialogProps {
  assetId: string;
  onOpenEvidenceDrawer?: (runId: string) => void;
}

export default function AgentDialog({ assetId, onOpenEvidenceDrawer }: AgentDialogProps) {
  const [isOpen, setIsOpen] = useState(true);
  const [isExpanded, setIsExpanded] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (queryText: string) => {
    if (!queryText.trim() || loading) return;

    const userMsgId = `user-${Date.now()}`;
    const agentMsgId = `agent-${Date.now()}`;

    const newMessages: ChatMessage[] = [
      ...messages,
      {
        id: userMsgId,
        sender: 'user',
        textDelta: queryText,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
      {
        id: agentMsgId,
        sender: 'agent',
        textDelta: '',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ];

    setMessages(newMessages);
    setLoading(true);

    try {
      await runAgentStreamQuery(assetId, queryText, (event) => {
        setMessages((prev) =>
          prev.map((msg) => {
            if (msg.id !== agentMsgId) return msg;

            if (event.type === 'status') {
              return {
                ...msg,
                statusMessage: { stage: event.stage, text: event.message },
              };
            } else if (event.type === 'text_delta') {
              return {
                ...msg,
                textDelta: (msg.textDelta || '') + event.delta,
              };
            } else if (event.type === 'advisory') {
              return {
                ...msg,
                advisory: event.advisory,
              };
            } else if (event.type === 'generative_ui' && event.kind === 'plotly_chart') {
              return {
                ...msg,
                chart: event,
              };
            } else if (event.type === 'done') {
              return {
                ...msg,
                statusMessage: undefined,
              };
            }
            return msg;
          })
        );
      });
    } catch (err) {
      console.error('Agent dialog streaming error:', err);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === agentMsgId
            ? {
                ...msg,
                textDelta:
                  (msg.textDelta || '') +
                  '\n\n⚠️ *Connection Error: Unable to complete streaming response from Agent Jane.*',
                statusMessage: undefined,
              }
            : msg
        )
      );
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-50 flex items-center gap-2.5 px-4 py-3 bg-[#001f2a] text-white font-medium text-sm rounded-full shadow-2xl hover:bg-[#002f3e] transition-all transform hover:scale-105 active:scale-95 border border-sky-400/30"
      >
        <Sparkles className="w-4 h-4 text-sky-400 animate-pulse" />
        <span>Open Agent Jane</span>
        <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
      </button>
    );
  }

  return (
    <div
      className={`fixed bottom-5 right-5 z-40 flex flex-col bg-white/95 backdrop-blur-xl border border-gray-200/90 rounded-3xl shadow-2xl transition-all duration-300 ease-in-out overflow-hidden ${
        isExpanded ? 'w-[740px] h-[84vh]' : 'w-[480px] h-[600px]'
      }`}
    >
      {/* Header Bar */}
      <div className="px-4 py-3.5 bg-gradient-to-r from-[#001f2a] to-[#003447] text-white flex items-center justify-between border-b border-sky-900/40 shrink-0 select-none">
        <div className="flex items-center gap-2.5">
          <div className="relative p-1.5 bg-sky-500/20 rounded-xl border border-sky-400/30">
            <Bot className="w-4 h-4 text-sky-300" />
            <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-emerald-400 rounded-full ring-2 ring-[#001f2a]" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <h3 className="font-bold text-xs tracking-wide text-white font-sans">Agent Jane</h3>
              <span className="text-[10px] bg-sky-500/20 text-sky-300 px-2 py-0.2 rounded-full border border-sky-400/30 font-mono">
                APM Co-Pilot
              </span>
            </div>
            <p className="text-[10px] text-sky-200/70 font-mono">
              Asset: <span className="text-white font-semibold">{assetId}</span> // LangGraph Autonomous
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            title={isExpanded ? 'Collapse Dialog' : 'Expand Dialog'}
            className="p-1.5 hover:bg-white/10 rounded-lg transition-colors text-sky-200 hover:text-white"
          >
            {isExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
          <button
            onClick={() => setIsOpen(false)}
            title="Minimize Dialog"
            className="p-1.5 hover:bg-white/10 rounded-lg transition-colors text-sky-200 hover:text-white"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Conversation Stream */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50/40">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-gray-500 space-y-3">
            <div className="p-3 bg-sky-100/60 text-sky-700 rounded-2xl border border-sky-200/60">
              <Sparkles className="w-6 h-6" />
            </div>
            <div>
              <h4 className="font-semibold text-xs text-gray-800 uppercase tracking-wider mb-1">
                Autonomous APM Advisory Ready
              </h4>
              <p className="text-xs text-gray-500 max-w-xs leading-relaxed">
                Ask Agent Jane about gas interference, BEP deviation, or anomaly diagnostic reports for{' '}
                <span className="font-semibold text-gray-700">{assetId}</span>.
              </p>
            </div>

            {/* Quick Prompt Chips */}
            <div className="flex flex-col gap-1.5 w-full max-w-xs pt-2">
              <button
                onClick={() =>
                  handleSendMessage('Analyze motor temperature spikes and intake drawdown.')
                }
                className="px-3 py-2 bg-white hover:bg-sky-50 border border-gray-200 hover:border-sky-300 rounded-xl text-left text-xs text-gray-700 font-medium transition-colors flex items-center justify-between"
              >
                <span>Diagnose drawdown & motor temp</span>
                <Zap className="w-3.5 h-3.5 text-sky-600" />
              </button>
              <button
                onClick={() =>
                  handleSendMessage('Show me telemetry trend line and TDH head calculations.')
                }
                className="px-3 py-2 bg-white hover:bg-sky-50 border border-gray-200 hover:border-sky-300 rounded-xl text-left text-xs text-gray-700 font-medium transition-colors flex items-center justify-between"
              >
                <span>Plot telemetry trend curve</span>
                <Zap className="w-3.5 h-3.5 text-sky-600" />
              </button>
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
          >
            {msg.sender === 'user' ? (
              <div className="max-w-[85%] px-4 py-2.5 bg-[#001f2a] text-white text-xs font-medium rounded-2xl rounded-tr-xs shadow-xs">
                {msg.textDelta}
                <span className="block text-[9px] text-sky-200/60 text-right mt-1 font-mono">
                  {msg.timestamp}
                </span>
              </div>
            ) : (
              <div className="w-full max-w-[96%] flex gap-2.5">
                <div className="w-7 h-7 rounded-xl bg-gradient-to-br from-sky-500 to-[#001f2a] text-white flex items-center justify-center text-xs font-bold shrink-0 mt-0.5 shadow-xs">
                  J
                </div>
                <div className="flex-1 bg-white border border-gray-200/80 rounded-2xl rounded-tl-xs p-3.5 shadow-xs space-y-2 text-xs">
                  {/* Status Banner */}
                  {msg.statusMessage && (
                    <StatusBannerBlock
                      stage={msg.statusMessage.stage}
                      message={msg.textDelta ? 'Synthesizing report...' : msg.statusMessage.text}
                    />
                  )}

                  {/* Advisory Action Card */}
                  {msg.advisory?.recommended_action && (
                    <AdvisoryActionCardBlock
                      title={msg.advisory.recommended_action.action_title}
                      urgency={msg.advisory.recommended_action.urgency}
                      confidence={msg.advisory.confidence_score}
                      onOpenEvidence={
                        onOpenEvidenceDrawer
                          ? () => onOpenEvidenceDrawer(msg.advisory.advisory_id)
                          : undefined
                      }
                    />
                  )}

                  {/* Markdown Stream Content */}
                  {msg.textDelta && <MarkdownBlock content={msg.textDelta} />}

                  {/* Generative Plotly Chart */}
                  {msg.chart && <PlotlyChartBlock chartPayload={msg.chart} />}

                  <span className="block text-[9px] text-gray-400 font-mono text-right pt-1 border-t border-gray-100">
                    {msg.timestamp}
                  </span>
                </div>
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Composer */}
      <div className="p-3 bg-white border-t border-gray-200/80 shrink-0">
        <MessageComposer onSendMessage={handleSendMessage} isLoading={loading} />
      </div>
    </div>
  );
}
