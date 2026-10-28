import React from 'react';
import {
  Gamepad2,
  TrendingUp,
  Pill,
  CalendarDays,
  Users,
  UserCheck,
  SunMedium,
  MessageSquare,
  Sparkles,
} from 'lucide-react';

interface IntentBadgeProps {
  intent: string;
  className?: string;
}

export const IntentBadge: React.FC<IntentBadgeProps> = ({ intent, className = '' }) => {
  const norm = (intent || '').toLowerCase();

  const config: Record<
    string,
    { label: string; icon: React.ComponentType<{ className?: string }>; bg: string; text: string; border: string }
  > = {
    game_progress: {
      label: 'GAME PROGRESS',
      icon: Gamepad2,
      bg: 'bg-purple-50',
      text: 'text-purple-800',
      border: 'border-purple-200/70',
    },
    cognitive_progress: {
      label: 'COGNITIVE PROGRESS / CPI',
      icon: TrendingUp,
      bg: 'bg-indigo-50',
      text: 'text-indigo-800',
      border: 'border-indigo-200/70',
    },
    medication_schedule: {
      label: 'MEDICATION SCHEDULE',
      icon: Pill,
      bg: 'bg-sky-50',
      text: 'text-sky-800',
      border: 'border-sky-200/70',
    },
    medication_adherence: {
      label: 'MEDICATION ADHERENCE',
      icon: Pill,
      bg: 'bg-teal-50',
      text: 'text-teal-800',
      border: 'border-teal-200/70',
    },
    event_lookup: {
      label: 'UPCOMING EVENTS',
      icon: CalendarDays,
      bg: 'bg-amber-50',
      text: 'text-amber-800',
      border: 'border-amber-200/70',
    },
    visit_recall: {
      label: 'VISIT RECALL',
      icon: Users,
      bg: 'bg-rose-50',
      text: 'text-rose-800',
      border: 'border-rose-200/70',
    },
    person_lookup: {
      label: 'PERSON LOOKUP',
      icon: UserCheck,
      bg: 'bg-cyan-50',
      text: 'text-cyan-800',
      border: 'border-cyan-200/70',
    },
    daily_routine: {
      label: 'DAILY ROUTINE',
      icon: SunMedium,
      bg: 'bg-orange-50',
      text: 'text-orange-800',
      border: 'border-orange-200/70',
    },
    general_conversation: {
      label: 'COMPANION CHAT',
      icon: MessageSquare,
      bg: 'bg-slate-100',
      text: 'text-slate-700',
      border: 'border-slate-200',
    },
  };

  const item = config[norm] || {
    label: norm.replace('_', ' ').toUpperCase(),
    icon: Sparkles,
    bg: 'bg-slate-50',
    text: 'text-slate-700',
    border: 'border-slate-200',
  };

  const Icon = item.icon;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[10px] font-bold tracking-wider uppercase border shadow-2xs ${item.bg} ${item.text} ${item.border} ${className}`}
    >
      <Icon className="w-3 h-3 shrink-0" />
      <span>{item.label}</span>
    </span>
  );
};
