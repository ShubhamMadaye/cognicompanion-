import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  CalendarDays,
  TrendingUp,
  Gamepad2,
  Brain,
  MessageSquare,
} from 'lucide-react';
import { DataProtectionModal } from '../ui/DataProtectionModal';

export const Sidebar: React.FC = () => {
  const [modalState, setModalState] = useState<{ isOpen: boolean; tab: 'privacy' | 'terms' }>({
    isOpen: false,
    tab: 'privacy',
  });

  return (
    <aside className="w-56 bg-[#f7f5f0] border-r border-[#e8e4dc] flex flex-col justify-between shrink-0 h-screen sticky top-0 select-none">
      <div className="overflow-y-auto">
        {/* Brand */}
        <div className="h-16 px-5 border-b border-[#e8e4dc] flex items-center gap-2.5">
          <img
            src="/logo1.png"
            alt="CogniCompanion"
            className="w-8 h-8 object-contain rounded"
          />
          <div>
            <h1 className="font-bold text-sm text-[#184e5a] tracking-tight leading-tight">
              CogniCompanion
            </h1>
            <p className="text-[10px] text-stone-500 font-medium">
              Caretaker & Family Workspace
            </p>
          </div>
        </div>

        {/* Navigation Grouping */}
        <nav className="p-3 space-y-5 text-xs">
          <div>
            <span className="px-3 text-[9px] font-semibold uppercase tracking-widest text-stone-400 block mb-1.5">
              Overview
            </span>
            <NavLink
              to="/dashboard"
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-1.5 rounded-sm transition-colors text-[12.5px] ${
                  isActive
                    ? 'bg-white text-[#184e5a] font-semibold shadow-2xs border-l-2 border-[#184e5a]'
                    : 'text-stone-600 hover:text-[#184e5a] hover:bg-[#ede9e1]'
                }`
              }
            >
              <LayoutDashboard className="w-4 h-4 text-[#184e5a] shrink-0" />
              <span>Today's Care</span>
            </NavLink>
          </div>

          <div>
            <span className="px-3 text-[9px] font-semibold uppercase tracking-widest text-stone-400 block mb-1.5">
              Care
            </span>
            <NavLink
              to="/timeline"
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-1.5 rounded-sm transition-colors text-[12.5px] ${
                  isActive
                    ? 'bg-white text-[#184e5a] font-semibold shadow-2xs border-l-2 border-[#184e5a]'
                    : 'text-stone-600 hover:text-[#184e5a] hover:bg-[#ede9e1]'
                }`
              }
            >
              <CalendarDays className="w-4 h-4 text-stone-500 shrink-0" />
              <span>Routines & Meds</span>
            </NavLink>
          </div>

          <div>
            <span className="px-3 text-[9px] font-semibold uppercase tracking-widest text-stone-400 block mb-1.5">
              Cognition
            </span>
            <div className="space-y-0.5">
              <NavLink
                to="/cpi"
                className={({ isActive }) =>
                  `flex items-center gap-2.5 px-3 py-1.5 rounded-sm transition-colors text-[12.5px] ${
                    isActive
                      ? 'bg-white text-[#184e5a] font-semibold shadow-2xs border-l-2 border-[#184e5a]'
                      : 'text-stone-600 hover:text-[#184e5a] hover:bg-[#ede9e1]'
                  }`
                }
              >
                <TrendingUp className="w-4 h-4 text-stone-500 shrink-0" />
                <span>Performance & Trends</span>
              </NavLink>
              <NavLink
                to="/games"
                className={({ isActive }) =>
                  `flex items-center gap-2.5 px-3 py-1.5 rounded-sm transition-colors text-[12.5px] ${
                    isActive
                      ? 'bg-white text-[#184e5a] font-semibold shadow-2xs border-l-2 border-[#184e5a]'
                      : 'text-stone-600 hover:text-[#184e5a] hover:bg-[#ede9e1]'
                  }`
                }
              >
                <Gamepad2 className="w-4 h-4 text-stone-500 shrink-0" />
                <span>Cognitive Exercises</span>
              </NavLink>
            </div>
          </div>

          <div>
            <span className="px-3 text-[9px] font-semibold uppercase tracking-widest text-stone-400 block mb-1.5">
              Patient
            </span>
            <NavLink
              to="/memories"
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-1.5 rounded-sm transition-colors text-[12.5px] ${
                  isActive
                    ? 'bg-white text-[#184e5a] font-semibold shadow-2xs border-l-2 border-[#184e5a]'
                    : 'text-stone-600 hover:text-[#184e5a] hover:bg-[#ede9e1]'
                }`
              }
            >
              <Brain className="w-4 h-4 text-stone-500 shrink-0" />
              <span>Memories & People</span>
            </NavLink>
          </div>

          <div>
            <span className="px-3 text-[9px] font-semibold uppercase tracking-widest text-stone-400 block mb-1.5">
              Assistant
            </span>
            <NavLink
              to="/assistant"
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-1.5 rounded-sm transition-colors text-[12.5px] ${
                  isActive
                    ? 'bg-white text-[#184e5a] font-semibold shadow-2xs border-l-2 border-[#184e5a]'
                    : 'text-stone-600 hover:text-[#184e5a] hover:bg-[#ede9e1]'
                }`
              }
            >
              <MessageSquare className="w-4 h-4 text-stone-500 shrink-0" />
              <span>Conversations</span>
            </NavLink>
          </div>
        </nav>
      </div>

      {/* Understated, calm footer note */}
      <div className="px-4 py-3 border-t border-[#e8e4dc]/70 text-[11px] text-stone-400 leading-tight space-y-1">
        <p className="font-medium text-stone-600">CogniCompanion <span className="font-normal text-stone-400">· Assistive</span></p>
        <div className="flex items-center gap-2 pt-0.5 text-[10px] text-stone-400">
          <button
            onClick={() => setModalState({ isOpen: true, tab: 'privacy' })}
            className="hover:text-stone-700 underline underline-offset-2 cursor-pointer"
          >
            Privacy
          </button>
          <span>·</span>
          <button
            onClick={() => setModalState({ isOpen: true, tab: 'terms' })}
            className="hover:text-stone-700 underline underline-offset-2 cursor-pointer"
          >
            Terms
          </button>
          <span className="text-stone-300">·</span>
          <span>Non-diagnostic</span>
        </div>
      </div>

      <DataProtectionModal
        isOpen={modalState.isOpen}
        initialTab={modalState.tab}
        onClose={() => setModalState({ ...modalState, isOpen: false })}
      />
    </aside>
  );
};
