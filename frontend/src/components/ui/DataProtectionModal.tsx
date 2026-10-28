import React, { useEffect } from 'react';
import { X } from 'lucide-react';

interface DataProtectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialTab?: 'privacy' | 'terms';
}

export const DataProtectionModal: React.FC<DataProtectionModalProps> = ({
  isOpen,
  onClose,
  initialTab = 'privacy',
}) => {
  const [activeTab, setActiveTab] = React.useState<'privacy' | 'terms'>(initialTab);

  useEffect(() => {
    setActiveTab(initialTab);
  }, [initialTab]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div
        className="bg-white border border-slate-200 rounded-lg max-w-2xl w-full max-h-[85vh] flex flex-col shadow-lg"
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setActiveTab('privacy')}
              className={`text-sm font-semibold pb-1 transition-colors border-b-2 ${
                activeTab === 'privacy'
                  ? 'border-slate-800 text-slate-900'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              Privacy Policy & Data Protection Notice
            </button>
            <button
              onClick={() => setActiveTab('terms')}
              className={`text-sm font-semibold pb-1 transition-colors border-b-2 ${
                activeTab === 'terms'
                  ? 'border-slate-800 text-slate-900'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              Terms of Service & Clinical Disclaimer
            </button>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 p-1 rounded transition-colors"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-4 text-sm text-slate-700 leading-relaxed">
          {activeTab === 'privacy' ? (
            <div className="space-y-4">
              <div>
                <h3 className="font-bold text-slate-900 mb-1">1. Scope and Purpose</h3>
                <p className="text-slate-600">
                  CogniCompanion is an assistive caregiver platform designed to support memory recall, routine management, and cognitive performance tracking for patients under care. This notice outlines how patient personal data, memory logs, and interaction transcripts are processed.
                </p>
              </div>

              <div>
                <h3 className="font-bold text-slate-900 mb-1">2. DPDP Act Considerations</h3>
                <p className="text-slate-600">
                  In alignment with the Digital Personal Data Protection (DPDP) Act, personal data is processed solely on the basis of authorized consent provided by the patient or their registered caregiver/guardian. Data collected is strictly limited to information necessary for providing memory grounding, routine assistance, and telemetry review.
                </p>
              </div>

              <div>
                <h3 className="font-bold text-slate-900 mb-1">3. Grounded Memories & Voice Transcripts</h3>
                <p className="text-slate-600">
                  Personal memories, relationship graphs, and schedule logs entered into the system are stored in dedicated vector and relational stores solely for personalized grounding. Transcripts are retained to enable caregiver auditability and verifiable answer provenance.
                </p>
              </div>

              <div>
                <h3 className="font-bold text-slate-900 mb-1">4. Data Access, Correction, and Erasure</h3>
                <p className="text-slate-600">
                  Caregivers and authorized family members may review, correct, or request deletion of any recorded memory or schedule entry at any time through the caregiver management portal.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="p-3 bg-amber-50/80 border border-amber-200/80 rounded text-amber-900 text-xs leading-relaxed">
                <strong>Non-Diagnostic Medical Disclaimer:</strong> CogniCompanion is an assistive software platform for caregiver support and routine assistance. It is not a medical device, does not provide dementia diagnosis, and does not replace the evaluation or treatment of licensed medical professionals.
              </div>

              <div>
                <h3 className="font-bold text-slate-900 mb-1">1. Assistive Performance Indicator (CPI)</h3>
                <p className="text-slate-600">
                  The Cognitive Performance Index (CPI) is a project-defined algorithmic performance indicator computed from game recall tasks, response consistency, and voice engagement. It provides comparative operational telemetry over time and must not be used as clinical diagnostic criteria.
                </p>
              </div>

              <div>
                <h3 className="font-bold text-slate-900 mb-1">2. Caregiver Responsibility</h3>
                <p className="text-slate-600">
                  Prescription administration, dietary needs, and critical medical routines must be directly verified by human caregivers. Automated reminders and timeline logs serve as an operational aid, not an autonomous medical safety system.
                </p>
              </div>

              <div>
                <h3 className="font-bold text-slate-900 mb-1">3. Service Availability</h3>
                <p className="text-slate-600">
                  Local offline-first components and network services are provided as-is. In the event of network interruption or device offline status, caregivers should follow established offline care protocols.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-200 bg-slate-50/50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-semibold bg-slate-800 hover:bg-slate-900 text-white rounded transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
