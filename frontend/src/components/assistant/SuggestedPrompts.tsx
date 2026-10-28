import React from 'react';
import { Sparkles } from 'lucide-react';

interface SuggestedPromptsProps {
  onSelectPrompt: (prompt: string) => void;
  disabled?: boolean;
}

const PROMPTS = [
  {
    label: "Today's game performance",
    query: "How did I perform in today's games?",
    category: "GAMES",
  },
  {
    label: "Morning medications",
    query: "What medicines do I take in the morning?",
    category: "MEDS",
  },
  {
    label: "Cognitive CPI trend",
    query: "How is my cognitive progress and CPI trend?",
    category: "CPI",
  },
  {
    label: "Recent visitors",
    query: "Who visited me recently?",
    category: "VISIT",
  },
  {
    label: "Upcoming appointments",
    query: "What appointments do I have scheduled?",
    category: "EVENTS",
  },
  {
    label: "Today's routine",
    query: "What is on my schedule today?",
    category: "ROUTINE",
  },
];

export const SuggestedPrompts: React.FC<SuggestedPromptsProps> = ({
  onSelectPrompt,
  disabled = false,
}) => {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
        <Sparkles className="w-3.5 h-3.5 text-teal-600" />
        <span>Suggested Patient Inquiries</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {PROMPTS.map((p) => (
          <button
            key={p.label}
            onClick={() => onSelectPrompt(p.query)}
            disabled={disabled}
            className="px-3 py-1.5 rounded-xl text-xs font-medium bg-white hover:bg-teal-50/70 border border-slate-200 hover:border-teal-300 text-slate-700 hover:text-teal-900 transition-all shadow-2xs hover:shadow-xs disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer text-left flex items-center gap-2 group"
          >
            <span className="text-[10px] font-bold text-teal-700 bg-teal-50 px-1.5 py-0.5 rounded group-hover:bg-teal-100/80 transition-colors">
              {p.category}
            </span>
            <span>{p.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
};
