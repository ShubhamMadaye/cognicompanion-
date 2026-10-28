import React, { useState } from 'react';
import { Database, ChevronDown, ChevronUp } from 'lucide-react';
import { GroundedSource } from '../../types';
import { SourceCard } from './SourceCard';

interface SourceListProps {
  sources?: GroundedSource[];
}

export const SourceList: React.FC<SourceListProps> = ({ sources = [] }) => {
  const [isOpen, setIsOpen] = useState<boolean>(true);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-3 pt-3 border-t border-slate-100/90 text-left">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-500 hover:text-slate-800 transition-colors cursor-pointer mb-2.5"
      >
        <Database className="w-3.5 h-3.5 text-teal-600" />
        <span>Grounded Evidence ({sources.length} source{sources.length > 1 ? 's' : ''})</span>
        {isOpen ? <ChevronUp className="w-3.5 h-3.5 ml-0.5" /> : <ChevronDown className="w-3.5 h-3.5 ml-0.5" />}
      </button>

      {isOpen && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {sources.map((src, idx) => (
            <SourceCard key={`${src.id}-${idx}`} source={src} />
          ))}
        </div>
      )}
    </div>
  );
};
