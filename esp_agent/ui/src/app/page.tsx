"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Database,
  FileText,
  GitCommit,
  Info,
  LineChart,
  MessageSquare,
  Plus,
  RefreshCw,
  Send,
  ShieldAlert,
  Sparkles,
  Terminal,
  Cpu,
  Layers,
} from "lucide-react";

interface DiagnosticResult {
  identified_fault: string;
  confidence_score: number;
  severity_level: string;
  evidence_list: string[];
  recommended_action: string;
}

interface Message {
  id: string;
  sender: "user" | "assistant";
  text: string;
  timestamp: string;
  result?: DiagnosticResult;
  isLoading?: boolean;
}

interface ChatSession {
  id: string;
  title: string;
  timestamp: string;
  severity: string;
  messages: Message[];
}

const SAMPLE_PROMPTS = [
  "ESP-Well-001 motor temperature is 142°C, what should I do?",
  "High radial vibration of 3.5 g on motor bearing",
  "PIP dropped to 120 psi, explain gas lock risk & mitigation",
  "Give me the chart and last 10 readings for motor temperature",
  "What safety precautions and tools are required for bearing replacement?",
  "Check overall health status of ESP-Well-001",
];

export default function Home() {
  const [assetId, setAssetId] = useState("ESP-Well-001");
  const [inputQuery, setInputQuery] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    checkHealth();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSubmitting]);

  const checkHealth = async () => {
    setBackendStatus("checking");
    try {
      const res = await fetch("http://localhost:8000/health");
      if (res.ok) {
        setBackendStatus("online");
      } else {
        setBackendStatus("offline");
      }
    } catch {
      setBackendStatus("offline");
    }
  };

  const startNewSession = () => {
    setMessages([]);
    setActiveSessionId(null);
    setInputQuery("");
  };

  const handleSend = async (queryText?: string) => {
    const textToSend = queryText || inputQuery;
    if (!textToSend.trim() || isSubmitting) return;

    const userMsgId = Date.now().toString();
    const userMessage: Message = {
      id: userMsgId,
      sender: "user",
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    const loadingMsgId = (Date.now() + 1).toString();
    const loadingMessage: Message = {
      id: loadingMsgId,
      sender: "assistant",
      text: "Analyzing telemetry metrics, checking rule thresholds, querying graph topology, and searching manuals...",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      isLoading: true,
    };

    setMessages((prev) => [...prev, userMessage, loadingMessage]);
    if (!queryText) setInputQuery("");
    setIsSubmitting(true);

    try {
      const response = await fetch("http://localhost:8000/diagnose", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_query: textToSend,
          asset_id: assetId,
          kb_id: "esp",
        }),
      });

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const data = await response.json();
      const diagResult: DiagnosticResult = data.result;

      const assistantMessage: Message = {
        id: loadingMsgId,
        sender: "assistant",
        text: diagResult.identified_fault,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        result: diagResult,
        isLoading: false,
      };

      setMessages((prev) => prev.map((m) => (m.id === loadingMsgId ? assistantMessage : m)));

      // Save to sessions history
      const newSession: ChatSession = {
        id: userMsgId,
        title: textToSend.length > 35 ? textToSend.slice(0, 35) + "..." : textToSend,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        severity: diagResult.severity_level,
        messages: [...messages, userMessage, assistantMessage],
      };
      setSessions((prev) => [newSession, ...prev.filter((s) => s.id !== newSession.id)]);
      setActiveSessionId(newSession.id);
    } catch (err: any) {
      const errorMessage: Message = {
        id: loadingMsgId,
        sender: "assistant",
        text: `Error connecting to backend API (http://localhost:8000). ${err.message || ""}`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        isLoading: false,
      };
      setMessages((prev) => prev.map((m) => (m.id === loadingMsgId ? errorMessage : m)));
    } finally {
      setIsSubmitting(false);
    }
  };

  const renderSeverityBadge = (severity: string) => {
    switch (severity.toLowerCase()) {
      case "critical":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800 border border-red-200">
            <ShieldAlert className="w-3.5 h-3.5 text-red-600" /> CRITICAL
          </span>
        );
      case "warning":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-600" /> WARNING
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> NORMAL
          </span>
        );
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50 text-gray-900 overflow-hidden">
      {/* Top Header */}
      <header className="h-16 bg-white border-b border-gray-200 px-6 flex items-center justify-between z-10 shadow-xs">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold shadow-xs">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-semibold text-gray-900 text-base leading-tight">ESP Diagnostic Assistant</h1>
            <p className="text-xs text-gray-500 flex items-center gap-1.5">
              <span>Domain: Electric Submersible Pump</span>
              <span className="w-1 h-1 rounded-full bg-gray-300"></span>
              <span className="font-mono text-indigo-600 bg-indigo-50 px-1.5 py-0.2 rounded text-[10px]">ESP_PUMPS</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Asset Selector */}
          <div className="flex items-center gap-2 bg-gray-100 px-3 py-1.5 rounded-md border border-gray-200 text-xs">
            <span className="text-gray-500 font-medium">Asset:</span>
            <select
              value={assetId}
              onChange={(e) => setAssetId(e.target.value)}
              className="bg-transparent font-semibold text-gray-800 focus:outline-none cursor-pointer"
            >
              <option value="ESP-Well-001">ESP-Well-001</option>
              <option value="ESP-Well-002">ESP-Well-002</option>
            </select>
          </div>

          {/* Backend Health Badge */}
          <div className="flex items-center gap-2">
            {backendStatus === "online" ? (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> Backend Connected
              </span>
            ) : (
              <button
                onClick={checkHealth}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-red-50 text-red-700 border border-red-200 hover:bg-red-100 transition-colors cursor-pointer"
              >
                <span className="w-2 h-2 rounded-full bg-red-500"></span> Backend Offline (Retry)
              </button>
            )}
          </div>

          {/* LLM Engine Badge */}
          <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-purple-50 text-purple-700 border border-purple-200">
            <Cpu className="w-3.5 h-3.5 text-purple-600" /> Phi-3 Mini (Local)
          </div>
        </div>
      </header>

      {/* Main Layout Area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar */}
        <aside className="w-72 bg-white border-r border-gray-200 flex flex-col justify-between hidden md:flex">
          <div className="p-4 space-y-4 overflow-y-auto">
            <button
              onClick={startNewSession}
              className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2.5 px-4 rounded-lg transition-colors text-sm shadow-xs cursor-pointer"
            >
              <Plus className="w-4 h-4" /> New Diagnosis Chat
            </button>

            {/* Quick Suggestions Section */}
            <div>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2.5 px-1 flex items-center justify-between">
                <span>Sample Prompts</span>
                <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
              </h3>
              <div className="space-y-1.5">
                {SAMPLE_PROMPTS.map((prompt, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(prompt)}
                    className="w-full text-left p-2 rounded-md hover:bg-gray-100 text-xs text-gray-700 transition-colors border border-transparent hover:border-gray-200 leading-snug cursor-pointer line-clamp-2"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>

            {/* History Sessions */}
            {sessions.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2.5 px-1">Recent Sessions</h3>
                <div className="space-y-1">
                  {sessions.map((sess) => (
                    <button
                      key={sess.id}
                      onClick={() => {
                        setMessages(sess.messages);
                        setActiveSessionId(sess.id);
                      }}
                      className={`w-full text-left p-2 rounded-md text-xs transition-colors flex items-center justify-between cursor-pointer ${
                        activeSessionId === sess.id
                          ? "bg-indigo-50 text-indigo-900 font-medium border border-indigo-200"
                          : "hover:bg-gray-100 text-gray-700"
                      }`}
                    >
                      <span className="truncate pr-2">{sess.title}</span>
                      <span className="text-[10px] text-gray-400 shrink-0">{sess.timestamp}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Footer Info */}
          <div className="p-4 border-t border-gray-200 bg-gray-50/50 text-[11px] text-gray-500 space-y-1">
            <p className="font-semibold text-gray-700">Domain-Agnostic Engine</p>
            <p>LangGraph • Pydantic v2 • Ollama Phi-3 Mini • FastAPI</p>
          </div>
        </aside>

        {/* Main Chat Area */}
        <main className="flex-1 flex flex-col bg-gray-50 overflow-hidden">
          {/* Chat Messages Scroll */}
          <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
            {messages.length === 0 ? (
              <div className="max-w-2xl mx-auto my-12 text-center space-y-6">
                <div className="w-16 h-16 bg-white border border-gray-200 rounded-2xl flex items-center justify-center mx-auto shadow-xs text-indigo-600">
                  <Activity className="w-8 h-8" />
                </div>
                <div className="space-y-2">
                  <h2 className="text-2xl font-bold text-gray-900">How can I assist with ESP Diagnosis?</h2>
                  <p className="text-sm text-gray-500 max-w-md mx-auto">
                    Ask questions about sensor telemetry, threshold breaches, component relationships, operating manuals, or charts.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-4 text-left">
                  {SAMPLE_PROMPTS.slice(0, 4).map((prompt, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSend(prompt)}
                      className="p-3.5 bg-white border border-gray-200 rounded-xl hover:border-indigo-300 hover:shadow-sm transition-all text-xs text-gray-700 font-medium flex items-center justify-between cursor-pointer group"
                    >
                      <span>{prompt}</span>
                      <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-indigo-600 transition-colors shrink-0 ml-2" />
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg) => (
                <div key={msg.id} className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"}`}>
                  {msg.sender === "user" ? (
                    <div className="bg-indigo-600 text-white rounded-2xl rounded-tr-xs px-4 py-3 max-w-xl text-sm shadow-xs">
                      <p>{msg.text}</p>
                      <p className="text-[10px] text-indigo-200 text-right mt-1">{msg.timestamp}</p>
                    </div>
                  ) : (
                    <div className="w-full max-w-3xl space-y-3">
                      {msg.isLoading ? (
                        <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-xs flex items-center gap-3">
                          <RefreshCw className="w-5 h-5 text-indigo-600 animate-spin" />
                          <span className="text-xs text-gray-600 font-medium">{msg.text}</span>
                        </div>
                      ) : msg.result ? (
                        /* Diagnostic Result Card */
                        <div className="bg-white border border-gray-200 rounded-2xl p-5 shadow-xs space-y-4">
                          {/* Card Header */}
                          <div className="flex items-start justify-between pb-3 border-b border-gray-100">
                            <div>
                              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">Identified Diagnosis</p>
                              <h3 className="text-xl font-bold text-gray-900">{msg.result.identified_fault}</h3>
                            </div>
                            <div>{renderSeverityBadge(msg.result.severity_level)}</div>
                          </div>

                          {/* Confidence Score Bar */}
                          <div className="space-y-1">
                            <div className="flex justify-between text-xs font-medium">
                              <span className="text-gray-500">Diagnostic Confidence</span>
                              <span className="text-gray-900 font-semibold">{Math.round(msg.result.confidence_score * 100)}%</span>
                            </div>
                            <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-indigo-600 rounded-full transition-all duration-500"
                                style={{ width: `${msg.result.confidence_score * 100}%` }}
                              ></div>
                            </div>
                          </div>

                          {/* Recommended Action Alert */}
                          <div className="bg-amber-50 border border-amber-200 rounded-xl p-3.5 text-xs text-amber-900 flex items-start gap-2.5">
                            <Info className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                            <div>
                              <span className="font-bold text-amber-950">Recommended Action: </span>
                              {msg.result.recommended_action}
                            </div>
                          </div>

                          {/* Local LLM Synthesis Quote */}
                          {msg.result.evidence_list.find((e) => e.includes("Local LLM")) && (
                            <div className="bg-purple-50 border border-purple-100 rounded-xl p-3.5 text-xs text-purple-900 space-y-1">
                              <div className="flex items-center gap-1.5 font-bold text-purple-950">
                                <Sparkles className="w-3.5 h-3.5 text-purple-600" /> Expert LLM Synthesis (Phi-3 Mini)
                              </div>
                              <p className="italic leading-relaxed text-purple-950">
                                {msg.result.evidence_list.find((e) => e.includes("Local LLM"))?.split(":", 2)[1]}
                              </p>
                            </div>
                          )}

                          {/* Terminal Visualization Chart Render */}
                          {msg.result.evidence_list.find((e) => e.includes("Terminal Visualization:")) && (
                            <div className="bg-gray-900 text-emerald-400 rounded-xl p-4 font-mono text-xs overflow-x-auto shadow-inner">
                              <div className="flex items-center gap-2 border-b border-gray-800 pb-2 mb-2 text-gray-400">
                                <Terminal className="w-4 h-4 text-emerald-500" /> Telemetry Bar Chart
                              </div>
                              <pre className="whitespace-pre">
                                {msg.result.evidence_list.find((e) => e.includes("Terminal Visualization:"))}
                              </pre>
                            </div>
                          )}

                          {/* Supporting Evidence List */}
                          <div className="space-y-2 pt-2 border-t border-gray-100">
                            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Supporting Evidence & Citations</h4>
                            <div className="space-y-1.5">
                              {msg.result.evidence_list
                                .filter((e) => !e.includes("Local LLM") && !e.includes("Terminal Visualization:"))
                                .map((ev, idx) => (
                                  <div key={idx} className="text-xs text-gray-700 bg-gray-50 p-2.5 rounded-lg border border-gray-100 flex items-start gap-2">
                                    {ev.includes("Rule Violation") ? (
                                      <ShieldAlert className="w-3.5 h-3.5 text-red-500 shrink-0 mt-0.5" />
                                    ) : ev.includes("Graph Fact") ? (
                                      <GitCommit className="w-3.5 h-3.5 text-indigo-500 shrink-0 mt-0.5" />
                                    ) : (
                                      <FileText className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                                    )}
                                    <span className="leading-snug">{ev}</span>
                                  </div>
                                ))}
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="bg-white border border-gray-200 rounded-xl p-4 text-xs text-red-600">{msg.text}</div>
                      )}
                    </div>
                  )}
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Bottom Chat Input Form */}
          <div className="p-4 bg-white border-t border-gray-200">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="max-w-4xl mx-auto flex items-center gap-2 bg-gray-100 p-1.5 rounded-xl border border-gray-300 focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-100 transition-all"
            >
              <input
                type="text"
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                placeholder="Ask about ESP temperature, vibration, intake pressure, charts, or SOPs..."
                disabled={isSubmitting}
                className="flex-1 bg-transparent px-3 py-2 text-sm focus:outline-none text-gray-900 placeholder-gray-400"
              />
              <button
                type="submit"
                disabled={!inputQuery.trim() || isSubmitting}
                className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 text-white p-2.5 rounded-lg transition-colors cursor-pointer disabled:cursor-not-allowed"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
            <p className="text-[10px] text-gray-400 text-center mt-2">
              Powered by LangGraph Agent Runtime • Universal Adapters • Local Ollama Phi-3 Mini Engine
            </p>
          </div>
        </main>
      </div>
    </div>
  );
}
