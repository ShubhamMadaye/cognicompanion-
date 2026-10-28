import React from 'react';
import { Gamepad2, Pill, Image as ImageIcon, CalendarDays, Brain, User, Clock, CheckCircle2 } from 'lucide-react';
import { GroundedSource } from '../../types';

interface SourceCardProps {
  source: GroundedSource;
}

export const SourceCard: React.FC<SourceCardProps> = ({ source }) => {
  const type = (source.source_type || '').toLowerCase();

  const getBadge = () => {
    switch (type) {
      case 'game_session':
        return {
          icon: Gamepad2,
          tag: 'GAME',
          color: 'text-purple-700 bg-purple-50 border-purple-200',
        };
      case 'cognitive_metric':
      case 'daily_statistic':
        return {
          icon: Brain,
          tag: 'CPI TELEMETRY',
          color: 'text-indigo-700 bg-indigo-50 border-indigo-200',
        };
      case 'medication':
        return {
          icon: Pill,
          tag: 'MEDICATION',
          color: 'text-teal-700 bg-teal-50 border-teal-200',
        };
      case 'event':
        return {
          icon: CalendarDays,
          tag: 'EVENT',
          color: 'text-amber-700 bg-amber-50 border-amber-200',
        };
      case 'person':
        return {
          icon: User,
          tag: 'PERSON',
          color: 'text-cyan-700 bg-cyan-50 border-cyan-200',
        };
      case 'memory':
      default:
        return {
          icon: ImageIcon,
          tag: 'MEMORY',
          color: 'text-rose-700 bg-rose-50 border-rose-200',
        };
    }
  };

  const badge = getBadge();
  const Icon = badge.icon;

  return (
    <div className="bg-white rounded-xl border border-slate-200/90 p-3 shadow-2xs hover:shadow-xs hover:border-slate-300 transition-all flex flex-col gap-1.5 text-left">
      <div className="flex items-center justify-between gap-2">
        <span
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[9px] font-bold tracking-wider uppercase border ${badge.color}`}
        >
          <Icon className="w-2.5 h-2.5 shrink-0" />
          <span>{badge.tag}</span>
        </span>
        {source.date && (
          <span className="text-[10px] text-slate-400 font-medium flex items-center gap-1">
            <Clock className="w-2.5 h-2.5" />
            {source.date}
          </span>
        )}
      </div>

      <div className="font-semibold text-xs text-slate-900 leading-snug truncate" title={source.title}>
        {source.title}
      </div>

      {source.summary && (
        <p className="text-[11px] text-slate-500 leading-relaxed line-clamp-2">
          {source.summary}
        </p>
      )}

      {source.details && (
        <div className="text-[10px] text-slate-600 bg-slate-50 rounded px-2 py-1 border border-slate-100 font-medium">
          {source.details}
        </div>
      )}
    </div>
  );
};
