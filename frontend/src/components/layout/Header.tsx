import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { usePatient } from '../../context/PatientContext';
import { ChevronDown, LogOut, UserPlus } from 'lucide-react';
import { AddPatientModal } from '../patients/AddPatientModal';

export const Header: React.FC = () => {
  const { user, logout } = useAuth();
  const { selectedPatient, patients, setSelectedPatient } = usePatient();
  const [isAddPatientOpen, setIsAddPatientOpen] = useState(false);
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const getInitials = (name?: string) => {
    if (!name) return 'CC';
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  };

  return (
    <>
      <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between sticky top-0 z-30">
        {/* Patient Selector & Connection */}
        <div className="flex items-center gap-2.5">
          {patients.length > 0 ? (
            <div className="relative">
              <select
                value={selectedPatient?.id || ''}
                onChange={(e) => {
                  const found = patients.find((p) => p.id === e.target.value);
                  if (found) setSelectedPatient(found);
                }}
                className="appearance-none pl-3 pr-8 py-1.5 bg-slate-50 border border-slate-200 rounded text-sm font-semibold text-slate-800 focus:outline-none focus:ring-1 focus:ring-slate-400 cursor-pointer"
              >
                {patients.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.full_name}
                  </option>
                ))}
              </select>
              <ChevronDown className="w-4 h-4 text-slate-400 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          ) : (
            <span className="text-xs font-medium text-stone-500 bg-stone-100 px-2.5 py-1 rounded">
              No patients connected
            </span>
          )}

          <button
            type="button"
            onClick={() => setIsAddPatientOpen(true)}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-[#184e5a] bg-[#184e5a]/10 hover:bg-[#184e5a]/20 rounded transition-colors"
            title="Create patient profile & connect device"
          >
            <UserPlus className="w-3.5 h-3.5" />
            <span>Connect Patient</span>
          </button>
        </div>

        {/* Right Controls: Caregiver Account Info */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2.5 pl-3 text-sm">
            <div className="w-7 h-7 rounded bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-700 font-bold text-xs">
              {getInitials(user?.full_name)}
            </div>
            <div className="hidden sm:block text-left">
              <p className="text-xs font-semibold text-slate-800 leading-tight">
                {user?.full_name || 'Caregiver'}
              </p>
              <div className="flex items-center gap-2">
                <span className="text-[10px] uppercase font-bold text-slate-400">
                  {user?.role || 'CAREGIVER'}
                </span>
                <button
                  onClick={handleLogout}
                  className="text-[11px] text-slate-400 hover:text-rose-600 flex items-center gap-0.5 transition-colors font-medium cursor-pointer"
                  title="Sign out"
                >
                  <LogOut className="w-2.5 h-2.5" />
                  <span>Sign out</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </header>

      <AddPatientModal
        isOpen={isAddPatientOpen}
        onClose={() => setIsAddPatientOpen(false)}
      />
    </>
  );
};
