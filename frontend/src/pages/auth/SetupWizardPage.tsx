import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { apiClient } from '../../api/client';
import { ShieldCheck, Lock, Mail, User as UserIcon, AlertCircle, Sparkles, Check, CheckCircle2 } from 'lucide-react';

const extractErrorMessage = (err: any): string => {
  const detail = err.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: any) => (d.msg ? String(d.msg).replace(/^Value error,\s*/i, '') : d.message || JSON.stringify(d)))
      .join('. ');
  }
  if (detail && typeof detail === 'object') {
    return detail.msg || detail.message || JSON.stringify(detail);
  }
  return err?.message || 'Error al inicializar el superadministrador.';
};

export const SetupWizardPage: React.FC = () => {
  const navigate = useNavigate();
  const { login, checkSetupStatus } = useAuth();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const hasMinLength = password.length >= 12;
  const hasLower = /[a-z]/.test(password);
  const hasUpper = /[A-Z]/.test(password);
  const hasDigit = /[0-9]/.test(password);
  const hasSymbol = /[^A-Za-z0-9]/.test(password);
  const classesCount = [hasLower, hasUpper, hasDigit, hasSymbol].filter(Boolean).length;
  const hasComplexity = classesCount >= 2;
  const passwordsMatch = password.length > 0 && password === confirmPassword;

  const isFormValid = fullName.trim().length >= 2 && email.includes('@') && hasMinLength && hasComplexity && passwordsMatch;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!passwordsMatch) {
      setError('Las contraseñas no coinciden.');
      return;
    }
    if (!hasMinLength) {
      setError('La contraseña debe tener al menos 12 caracteres.');
      return;
    }
    setError(null);
    setLoading(true);

    try {
      const response = await apiClient.post('/auth/setup-initial-admin', {
        email: email.trim().toLowerCase(),
        full_name: fullName.trim(),
        password,
      });

      const { access_token, refresh_token, user } = response.data;
      login(access_token, refresh_token, user);
      await checkSetupStatus();
      navigate('/');
    } catch (err: any) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-emerald-950 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-emerald-600 to-teal-500 flex items-center justify-center text-white mx-auto shadow-xl ring-4 ring-emerald-500/20 mb-4 animate-in fade-in zoom-in duration-300">
          <ShieldCheck className="w-9 h-9" />
        </div>
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 mb-3">
          <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
          <span>Primer Arranque Detectado · First-Run Setup</span>
        </div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight sm:text-4xl">
          Bienvenido a SuperDato
        </h1>
        <p className="mt-2 text-sm text-slate-300 max-w-sm mx-auto">
          Configura la cuenta de <strong>Superadministrador</strong> para comenzar a usar la plataforma.
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-lg">
        <div className="bg-white/95 backdrop-blur-md py-8 px-6 shadow-2xl rounded-3xl border border-white/20 sm:px-10">
          {error && (
            <div className="mb-5 bg-red-50 border border-red-200 rounded-xl p-3.5 flex items-start space-x-2.5 text-red-700 text-xs">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                Nombre del Administrador
              </label>
              <div className="relative rounded-xl shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <UserIcon className="h-4 w-4" />
                </div>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="block w-full pl-10 pr-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white text-slate-800 placeholder-slate-400 transition"
                  placeholder="Ej: Administrador Principal"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                Correo Electrónico
              </label>
              <div className="relative rounded-xl shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Mail className="h-4 w-4" />
                </div>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="block w-full pl-10 pr-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white text-slate-800 placeholder-slate-400 transition"
                  placeholder="admin@midominio.com"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                Contraseña Maestra (mínimo 12 caracteres)
              </label>
              <div className="relative rounded-xl shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Lock className="h-4 w-4" />
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full pl-10 pr-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white text-slate-800 placeholder-slate-400 transition"
                  placeholder="Crea una contraseña segura"
                />
              </div>

              {/* Password strength checklist */}
              <div className="mt-2 p-2.5 bg-slate-50 border border-slate-100 rounded-xl space-y-1 text-xs">
                <div className={`flex items-center gap-1.5 ${hasMinLength ? 'text-emerald-700' : 'text-slate-400'}`}>
                  {hasMinLength ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> : <div className="w-3.5 h-3.5 rounded-full border border-slate-300" />}
                  <span>Mínimo 12 caracteres ({password.length}/12)</span>
                </div>
                <div className={`flex items-center gap-1.5 ${hasComplexity ? 'text-emerald-700' : 'text-slate-400'}`}>
                  {hasComplexity ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> : <div className="w-3.5 h-3.5 rounded-full border border-slate-300" />}
                  <span>Combina mayúsculas, minúsculas, números o símbolos</span>
                </div>
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                Confirmar Contraseña
              </label>
              <div className="relative rounded-xl shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Lock className="h-4 w-4" />
                </div>
                <input
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="block w-full pl-10 pr-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white text-slate-800 placeholder-slate-400 transition"
                  placeholder="Repite la contraseña"
                />
              </div>
              {confirmPassword.length > 0 && (
                <p className={`mt-1 text-xs flex items-center gap-1 ${passwordsMatch ? 'text-emerald-600' : 'text-red-500'}`}>
                  {passwordsMatch ? <Check className="w-3.5 h-3.5" /> : <AlertCircle className="w-3.5 h-3.5" />}
                  {passwordsMatch ? 'Las contraseñas coinciden' : 'Las contraseñas no coinciden'}
                </p>
              )}
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={loading || !isFormValid}
                className="w-full flex justify-center items-center gap-2 py-3 px-4 border border-transparent rounded-xl shadow-md text-sm font-bold text-white bg-emerald-600 hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed transition transform active:scale-[0.99]"
              >
                {loading ? (
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    <ShieldCheck className="w-4 h-4" />
                    <span>Inicializar SuperDato y Entrar</span>
                  </>
                )}
              </button>
            </div>
          </form>

          <div className="mt-6 border-t border-slate-100 pt-4 text-center">
            <p className="text-xs text-slate-400">
              🔒 Una vez creada esta cuenta, el asistente se desactivará automáticamente y los registros posteriores quedarán cerrados por invitación.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

