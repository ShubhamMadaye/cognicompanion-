import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { DataProtectionModal } from '../ui/DataProtectionModal';

export const AppLayout: React.FC = () => {
  const [modalState, setModalState] = useState<{ isOpen: boolean; tab: 'privacy' | 'terms' }>({
    isOpen: false,
    tab: 'privacy',
  });

  return (
    <div className="min-h-screen flex bg-slate-50 font-sans text-slate-800">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        <main className="flex-1 p-6 md:p-8 max-w-6xl w-full mx-auto">
          <Outlet />
        </main>
        <footer className="border-t border-slate-200/80 px-6 py-4 text-xs text-slate-500 flex flex-col sm:flex-row items-center justify-between gap-3 max-w-6xl w-full mx-auto">
          <p className="text-center sm:text-left">
            CogniCompanion Assistive Telemetry & Caretaker Support · Not a medical diagnosis system
          </p>
          <div className="flex items-center gap-4 shrink-0">
            <button
              onClick={() => setModalState({ isOpen: true, tab: 'privacy' })}
              className="text-slate-500 hover:text-slate-800 underline underline-offset-2 transition-colors cursor-pointer"
            >
              Privacy Policy & Data Protection Notice
            </button>
            <span>·</span>
            <button
              onClick={() => setModalState({ isOpen: true, tab: 'terms' })}
              className="text-slate-500 hover:text-slate-800 underline underline-offset-2 transition-colors cursor-pointer"
            >
              Terms of Service
            </button>
          </div>
        </footer>
      </div>

      <DataProtectionModal
        isOpen={modalState.isOpen}
        initialTab={modalState.tab}
        onClose={() => setModalState({ ...modalState, isOpen: false })}
      />
    </div>
  );
};
