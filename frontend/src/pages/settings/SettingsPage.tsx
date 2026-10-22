import React, { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useHousehold } from '../../context/HouseholdContext';
import { householdsApi } from '../../api/households.api';
import { catalogApi } from '../../api/catalog.api';
import {
  Settings,
  Users,
  Shield,
  Plus,
  UserPlus,
  CheckCircle2,
  AlertCircle,
  Trash2,
  Sparkles,
  RefreshCw,
  ShoppingCart,
  Check,
  Save,
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

  // Mercadona Online Integration State
  const [mercadonaEnabled, setMercadonaEnabled] = useState(false);
  const [mercadonaPostalCode, setMercadonaPostalCode] = useState('50007');
  const [isSavingMercadona, setIsSavingMercadona] = useState(false);
  const [mercadonaSaveSuccess, setMercadonaSaveSuccess] = useState(false);
  const [isSyncingCatalog, setIsSyncingCatalog] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);
  const [isEnriching, setIsEnriching] = useState(false);
  const [enrichResult, setEnrichResult] = useState<string | null>(null);

  useEffect(() => {
    if (activeHousehold?.settings) {
      setMercadonaEnabled(!!activeHousehold.settings.mercadona_online_enabled);
      setMercadonaPostalCode(activeHousehold.settings.mercadona_postal_code || '50007');
    }
  }, [activeHousehold]);

  // Warehouse resolution helper
  const getWarehouseName = (cp: string) => {
    const prefix = cp.trim().slice(0, 2);
    const map: Record<string, string> = {
      '50': 'zar1 (Zaragoza)',
      '28': 'mad1 (Madrid)',
      '08': 'bcn1 (Barcelona)',
      '46': 'vlc1 (Valencia)',
      '41': 'sev1 (Sevilla)',
      '03': 'alc1 (Alicante)',
      '29': 'agp1 (Málaga)',
      '30': 'mur1 (Murcia)',
      '48': 'bio1 (Bilbao)',
    };
    return map[prefix] || 'zar1 (Almacén predeterminado)';
  };

  const handleSaveMercadonaSettings = async () => {
    if (!activeHousehold) return;
    try {
      setIsSavingMercadona(true);
      setMercadonaSaveSuccess(false);
      await householdsApi.update(activeHousehold.id, {
        settings: {
          mercadona_online_enabled: mercadonaEnabled,
          mercadona_postal_code: mercadonaPostalCode.trim(),
        },
      });
      await refreshHouseholds();
      setMercadonaSaveSuccess(true);
      setTimeout(() => setMercadonaSaveSuccess(false), 3000);
    } catch {
      alert('Error al guardar la configuración de Mercadona Online.');
    } finally {
      setIsSavingMercadona(false);
    }
  };

  const handleSyncMercadonaCatalog = async () => {
    try {
      setIsSyncingCatalog(true);
      setSyncResult(null);
      const res = await catalogApi.syncMercadonaCatalog(mercadonaPostalCode, 20);
      setSyncResult(
        `Catálogo actualizado con éxito (${res.warehouse_code}): ${res.products_upserted} artículos procesados en ${res.subcategories_processed} categorías.`
      );
      queryClient.invalidateQueries({ queryKey: ['products'] });
    } catch {
      setSyncResult('Error al sincronizar con el catálogo público de Mercadona.');
    } finally {
      setIsSyncingCatalog(false);
    }
  };

  const handleEnrichProducts = async () => {
    try {
      setIsEnriching(true);
      setEnrichResult(null);
      const res = await catalogApi.enrichMercadonaProducts(0.82);
      setEnrichResult(
        `Auto-vinculación completada: ${res.auto_enriched_count} productos vinculados con éxito (${res.pending_suggestions_count} sugerencias adicionales para revisión manual).`
      );
      queryClient.invalidateQueries({ queryKey: ['products'] });
    } catch {
      setEnrichResult('Error al ejecutar la vinculación de productos.');
    } finally {
      setIsEnriching(false);
    }
  };

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

      {/* Mercadona Online Integration Card */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-100 pb-4">
          <div className="flex items-start space-x-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center flex-shrink-0 mt-0.5">
              <ShoppingCart className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <span>Catálogo Online Mercadona</span>
                <span className="text-[11px] font-semibold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full">
                  Fase E · Oficial
                </span>
              </h2>
              <p className="text-xs text-slate-500 mt-1 max-w-xl">
                Enriquece automáticamente los nombres del ticket con fotos oficiales de la tienda online de Mercadona,
                marcas comerciales (Hacendado, Bosque Verde, Deliplus, Compy) y envases detallados.
              </p>
            </div>
          </div>

          <label className="relative inline-flex items-center cursor-pointer flex-shrink-0">
            <input
              type="checkbox"
              checked={mercadonaEnabled}
              onChange={(e) => setMercadonaEnabled(e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
            <span className="ml-3 text-xs font-semibold text-slate-700">
              {mercadonaEnabled ? 'Activado' : 'Desactivado'}
            </span>
          </label>
        </div>

        {mercadonaEnabled ? (
          <div className="space-y-4 pt-1">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  Código Postal para Almacén Online
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    maxLength={5}
                    value={mercadonaPostalCode}
                    onChange={(e) => setMercadonaPostalCode(e.target.value)}
                    placeholder="50007"
                    className="w-32 px-3 py-2 border border-slate-200 rounded-xl text-sm font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                  <span className="text-xs text-slate-500 font-medium">
                    → Almacén resuelto: <strong className="text-emerald-700">{getWarehouseName(mercadonaPostalCode)}</strong>
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  Permite descargar el surtido y precios exactos del bloque logístico de tu zona.
                </p>
              </div>

              <div className="flex items-end justify-start sm:justify-end gap-2">
                <button
                  type="button"
                  disabled={isSavingMercadona}
                  onClick={handleSaveMercadonaSettings}
                  className="inline-flex items-center space-x-1.5 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-semibold shadow-sm transition disabled:opacity-50"
                >
                  {mercadonaSaveSuccess ? <Check className="w-4 h-4 text-emerald-400" /> : <Save className="w-4 h-4" />}
                  <span>{mercadonaSaveSuccess ? '¡Guardado!' : 'Guardar Ajustes'}</span>
                </button>
              </div>
            </div>

            {/* Sync & Enrichment Action Buttons */}
            <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 space-y-3">
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Operaciones del Catálogo Local
              </h3>
              <p className="text-xs text-slate-500">
                Los datos se sincronizan con una tabla local de tu dispositivo. La navegación normal nunca realiza peticiones
                externas en tiempo real, garantizando máxima velocidad y total privacidad.
              </p>

              <div className="flex flex-wrap gap-2.5 pt-1">
                <button
                  type="button"
                  disabled={isSyncingCatalog}
                  onClick={handleSyncMercadonaCatalog}
                  className="inline-flex items-center space-x-2 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold shadow-sm transition disabled:opacity-50"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isSyncingCatalog ? 'animate-spin' : ''}`} />
                  <span>{isSyncingCatalog ? 'Descargando surtido...' : '1. Sincronizar Catálogo Online'}</span>
                </button>

                <button
                  type="button"
                  disabled={isEnriching}
                  onClick={handleEnrichProducts}
                  className="inline-flex items-center space-x-2 px-3.5 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-semibold shadow-sm transition disabled:opacity-50"
                >
                  <Sparkles className={`w-3.5 h-3.5 ${isEnriching ? 'animate-spin' : ''}`} />
                  <span>{isEnriching ? 'Vinculando productos...' : '2. Auto-vincular Productos (Fuzzy Match)'}</span>
                </button>
              </div>

              {syncResult && (
                <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 flex items-center space-x-2 text-emerald-800 text-xs">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  <span>{syncResult}</span>
                </div>
              )}

              {enrichResult && (
                <div className="bg-purple-50 border border-purple-200 rounded-xl p-3 flex items-center space-x-2 text-purple-900 text-xs">
                  <Sparkles className="w-4 h-4 text-purple-600 flex-shrink-0" />
                  <span>{enrichResult}</span>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="bg-slate-50 border border-dashed border-slate-200 rounded-2xl p-4 text-center">
            <p className="text-xs text-slate-500">
              La integración está actualmente desactivada para este hogar. Actívala arriba para mostrar fotos oficiales de productos y marcas comerciales.
            </p>
          </div>
        )}
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
