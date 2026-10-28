import React, { useState, useEffect } from 'react';
import { usePatient } from '../context/PatientContext';
import { Brain, Users, Plus, Calendar, MapPin, RotateCw, AlertCircle, Sparkles } from 'lucide-react';
import { memoriesApi } from '../api/memories';
// NOTE: mockData is NOT imported. Memories always uses live backend data.
import { Memory, Person, MemoryType } from '../types';

export const Memories: React.FC = () => {
  const { selectedPatient } = usePatient();
  const [activeTab, setActiveTab] = useState<'memories' | 'people'>('memories');
  // Rule: initial state is empty — not mock data.
  const [memories, setMemories] = useState<Memory[]>([]);
  const [people, setPeople] = useState<Person[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const [isAddingMemory, setIsAddingMemory] = useState(false);
  const [memTitle, setMemTitle] = useState('');
  const [memDesc, setMemDesc] = useState('');
  const [memType, setMemType] = useState<MemoryType>('VISIT');
  const [memDate, setMemDate] = useState(new Date().toISOString().split('T')[0]);
  const [memLocation, setMemLocation] = useState('');
  const [memSignificant, setMemSignificant] = useState(true);

  const [isAddingPerson, setIsAddingPerson] = useState(false);
  const [personName, setPersonName] = useState('');
  const [personRel, setPersonRel] = useState('');
  const [personDesc, setPersonDesc] = useState('');

  const loadMemoriesAndPeople = async () => {
    if (!selectedPatient?.id) return;
    setIsLoading(true);
    setFetchError(null);
    try {
      const [memList, peopleList] = await Promise.all([
        memoriesApi.listMemories(selectedPatient.id),
        memoriesApi.listPeople(selectedPatient.id),
      ]);
      setMemories(memList);
      setPeople(peopleList);
    } catch (err) {
      setFetchError('Could not load memories. Check backend connection.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadMemoriesAndPeople();
  }, [selectedPatient?.id]);

  const handleCreateMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPatient?.id) return;

    const created = await memoriesApi.createMemory(selectedPatient.id, {
      title: memTitle,
      description: memDesc,
      memory_type: memType,
      event_date: memDate,
      location: memLocation || undefined,
      is_significant: memSignificant,
    });

    setMemories([created, ...memories]);
    setIsAddingMemory(false);
    setMemTitle('');
    setMemDesc('');
    setMemLocation('');
  };

  const handleCreatePerson = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPatient?.id) return;

    const created = await memoriesApi.createPerson(selectedPatient.id, {
      name: personName,
      relationship: personRel,
      description: personDesc,
      is_active: true,
    });

    setPeople([...people, created]);
    setIsAddingPerson(false);
    setPersonName('');
    setPersonRel('');
    setPersonDesc('');
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Personalized Memory & People Engine</h2>
          <p className="text-xs text-slate-500">
            Caregiver-managed repository of familiar memories, relatives, and biographical facts.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex p-1 bg-slate-200/70 rounded-xl text-xs font-semibold">
            <button
              onClick={() => setActiveTab('memories')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg transition-all ${activeTab === 'memories'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
                }`}
            >
              <Brain className="w-3.5 h-3.5" />
              <span>Memories ({memories.length})</span>
            </button>
            <button
              onClick={() => setActiveTab('people')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg transition-all ${activeTab === 'people'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
                }`}
            >
              <Users className="w-3.5 h-3.5" />
              <span>People ({people.length})</span>
            </button>
          </div>

          {activeTab === 'memories' ? (
            <button
              onClick={() => setIsAddingMemory(true)}
              className="px-3.5 py-1.5 bg-teal-700 hover:bg-teal-800 text-white rounded-lg text-xs font-semibold flex items-center gap-1 shadow-sm transition-all"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Memory</span>
            </button>
          ) : (
            <button
              onClick={() => setIsAddingPerson(true)}
              className="px-3.5 py-1.5 bg-teal-700 hover:bg-teal-800 text-white rounded-lg text-xs font-semibold flex items-center gap-1 shadow-sm transition-all"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Person</span>
            </button>
          )}
        </div>
      </div>

      {activeTab === 'memories' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {memories.map((mem) => (
            <div
              key={mem.id}
              className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-subtle flex flex-col justify-between space-y-3"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-teal-800 bg-teal-50 px-2 py-0.5 rounded border border-teal-200/50">
                    {mem.memory_type}
                  </span>
                  {mem.is_significant && (
                    <span className="flex items-center gap-1 text-[10px] font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded">
                      <Sparkles className="w-3 h-3" />
                      <span>Key Memory</span>
                    </span>
                  )}
                </div>

                <h3 className="text-base font-bold text-slate-900 leading-snug">{mem.title}</h3>
                <p className="text-xs text-slate-600 leading-relaxed line-clamp-3">
                  {mem.description}
                </p>

                {mem.media && mem.media.length > 0 && (
                  <div className="mt-2 rounded-xl overflow-hidden border border-slate-100 max-h-40">
                    <img
                      src={mem.media[0].file_url}
                      alt={mem.title}
                      className="w-full h-36 object-cover"
                    />
                  </div>
                )}
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
                <div className="flex items-center gap-1 font-medium text-slate-500">
                  <Calendar className="w-3.5 h-3.5" />
                  <span>{mem.event_date}</span>
                </div>
                {mem.location && (
                  <div className="flex items-center gap-1 text-slate-400">
                    <MapPin className="w-3.5 h-3.5" />
                    <span>{mem.location}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'people' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          {people.map((person) => (
            <div
              key={person.id}
              className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-subtle flex flex-col items-center text-center space-y-3"
            >
              <div className="w-20 h-20 rounded-full overflow-hidden border-2 border-teal-100 shadow-sm bg-slate-100 flex items-center justify-center">
                {person.photo_url ? (
                  <img
                    src={person.photo_url}
                    alt={person.name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <Users className="w-8 h-8 text-slate-400" />
                )}
              </div>

              <div>
                <h3 className="text-base font-bold text-slate-900">{person.name}</h3>
                <span className="text-xs font-semibold text-teal-700 bg-teal-50 px-2 py-0.5 rounded-full inline-block mt-1">
                  {person.relationship || 'Family/Friend'}
                </span>
              </div>

              <p className="text-xs text-slate-500 leading-relaxed line-clamp-3">
                {person.description || 'No notes added.'}
              </p>
            </div>
          ))}
        </div>
      )}

      {isAddingMemory && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 space-y-4 border border-slate-200 shadow-elevated">
            <h3 className="text-base font-bold text-slate-900">Add New Personal Memory</h3>
            <form onSubmit={handleCreateMemory} className="space-y-3.5">
              <div>
                <label className="text-xs font-semibold text-slate-700">Memory Title</label>
                <input
                  type="text"
                  required
                  value={memTitle}
                  onChange={(e) => setMemTitle(e.target.value)}
                  placeholder="e.g. Afternoon with grandson in veranda"
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-teal-500/20"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-slate-700">Category</label>
                  <select
                    value={memType}
                    onChange={(e) => setMemType(e.target.value as MemoryType)}
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
                  >
                    <option value="VISIT">Family Visit</option>
                    <option value="OUTING">Outing / Garden</option>
                    <option value="FAMILY_STORY">Family Story / Memory</option>
                    <option value="APPOINTMENT">Doctor Appointment</option>
                    <option value="GENERAL">General</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700">Event Date</label>
                  <input
                    type="date"
                    required
                    value={memDate}
                    onChange={(e) => setMemDate(e.target.value)}
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700">Description (Natural Language)</label>
                <textarea
                  rows={3}
                  required
                  value={memDesc}
                  onChange={(e) => setMemDesc(e.target.value)}
                  placeholder="Describe the moment in detail. This gets embedded for semantic AI voice retrieval..."
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-teal-500/20"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="sig"
                  checked={memSignificant}
                  onChange={(e) => setMemSignificant(e.target.checked)}
                  className="rounded text-teal-600 focus:ring-teal-500"
                />
                <label htmlFor="sig" className="text-xs text-slate-700 font-medium">
                  Pin as Significant Memory (High AI Priority)
                </label>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAddingMemory(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-teal-700 hover:bg-teal-800 text-white text-xs font-semibold rounded-lg"
                >
                  Save Memory
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {isAddingPerson && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 space-y-4 border border-slate-200 shadow-elevated">
            <h3 className="text-base font-bold text-slate-900">Add Known Person</h3>
            <form onSubmit={handleCreatePerson} className="space-y-3.5">
              <div>
                <label className="text-xs font-semibold text-slate-700">Full Name</label>
                <input
                  type="text"
                  required
                  value={personName}
                  onChange={(e) => setPersonName(e.target.value)}
                  placeholder="e.g. Dr. Rajesh Khanna"
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700">Relationship</label>
                <input
                  type="text"
                  required
                  value={personRel}
                  onChange={(e) => setPersonRel(e.target.value)}
                  placeholder="e.g. Cardiologist, Granddaughter, Son"
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700">Caregiver Description</label>
                <textarea
                  rows={2}
                  value={personDesc}
                  onChange={(e) => setPersonDesc(e.target.value)}
                  placeholder="Details to help AI answer 'Who is this person?'"
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAddingPerson(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-teal-700 hover:bg-teal-800 text-white text-xs font-semibold rounded-lg"
                >
                  Add Person
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
