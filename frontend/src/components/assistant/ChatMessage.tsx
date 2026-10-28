import React from 'react';
import { User, Bot, Clock } from 'lucide-react';
import { ChatMessageItem } from '../../types';
import { ConfidenceBadge } from './ConfidenceBadge';
import { IntentBadge } from './IntentBadge';
import { SourceList } from './SourceList';

interface ChatMessageProps {
  message: ChatMessageItem;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end gap-3 items-start pl-8">
        <div className="flex flex-col items-end max-w-xl">
          <div className="flex items-center gap-1.5 text-[11px] text-slate-400 font-medium mb-1">
            <span>You</span>
            <Clock className="w-2.5 h-2.5" />
            <span>{message.timestamp.slice(11, 16)}</span>
          </div>
          <div className="p-3.5 rounded-2xl rounded-tr-xs bg-slate-900 text-white text-sm font-normal leading-relaxed shadow-xs">
            {message.content}
          </div>
        </div>
        <div className="w-8 h-8 rounded-xl bg-slate-200 border border-slate-300 flex items-center justify-center text-slate-700 shrink-0 mt-4 shadow-2xs">
          <User className="w-4 h-4 text-slate-600" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start gap-3 items-start pr-8">
      <div className="w-8 h-8 rounded-xl bg-teal-700 flex items-center justify-center text-white shrink-0 mt-4 shadow-sm border border-teal-800">
        <Bot className="w-4 h-4 text-white" />
      </div>

      <div className="flex flex-col items-start max-w-2xl w-full">
        <div className="flex items-center gap-2 mb-1.5 flex-wrap">
          <span className="text-xs font-bold text-slate-800">CogniCompanion Assistant</span>
          {message.intent && <IntentBadge intent={message.intent} />}
          {message.confidence && <ConfidenceBadge confidence={message.confidence} />}
          <span className="text-[10px] text-slate-400 ml-auto font-mono">
            {message.timestamp.slice(11, 16)}
          </span>
        </div>

        <div className="p-4 rounded-2xl rounded-tl-xs bg-white border border-slate-200 text-slate-800 text-sm leading-relaxed shadow-xs w-full space-y-3">
          <p className="whitespace-pre-wrap font-normal text-[13px] leading-relaxed text-slate-800">
            {message.content}
          </p>

          {message.sources && message.sources.length > 0 && (
            <SourceList sources={message.sources} />
          )}
        </div>
      </div>
    </div>
  );
};
