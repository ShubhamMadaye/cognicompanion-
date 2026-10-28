import React, { useState, useEffect } from 'react';
import {
  MessageSquare,
  FileText,
  RotateCw,
  CheckCircle,
  User,
  Bot,
  ArrowDown,
  ShieldCheck,
  AlertCircle,
  Sparkles,
} from 'lucide-react';
import { usePatient } from '../context/PatientContext';
import { assistantApi } from '../api/assistant';
import { ConversationTurn } from '../types';
// NOTE: mockData is NOT imported. Assistant always uses live backend data.
import { ChatWindow } from '../components/assistant/ChatWindow';

export const Assistant: React.FC = () => {
  const { selectedPatient } = usePatient();
  const [activeTab, setActiveTab] = useState<'chat' | 'logs'>('chat');
  // Rule: initial state is empty — not mock data.
  const [conversations, setConversations] = useState<ConversationTurn[]>([]);
  const [isLoadingLogs, setIsLoadingLogs] = useState<boolean>(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const fetchConversations = async () => {
    if (!selectedPatient?.id) return;
    setIsLoadingLogs(true);
    setFetchError(null);
    try {
      const data = await assistantApi.listConversations(selectedPatient.id);
      setConversations(data);
    } catch (err) {
      setFetchError('Could not load conversation history. Check backend connection.');
    } finally {
      setIsLoadingLogs(false);
    }
  };

  useEffect(() => {
    fetchConversations();
  }, [selectedPatient?.id]);

  return (
    <div className="space-y-5 max-w-5xl">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-slate-900">AI Clinical Assistant</h2>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-teal-50 text-teal-800 border border-teal-200 flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-teal-600" />
              PME Grounded RAG
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Grounded intelligence for memories, routines, medications, game performance, and cognitive progress.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center bg-slate-100/80 p-1 rounded-xl border border-slate-200/70 shrink-0 self-start">
          <button
            onClick={() => setActiveTab('chat')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${activeTab === 'chat'
                ? 'bg-white text-slate-900 shadow-xs border border-slate-200/70 font-bold'
                : 'text-slate-600 hover:text-slate-900'
              }`}
          >
            <MessageSquare className="w-3.5 h-3.5 text-teal-700" />
            <span>Interactive Chatbot</span>
          </button>
          <button
            onClick={() => setActiveTab('logs')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${activeTab === 'logs'
                ? 'bg-white text-slate-900 shadow-xs border border-slate-200/70 font-bold'
                : 'text-slate-600 hover:text-slate-900'
              }`}
          >
            <FileText className="w-3.5 h-3.5 text-teal-700" />
            <span>Explainability & Audit Logs</span>
          </button>
        </div>
      </div>

      {/* Main Tab Content */}
      {activeTab === 'chat' ? (
        <ChatWindow />
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">
              Audit log of verified multi-turn interactions and source grounding
            </span>
            <button
              onClick={fetchConversations}
              disabled={isLoadingLogs}
              className="px-3 py-1.5 bg-white border border-slate-200 text-slate-700 rounded-xl shadow-2xs hover:bg-slate-50 transition-all flex items-center gap-1.5 text-xs font-semibold cursor-pointer"
            >
              <RotateCw className={`w-3.5 h-3.5 ${isLoadingLogs ? 'animate-spin' : ''}`} />
              <span>Refresh Logs</span>
            </button>
          </div>

          <div className="space-y-4">
            {conversations.map((turn) => {
              const confidencePct = Math.round(turn.confidence_score * 100);
              const hasSources = turn.sources && turn.sources.length > 0;

              return (
                <div
                  key={turn.id}
                  className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs space-y-3"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-teal-800 bg-teal-50 px-2.5 py-0.5 rounded border border-teal-200/60">
                        Intent: {turn.intent_type}
                      </span>
                      <span className="text-xs text-slate-400 font-medium">
                        {turn.timestamp.slice(0, 10)} at {turn.timestamp.slice(11, 16)} UTC
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-slate-600">Model Grounding:</span>
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center gap-1">
                        <CheckCircle className="w-3 h-3" />
                        {confidencePct}%
                      </span>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-start gap-3">
                      <div className="w-7 h-7 rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center text-xs font-bold text-slate-700 shrink-0 mt-0.5">
                        <User className="w-3.5 h-3.5 text-slate-600" />
                      </div>
                      <div className="flex-1">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Patient Query</span>
                        <div className="p-3 mt-1 rounded-xl bg-slate-50 border border-slate-200/70 text-xs font-semibold text-slate-900 leading-relaxed">
                          "{turn.patient_query}"
                        </div>
                      </div>
                    </div>

                    <div className="flex justify-center pl-4 text-slate-300">
                      <ArrowDown className="w-3.5 h-3.5" />
                    </div>

                    <div className="flex items-start gap-3">
                      <div className="w-7 h-7 rounded-xl bg-teal-700 flex items-center justify-center text-xs font-bold text-white shrink-0 mt-0.5 shadow-2xs">
                        <Bot className="w-3.5 h-3.5 text-white" />
                      </div>
                      <div className="flex-1">
                        <span className="text-[10px] font-bold text-teal-700 uppercase tracking-wider">Assistant Response</span>
                        <div className="p-3.5 mt-1 rounded-xl bg-teal-50/40 border border-teal-200/50 text-xs font-medium text-slate-900 leading-relaxed">
                          {turn.assistant_response}
                        </div>
                      </div>
                    </div>
                  </div>

                  {hasSources && (
                    <div className="pt-2 border-t border-slate-100">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">
                        Provenance Sources ({turn.sources.length})
                      </span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {turn.sources.map((src, idx) => (
                          <div
                            key={`${src.id}-${idx}`}
                            className="p-2.5 rounded-lg border border-slate-200/70 bg-slate-50/60 text-xs flex flex-col gap-1"
                          >
                            <div className="font-semibold text-slate-800 text-[11px] truncate">
                              {src.title}
                            </div>
                            {src.detail && (
                              <div className="text-[10px] text-slate-500 line-clamp-2">
                                {src.detail}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
