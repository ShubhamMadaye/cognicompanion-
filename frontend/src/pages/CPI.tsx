import React, { useState, useEffect } from 'react';
import { ShieldCheck, Activity, Brain, Gamepad2, CheckCircle2, Clock, RotateCw, AlertCircle } from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts';
import { usePatient } from '../context/PatientContext';
import { cpiApi } from '../api/cpi';
import { CPIMetrics } from '../types';
// NOTE: mockData is NOT imported here. CPI always uses live backend data.
// If the API fails, the user sees an error state — not fake metrics.

export const CPI: React.FC = () => {
  const { selectedPatient } = usePatient();
  // Rule: initial state is null — not mock data.
  // If fetchMetrics() fails, error is shown instead of fake CPI values.
  const [metrics, setMetrics] = useState<CPIMetrics | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const fetchMetrics = async () => {
    setFetchError(null);

    if (!selectedPatient?.id) {
      setMetrics(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);

    try {
      const data = await cpiApi.getCPIMetrics(selectedPatient.id);
      setMetrics(data);
    } catch {
      setFetchError('Could not load CPI metrics. Check backend connection.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, [selectedPatient?.id]);

  const historicalTrends = metrics?.historical_trends ?? [];
  const hasTrends = historicalTrends.length > 0;

  if (!selectedPatient) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="text-center">
          <AlertCircle className="mx-auto mb-3 h-8 w-8 text-slate-400" />
          <h2 className="text-lg font-semibold text-slate-800">
            No patient selected
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Select a patient to view CPI metrics.
          </p>
        </div>
      </div>
    );
  }

  if (isLoading && !metrics) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="text-center">
          <RotateCw className="mx-auto mb-3 h-8 w-8 animate-spin text-slate-500" />
          <p className="text-sm text-slate-500">
            Loading CPI metrics...
          </p>
        </div>
      </div>
    );
  }

  if (fetchError && !metrics) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="max-w-md text-center">
          <AlertCircle className="mx-auto mb-3 h-8 w-8 text-red-500" />

          <h2 className="text-lg font-semibold text-slate-800">
            Unable to load CPI metrics
          </h2>

          <p className="mt-1 text-sm text-slate-500">
            {fetchError}
          </p>

          <button
            onClick={fetchMetrics}
            className="mt-4 inline-flex items-center gap-2 rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
          >
            <RotateCw className="h-4 w-4" />
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="text-center">
          <AlertCircle className="mx-auto mb-3 h-8 w-8 text-slate-400" />
          <p className="text-sm text-slate-500">
            No CPI data available for this patient.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {fetchError && metrics && (
        <div className="flex items-center justify-between gap-4 rounded-md border border-red-200 bg-red-50 px-4 py-3">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 shrink-0 text-red-500" />

            <p className="text-sm text-red-700">
              {fetchError}
            </p>
          </div>

          <button
            onClick={fetchMetrics}
            disabled={isLoading}
            className="inline-flex shrink-0 items-center gap-2 rounded-md border border-red-200 bg-white px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
          >
            <RotateCw
              className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`}
            />
            Retry
          </button>
        </div>
      )}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Cognitive Performance Index (CPI)</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Assistive multi-domain performance telemetry computed from patient gameplay, recall accuracy, and response consistency.
          </p>
        </div>
        <button
          onClick={fetchMetrics}
          disabled={isLoading}
          className="px-3.5 py-1.5 bg-white border border-slate-200 text-slate-700 rounded-xl shadow-sm hover:bg-slate-50 transition-all flex items-center gap-1.5 text-xs font-semibold self-start"
        >
          <RotateCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh Metrics</span>
        </button>
      </div>

      {/* ── Required Non-Clinical Notice ───────────────────────────────────── */}
      <div className="p-4 rounded-2xl bg-amber-50/90 border border-amber-200/80 text-amber-900 flex items-start gap-3.5 shadow-sm">
        <ShieldCheck className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <h4 className="text-xs font-bold uppercase tracking-wider text-amber-900">Assistive Telemetry Notice</h4>
          <p className="text-xs leading-relaxed text-amber-800">
            <strong>CPI is an assistive performance indicator and is not a medical diagnosis.</strong> This metric is intended solely to help caregivers and doctors monitor behavioral engagement and cognitive exercise trends over time.
          </p>
        </div>
      </div>

      {/* ── 4 Telemetry Metrics ────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase text-slate-400 tracking-wider">
              Overall Performance
            </span>
            <div className="p-1.5 rounded-xl bg-teal-50 text-teal-700">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900">{metrics.overall_score}</span>
            {metrics.change_vs_last_week != null && (
              <span className="text-xs font-bold text-teal-800 bg-teal-50 px-2 py-0.5 rounded-full">
                +{metrics.change_vs_last_week}% 7-day
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-2 font-medium">Telemetry composite index</p>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase text-slate-400 tracking-wider">
              Memory Recall Accuracy
            </span>
            <div className="p-1.5 rounded-xl bg-indigo-50 text-indigo-700">
              <Brain className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900">{metrics.memory_recall != null ? `${metrics.memory_recall}%` : 'N/A'}</span>
          </div>
          <p className="text-xs text-slate-500 mt-2 font-medium">Picture & Story recall exercises</p>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase text-slate-400 tracking-wider">
              Sequence & Pattern Tasks
            </span>
            <div className="p-1.5 rounded-xl bg-purple-50 text-purple-700">
              <Gamepad2 className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900">{metrics.sequence_accuracy != null ? `${metrics.sequence_accuracy}%` : 'N/A'}</span>
          </div>
          <p className="text-xs text-slate-500 mt-2 font-medium">Sequence recognition accuracy</p>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase text-slate-400 tracking-wider">
              Session Engagement
            </span>
            <div className="p-1.5 rounded-xl bg-emerald-50 text-emerald-700">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900">{metrics.completion_rate != null ? `${metrics.completion_rate}%` : 'N/A'}</span>
          </div>
          <p className="text-xs text-slate-500 mt-2 font-medium">Regular daily game adherence</p>
        </div>
      </div>

      {/* ── Trend Chart (Restrained Apple Health Style) ────────────────────── */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Activity className="w-4 h-4 text-teal-700" />
              <span>7-Day Cognitive Performance Trajectory</span>
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Comparative trends across general index, memory recall, and reaction speed
            </p>
          </div>
        </div>

        {hasTrends ? (
          <div className="h-72 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={historicalTrends}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} tickLine={false} />
                <YAxis domain={[50, 100]} stroke="#94a3b8" fontSize={12} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#ffffff',
                    borderRadius: '1rem',
                    border: '1px solid #e2e8f0',
                    boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.07)',
                    fontSize: '12px',
                  }}
                />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                <Line
                  type="monotone"
                  dataKey="cpi"
                  name="Cognitive Performance (CPI)"
                  stroke="#0f766e" // Teal 700
                  strokeWidth={3}
                  dot={{ fill: '#0f766e', r: 4 }}
                />
                <Line
                  type="monotone"
                  dataKey="memory"
                  name="Memory Recall"
                  stroke="#4f46e5" // Indigo 600
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="reaction"
                  name="Reaction Index"
                  stroke="#d97706" // Amber 600
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="h-64 flex flex-col items-center justify-center text-slate-400 space-y-2 border-2 border-dashed border-slate-200 rounded-xl">
            <Clock className="w-8 h-8 text-slate-300" />
            <p className="text-xs font-medium">No historical telemetry data available yet for this patient.</p>
          </div>
        )}
      </div>
    </div>
  );
};
