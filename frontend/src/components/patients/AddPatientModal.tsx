import React, { useState } from 'react';
import { X, UserPlus, CheckCircle, AlertCircle, Eye, EyeOff } from 'lucide-react';
import { patientsApi } from '../../api/patients';
import { usePatient } from '../../context/PatientContext';
import { Patient } from '../../types';

interface AddPatientModalProps {
  isOpen: boolean;
  onClose: () => void;
  onPatientCreated?: (patient: Patient) => void;
}

export const AddPatientModal: React.FC<AddPatientModalProps> = ({
  isOpen,
  onClose,
  onPatientCreated,
}) => {
  const { refreshPatients, setSelectedPatient } = usePatient();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [relationship, setRelationship] = useState('Family Member');
  const [language, setLanguage] = useState('en');
  const [dob, setDob] = useState('');
  const [emergencyName, setEmergencyName] = useState('');
  const [emergencyPhone, setEmergencyPhone] = useState('');
  const [medicalNotes, setMedicalNotes] = useState('');

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdCredentials, setCreatedCredentials] = useState<{
    email: string;
    fullName: string;
  } | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!fullName.trim() || !email.trim() || !password.trim()) {
      setError('Please provide full name, email, and password.');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }

    setIsLoading(true);
    try {
      const created = await patientsApi.createPatient({
        full_name: fullName.trim(),
        email: email.trim().toLowerCase(),
        password: password,
        date_of_birth: dob || null,
        preferred_language: language,
        caregiver_relationship: relationship,
        emergency_contact_name: emergencyName.trim() || null,
        emergency_contact_phone: emergencyPhone.trim() || null,
        medical_notes: medicalNotes.trim() || null,
        is_primary_caregiver: true,
      });

      await refreshPatients();
      setSelectedPatient(created);

      if (onPatientCreated) {
        onPatientCreated(created);
      }

      setCreatedCredentials({
        email: email.trim().toLowerCase(),
        fullName: fullName.trim(),
      });
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      if (axiosError?.response?.data?.detail) {
        setError(axiosError.response.data.detail);
      } else {
        setError('Failed to create patient account. Verify your backend connection.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleDone = () => {
    setCreatedCredentials(null);
    setFullName('');
    setEmail('');
    setPassword('');
    setDob('');
    setEmergencyName('');
    setEmergencyPhone('');
    setMedicalNotes('');
    setError(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/50 p-4">
      <div className="relative w-full max-w-lg rounded-lg border border-stone-200 bg-white shadow-xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-stone-200 px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded bg-[#184e5a]/10 flex items-center justify-center text-[#184e5a]">
              <UserPlus className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-stone-900 leading-tight">
                Connect New Patient
              </h2>
              <p className="text-xs text-stone-500">
                Create a patient profile & credentials for the Patient App
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-stone-400 hover:text-stone-700 p-1 rounded transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto px-6 py-5 flex-1 space-y-4">
          {createdCredentials ? (
            <div className="py-4 space-y-4 text-center">
              <div className="mx-auto w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center">
                <CheckCircle className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-stone-900">
                  Patient Profile Connected Successfully
                </h3>
                <p className="text-xs text-stone-600 mt-1 max-w-sm mx-auto">
                  <strong>{createdCredentials.fullName}</strong> is now assigned to your care dashboard.
                </p>
              </div>

              <div className="bg-stone-50 border border-stone-200 rounded p-4 text-left space-y-2 text-xs">
                <p className="font-semibold text-stone-800 uppercase tracking-wider text-[11px]">
                  Patient Companion App Credentials:
                </p>
                <div className="flex justify-between py-1 border-b border-stone-200">
                  <span className="text-stone-500">App Login Email:</span>
                  <span className="font-mono font-medium text-stone-900">{createdCredentials.email}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-stone-500">App Login Password:</span>
                  <span className="font-mono font-medium text-stone-900">•••••••• (configured)</span>
                </div>
                <p className="text-[11px] text-stone-500 mt-2">
                  Use these credentials to sign in on the patient's tablet or phone.
                </p>
              </div>

              <button
                type="button"
                onClick={handleDone}
                className="w-full py-2.5 px-4 bg-[#184e5a] text-white rounded font-medium text-sm hover:bg-[#143e48] transition-colors"
              >
                Go to Care Dashboard
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded flex items-center gap-2 text-xs text-rose-800">
                  <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
                  <span>{error}</span>
                </div>
              )}

              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-stone-500">
                  Patient Identity & App Login
                </h4>

                <div>
                  <label className="block text-xs font-medium text-stone-700 mb-1">
                    Patient Full Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. Rameshwar Madaye"
                    className="w-full px-3 py-2 text-sm border border-stone-300 rounded focus:outline-none focus:border-[#184e5a]"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-stone-700 mb-1">
                      Patient Login Email *
                    </label>
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="patient@example.com"
                      className="w-full px-3 py-2 text-sm border border-stone-300 rounded focus:outline-none focus:border-[#184e5a]"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-stone-700 mb-1">
                      Patient Login Password *
                    </label>
                    <div className="relative">
                      <input
                        type={showPassword ? 'text' : 'password'}
                        required
                        minLength={8}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="Min 8 characters"
                        className="w-full pl-3 pr-9 py-2 text-sm border border-stone-300 rounded focus:outline-none focus:border-[#184e5a]"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-700"
                      >
                        {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <div className="space-y-3 pt-2 border-t border-stone-100">
                <h4 className="text-xs font-bold uppercase tracking-wider text-stone-500">
                  Care Relationship & Preferences
                </h4>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-stone-700 mb-1">
                      Your Relationship to Patient
                    </label>
                    <select
                      value={relationship}
                      onChange={(e) => setRelationship(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-stone-300 rounded focus:outline-none focus:border-[#184e5a]"
                    >
                      <option value="Daughter">Daughter</option>
                      <option value="Son">Son</option>
                      <option value="Spouse">Spouse</option>
                      <option value="Family Member">Family Member</option>
                      <option value="Primary Caregiver">Primary Caregiver</option>
                      <option value="Professional Nurse">Professional Nurse</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-stone-700 mb-1">
                      Preferred Language
                    </label>
                    <select
                      value={language}
                      onChange={(e) => setLanguage(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-stone-300 rounded focus:outline-none focus:border-[#184e5a]"
                    >
                      <option value="en">English</option>
                      <option value="hi">Hindi (हिंदी)</option>
                      <option value="bn">Bengali (বাংলা)</option>
                      <option value="as">Assamese (অসমীয়া)</option>
                      <option value="mni">Manipuri (মৈতৈলোন্)</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-stone-700 mb-1">
                      Date of Birth (Optional)
                    </label>
                    <input
                      type="date"
                      value={dob}
                      onChange={(e) => setDob(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-stone-300 rounded focus:outline-none focus:border-[#184e5a]"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-stone-700 mb-1">
                      Emergency Phone (Optional)
                    </label>
                    <input
                      type="tel"
                      value={emergencyPhone}
                      onChange={(e) => setEmergencyPhone(e.target.value)}
                      placeholder="+91 98765 43210"
                      className="w-full px-3 py-2 text-sm border border-stone-300 rounded focus:outline-none focus:border-[#184e5a]"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-stone-700 mb-1">
                    Emergency Contact Name (Optional)
                  </label>
                  <input
                    type="text"
                    value={emergencyName}
                    onChange={(e) => setEmergencyName(e.target.value)}
                    placeholder="e.g. Rahul Sharma"
                    className="w-full px-3 py-2 text-sm border border-stone-300 rounded focus:outline-none focus:border-[#184e5a]"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-stone-700 mb-1">
                    Care & Medical Notes (Optional)
                  </label>
                  <textarea
                    rows={2}
                    value={medicalNotes}
                    onChange={(e) => setMedicalNotes(e.target.value)}
                    placeholder="e.g. Mild memory impairment, loves classical music, prefers morning walks."
                    className="w-full px-3 py-2 text-sm border border-stone-300 rounded focus:outline-none focus:border-[#184e5a]"
                  />
                </div>
              </div>

              <div className="pt-3 border-t border-stone-200 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={isLoading}
                  className="px-4 py-2 text-xs font-medium text-stone-600 hover:text-stone-900 border border-stone-300 rounded"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="px-4 py-2 text-xs font-medium bg-[#184e5a] text-white rounded hover:bg-[#143e48] transition-colors disabled:opacity-50 flex items-center gap-1.5"
                >
                  {isLoading ? 'Creating Account...' : 'Create & Connect Patient'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
