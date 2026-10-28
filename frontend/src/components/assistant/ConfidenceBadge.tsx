import React from 'react';
import { CheckCircle2, AlertTriangle, HelpCircle, ShieldCheck } from 'lucide-react';
import { ConfidenceInfo } from '../../types';

interface ConfidenceBadgeProps {
  confidence?: ConfidenceInfo | number;
  className?: string;
  showPercent?: boolean;
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({
  confidence,
  className = '',
  showPercent = true,
}) => {
  let score = 0.85;
  let level: 'HIGH' | 'MEDIUM' | 'LOW' | 'UNKNOWN' = 'HIGH';

  if (typeof confidence === 'number') {
    score = confidence;
    level = score >= 0.75 ? 'HIGH' : score >= 0.5 ? 'MEDIUM' : score > 0 ? 'LOW' : 'UNKNOWN';
  } else if (confidence && typeof confidence === 'object') {
    score = confidence.score ?? 0.85;
    level = confidence.level ?? 'HIGH';
  }

  const percent = Math.round(score * 100);
  const factorsTooltip =
    confidence && typeof confidence === 'object' && confidence.factors
      ? `\nEvidence Strength: ${Math.round((confidence.factors.evidence_strength ?? 0) * 100)}% | Relevance: ${Math.round((confidence.factors.retrieval_relevance ?? 0) * 100)}% | Coverage: ${Math.round((confidence.factors.query_coverage ?? 0) * 100)}%`
      : '';

  if (level === 'HIGH') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200/80 shadow-xs ${className}`}
        title={`Grounded Confidence: ${percent}% (High evidence quality)${factorsTooltip}`}
      >
        <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
        <span>High Confidence</span>
        {showPercent && <span className="text-emerald-700/80 font-mono text-[10px]">({percent}%)</span>}
      </span>
    );
  }

  if (level === 'MEDIUM') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-800 border border-amber-200/80 shadow-xs ${className}`}
        title={`Grounded Confidence: ${percent}% (Moderate evidence quality)${factorsTooltip}`}
      >
        <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
        <span>Medium Confidence</span>
        {showPercent && <span className="text-amber-700/80 font-mono text-[10px]">({percent}%)</span>}
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200 shadow-xs ${className}`}
      title="Limited or unrecorded evidence in database"
    >
      <HelpCircle className="w-3.5 h-3.5 text-slate-500" />
      <span>Low / Unrecorded</span>
      {showPercent && score > 0 && <span className="text-slate-500 font-mono text-[10px]">({percent}%)</span>}
    </span>
  );
};
