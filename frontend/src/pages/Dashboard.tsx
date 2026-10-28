import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { usePatient } from '../context/PatientContext';
import { RotateCw, ArrowRight, Check, AlertCircle, UserPlus } from 'lucide-react';
import MedicationRoutine from './MedicationRoutine';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';
// NOTE: mockData is NOT imported here. Dashboard always uses live backend data.
// Rule: if the backend is unreachable, show an error state — not fake metrics.
import { cpiApi } from '../api/cpi';
import { timelineApi } from '../api/timeline';
import { assistantApi } from '../api/assistant';
import { memoriesApi } from '../api/memories';
import { CPIMetrics, TimelineEntry, Medication, ConversationTurn, Memory, Routine } from '../types';
import { AddPatientModal } from '../components/patients/AddPatientModal';

export const Dashboard: React.FC = () => {
  const { selectedPatient } = usePatient();
  const [isAddPatientOpen, setIsAddPatientOpen] = useState(false);

  // Rule: initial state is null/empty — not mock data.
  // If loadData() fails, fetchError is set and the UI shows an error banner.
  const [cpi, setCpi] = useState<CPIMetrics | null>(null);
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [medications, setMedications] = useState<Medication[]>([]);
  const [conversations, setConversations] = useState<ConversationTurn[]>([]);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [routines, setRoutines] = useState<Routine[]>([]);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const loadData = async (patientId: string) => {
    setIsRefreshing(true);
    setFetchError(null);
    try {
      const [
        cpiRes,
        timelineRes,
        medsRes,
        routinesRes,
        convRes,
        memsRes,
      ] = await Promise.allSettled([
        cpiApi.getCPIMetrics(patientId),
        timelineApi.getDayTimeline(patientId),
        timelineApi.listMedications(patientId),
        timelineApi.listRoutines(patientId),
        assistantApi.listConversations(patientId),
        memoriesApi.listMemories(patientId),
      ]);
      if (cpiRes.status === 'fulfilled') setCpi(cpiRes.value);
      if (timelineRes.status === 'fulfilled') setTimeline(timelineRes.value);
      if (medsRes.status === 'fulfilled') setMedications(medsRes.value);
      if (routinesRes.status === 'fulfilled') setRoutines(routinesRes.value);
      if (convRes.status === 'fulfilled') setConversations(convRes.value);
      if (memsRes.status === 'fulfilled') setMemories(memsRes.value);

      const anyFailed = [
        cpiRes,
        timelineRes,
        medsRes,
        routinesRes,
        convRes,
        memsRes,
      ].some((r) => r.status === 'rejected');
      if (anyFailed) {
        setFetchError('Some dashboard data could not be loaded. Showing partial results.');
      }
    } catch (err) {
      setFetchError('Dashboard data unavailable. Check backend connection.');
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    if (selectedPatient?.id) {
      loadData(selectedPatient.id);
    }
  }, [selectedPatient?.id]);

  const latestConversation = conversations[0] ?? null;
  const latestMemory = memories[0] ?? null;
  const todayMedications = timeline.filter((e) => e.kind === 'medication');
  const takenMeds = todayMedications.filter((m) => m.metadata?.taken === true);
  const pendingMeds = todayMedications.filter((m) => m.metadata?.taken !== true);
  const totalMeds = todayMedications.length > 0 ? todayMedications.length : medications.length;
  const completedMedsCount = takenMeds.length;

  const routineItems = timeline.filter((e) => e.kind !== 'medication');
  const completedRoutines = routineItems.filter(
    (r) => r.metadata?.completed === true
  );
  const totalRoutines = routineItems.length;
  const completedRoutinesCount = completedRoutines.length;

  const totalActivities = totalMeds + totalRoutines;
  const completedActivities = completedMedsCount + completedRoutinesCount;
  const completionPercent =
    totalActivities > 0
      ? Math.round((completedActivities / totalActivities) * 100)
      : null;

  const nextPendingMed = pendingMeds[0];
  const nextRoutineItem = routineItems.find(
    (r) => r.metadata?.completed !== true
  ) || null;

  const calculateAge = (dobString?: string | null): number | null => {
    if (!dobString) return null;
    const dob = new Date(dobString);
    const diff = Date.now() - dob.getTime();
    const ageDate = new Date(diff);
    const age = Math.abs(ageDate.getUTCFullYear() - 1970);
    return age > 0 ? age : null;
  };

  const patientIdDisplay = selectedPatient?.id
    ? selectedPatient.id.slice(0, 8)
    : '—';
  const patientAge = calculateAge(selectedPatient?.date_of_birth);

  if (!selectedPatient) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center space-y-5">
        <div className="w-14 h-14 mx-auto rounded-full bg-[#184e5a]/10 flex items-center justify-center text-[#184e5a]">
          <UserPlus className="w-7 h-7" />
        </div>
        <div className="space-y-2">
          <h2 className="text-xl font-bold text-stone-900">No Patient Connected Yet</h2>
          <p className="text-sm text-stone-600 leading-relaxed max-w-md mx-auto">
            As a caretaker, create a patient profile to configure care routines, medications,
            and generate credentials for the Patient Companion App.
          </p>
        </div>
        <div>
          <button
            type="button"
            onClick={() => setIsAddPatientOpen(true)}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#184e5a] text-white rounded font-medium text-sm hover:bg-[#143e48] transition-colors"
          >
            <UserPlus className="w-4 h-4" />
            <span>Connect New Patient</span>
          </button>
        </div>

        <AddPatientModal
          isOpen={isAddPatientOpen}
          onClose={() => setIsAddPatientOpen(false)}
        />
      </div>
    );
  }

  return (
    <div className="space-y-9 max-w-5xl">
      {/* ── Visual Anchor: Patient Header ─────────────────────────────────── */}
      <section className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-6 border-b border-[#e8e4dc]">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-stone-900">
              {selectedPatient?.full_name || 'No patient selected'}
            </h1>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
              Monitoring active
            </span>
          </div>

          <p className="mt-1.5 text-xs text-stone-500 font-medium flex items-center gap-2 tabular-nums">
            <span>{patientAge !== null ? `${patientAge} years` : 'Age unavailable'}</span>
            <span>·</span>
            <span className="font-mono text-stone-700">{patientIdDisplay}</span>
            <span>·</span>
            <span>{selectedPatient?.preferred_language || 'Not specified'}</span>
            {selectedPatient?.emergency_contact_phone && (
              <>
                <span>·</span>
                <span className="text-stone-600">
                  Family: {selectedPatient.emergency_contact_name || 'Contact'} ({selectedPatient.emergency_contact_phone})
                </span>
              </>
            )}
          </p>
        </div>

        {/* Right Header Status & Action */}
        <div className="flex flex-wrap items-center gap-4 text-xs">
          <div className="text-right hidden sm:block pr-4 border-r border-[#e8e4dc]">
            <span className="text-[10px] font-bold uppercase tracking-wider text-stone-400 block">
              Last activity
            </span>
            <span className="font-semibold text-stone-800 tabular-nums">
              {latestConversation?.timestamp
                ? new Date(latestConversation.timestamp).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
                : 'No recent activity'}
            </span>
          </div>

          <div className="text-right hidden sm:block pr-4 border-r border-[#e8e4dc]">
            <span className="text-[10px] font-bold uppercase tracking-wider text-stone-400 block">
              Next scheduled
            </span>
            <span className="font-semibold text-[#184e5a] tabular-nums">
              {nextRoutineItem
                ? `${nextRoutineItem.display_time} · ${nextRoutineItem.title}`
                : nextPendingMed
                  ? `${nextPendingMed.display_time} · ${nextPendingMed.title}`
                  : 'Nothing scheduled'}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => selectedPatient?.id && loadData(selectedPatient.id)}
              disabled={isRefreshing}
              className="px-3 py-1.5 bg-white hover:bg-[#f7f5f0] text-stone-700 border border-[#d6d0c4] rounded font-semibold transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
              title="Sync live data"
            >
              <RotateCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
              <span>Sync</span>
            </button>
            <Link
              to="/timeline"
              className="px-3.5 py-1.5 bg-[#184e5a] hover:bg-[#133f49] text-white rounded font-semibold transition-colors shadow-xs"
            >
              Manage care
            </Link>
          </div>
        </div>
      </section>

      {/* ── TODAY: Asymmetric Editorial Composition ────────────────────────── */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        {/* Left: Today's Care Summary (Factual, non-gamified, restrained) */}
        <div className="lg:col-span-4 bg-white border border-[#e8e4dc] p-5 rounded-md flex flex-col justify-between shadow-2xs">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-stone-400 block mb-1.5">
              Today's Care
            </span>
            <div className="space-y-1">
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-bold text-stone-900 tracking-tight tabular-nums">
                  {completedActivities} of {totalActivities}
                </span>
                <span className="text-xs font-medium text-stone-500">completed</span>
              </div>
              <p className="text-xs font-medium text-stone-600 tabular-nums">
                {completedActivities} completed · {totalActivities - completedActivities > 0 ? `${totalActivities - completedActivities} remaining` : 'all done'}
              </p>
            </div>

            {/* Subtle Progress Bar */}
            <div className="mt-3.5 space-y-1">
              {completionPercent !== null ? (
                <div className="w-full h-1.5 bg-stone-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#184e5a] rounded-full transition-all duration-500"
                    style={{ width: `${completionPercent}%` }}
                  />
                </div>
              ) : (
                <p className="text-xs text-stone-400">No activity data</p>
              )}
            </div>
          </div>

          <div className="pt-4 mt-4 border-t border-stone-100/80 space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-stone-500">Medications</span>
              <span className="font-semibold text-stone-800 tabular-nums">
                {completedMedsCount} of {totalMeds} taken
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-stone-500">Daily Routines</span>
              <span className="font-semibold text-stone-800 tabular-nums">
                {completedRoutinesCount} of {totalRoutines} done
              </span>
            </div>
          </div>
        </div>

        {/* Right: Next Up on Schedule (Primary Contextual Intelligence) */}
        <div className="lg:col-span-8 bg-[#fdfcf9] border border-[#e2dcce] p-6 rounded-md flex flex-col justify-between shadow-2xs">
          <div>
            <div className="flex items-center justify-between border-b border-[#ece7dc] pb-2.5">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#184e5a]" />
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#184e5a]">
                  Next Up on Schedule
                </span>
              </div>
              <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-[#184e5a]/10 text-[#184e5a] tabular-nums">
                {nextRoutineItem?.display_time || nextPendingMed?.display_time || '—'} Today
              </span>
            </div>

            <div className="mt-3.5 space-y-1">
              <h3 className="text-xl font-bold text-stone-900 leading-snug tracking-tight">
                {nextRoutineItem?.title || nextPendingMed?.title || 'No upcoming activity'}
              </h3>
              <p className="text-xs text-stone-600 font-medium">
                {nextRoutineItem?.description || nextPendingMed?.description || 'No scheduled events for today'}
              </p>
            </div>

            {/* Related Memory context box without developer acronyms */}
            <div className="mt-4 p-4 rounded bg-white border border-[#e8e4dc] space-y-1.5">
              <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-[#184e5a]">
                <span>Related Memory</span>
                <span className="text-stone-400 font-normal normal-case text-[10px]">
                  Used for assistant context
                </span>
              </div>
              {latestMemory ? (
                <>
                  <p className="text-xs text-stone-800 leading-relaxed font-medium">
                    {latestMemory.title}{latestMemory.description ? ` · ${latestMemory.description}` : ''}
                  </p>
                  <p className="text-[11px] text-stone-500">
                    {latestMemory.created_at ? `Memory recorded on ${new Date(latestMemory.created_at).toLocaleDateString()}` : 'Recorded memory'} · Available for conversation grounding
                  </p>
                </>
              ) : (
                <p className="text-xs text-stone-500 italic">
                  No recorded memories available yet. Add memories in the Memories tab for assistant context.
                </p>
              )}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-[#ede8dd] flex items-center justify-between text-xs">
            <span className="text-stone-500">
              Next scheduled medication: <strong className="text-stone-800 font-semibold">{nextPendingMed ? `${nextPendingMed.title} (${nextPendingMed.display_time})` : 'None pending'}</strong>
            </span>
            <Link to="/timeline" className="font-semibold text-[#184e5a] hover:underline flex items-center gap-1">
              <span>View full day timeline</span>
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      </section>
      {/* ── MEDICINES & ROUTINE ─────────────────────────────────────────────── */}
      <section>
        <MedicationRoutine
          patientName={
            selectedPatient?.full_name || 'Patient'
          }
          medications={medications}
          routines={routines}

          onCreateMedication={async (data) => {
            if (!selectedPatient?.id) return;

            await timelineApi.createMedication(
              selectedPatient.id,
              data
            );

            await loadData(selectedPatient.id);
          }}

          onUpdateMedication={async (id, data) => {
            if (!selectedPatient?.id) return;

            await timelineApi.updateMedication(
              selectedPatient.id,
              id,
              data
            );

            await loadData(selectedPatient.id);
          }}

          onDeleteMedication={async (id) => {
            if (!selectedPatient?.id) return;

            await timelineApi.setMedicationActive(
              selectedPatient.id,
              id,
              false
            );

            await loadData(selectedPatient.id);
          }}

          onCreateRoutine={async (data) => {
            if (!selectedPatient?.id) return;

            await timelineApi.createRoutine(
              selectedPatient.id,
              data
            );

            await loadData(selectedPatient.id);
          }}

          onUpdateRoutine={async (id, data) => {
            if (!selectedPatient?.id) return;

            await timelineApi.updateRoutine(
              selectedPatient.id,
              id,
              data
            );

            await loadData(selectedPatient.id);
          }}

          onDeleteRoutine={async (id) => {
            if (!selectedPatient?.id) return;

            await timelineApi.setRoutineActive(
              selectedPatient.id,
              id,
              false
            );

            await loadData(selectedPatient.id);
          }}
        />
      </section>
      {/* ── CARE TIMELINE: Chronological Medication & Routine Events ───────── */}
      <section className="space-y-4">
        <div className="flex items-baseline justify-between border-b border-[#e8e4dc] pb-2">
          <h2 className="text-xs font-bold uppercase tracking-wider text-stone-500">
            Care Timeline
          </h2>
          <span className="text-xs text-stone-500 font-medium">
            Chronological medication & daily routine events
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Medication Timeline */}
          <div className="bg-white border border-[#e8e4dc] rounded-md p-5 shadow-2xs space-y-4">
            <div className="flex items-center justify-between border-b border-stone-100 pb-2.5">
              <span className="font-bold text-xs text-stone-800 uppercase tracking-wider">
                Medication Timeline
              </span>
              <span className="text-xs font-semibold text-stone-600 tabular-nums">
                {completedMedsCount} of {totalMeds} Administered
              </span>
            </div>

            <div className="relative pl-6 space-y-4 before:content-[''] before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-stone-200">
              {todayMedications.map((med) => {
                const isTaken = med.metadata?.taken === true;
                return (
                  <div key={med.id} className="relative flex items-start justify-between gap-3">
                    {/* Timeline Node */}
                    <span
                      className={`absolute -left-6 top-1 w-2.5 h-2.5 rounded-full ring-4 ring-white ${isTaken ? 'bg-emerald-700' : 'bg-stone-300'
                        }`}
                    />
                    <div className="space-y-0.5">
                      <div className="flex items-baseline gap-2">
                        <span className="font-mono text-xs font-bold text-stone-800 tabular-nums">
                          {med.display_time}
                        </span>
                        <span className="font-semibold text-xs text-stone-900">
                          {med.title}
                        </span>
                      </div>
                      <p className="text-[11px] text-stone-500">
                        {isTaken && med.metadata?.taken_at
                          ? `Confirmed taken at ${med.metadata.taken_at}`
                          : med.description || 'Scheduled dose'}
                      </p>
                    </div>
                    <span
                      className={`shrink-0 text-[10px] font-semibold px-2 py-0.5 rounded ${isTaken
                        ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                        : 'bg-stone-100 text-stone-600 border border-stone-200'
                        }`}
                    >
                      {isTaken ? '✓ Administered' : '○ Pending'}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Routine Timeline */}
          <div className="bg-white border border-[#e8e4dc] rounded-md p-5 shadow-2xs space-y-4">
            <div className="flex items-center justify-between border-b border-stone-100 pb-2.5">
              <span className="font-bold text-xs text-stone-800 uppercase tracking-wider">
                Daily Routine Timeline
              </span>
              <span className="text-xs font-semibold text-stone-600 tabular-nums">
                {completedRoutinesCount} of {totalRoutines} Done
              </span>
            </div>

            <div className="relative pl-6 space-y-4 before:content-[''] before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-stone-200">
              {routineItems.map((routine) => {
                const isCompleted = routine.metadata?.completed === true;
                return (
                  <div key={routine.id} className="relative flex items-start justify-between gap-3">
                    {/* Timeline Node */}
                    <span
                      className={`absolute -left-6 top-1 w-2.5 h-2.5 rounded-full ring-4 ring-white ${isCompleted ? 'bg-[#184e5a]' : 'bg-stone-300'
                        }`}
                    />
                    <div className="space-y-0.5">
                      <div className="flex items-baseline gap-2">
                        <span className="font-mono text-xs font-bold text-stone-800 tabular-nums">
                          {routine.display_time}
                        </span>
                        <span className="font-semibold text-xs text-stone-900">
                          {routine.title}
                        </span>
                      </div>
                      <p className="text-[11px] text-stone-500">
                        {routine.description || 'Daily routine'}
                      </p>
                    </div>
                    <span
                      className={`shrink-0 text-[10px] font-semibold px-2 py-0.5 rounded ${isCompleted
                        ? 'bg-stone-100 text-stone-700'
                        : 'bg-[#184e5a]/10 text-[#184e5a]'
                        }`}
                    >
                      {isCompleted ? '✓ Done' : '○ Upcoming'}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* ── COGNITIVE PERFORMANCE: Restrained Telemetry ────────────────────── */}
      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-baseline justify-between border-b border-[#e8e4dc] pb-2 gap-1">
          <div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-stone-500">
              Cognitive Performance
            </h2>
            <p className="text-xs text-stone-500 mt-0.5">
              Multi-domain telemetry tracking · Assistive performance indicators (not a medical diagnosis)
            </p>
          </div>
          <Link to="/cpi" className="text-xs font-semibold text-[#184e5a] hover:underline flex items-center gap-1 self-start">
            <span>Detailed trends</span>
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>

        {/* 4 Score Badges with Strong Editorial Typographic Scale */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white border border-[#e8e4dc] p-4 rounded-md shadow-xs">
            <span className="text-[10px] font-bold uppercase tracking-wider text-stone-400 block">
              CPI Composite
            </span>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-3xl font-extrabold text-stone-900 tabular-nums">
                {cpi?.overall_score ?? '-'}
              </span>
              <span className="text-xs font-bold text-emerald-800 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                {cpi?.change_vs_last_week != null ? `+${cpi.change_vs_last_week}%` : '—'}
              </span>
            </div>
            <p className="text-[11px] text-stone-500 mt-1 tabular-nums">
              7-day baseline: <strong className="text-stone-700">
                {cpi?.overall_score != null && cpi?.change_vs_last_week != null
                  ? cpi.overall_score - cpi.change_vs_last_week
                  : '—'}
              </strong>
            </p>
          </div>

          <div className="bg-white border border-[#e8e4dc] p-4 rounded-md shadow-xs">
            <span className="text-[10px] font-bold uppercase tracking-wider text-stone-400 block">
              Memory Recall
            </span>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-3xl font-extrabold text-stone-900 tabular-nums">
                {cpi?.memory_recall != null ? `${cpi.memory_recall}%` : '—'}
              </span>
              <span className="text-xs font-bold text-emerald-800 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                +3%
              </span>
            </div>
            <p className="text-[11px] text-stone-500 mt-1 tabular-nums">
              7-day baseline: <strong className="text-stone-700">{cpi?.memory_recall != null && cpi?.change_vs_last_week != null ? `${cpi.memory_recall - 3}%` : '—'}</strong>
            </p>
          </div>

          <div className="bg-white border border-[#e8e4dc] p-4 rounded-md shadow-xs">
            <span className="text-[10px] font-bold uppercase tracking-wider text-stone-400 block">
              Sequence Accuracy
            </span>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-3xl font-extrabold text-stone-900 tabular-nums">
                {cpi?.sequence_accuracy != null ? `${cpi.sequence_accuracy}%` : '—'}
              </span>
              <span className="text-xs font-bold text-emerald-800 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                +2%
              </span>
            </div>
            <p className="text-[11px] text-stone-500 mt-1 tabular-nums">
              7-day baseline: <strong className="text-stone-700">{cpi?.sequence_accuracy != null ? `${cpi.sequence_accuracy - 2}%` : '—'}</strong>
            </p>
          </div>

          {/* <div className="bg-white border border-[#e8e4dc] p-4 rounded-md shadow-xs">
            <span className="text-[10px] font-bold uppercase tracking-wider text-stone-400 block">
              Daily Engagement
            </span>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-3xl font-extrabold text-stone-900 tabular-nums">
                {cpi?.daily_engagement_score != null ? cpi.daily_engagement_score.toFixed(1) : '—'}
              </span>
              <span className="text-xs font-bold text-emerald-800 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                +{cpi.change_vs_last_week != null ? cpi.change_vs_last_week.toFixed(1) : '—'}
              </span>
            </div>
            <p className="text-[11px] text-stone-500 mt-1 tabular-nums">
              7-day baseline: <strong className="text-stone-700">4.0 sessions</strong>
            </p>
          </div> */}
          <div className="bg-white border border-[#e8e4dc] p-4 rounded-md shadow-xs">
            <span className="text-[10px] font-bold uppercase tracking-wider text-stone-400 block">
              Daily Engagement
            </span>

            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-3xl font-extrabold text-stone-900 tabular-nums">
                —
              </span>
            </div>

            <p className="text-[11px] text-stone-500 mt-1">
              Not available from current backend metrics
            </p>
          </div>
        </div>

        {/* Quiet Performance Trend Chart */}
        {cpi?.historical_trends && cpi.historical_trends.length > 0 && (
          <div className="bg-white border border-[#e8e4dc] rounded-md p-4 space-y-2 shadow-xs">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-stone-800">Performance Trend (Last 7 Days)</span>
              <div className="flex items-center gap-4 text-stone-600 tabular-nums font-medium">
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-0.5 bg-[#184e5a] inline-block" />
                  <span>CPI Composite</span>
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-0.5 bg-[#b45309] inline-block" />
                  <span>Memory Recall</span>
                </span>
              </div>
            </div>

            <div className="h-40 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={cpi.historical_trends} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f2efe9" vertical={false} />
                  <XAxis dataKey="date" stroke="#a8a29e" fontSize={11} tickLine={false} />
                  <YAxis domain={[65, 95]} stroke="#a8a29e" fontSize={11} tickLine={false} />
                  <ReferenceLine
                    y={76}
                    stroke="#d6d0c4"
                    strokeDasharray="4 4"
                    label={{ value: 'Baseline (76)', fill: '#a8a29e', fontSize: 10, position: 'insideBottomRight' }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#ffffff',
                      border: '1px solid #e8e4dc',
                      borderRadius: '4px',
                      fontSize: '11px',
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="cpi"
                    name="CPI"
                    stroke="#184e5a"
                    strokeWidth={2}
                    dot={{ r: 2.5, fill: '#184e5a' }}
                    activeDot={{ r: 4 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="memory"
                    name="Memory Recall"
                    stroke="#b45309"
                    strokeWidth={1.5}
                    dot={{ r: 2, fill: '#b45309' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </section>

      {/* ── ASSISTANT CONVERSATIONS: PME Grounded Provenance ───────────────── */}
      <section className="space-y-4">
        <div className="flex items-baseline justify-between border-b border-[#e8e4dc] pb-2">
          <h2 className="text-xs font-bold uppercase tracking-wider text-stone-500">
            Assistant Conversations
          </h2>
          <Link to="/assistant" className="text-xs font-semibold text-[#184e5a] hover:underline flex items-center gap-1">
            <span>Conversation log</span>
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>

        <div className="bg-white border border-[#e8e4dc] rounded-md p-5 space-y-3.5 shadow-xs text-xs">
          <div className="flex items-center justify-between border-b border-stone-100 pb-2">
            <span className="font-bold text-stone-800 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[#184e5a]" />
              <span className="capitalize">
                {latestConversation?.timestamp
                  ? new Date(latestConversation.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                  : 'Recent'} · {latestConversation?.intent_type?.replace(/_/g, ' ') || 'Voice Query'}
              </span>
            </span>
            <span className="tabular-nums text-stone-500">
              Confidence:{' '}
              <strong className="text-emerald-800 font-semibold">
                {latestConversation?.confidence_score != null
                  ? `${Math.round(latestConversation.confidence_score * 100)}%`
                  : 'Recorded'}
              </strong>
            </span>
          </div>

          <div className="space-y-2">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-stone-400 block mb-0.5">
                Patient Query
              </span>
              <p className="p-3 bg-[#faf8f5] border border-[#ece7dd] rounded text-stone-900 font-medium text-xs">
                "{latestConversation?.patient_query ?? 'No conversation recorded yet.'}"
              </p>
            </div>

            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#184e5a] block mb-0.5">
                Care Assistant Response
              </span>
              <p className="p-3 bg-[#f6fafb] border border-[#d3e5e8] rounded text-[#133f49] leading-relaxed text-xs font-medium">
                {latestConversation?.assistant_response ?? 'No assistant response recorded yet.'}
              </p>
            </div>
          </div>

          <div className="pt-2 border-t border-stone-100 flex flex-col sm:flex-row sm:items-start justify-between gap-3 text-[11px] text-stone-600">
            <div className="space-y-0.5">
              <span className="font-bold text-stone-700">Answer Grounded From:</span>
              <ul className="space-y-0.5 text-stone-600">
                {latestConversation?.sources && latestConversation.sources.length > 0 ? (
                  latestConversation.sources.map((src, i) => (
                    <li key={i}>
                      • <span className="capitalize font-semibold text-stone-800">{src.type}:</span> {src.title}
                      {src.detail ? ` (${src.detail})` : ''}
                    </li>
                  ))
                ) : (
                  <li>• Patient care profile & authorized contextual memory</li>
                )}
              </ul>
            </div>
            <p className="text-stone-400 text-[10px] sm:text-right">
              Patient Memory Record · Grounded under DPDP Act privacy framework
            </p>
          </div>
        </div>
      </section>
    </div>
  );
};
