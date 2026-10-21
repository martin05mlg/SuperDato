import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useHousehold } from '../../context/HouseholdContext';
import { householdsApi } from '../../api/households.api';
import {
  Settings,
  Users,
  Shield,
  Plus,
  UserPlus,
  CheckCircle2,
  AlertCircle,
  Trash2,
} from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { activeHousehold, refreshHouseholds } = useHousehold();

  // State for creating new household
  const [showNewModal, setShowNewModal] = useState(false);
  const [newHouseholdName, setNewHouseholdName] = useState('');

  // State for inviting members
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<'ADMIN' | 'MEMBER'>('MEMBER');
  const [generatedInviteToken, setGeneratedInviteToken] = useState<string | null>(null);
  const [inviteError, setInviteError] = useState<string | null>(null);

  // Fetch members of active household
  const { data: members = [] } = useQuery({
    queryKey: ['members', activeHousehold?.id],
    queryFn: () => (activeHousehold ? householdsApi.getMembers(activeHousehold.id) : Promise.resolve([])),
    enabled: !!activeHousehold,
  });

  const handleCreateHousehold = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newHouseholdName.trim()) return;

    try {
      await householdsApi.create({ name: newHouseholdName.trim() });
      await refreshHouseholds();
      setNewHouseholdName('');
      setShowNewModal(false);
    } catch {
      alert('Error al crear el nuevo hogar.');
    }
  };

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeHousehold || !inviteEmail.trim()) return;

    try {
      setInviteError(null);
      const res: any = await householdsApi.invite(activeHousehold.id, {
        invited_email: inviteEmail.trim(),
        role: inviteRole,
      });
      setGeneratedInviteToken(res.invitation_token);
      setInviteEmail('');
      queryClient.invalidateQueries({ queryKey: ['members', activeHousehold.id] });
    } catch (err: any) {
      setInviteError(err.response?.data?.detail || 'Error al invitar al miembro.');
    }
  };

  const handleRemoveMember = async (userId: string) => {
    if (!activeHousehold) return;
    if (!confirm('¿Estás seguro de que deseas eliminar a este miembro del hogar?')) return;

    try {
      await householdsApi.removeMember(activeHousehold.id, userId);
      queryClient.invalidateQueries({ queryKey: ['members', activeHousehold.id] });
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Error al eliminar miembro.');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Ajustes del Hogar</h1>
          <p className="text-sm text-slate-500 mt-1">
            Gestiona los miembros, permisos y roles de{' '}
            <span className="font-semibold text-slate-800">{activeHousehold?.name || 'tu hogar'}</span>.
          </p>
        </div>

        <button
          onClick={() => setShowNewModal(true)}
          className="inline-flex items-center space-x-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-4 py-2 rounded-xl text-sm shadow-sm transition"
        >
          <Plus className="w-4 h-4" />
          <span>Crear Nuevo Hogar</span>
        </button>
      </div>

      {/* Household Info Card */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
        <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
          <Settings className="w-5 h-5 text-emerald-600" />
          <span>Configuración General</span>
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm pt-2">
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
            <span className="text-xs text-slate-500 font-medium uppercase tracking-wider">Nombre</span>
            <div className="font-semibold text-slate-800 mt-1">{activeHousehold?.name || 'Hogar'}</div>
          </div>
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
            <span className="text-xs text-slate-500 font-medium uppercase tracking-wider">Moneda</span>
            <div className="font-semibold text-slate-800 mt-1">{activeHousehold?.currency || 'EUR'} (€)</div>
          </div>
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
            <span className="text-xs text-slate-500 font-medium uppercase tracking-wider">Tu Rol</span>
            <div className="font-semibold text-emerald-700 mt-1 flex items-center space-x-1.5">
              <Shield className="w-4 h-4" />
              <span>{activeHousehold?.role || 'OWNER'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Members & RBAC Card */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
            <Users className="w-5 h-5 text-emerald-600" />
            <span>Miembros del Hogar ({members.length})</span>
          </h2>
        </div>

        {/* Members List Table */}
        <div className="border border-slate-200 rounded-2xl overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500 font-semibold text-xs border-b border-slate-200 uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">Usuario</th>
                <th className="py-3 px-4">Correo</th>
                <th className="py-3 px-4 text-center">Rol</th>
                <th className="py-3 px-4 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {members.map((m) => (
                <tr key={m.id} className="hover:bg-slate-50/50">
                  <td className="py-3 px-4 font-semibold text-slate-900">{m.user_name}</td>
                  <td className="py-3 px-4 text-slate-600">{m.user_email}</td>
                  <td className="py-3 px-4 text-center">
                    <span
                      className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                        m.role === 'OWNER'
                          ? 'bg-purple-50 text-purple-700 border border-purple-200'
                          : m.role === 'ADMIN'
                          ? 'bg-blue-50 text-blue-700 border border-blue-200'
                          : 'bg-slate-100 text-slate-700'
                      }`}
                    >
                      {m.role}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    {m.role !== 'OWNER' && (
                      <button
                        onClick={() => handleRemoveMember(m.user_id)}
                        className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition"
                        title="Eliminar miembro"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Invite Member Section */}
        <div className="bg-slate-50 p-5 rounded-2xl border border-slate-200 space-y-3">
          <h3 className="text-sm font-bold text-slate-800 flex items-center space-x-1.5">
            <UserPlus className="w-4 h-4 text-emerald-600" />
            <span>Invitar a un nuevo miembro a este hogar</span>
          </h3>

          {inviteError && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-3 flex items-center space-x-2 text-red-700 text-xs">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{inviteError}</span>
            </div>
          )}

          {generatedInviteToken && (
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 space-y-1 text-emerald-900 text-xs">
              <div className="flex items-center space-x-1 font-semibold text-emerald-800">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Invitación generada exitosamente</span>
              </div>
              <p className="text-[11px] text-emerald-700">
                Comparte este token de invitación: <code className="bg-white px-1.5 py-0.5 rounded border border-emerald-200 font-mono text-[10px]">{generatedInviteToken}</code>
              </p>
            </div>
          )}

          <form onSubmit={handleInvite} className="flex flex-col sm:flex-row gap-3">
            <input
              type="email"
              required
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="correo@ejemplo.com"
              className="flex-1 px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
            />
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value as any)}
              aria-label="Seleccionar rol del nuevo miembro"
              className="px-3 py-2 border border-slate-200 rounded-xl text-sm text-slate-700 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="MEMBER">Miembro (Consulta y subida)</option>
              <option value="ADMIN">Administrador (Gestión)</option>
            </select>
            <button
              type="submit"
              className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-4 py-2 rounded-xl text-sm transition"
            >
              Enviar Invitación
            </button>
          </form>
        </div>
      </div>

      {/* Modal to Create New Household */}
      {showNewModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-6 max-w-md w-full shadow-xl space-y-4">
            <h3 className="text-lg font-bold text-slate-900">Crear Nuevo Hogar</h3>
            <p className="text-xs text-slate-500">
              Cada hogar mantiene sus propios tickets, presupuestos y miembros independientes.
            </p>

            <form onSubmit={handleCreateHousehold} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Nombre del Hogar
                </label>
                <input
                  type="text"
                  required
                  value={newHouseholdName}
                  onChange={(e) => setNewHouseholdName(e.target.value)}
                  placeholder="ej: Casa Playa, Familia López..."
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewModal(false)}
                  className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-xl transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl shadow-sm transition"
                >
                  Crear Hogar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
