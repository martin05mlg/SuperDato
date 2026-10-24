import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { apiClient } from '../../api/client';
import { ShoppingBag, Lock, Mail, AlertCircle, Sparkles } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const response = await apiClient.post('/auth/login', {
        email,
        password,
      });

      const { access_token, refresh_token, user } = response.data;
      login(access_token, refresh_token, user);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al iniciar sesión. Revisa tus credenciales.');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickAdminLogin = async () => {
    const defaultEmail = 'admin@superdato.com';
    const defaultPassword = 'SuperDatoAdmin2026!';
    setEmail(defaultEmail);
    setPassword(defaultPassword);
    setError(null);
    setLoading(true);

    try {
      const response = await apiClient.post('/auth/login', {
        email: defaultEmail,
        password: defaultPassword,
      });

      const { access_token, refresh_token, user } = response.data;
      login(access_token, refresh_token, user);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al iniciar sesión con cuenta de superadministrador.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="w-12 h-12 rounded-2xl bg-emerald-600 flex items-center justify-center text-white mx-auto shadow-md">
          <ShoppingBag className="w-7 h-7" />
        </div>
        <h2 className="mt-4 text-center text-2xl font-extrabold text-slate-900 tracking-tight">
          Inicia sesión en SuperDato
        </h2>
        <p className="mt-2 text-center text-sm text-slate-500">
          Control y analítica de tickets digitales de Mercadona
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 shadow-sm border border-slate-200 rounded-2xl sm:px-10">
          {error && (
            <div className="mb-4 bg-red-50 border border-red-200 rounded-xl p-3 flex items-start space-x-2 text-red-700 text-xs">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <div className="mb-5 bg-emerald-50/80 border border-emerald-200 rounded-xl p-3 text-emerald-900 text-xs space-y-1.5">
            <div className="font-bold flex items-center space-x-1.5 text-emerald-800">
              <Sparkles className="w-4 h-4 text-emerald-600" />
              <span>Credenciales Superadministrador:</span>
            </div>
            <div className="font-mono text-xs text-slate-800 bg-white/90 p-2 rounded-lg border border-emerald-100 flex flex-col space-y-0.5">
              <div><span className="text-slate-400">Usuario:</span> <span className="font-semibold select-all">admin@superdato.com</span></div>
              <div><span className="text-slate-400">Clave:</span> <span className="font-semibold select-all">SuperDatoAdmin2026!</span></div>
            </div>
          </div>

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Correo Electrónico
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="usuario@ejemplo.com"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Contraseña
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-xl shadow-sm text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 disabled:opacity-50 transition"
            >
              {loading ? 'Iniciando sesión...' : 'Entrar'}
            </button>
          </form>

          <div className="relative my-5">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-200" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white px-2 text-slate-400 font-semibold tracking-wider">o pruébalo al instante</span>
            </div>
          </div>

          <button
            type="button"
            onClick={handleQuickAdminLogin}
            disabled={loading}
            className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 border border-emerald-200 rounded-xl text-xs font-semibold text-emerald-800 bg-emerald-50/80 hover:bg-emerald-100 transition disabled:opacity-50 shadow-2xs"
          >
            <Sparkles className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Acceso Rápido Superadministrador (1 clic)</span>
          </button>

          <div className="mt-6 text-center text-xs text-slate-500">
            ¿No tienes cuenta?{' '}
            <Link to="/register" className="font-semibold text-emerald-600 hover:text-emerald-500">
              Regístrate aquí
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

