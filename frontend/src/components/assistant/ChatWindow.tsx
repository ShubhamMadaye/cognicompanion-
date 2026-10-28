import React, { useState, useRef, useEffect } from 'react';
import { PlusCircle, Sparkles, Bot, AlertCircle } from 'lucide-react';
import { usePatient } from '../../context/PatientContext';
import { assistantApi } from '../../api/assistant';
import { ChatMessageItem } from '../../types';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { SuggestedPrompts } from './SuggestedPrompts';

export const ChatWindow: React.FC = () => {
  const { selectedPatient } = usePatient();
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize with greeting
  useEffect(() => {
    if (selectedPatient) {
      setMessages([
        {
          id: 'initial-greeting',
          role: 'assistant',
          content: `Namaste! I am CogniCompanion, assisting with ${selectedPatient.full_name}'s memories, routines, medications, game sessions, and cognitive progress. How can I help you today?`,
          intent: 'general_conversation',
          confidence: { score: 1.0, level: 'HIGH' },
          timestamp: new Date().toISOString(),
        },
      ]);
      setConversationId(undefined);
    }
  }, [selectedPatient?.id]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSendMessage = async (query: string) => {
    if (!selectedPatient?.id || isLoading) return;

    const userTurnId = `user-${Date.now()}`;
    const userMsg: ChatMessageItem = {
      id: userTurnId,
      role: 'user',
      content: query,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);
    setError(null);

    try {
      const resp = await assistantApi.sendMessage(
        selectedPatient.id,
        query,
        conversationId,
        selectedPatient.preferred_language || 'en'
      );

      if (resp.conversation_id) {
        setConversationId(resp.conversation_id);
      }

      const asstMsg: ChatMessageItem = {
        id: `asst-${Date.now()}`,
        role: 'assistant',
        content: resp.answer || resp.reply,
        intent: resp.intent,
        confidence: resp.confidence_info || (typeof resp.confidence === 'object' ? resp.confidence : { score: resp.confidence, level: 'HIGH' }),
        sources: resp.sources,
        timestamp: resp.created_at || new Date().toISOString(),
      };

      setMessages((prev) => [...prev, asstMsg]);
    } catch (err: any) {
      setError(err?.message || 'Failed to reach the assistant. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStartNewChat = () => {
    setConversationId(undefined);
    setMessages([
      {
        id: `new-session-${Date.now()}`,
        role: 'assistant',
        content: `Started a fresh conversation session for ${selectedPatient?.full_name || 'the patient'}. Feel free to ask about any memories, game performance, or medications.`,
        intent: 'general_conversation',
        confidence: { score: 1.0, level: 'HIGH' },
        timestamp: new Date().toISOString(),
      },
    ]);
  };

  return (
    <div className="bg-slate-50/70 rounded-2xl border border-slate-200/90 flex flex-col h-[740px] shadow-sm overflow-hidden">
      {/* Chat Window Header */}
      <div className="h-16 px-6 bg-white border-b border-slate-200/80 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-teal-700 flex items-center justify-center text-white shadow-xs">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-sm text-slate-900 leading-tight">
                CogniCompanion Assistant
              </h3>
              <span className="text-[10px] font-bold text-teal-800 bg-teal-50 px-2 py-0.5 rounded border border-teal-200/60">
                PME Grounded
              </span>
            </div>
            <p className="text-[11px] text-slate-500 font-medium">
              Inquiring on behalf of <strong className="text-slate-700">{selectedPatient?.full_name}</strong>
            </p>
          </div>
        </div>

        <button
          onClick={handleStartNewChat}
          className="px-3.5 py-1.5 rounded-xl border border-slate-200 hover:border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center gap-1.5 transition-all shadow-2xs cursor-pointer"
          title="Start fresh conversation"
        >
          <PlusCircle className="w-3.5 h-3.5 text-teal-700" />
          <span>New Session</span>
        </button>
      </div>

      {/* Message Stream */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}

        {isLoading && (
          <div className="flex justify-start gap-3 items-start pr-8 animate-pulse">
            <div className="w-8 h-8 rounded-xl bg-teal-700 flex items-center justify-center text-white shrink-0 mt-4 shadow-sm">
              <Bot className="w-4 h-4 text-white" />
            </div>
            <div className="p-4 rounded-2xl rounded-tl-xs bg-white border border-slate-200 text-slate-500 text-xs shadow-xs flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-teal-600 animate-spin" />
              <span>Checking grounded patient evidence & synthesizing compassionate reply...</span>
            </div>
          </div>
        )}

        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Bottom Controls */}
      <div className="p-4 bg-white border-t border-slate-200/80 space-y-3 shrink-0">
        <SuggestedPrompts onSelectPrompt={handleSendMessage} disabled={isLoading} />
        <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
      </div>
    </div>
  );
};
