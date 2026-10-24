import React, { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { adminApi } from '../../api/admin.api';
import { useAuth } from '../../context/AuthContext';
import { Navigate } from 'react-router-dom';
import type { RegistrationToken, User, Household, SystemInfo, SystemSettings } from '../../types';
import {
  ShieldAlert,
  Users,
  Home,
  KeyRound,
  Server,
  Plus,
  Trash2,
  Copy,
  Check,
  Search,
  Activity,
  Lock,
  Edit2,
  RefreshCw,
  ShoppingBag,
  Database,
  CheckCircle2,
  XCircle,
  Globe,
  ExternalLink,
  Eye,
  EyeOff,
  Save,
  AlertTriangle,
} from 'lucide-react';

type AdminTab = 'tokens' | 'users' | 'households' | 'oauth' | 'system';

export const AdminDashboardPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<AdminTab>('tokens');

  // Search filters
  const [userSearch, setUserSearch] = useState('');
  const [householdSearch, setHouseholdSearch] = useState('');

  // Token creation modal/form state
  const [showTokenModal, setShowTokenModal] = useState(false);
  const [tokenNote, setTokenNote] = useState('');
  const [tokenMaxUses, setTokenMaxUses] = useState(1);
  const [tokenCustomCode, setTokenCustomCode] = useState('');
  const [isCreatingToken, setIsCreatingToken] = useState(false);
  const [copiedToken, setCopiedToken] = useState<string | null>(null);

  // User password reset state
  const [resettingUserId, setResettingUserId] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState('');
  const [isResettingPassword, setIsResettingPassword] = useState(false);

  // Household edit state
  const [editingHousehold, setEditingHousehold] = useState<Household | null>(null);
  const [editHouseholdName, setEditHouseholdName] = useState('');
  const [isSavingHousehold, setIsSavingHousehold] = useState(false);

  // Action status message
  const [statusMessage, setStatusMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const showNotification = (text: string, type: 'success' | 'error' = 'success') => {
    setStatusMessage({ text, type });
    setTimeout(() => setStatusMessage(null), 4000);
  };

  // Queries
  const { data: stats } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: adminApi.getStats,
  });

  const { data: tokens = [], isLoading: isLoadingTokens } = useQuery<RegistrationToken[]>({
    queryKey: ['admin-tokens'],
    queryFn: adminApi.listTokens,
    enabled: activeTab === 'tokens',
  });

  const { data: allUsers = [], isLoading: isLoadingUsers } = useQuery<User[]>({
    queryKey: ['admin-users'],
    queryFn: adminApi.listUsers,
    enabled: activeTab === 'users',
  });

  const { data: allHouseholds = [], isLoading: isLoadingHouseholds } = useQuery<Household[]>({
    queryKey: ['admin-households'],
    queryFn: adminApi.listHouseholds,
    enabled: activeTab === 'households',
  });

  const { data: systemInfo } = useQuery<SystemInfo>({
    queryKey: ['admin-system'],
    queryFn: adminApi.getSystemInfo,
    enabled: activeTab === 'system',
  });

  const { data: systemSettings } = useQuery<SystemSettings>({
    queryKey: ['admin-settings'],
    queryFn: adminApi.getSettings,
  });

  // Settings form state
  const [serverUrlInput, setServerUrlInput] = useState('');
  const [clientIdInput, setClientIdInput] = useState('');
  const [clientSecretInput, setClientSecretInput] = useState('');
  const [showSecret, setShowSecret] = useState(false);
  const [isSavingSettings, setIsSavingSettings] = useState(false);
  const [copiedRedirectUri, setCopiedRedirectUri] = useState(false);
  const [showGuide, setShowGuide] = useState(false);

  useEffect(() => {
    if (systemSettings) {
      setServerUrlInput(systemSettings.server_public_url || '');
      setClientIdInput(systemSettings.google_client_id || '');
      setClientSecretInput(systemSettings.google_client_secret_masked || '');
    }
  }, [systemSettings]);

  const calculatedRedirectUri = serverUrlInput.trim()
    ? `${serverUrlInput.trim().replace(/\/+$/, '')}/integrations/google/callback`
    : (systemSettings?.google_redirect_uri || 'http://localhost:5173/integrations/google/callback');

  const handleCopyRedirectUri = () => {
    navigator.clipboard.writeText(calculatedRedirectUri);
    setCopiedRedirectUri(true);
    setTimeout(() => setCopiedRedirectUri(false), 2500);
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsSavingSettings(true);
      await adminApi.updateSettings({
        server_public_url: serverUrlInput.trim(),
        google_client_id: clientIdInput.trim(),
        google_client_secret: clientSecretInput.trim().startsWith('••') ? undefined : clientSecretInput.trim(),
      });
      queryClient.invalidateQueries({ queryKey: ['admin-settings'] });
      showNotification('Configuración de Google OAuth y Servidor guardada con éxito.');
    } catch (err: any) {
      showNotification(err.response?.data?.detail || 'Error al guardar configuración.', 'error');
    } finally {
      setIsSavingSettings(false);
    }
  };

  // Guard: Superuser only
  if (!user?.is_superuser) {
    return <Navigate to="/" replace />;
  }

  // Token Creation Handler
  const handleCreateToken = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsCreatingToken(true);
      await adminApi.createToken({
        token: tokenCustomCode.trim() ? tokenCustomCode.trim().toUpperCase() : undefined,
        note: tokenNote.trim() || undefined,
        max_uses: Number(tokenMaxUses) || 1,
      });
      setShowTokenModal(false);
      setTokenNote('');
      setTokenCustomCode('');
      setTokenMaxUses(1);
      queryClient.invalidateQueries({ queryKey: ['admin-tokens'] });
      queryClient.invalidateQueries({ queryKey: ['admin-stats'] });
      showNotification('Token de registro generado con éxito.');
    } catch (err: any) {
      showNotification(err.response?.data?.detail || 'Error al generar token.', 'error');
    } finally {
      setIsCreatingToken(false);
    }
  };

  // Copy token to clipboard
  const handleCopyToken = (tokenStr: string) => {
    navigator.clipboard.writeText(tokenStr);
    setCopiedToken(tokenStr);
    setTimeout(() => setCopiedToken(null), 2500);
  };

  // Revoke token
  const handleRevokeToken = async (id: string) => {
    if (!confirm('¿Deseas revocar este token de registro? No podrá ser utilizado nuevamente.')) return;
    try {
      await adminApi.revokeToken(id);
      queryClient.invalidateQueries({ queryKey: ['admin-tokens'] });
      queryClient.invalidateQueries({ queryKey: ['admin-stats'] });
      showNotification('Token revocado.');
    } catch (err: any) {
      showNotification(err.response?.data?.detail || 'Error al revocar token.', 'error');
    }
  };

  // Toggle user active status
  const handleToggleUserActive = async (targetUser: User) => {
    try {
      await adminApi.updateUser(targetUser.id, { is_active: !targetUser.is_active });
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      queryClient.invalidateQueries({ queryKey: ['admin-stats'] });
      showNotification(`Usuario ${targetUser.email} ${!targetUser.is_active ? 'activado' : 'desactivado'}.`);
    } catch (err: any) {
      showNotification(err.response?.data?.detail || 'Error al modificar usuario.', 'error');
    }
  };

  // Toggle superuser flag
  const handleToggleSuperuser = async (targetUser: User) => {
    if (targetUser.id === user.id) {
      alert('No puedes revocar tus propios privilegios de superadministrador.');
      return;
    }
    try {
      await adminApi.updateUser(targetUser.id, { is_superuser: !targetUser.is_superuser });
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      showNotification(`Permisos actualizados para ${targetUser.email}.`);
    } catch (err: any) {
      showNotification(err.response?.data?.detail || 'Error al cambiar permisos.', 'error');
    }
  };

  // Reset user password
  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resettingUserId || !newPassword.trim()) return;
    try {
      setIsResettingPassword(true);
      await adminApi.resetUserPassword(resettingUserId, newPassword.trim());
      setResettingUserId(null);
      setNewPassword('');
      showNotification('Contraseña restablecida correctamente.');
    } catch (err: any) {
      showNotification(err.response?.data?.detail || 'Error al restablecer contraseña.', 'error');
    } finally {
      setIsResettingPassword(false);
    }
  };

  // Delete user
  const handleDeleteUser = async (targetUser: User) => {
    if (targetUser.id === user.id) {
      alert('No puedes eliminar tu propia cuenta de superadministrador.');
      return;
    }
    if (!confirm(`¿Eliminar permanentemente al usuario ${targetUser.email}? Esta acción es irreversible.`)) return;
    try {
      await adminApi.deleteUser(targetUser.id);
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      queryClient.invalidateQueries({ queryKey: ['admin-stats'] });
      showNotification(`Usuario ${targetUser.email} eliminado.`);
    } catch (err: any) {
      showNotification(err.response?.data?.detail || 'Error al eliminar usuario.', 'error');
    }
  };

  // Save household name
  const handleSaveHousehold = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingHousehold || !editHouseholdName.trim()) return;
    try {
      setIsSavingHousehold(true);
      await adminApi.updateHousehold(editingHousehold.id, { name: editHouseholdName.trim() });
      setEditingHousehold(null);
      setEditHouseholdName('');
      queryClient.invalidateQueries({ queryKey: ['admin-households'] });
      showNotification('Hogar actualizado con éxito.');
    } catch (err: any) {
      showNotification(err.response?.data?.detail || 'Error al actualizar hogar.', 'error');
    } finally {
      setIsSavingHousehold(false);
    }
  };

  // Delete household
  const handleDeleteHousehold = async (household: Household) => {
    if (!confirm(`¿Eliminar el hogar "${household.name}" y desvincular a sus miembros?`)) return;
    try {
      await adminApi.deleteHousehold(household.id);
      queryClient.invalidateQueries({ queryKey: ['admin-households'] });
      queryClient.invalidateQueries({ queryKey: ['admin-stats'] });
      showNotification(`Hogar "${household.name}" eliminado.`);
    } catch (err: any) {
      showNotification(err.response?.data?.detail || 'Error al eliminar hogar.', 'error');
    }
  };

  const filteredUsers = allUsers.filter((u) => {
    const term = userSearch.toLowerCase();
    return u.email.toLowerCase().includes(term) || u.full_name.toLowerCase().includes(term);
  });

  const filteredHouseholds = allHouseholds.filter((h) => {
    const term = householdSearch.toLowerCase();
    return h.name.toLowerCase().includes(term);
  });

  return (
    <div className="space-y-6">
      {/* Toast Notification */}
      {statusMessage && (
        <div
          className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-2xl shadow-lg border text-sm font-semibold flex items-center space-x-2 animate-in fade-in slide-in-from-top-2 ${
            statusMessage.type === 'success'
              ? 'bg-emerald-50 text-emerald-900 border-emerald-200'
              : 'bg-red-50 text-red-900 border-red-200'
          }`}
        >
          {statusMessage.type === 'success' ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
          ) : (
            <XCircle className="w-5 h-5 text-red-600" />
          )}
          <span>{statusMessage.text}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center space-x-2.5">
            <span className="w-8 h-8 rounded-xl bg-purple-100 text-purple-700 flex items-center justify-center font-bold">
              <ShieldAlert className="w-5 h-5" />
            </span>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Panel de Superadministración</h1>
            <span className="bg-purple-100 text-purple-800 text-xs font-bold px-2.5 py-0.5 rounded-full border border-purple-200">
              Superuser
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Gestión global de usuarios, hogares, tokens de invitación cerrada y diagnóstico del servidor.
          </p>
        </div>

        <button
          onClick={() => {
            queryClient.invalidateQueries({ queryKey: ['admin-stats'] });
            queryClient.invalidateQueries({ queryKey: ['admin-tokens'] });
            queryClient.invalidateQueries({ queryKey: ['admin-users'] });
            queryClient.invalidateQueries({ queryKey: ['admin-households'] });
            queryClient.invalidateQueries({ queryKey: ['admin-system'] });
          }}
          className="inline-flex items-center space-x-1.5 px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-xl transition"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Actualizar datos</span>
        </button>
      </div>

      {/* KPI Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Usuarios Totales</span>
            <Users className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-black text-slate-900 mt-2">
            {stats ? stats.users_count : '—'}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">
            {stats ? `${stats.active_users_count} activos` : ''}
          </div>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Hogares Creados</span>
            <Home className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-2xl font-black text-slate-900 mt-2">
            {stats ? stats.households_count : '—'}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">Multi-tenant</div>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Tickets Importados</span>
            <ShoppingBag className="w-4 h-4 text-purple-600" />
          </div>
          <div className="text-2xl font-black text-slate-900 mt-2">
            {stats ? stats.receipts_count : '—'}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">
            {stats ? `${stats.pending_receipts_count} pendientes` : ''}
          </div>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Gasto Auditado</span>
            <Activity className="w-4 h-4 text-teal-600" />
          </div>
          <div className="text-2xl font-black text-slate-900 mt-2">
            {stats ? `${stats.total_spend.toFixed(2)} €` : '—'}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">
            {stats ? `${stats.products_count} productos` : ''}
          </div>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Tokens Activos</span>
            <KeyRound className="w-4 h-4 text-amber-600" />
          </div>
          <div className="text-2xl font-black text-slate-900 mt-2">
            {stats ? stats.active_registration_tokens_count : '—'}
          </div>
          <div className="text-[11px] text-amber-600 font-semibold mt-0.5">Acceso cerrado</div>
        </div>
      </div>

      {/* Tabs Switcher */}
      <div className="flex items-center space-x-2 border-b border-slate-200 pb-2">
        <button
          onClick={() => setActiveTab('tokens')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-sm font-semibold transition ${
            activeTab === 'tokens'
              ? 'bg-purple-600 text-white shadow-sm'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <KeyRound className="w-4 h-4" />
          <span>Tokens de Registro</span>
        </button>

        <button
          onClick={() => setActiveTab('users')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-sm font-semibold transition ${
            activeTab === 'users'
              ? 'bg-purple-600 text-white shadow-sm'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <Users className="w-4 h-4" />
          <span>Usuarios ({allUsers.length || stats?.users_count || 0})</span>
        </button>

        <button
          onClick={() => setActiveTab('households')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-sm font-semibold transition ${
            activeTab === 'households'
              ? 'bg-purple-600 text-white shadow-sm'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <Home className="w-4 h-4" />
          <span>Hogares ({allHouseholds.length || stats?.households_count || 0})</span>
        </button>

        <button
          onClick={() => setActiveTab('oauth')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-sm font-semibold transition ${
            activeTab === 'oauth'
              ? 'bg-purple-600 text-white shadow-sm'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <Globe className="w-4 h-4" />
          <span>Google OAuth & Servidor</span>
        </button>

        <button
          onClick={() => setActiveTab('system')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-sm font-semibold transition ${
            activeTab === 'system'
              ? 'bg-purple-600 text-white shadow-sm'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <Server className="w-4 h-4" />
          <span>Diagnóstico del Servidor</span>
        </button>
      </div>

      {/* TAB 1: REGISTRATION TOKENS */}
      {activeTab === 'tokens' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Tokens de Registro de Superadministrador</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                El autoregistro público está bloqueado. Solo usuarios con un token activo pueden registrarse.
              </p>
            </div>
            <button
              onClick={() => setShowTokenModal(true)}
              className="inline-flex items-center space-x-1.5 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold rounded-xl shadow-sm transition"
            >
              <Plus className="w-4 h-4" />
              <span>Generar Nuevo Token</span>
            </button>
          </div>

          {/* Tokens Table */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold text-xs uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Código del Token</th>
                    <th className="py-3 px-4">Nota / Destinatario</th>
                    <th className="py-3 px-4 text-center">Usos</th>
                    <th className="py-3 px-4 text-center">Estado</th>
                    <th className="py-3 px-4">Fecha Creación</th>
                    <th className="py-3 px-4 text-center">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {tokens.map((t) => (
                    <tr key={t.id} className="hover:bg-slate-50/70 transition">
                      <td className="py-3 px-4">
                        <div className="flex items-center space-x-2">
                          <code className="font-mono font-bold text-purple-900 bg-purple-50 px-2 py-1 rounded-lg border border-purple-200 text-xs">
                            {t.token}
                          </code>
                          <button
                            type="button"
                            onClick={() => handleCopyToken(t.token)}
                            className="p-1 text-slate-400 hover:text-slate-700 rounded hover:bg-slate-100 transition"
                            title="Copiar token"
                          >
                            {copiedToken === t.token ? (
                              <Check className="w-3.5 h-3.5 text-emerald-600" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-slate-700 text-xs">
                        {t.note || <span className="text-slate-400 italic">Sin nota</span>}
                      </td>
                      <td className="py-3 px-4 text-center font-semibold text-xs text-slate-700">
                        {t.times_used} / {t.max_uses}
                      </td>
                      <td className="py-3 px-4 text-center">
                        {t.is_active && t.times_used < t.max_uses ? (
                          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            <CheckCircle2 className="w-3 h-3" />
                            <span>Activo</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-500 border border-slate-200">
                            <XCircle className="w-3 h-3" />
                            <span>{t.times_used >= t.max_uses ? 'Agotado' : 'Inactivo'}</span>
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-slate-500 text-xs">
                        {t.created_at ? t.created_at.slice(0, 10) : '—'}
                      </td>
                      <td className="py-3 px-4 text-center">
                        {t.is_active && (
                          <button
                            type="button"
                            onClick={() => handleRevokeToken(t.id)}
                            className="text-xs font-medium text-red-600 hover:text-red-700 hover:bg-red-50 px-2 py-1 rounded-lg transition"
                          >
                            Revocar
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                  {tokens.length === 0 && !isLoadingTokens && (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-slate-400 text-xs">
                        No hay tokens registrados. Genera el primero con el botón superior.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: USERS MANAGEMENT */}
      {activeTab === 'users' && (
        <div className="space-y-4">
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              <input
                type="text"
                value={userSearch}
                onChange={(e) => setUserSearch(e.target.value)}
                placeholder="Buscar usuario por email o nombre..."
                className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold text-xs uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Usuario / Email</th>
                    <th className="py-3 px-4">Nombre Completo</th>
                    <th className="py-3 px-4 text-center">Superuser</th>
                    <th className="py-3 px-4 text-center">Estado</th>
                    <th className="py-3 px-4">Fecha Registro</th>
                    <th className="py-3 px-4 text-center">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredUsers.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-50/70 transition">
                      <td className="py-3 px-4 font-semibold text-slate-900 text-xs">
                        <div>{u.email}</div>
                        <div className="font-mono text-[10px] text-slate-400">{u.id}</div>
                      </td>
                      <td className="py-3 px-4 text-slate-700 text-xs">{u.full_name}</td>
                      <td className="py-3 px-4 text-center">
                        <button
                          type="button"
                          onClick={() => handleToggleSuperuser(u)}
                          className={`px-2 py-0.5 rounded-full text-[11px] font-bold border transition ${
                            u.is_superuser
                              ? 'bg-purple-100 text-purple-800 border-purple-300'
                              : 'bg-slate-100 text-slate-500 border-slate-200 hover:border-purple-300'
                          }`}
                        >
                          {u.is_superuser ? 'Superadmin' : 'Estándar'}
                        </button>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <button
                          type="button"
                          onClick={() => handleToggleUserActive(u)}
                          className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border transition ${
                            u.is_active
                              ? 'bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100'
                              : 'bg-red-50 text-red-700 border-red-200 hover:bg-red-100'
                          }`}
                        >
                          {u.is_active ? 'Activo' : 'Bloqueado'}
                        </button>
                      </td>
                      <td className="py-3 px-4 text-slate-500 text-xs">
                        {u.created_at ? u.created_at.slice(0, 10) : '—'}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <div className="flex items-center justify-center space-x-1.5">
                          <button
                            type="button"
                            onClick={() => {
                              setResettingUserId(u.id);
                              setNewPassword('');
                            }}
                            className="p-1.5 text-slate-600 hover:text-purple-700 rounded-lg hover:bg-purple-50 transition"
                            title="Restablecer contraseña"
                          >
                            <Lock className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDeleteUser(u)}
                            className="p-1.5 text-slate-400 hover:text-red-600 rounded-lg hover:bg-red-50 transition"
                            title="Eliminar usuario"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {filteredUsers.length === 0 && !isLoadingUsers && (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-slate-400 text-xs">
                        No se encontraron usuarios coincidentes.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: HOUSEHOLDS MANAGEMENT */}
      {activeTab === 'households' && (
        <div className="space-y-4">
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              <input
                type="text"
                value={householdSearch}
                onChange={(e) => setHouseholdSearch(e.target.value)}
                placeholder="Buscar hogar por nombre..."
                className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold text-xs uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Nombre del Hogar</th>
                    <th className="py-3 px-4">Moneda</th>
                    <th className="py-3 px-4">ID del Hogar</th>
                    <th className="py-3 px-4">Fecha Creación</th>
                    <th className="py-3 px-4 text-center">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredHouseholds.map((h) => (
                    <tr key={h.id} className="hover:bg-slate-50/70 transition">
                      <td className="py-3 px-4 font-bold text-slate-900 text-sm">
                        <div className="flex items-center space-x-2">
                          <Home className="w-4 h-4 text-purple-600" />
                          <span>{h.name}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-slate-700 text-xs font-semibold">{h.currency} (€)</td>
                      <td className="py-3 px-4 font-mono text-[11px] text-slate-400">{h.id}</td>
                      <td className="py-3 px-4 text-slate-500 text-xs">
                        {h.created_at ? h.created_at.slice(0, 10) : '—'}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <div className="flex items-center justify-center space-x-2">
                          <button
                            type="button"
                            onClick={() => {
                              setEditingHousehold(h);
                              setEditHouseholdName(h.name);
                            }}
                            className="inline-flex items-center space-x-1 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:text-purple-700 bg-slate-100 hover:bg-purple-50 rounded-lg transition"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                            <span>Renombrar</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDeleteHousehold(h)}
                            className="p-1.5 text-slate-400 hover:text-red-600 rounded-lg hover:bg-red-50 transition"
                            title="Eliminar hogar"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {filteredHouseholds.length === 0 && !isLoadingHouseholds && (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-slate-400 text-xs">
                        No se encontraron hogares.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: GOOGLE OAUTH & SYSTEM CONFIGURATION */}
      {activeTab === 'oauth' && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-6">
            <div className="border-b border-slate-100 pb-4">
              <div className="flex items-center space-x-2">
                <Globe className="w-5 h-5 text-purple-600" />
                <h3 className="text-base font-bold text-slate-900">
                  Configuración de Google OAuth 2.0 y Servidor
                </h3>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Configura las credenciales de tu proyecto de Google Cloud para habilitar la importación automática de tickets de Mercadona desde Gmail. Los cambios guardados se aplican dinámicamente en tiempo real.
              </p>
            </div>

            <form onSubmit={handleSaveSettings} className="space-y-6">
              {/* URL Pública del Servidor */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  URL Pública del Servidor / Dominio Base
                </label>
                <div className="relative">
                  <input
                    type="url"
                    required
                    value={serverUrlInput}
                    onChange={(e) => setServerUrlInput(e.target.value)}
                    placeholder="http://localhost:5173 o https://superdato.tudominio.com"
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-mono focus:bg-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                </div>
                <p className="text-[11px] text-slate-500 mt-1.5">
                  La dirección base con la que acceden los usuarios desde su navegador. La URI de redirección se calcula automáticamente a partir de esta URL.
                </p>
              </div>

              {/* URI de Redirección Autorizada (Calculada y Copiable) */}
              <div className="bg-purple-50/70 border border-purple-200/80 rounded-2xl p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-purple-950 uppercase tracking-wider flex items-center space-x-1.5">
                    <span>URI de redireccionamiento autorizada de Google</span>
                    <span className="bg-purple-200/80 text-purple-800 text-[10px] px-2 py-0.5 rounded-full font-bold">
                      Auto-calculada
                    </span>
                  </span>
                  <button
                    type="button"
                    onClick={handleCopyRedirectUri}
                    className="inline-flex items-center space-x-1 text-xs font-semibold px-2.5 py-1 bg-white hover:bg-purple-100 text-purple-700 rounded-lg border border-purple-200 shadow-sm transition"
                  >
                    {copiedRedirectUri ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                        <span className="text-emerald-700 font-bold">Copiada</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        <span>Copiar URI</span>
                      </>
                    )}
                  </button>
                </div>

                <div className="bg-white px-3.5 py-2.5 rounded-xl border border-purple-200 text-xs font-mono text-purple-900 select-all break-all shadow-inner">
                  {calculatedRedirectUri}
                </div>

                <p className="text-[11px] text-purple-700/90 leading-relaxed">
                  Pega exactamente este valor en <strong>Google Cloud Console &rarr; Credenciales &rarr; Tu ID de Cliente &rarr; URIs de redireccionamiento autorizados</strong>.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
                {/* Google Client ID */}
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
                      Google Client ID
                    </label>
                    {clientIdInput.endsWith('.apps.googleusercontent.com') && (
                      <span className="text-[10px] font-semibold text-emerald-600 flex items-center space-x-1">
                        <CheckCircle2 className="w-3 h-3" />
                        <span>Formato válido</span>
                      </span>
                    )}
                  </div>
                  <input
                    type="text"
                    value={clientIdInput}
                    onChange={(e) => setClientIdInput(e.target.value)}
                    placeholder="ej. 123456789-xxxxxxxx.apps.googleusercontent.com"
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-mono focus:bg-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                  <p className="text-[11px] text-slate-400 mt-1">
                    Identificador de cliente de aplicación web creado en Google Cloud Console.
                  </p>
                </div>

                {/* Google Client Secret */}
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
                      Google Client Secret
                    </label>
                    {systemSettings?.google_client_secret_set && (
                      <span className="text-[10px] font-semibold text-emerald-600 flex items-center space-x-1">
                        <CheckCircle2 className="w-3 h-3" />
                        <span>Cifrado y guardado</span>
                      </span>
                    )}
                  </div>
                  <div className="relative">
                    <input
                      type={showSecret ? 'text' : 'password'}
                      value={clientSecretInput}
                      onChange={(e) => setClientSecretInput(e.target.value)}
                      placeholder={systemSettings?.google_client_secret_set ? '•••••••••••• (dejar intacto para mantener)' : 'ej. GOCSPX-xxxxxxxxxxxxxxxx'}
                      className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-mono pr-10 focus:bg-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                    <button
                      type="button"
                      onClick={() => setShowSecret(!showSecret)}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600 rounded-md"
                    >
                      {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Se almacena cifrado en la base de datos con Fernet (AES-128-CBC + HMAC-SHA256).
                  </p>
                </div>
              </div>

              {/* Botón Guardar */}
              <div className="flex items-center justify-between pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowGuide(!showGuide)}
                  className="text-xs font-semibold text-purple-600 hover:text-purple-800 flex items-center space-x-1.5 transition"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  <span>{showGuide ? 'Ocultar guía de Google Cloud' : 'Ver guía paso a paso para configurar Google Cloud'}</span>
                </button>

                <button
                  type="submit"
                  disabled={isSavingSettings}
                  className="inline-flex items-center space-x-2 px-5 py-2.5 bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold rounded-xl shadow-md transition disabled:opacity-50"
                >
                  <Save className="w-4 h-4" />
                  <span>{isSavingSettings ? 'Guardando...' : 'Guardar Configuración'}</span>
                </button>
              </div>
            </form>
          </div>

          {/* Guía Paso a Paso */}
          {showGuide && (
            <div className="bg-slate-900 text-slate-100 rounded-2xl p-6 shadow-xl space-y-4 border border-slate-800 animate-in fade-in slide-in-from-top-2">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center space-x-2">
                  <span className="text-amber-400 font-bold">📋</span>
                  <h4 className="text-sm font-bold text-white tracking-wide">
                    Guía Rápida: Cómo crear tus Credenciales en Google Cloud Console
                  </h4>
                </div>
                <a
                  href="https://console.cloud.google.com/apis/credentials"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center space-x-1.5 px-3 py-1 bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold rounded-lg transition"
                >
                  <span>Abrir Google Console</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-slate-300">
                <div className="bg-slate-800/80 p-4 rounded-xl border border-slate-700/60 space-y-2">
                  <div className="font-bold text-amber-300 text-xs">1. Crear Proyecto y Habilitar Gmail API</div>
                  <p className="leading-relaxed">
                    Entra en Google Cloud Console, crea un nuevo proyecto llamado <strong>SuperDato</strong> y ve a <em>APIs y Servicios &rarr; Biblioteca</em>. Busca <strong>Gmail API</strong> y pulsa <strong>Habilitar</strong>.
                  </p>
                </div>

                <div className="bg-slate-800/80 p-4 rounded-xl border border-slate-700/60 space-y-2">
                  <div className="font-bold text-amber-300 text-xs">2. Pantalla de Consentimiento OAuth</div>
                  <p className="leading-relaxed">
                    En <em>Pantalla de consentimiento</em>, elige <strong>Externo</strong>. Rellena el nombre de la app y tu email. En la sección <em>Permisos (Scopes)</em> añade <code>https://www.googleapis.com/auth/gmail.readonly</code>.
                  </p>
                </div>

                <div className="bg-slate-800/80 p-4 rounded-xl border border-slate-700/60 space-y-2">
                  <div className="font-bold text-amber-300 text-xs">3. Crear ID de Cliente OAuth</div>
                  <p className="leading-relaxed">
                    En <em>Credenciales &rarr; Crear credenciales</em>, selecciona <strong>ID de cliente de OAuth</strong>. Selecciona Tipo: <strong>Aplicación web</strong>.
                  </p>
                </div>

                <div className="bg-slate-800/80 p-4 rounded-xl border border-slate-700/60 space-y-2">
                  <div className="font-bold text-amber-300 text-xs">4. Pegar URI de Redirección Autorizada</div>
                  <p className="leading-relaxed">
                    En el apartado <strong>URIs de redireccionamiento autorizados</strong>, pulsa <em>Añadir URI</em> y pega exactamente:
                    <br />
                    <code className="text-purple-300 font-mono text-[11px] select-all bg-slate-900 px-1 py-0.5 rounded">
                      {calculatedRedirectUri}
                    </code>
                  </p>
                </div>
              </div>

              <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3 text-[11px] text-amber-200 flex items-start space-x-2">
                <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                <span>
                  <strong>Usuarios de prueba:</strong> Mientras la app esté en modo <em>Prueba</em> en Google Cloud, añade los correos de Gmail que desees sincronizar en la sección <em>Usuarios de prueba</em> de la pantalla de consentimiento.
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 5: SYSTEM & SERVER INFO */}
      {activeTab === 'system' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
              <h3 className="text-base font-bold text-slate-900 flex items-center space-x-2">
                <Server className="w-5 h-5 text-purple-600" />
                <span>Estado del Servidor</span>
              </h3>

              <div className="divide-y divide-slate-100 text-xs">
                <div className="py-2.5 flex items-center justify-between">
                  <span className="text-slate-500">Aplicación:</span>
                  <span className="font-semibold text-slate-900">{systemInfo?.app_name || 'SuperDato'}</span>
                </div>
                <div className="py-2.5 flex items-center justify-between">
                  <span className="text-slate-500">Versión:</span>
                  <span className="font-mono font-semibold text-slate-900">{systemInfo?.version || '2.0.0'}</span>
                </div>
                <div className="py-2.5 flex items-center justify-between">
                  <span className="text-slate-500">Entorno:</span>
                  <span className="font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md uppercase">
                    {systemInfo?.environment || 'development'}
                  </span>
                </div>
                <div className="py-2.5 flex items-center justify-between">
                  <span className="text-slate-500">Motor de Base de Datos:</span>
                  <span className="font-mono text-slate-700">{systemInfo?.database || 'sqlite+aiosqlite'}</span>
                </div>
                <div className="py-2.5 flex items-center justify-between">
                  <span className="text-slate-500">Versión de Python:</span>
                  <span className="font-mono text-slate-700">{systemInfo?.python_version || '3.14'}</span>
                </div>
                <div className="py-2.5 flex items-center justify-between">
                  <span className="text-slate-500">Hora del Servidor (UTC):</span>
                  <span className="font-mono text-slate-700">{systemInfo?.server_time || '—'}</span>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
              <h3 className="text-base font-bold text-slate-900 flex items-center space-x-2">
                <Database className="w-5 h-5 text-emerald-600" />
                <span>Listo para Docker y Producción</span>
              </h3>

              <p className="text-xs text-slate-600 leading-relaxed">
                SuperDato está configurado para ejecutarse en contenedores Docker mediante <code>docker-compose.yml</code>.
                Toda la autenticación multi-hogar, tokens de invitación cerrada, catálogo determinístico de Mercadona
                y aislamiento RBAC están activados.
              </p>

              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-xs font-mono space-y-1 text-slate-800">
                <div className="text-slate-400 font-sans text-[11px] mb-1 font-semibold">Despliegue rápido en producción:</div>
                <div>docker-compose build</div>
                <div>docker-compose up -d</div>
              </div>

              <div className="text-[11px] text-slate-500 pt-2 flex items-center space-x-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>Modo seguro activado: no se admiten registros sin token emitido por el Superadmin.</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: CREATE REGISTRATION TOKEN */}
      {showTokenModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-slate-900 flex items-center space-x-2">
                <KeyRound className="w-5 h-5 text-purple-600" />
                <span>Generar Token de Registro</span>
              </h3>
              <button
                type="button"
                onClick={() => setShowTokenModal(false)}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateToken} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Nota / Destinatario (opcional)
                </label>
                <input
                  type="text"
                  value={tokenNote}
                  onChange={(e) => setTokenNote(e.target.value)}
                  placeholder="Ej: Para Pedro en la casa de campo"
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Código Personalizado (opcional)
                </label>
                <input
                  type="text"
                  value={tokenCustomCode}
                  onChange={(e) => setTokenCustomCode(e.target.value)}
                  placeholder="Dejar vacío para auto-generar (SUP-XXXX-XXXX)"
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm font-mono uppercase focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Usos Máximos
                </label>
                <input
                  type="number"
                  min={1}
                  max={1000}
                  value={tokenMaxUses}
                  onChange={(e) => setTokenMaxUses(Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Indica cuántas cuentas pueden registrarse con este mismo token antes de desactivarse automáticamente.
                </p>
              </div>

              <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowTokenModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 rounded-xl hover:bg-slate-100 transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isCreatingToken}
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold rounded-xl shadow-sm transition disabled:opacity-50"
                >
                  {isCreatingToken ? 'Generando...' : 'Crear Token Seguro'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: RESET PASSWORD */}
      {resettingUserId && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-sm w-full p-6 space-y-4">
            <h3 className="text-base font-bold text-slate-900 flex items-center space-x-2">
              <Lock className="w-5 h-5 text-purple-600" />
              <span>Restablecer Contraseña</span>
            </h3>

            <form onSubmit={handleResetPassword} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Nueva Contraseña Temporal
                </label>
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Introduce al menos 8 caracteres"
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              <div className="flex items-center justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setResettingUserId(null)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 rounded-xl hover:bg-slate-100 transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isResettingPassword || newPassword.length < 8}
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold rounded-xl shadow-sm transition disabled:opacity-50"
                >
                  {isResettingPassword ? 'Guardando...' : 'Cambiar Contraseña'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: RENAME HOUSEHOLD */}
      {editingHousehold && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-sm w-full p-6 space-y-4">
            <h3 className="text-base font-bold text-slate-900 flex items-center space-x-2">
              <Edit2 className="w-5 h-5 text-purple-600" />
              <span>Renombrar Hogar</span>
            </h3>

            <form onSubmit={handleSaveHousehold} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Nombre del Hogar
                </label>
                <input
                  type="text"
                  required
                  value={editHouseholdName}
                  onChange={(e) => setEditHouseholdName(e.target.value)}
                  placeholder="Nombre del hogar"
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              <div className="flex items-center justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setEditingHousehold(null)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 rounded-xl hover:bg-slate-100 transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isSavingHousehold || !editHouseholdName.trim()}
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold rounded-xl shadow-sm transition disabled:opacity-50"
                >
                  {isSavingHousehold ? 'Guardando...' : 'Guardar Nombre'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
