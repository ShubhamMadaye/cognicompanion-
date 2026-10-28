import React, { useState, useEffect } from 'react';
import { Pill, Clock, CheckCircle2, Circle, Filter, Calendar, RotateCw, AlertCircle } from 'lucide-react';
import { usePatient } from '../context/PatientContext';
import { timelineApi } from '../api/timeline';
import { TimelineEntry, Medication } from '../types';
// NOTE: mockData is NOT imported. Timeline always uses live backend data.

export const Timeline: React.FC = () => {
  const { selectedPatient } = usePatient();
  const [selectedDay, setSelectedDay] = useState<string>(
    new Date().toISOString().split('T')[0]
  );
  const [filterType, setFilterType] = useState<string>('ALL');
  // Rule: initial state is empty/null — not mock data.
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [medications, setMedications] = useState<Medication[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const fetchTimeline = async () => {
    if (!selectedPatient?.id) return;
    setIsLoading(true);
    setFetchError(null);
    try {
      const [tlData, medData] = await Promise.all([
        timelineApi.getDayTimeline(selectedPatient.id, selectedDay),
        timelineApi.listMedications(selectedPatient.id),
      ]);
      setTimeline(tlData);
      setMedications(medData);
    } catch (err) {
      setFetchError('Could not load timeline. Check backend connection.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTimeline();
  }, [selectedPatient?.id, selectedDay]);

  const filteredTimeline = timeline.filter((entry) => {
    if (filterType === 'ALL') return true;
    if (filterType === 'MEDICATION') return entry.kind === 'medication';
    if (filterType === 'ROUTINE') return entry.kind === 'routine';
    if (filterType === 'MEMORY') return entry.kind === 'memory';
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Patient Activity Timeline</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Chronological, data-first log of medication doses, daily routines, cognitive games, and recorded memory events.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchTimeline}
            disabled={isLoading}
            className="p-2 bg-white border border-slate-200 text-slate-700 rounded-xl shadow-sm hover:bg-slate-50 transition-all flex items-center gap-1 text-xs font-semibold"
            title="Refresh Timeline"
          >
            <RotateCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
          <div className="flex items-center gap-1.5 bg-white border border-slate-200 rounded-xl px-3 py-1.5 shadow-sm text-xs">
            <Calendar className="w-3.5 h-3.5 text-slate-500" />
            <input
              type="date"
              value={selectedDay}
              onChange={(e) => setSelectedDay(e.target.value)}
              className="bg-transparent text-xs font-bold text-slate-800 outline-none cursor-pointer"
            />
          </div>
        </div>
      </div>

      {/* Filter Chips */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
        <span className="text-slate-400 font-semibold mr-1 flex items-center gap-1">
          <Filter className="w-3 h-3" /> Filter:
        </span>
        {['ALL', 'MEDICATION', 'ROUTINE', 'MEMORY'].map((type) => (
          <button
            key={type}
            onClick={() => setFilterType(type)}
            className={`px-3 py-1.5 rounded-xl font-semibold transition-all ${
              filterType === type
                ? 'bg-slate-900 text-white shadow-sm'
                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            {type === 'ALL' ? 'All Activities' : type.charAt(0) + type.slice(1).toLowerCase() + 's'}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Chronological Activity Feed */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm space-y-6">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Clock className="w-4 h-4 text-teal-700" />
              <span>Activities for {selectedDay}</span>
            </h3>
            <span className="text-xs font-semibold text-slate-500">
              {filteredTimeline.length} events logged
            </span>
          </div>

          <div className="relative pl-6 space-y-6 before:absolute before:left-3 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
            {filteredTimeline.length > 0 ? (
              filteredTimeline.map((item) => {
                const isTaken = item.metadata?.taken === true;

                return (
                  <div key={item.id} className="relative flex items-start gap-4">
                    {/* Timeline icon dot */}
                    <div
                      className={`absolute -left-6 top-1 w-6 h-6 rounded-full border-2 border-white flex items-center justify-center text-xs shadow-sm ${
                        item.kind === 'medication'
                          ? isTaken
                            ? 'bg-emerald-600 text-white'
                            : 'bg-amber-500 text-white'
                          : item.kind === 'memory'
                          ? 'bg-teal-700 text-white'
                          : 'bg-slate-700 text-white'
                      }`}
                    >
                      {item.kind === 'medication' ? (
                        <Pill className="w-3 h-3" />
                      ) : item.kind === 'memory' ? (
                        <span className="text-[10px]">👥</span>
                      ) : (
                        <Clock className="w-3 h-3" />
                      )}
                    </div>

                    {/* Activity Details Card */}
                    <div className="flex-1 p-4 rounded-xl bg-slate-50/90 border border-slate-200/80 space-y-2 hover:bg-slate-50 transition-colors">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-slate-900">{item.title}</span>
                          <span
                            className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md ${
                              item.kind === 'medication'
                                ? 'bg-blue-50 text-blue-800 border border-blue-200/50'
                                : item.kind === 'memory'
                                ? 'bg-teal-50 text-teal-800 border border-teal-200/50'
                                : 'bg-slate-200/70 text-slate-700'
                            }`}
                          >
                            {item.kind}
                          </span>
                        </div>
                        <span className="text-xs font-semibold text-slate-500 bg-white px-2 py-0.5 rounded border border-slate-200">
                          {item.display_time}
                        </span>
                      </div>

                      {item.description && (
                        <p className="text-xs text-slate-600 leading-relaxed font-normal">{item.description}</p>
                      )}

                      {/* Status & Outcome details */}
                      {item.kind === 'medication' && (
                        <div className="pt-1 flex items-center gap-2 text-xs font-semibold">
                          {isTaken ? (
                            <span className="text-emerald-700 flex items-center gap-1 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                              <CheckCircle2 className="w-3.5 h-3.5" /> Taken at {item.metadata?.taken_at || 'scheduled time'}
                            </span>
                          ) : (
                            <span className="text-amber-700 flex items-center gap-1 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                              <Circle className="w-3.5 h-3.5" /> Scheduled for bedtime
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="p-8 text-center text-slate-400 space-y-2 border-2 border-dashed border-slate-200 rounded-xl">
                <Clock className="w-8 h-8 text-slate-300 mx-auto" />
                <p className="text-xs font-semibold">No timeline entries found for this date.</p>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Prescription Schedule */}
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Pill className="w-4 h-4 text-teal-700" />
                <span>Prescribed Regimen</span>
              </h3>
              <span className="text-[11px] font-semibold text-slate-400">Active</span>
            </div>

            <div className="space-y-3">
              {medications.map((med) => (
                <div key={med.id} className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 space-y-1">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold text-slate-900">{med.name}</h4>
                    <span className="text-[10px] font-bold text-teal-800 bg-teal-50 px-2 py-0.5 rounded border border-teal-200/50">
                      {med.dosage}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-600 font-medium">
                    {med.frequency} • {med.timing} ({med.scheduled_time?.slice(0, 5)})
                  </p>
                  {med.instructions && (
                    <p className="text-[11px] text-slate-500 italic mt-0.5">{med.instructions}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
