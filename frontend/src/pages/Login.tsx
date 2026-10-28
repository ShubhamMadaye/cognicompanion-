import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Lock,
  Mail,
  ArrowRight,
  User,
  Eye,
  EyeOff,
  AlertCircle,
} from 'lucide-react';
import { DataProtectionModal } from '../components/ui/DataProtectionModal';

export const Login: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'signin' | 'signup'>('signin');

  // Sign in form state — no hardcoded demo credentials
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  // Sign up form state — caretaker / family member
  const [signUpName, setSignUpName] = useState('');
  const [signUpEmail, setSignUpEmail] = useState('');
  const [signUpPassword, setSignUpPassword] = useState('');

  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [modalState, setModalState] = useState<{ isOpen: boolean; tab: 'privacy' | 'terms' }>({
    isOpen: false,
    tab: 'privacy',
  });

  const { login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const redirectPath = (location.state as { from?: { pathname: string } })?.from?.pathname || '/dashboard';

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    try {
      await login(email.trim(), password);
      navigate(redirectPath, { replace: true });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Invalid credentials. Please verify your email and password.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (signUpPassword.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }
    setIsLoading(true);
    setError('');
    try {
      await register(signUpEmail.trim(), signUpPassword, signUpName.trim(), 'CAREGIVER');
      navigate('/dashboard', { replace: true });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Registration failed. Please try again.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#fcfbfa] flex flex-col items-center justify-center p-4 sm:p-6 text-slate-800">
      <div className="max-w-md w-full bg-white rounded-md border border-slate-200 shadow-sm overflow-hidden">
        {/* Header Branding with Dashboard Logo */}
        <div className="pt-8 pb-5 px-8 text-center border-b border-slate-100 bg-[#fdfdfd]">
          <img
            src="/logo1.png"
            alt="CogniCompanion Logo"
            className="w-14 h-14 mx-auto mb-3 object-contain rounded"
          />
          <h1 className="text-xl font-bold text-[#1b4d5a] tracking-tight">
            CogniCompanion
          </h1>
          <p className="text-xs text-slate-500 font-medium mt-1">
            Caretaker & Family Support Portal
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="px-8 pt-4">
          <div className="grid grid-cols-2 p-0.5 bg-slate-100 rounded border border-slate-200">
            <button
              type="button"
              onClick={() => {
                setActiveTab('signin');
                setError('');
              }}
              className={`py-1.5 text-xs font-semibold rounded transition-colors ${
                activeTab === 'signin'
                  ? 'bg-white text-[#1b4d5a] shadow-sm font-bold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setActiveTab('signup');
                setError('');
              }}
              className={`py-1.5 text-xs font-semibold rounded transition-colors ${
                activeTab === 'signup'
                  ? 'bg-white text-[#1b4d5a] shadow-sm font-bold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Register Account
            </button>
          </div>
        </div>

        <div className="p-8 pt-5 space-y-4 text-xs">
          {/* Error Message */}
          {error && (
            <div className="p-2.5 rounded bg-rose-50 border border-rose-200 text-xs text-rose-800 font-medium flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {activeTab === 'signin' ? (
            /* Sign In Form */
            <form onSubmit={handleLogin} className="space-y-3.5">
              <div className="space-y-1">
                <label className="font-semibold text-slate-700">Email Address</label>
                <div className="relative">
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="w-full pl-8 pr-3 py-2 bg-slate-50 border border-slate-200 rounded text-xs text-slate-900 focus:outline-none focus:ring-1 focus:ring-[#1b4d5a] focus:border-[#1b4d5a] placeholder:text-slate-400"
                    placeholder="caregiver@example.com"
                  />
                  <Mail className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                </div>
              </div>

              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <label className="font-semibold text-slate-700">Password</label>
                </div>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="w-full pl-8 pr-8 py-2 bg-slate-50 border border-slate-200 rounded text-xs text-slate-900 focus:outline-none focus:ring-1 focus:ring-[#1b4d5a] focus:border-[#1b4d5a] placeholder:text-slate-400"
                    placeholder="••••••••"
                  />
                  <Lock className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer"
                  >
                    {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-2.5 bg-[#1b4d5a] hover:bg-[#143d48] disabled:opacity-70 text-white font-semibold rounded transition-colors flex items-center justify-center gap-1.5 mt-2 cursor-pointer"
              >
                <span>{isLoading ? 'Signing In...' : 'Sign In'}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </form>
          ) : (
            /* Sign Up Form */
            <form onSubmit={handleRegister} className="space-y-3.5">
              <div className="space-y-1">
                <label className="font-semibold text-slate-700">Full Name</label>
                <div className="relative">
                  <input
                    type="text"
                    value={signUpName}
                    onChange={(e) => setSignUpName(e.target.value)}
                    required
                    className="w-full pl-8 pr-3 py-2 bg-slate-50 border border-slate-200 rounded text-xs text-slate-900 focus:outline-none focus:ring-1 focus:ring-[#1b4d5a] focus:border-[#1b4d5a] placeholder:text-slate-400"
                    placeholder="Caregiver / Family Member Name"
                  />
                  <User className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                </div>
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-slate-700">Email Address</label>
                <div className="relative">
                  <input
                    type="email"
                    value={signUpEmail}
                    onChange={(e) => setSignUpEmail(e.target.value)}
                    required
                    className="w-full pl-8 pr-3 py-2 bg-slate-50 border border-slate-200 rounded text-xs text-slate-900 focus:outline-none focus:ring-1 focus:ring-[#1b4d5a] focus:border-[#1b4d5a] placeholder:text-slate-400"
                    placeholder="caregiver@example.com"
                  />
                  <Mail className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                </div>
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-slate-700">Password</label>
                <div className="relative">
                  <input
                    type="password"
                    value={signUpPassword}
                    onChange={(e) => setSignUpPassword(e.target.value)}
                    required
                    minLength={8}
                    className="w-full pl-8 pr-3 py-2 bg-slate-50 border border-slate-200 rounded text-xs text-slate-900 focus:outline-none focus:ring-1 focus:ring-[#1b4d5a] focus:border-[#1b4d5a] placeholder:text-slate-400"
                    placeholder="••••••••"
                  />
                  <Lock className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-2.5 bg-[#1b4d5a] hover:bg-[#143d48] disabled:opacity-70 text-white font-semibold rounded transition-colors flex items-center justify-center gap-1.5 mt-2 cursor-pointer"
              >
                <span>{isLoading ? 'Registering...' : 'Create Caretaker Account & Enter'}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </form>
          )}

          {/* Compliance & Policy Links */}
          <div className="pt-3 border-t border-slate-100 flex items-center justify-center gap-3 text-[11px] text-slate-500">
            <button
              type="button"
              onClick={() => setModalState({ isOpen: true, tab: 'privacy' })}
              className="hover:text-slate-900 hover:underline underline-offset-2 transition-colors cursor-pointer"
            >
              Privacy Policy
            </button>
            <span>·</span>
            <button
              type="button"
              onClick={() => setModalState({ isOpen: true, tab: 'terms' })}
              className="hover:text-slate-900 hover:underline underline-offset-2 transition-colors cursor-pointer"
            >
              Terms of Service
            </button>
          </div>
        </div>
      </div>

      <DataProtectionModal
        isOpen={modalState.isOpen}
        onClose={() => setModalState({ isOpen: false, tab: 'privacy' })}
        initialTab={modalState.tab}
      />
    </div>
  );
};
