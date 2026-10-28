import React, { useState, useEffect } from 'react';
import { Gamepad2, AlertCircle, RotateCw } from 'lucide-react';
import { usePatient } from '../context/PatientContext';
import { gamesApi } from '../api/games';
import { GameCatalogItem, GameSession } from '../types';
// NOTE: mockData is NOT imported. Games always uses live backend data.

export const Games: React.FC = () => {
  const { selectedPatient } = usePatient();
  // Rule: initial state is empty — not mock data.
  const [catalog, setCatalog] = useState<GameCatalogItem[]>([]);
  const [sessions, setSessions] = useState<GameSession[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const fetchData = async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      const [catalogData, historyData] = await Promise.all([
        gamesApi.listGames(),
        selectedPatient?.id ? gamesApi.getHistory(selectedPatient.id) : Promise.resolve([]),
      ]);
      setCatalog(catalogData);
      setSessions(historyData);
    } catch (err) {
      setFetchError('Could not load game data. Check backend connection.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedPatient?.id]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Cognitive Gaming Analytics</h2>
          <p className="text-xs text-slate-500">Loading game data...</p>
        </div>
        <div className="flex items-center justify-center py-16 text-slate-400 text-sm">
          <RotateCw className="w-4 h-4 animate-spin mr-2" />
          Fetching game catalog and history...
        </div>
      </div>
    );
  }

  if (fetchError) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Cognitive Gaming Analytics</h2>
        </div>
        <div className="flex items-start gap-3 p-4 rounded-xl bg-red-50 border border-red-200 text-red-800 text-sm">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
          <div>
            <p className="font-semibold">Could not load game data</p>
            <p className="text-xs text-red-600 mt-1">{fetchError}</p>
          </div>
          <button
            onClick={fetchData}
            className="ml-auto text-xs font-semibold text-red-700 hover:underline shrink-0"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Cognitive Gaming Analytics</h2>
          <p className="text-xs text-slate-500">
            Real-time metrics from the 4 evidence-based cognitive games played on the patient tablet.
          </p>
        </div>
        <button
          onClick={fetchData}
          className="p-2 bg-white border border-slate-200 text-slate-600 rounded-xl shadow-sm hover:bg-slate-50 transition-all"
          title="Refresh"
        >
          <RotateCw className="w-3.5 h-3.5" />
        </button>
      </div>

      {catalog.length === 0 ? (
        <div className="text-center py-10 text-slate-400 text-sm border border-dashed border-slate-200 rounded-xl">
          No game catalog available. Backend may not have returned data.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {catalog.map((game) => (
            <div key={game.id} className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-subtle space-y-3">
              <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center text-xl shadow-xs">
                {game.icon_emoji}
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900">{game.name}</h3>
                <p className="text-xs text-slate-500 mt-1 line-clamp-2 leading-relaxed">{game.description}</p>
              </div>
              <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs font-semibold">
                <span className="text-teal-700 bg-teal-50 px-2 py-0.5 rounded">Adaptive Difficulty</span>
                <span className="text-slate-400">{game.estimated_duration_seconds}s</span>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-subtle space-y-4">
        <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <Gamepad2 className="w-4 h-4 text-teal-600" />
          <span>Recent Game Sessions & Adaptive Adjustments</span>
        </h3>

        {sessions.length === 0 ? (
          <div className="text-center py-8 text-slate-400 text-sm">
            No game sessions recorded yet.
            {!selectedPatient && (
              <p className="mt-1 text-xs">Select a patient to view their game history.</p>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                  <th className="pb-3">Game Type</th>
                  <th className="pb-3">Difficulty</th>
                  <th className="pb-3">Accuracy</th>
                  <th className="pb-3">Reaction Time</th>
                  <th className="pb-3">Mistakes</th>
                  <th className="pb-3">Next Adaptive Level</th>
                  <th className="pb-3">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sessions.map((sess) => (
                  <tr key={sess.id} className="text-slate-700">
                    <td className="py-3 font-semibold text-slate-900">{sess.game_type?.replace('_', ' ')}</td>
                    <td className="py-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700">
                        {sess.difficulty_level}
                      </span>
                    </td>
                    <td className="py-3 font-bold text-teal-700">{Math.round((sess.accuracy || 0) * 100)}%</td>
                    <td className="py-3 font-medium text-slate-600">{sess.reaction_time_ms} ms</td>
                    <td className="py-3 font-medium text-slate-600">{sess.mistakes}</td>
                    <td className="py-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-teal-50 text-teal-800 border border-teal-200">
                        → {sess.next_difficulty}
                      </span>
                    </td>
                    <td className="py-3 text-slate-400 font-medium">{sess.started_at.slice(0, 10)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
