import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useHousehold } from '../../context/HouseholdContext';
import { integrationsApi } from '../../api/integrations.api';
import {
  RefreshCw,
  Mail,
  CheckCircle2,
  Clock,
  ShieldCheck,
  Loader2,
  FileText,
} from 'lucide-react';

export const ImportsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { activeHousehold } = useHousehold();
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncFeedback, setSyncFeedback] = useState<string | null>(null);

  // Queries
  const { data: googleConn } = useQuery({
    queryKey: ['googleStatus', activeHousehold?.id],
    queryFn: () => (activeHousehold ? integrationsApi.getGoogleStatus(activeHousehold.id) : Promise.resolve(null)),
    enabled: !!activeHousehold,
  });

  const { data: importJobs = [], isLoading: loadingJobs } = useQuery({
    queryKey: ['importJobs', activeHousehold?.id],
    queryFn: () => (activeHousehold ? integrationsApi.getImportJobs(activeHousehold.id) : Promise.resolve([])),
    enabled: !!activeHousehold,
  });

  const handleConnectGoogle = async () => {
    if (!activeHousehold) return;
    try {
      const authUrl = await integrationsApi.getGoogleAuthUrl(activeHousehold.id);
      window.location.href = authUrl;
    } catch {
      alert('Error al generar la URL de autorización de Google.');
    }
  };

  const handleDisconnectGoogle = async () => {
    if (!activeHousehold) return;
    if (!confirm('¿Deseas desconectar tu cuenta de Google y revocar el acceso?')) return;
    try {
      await integrationsApi.disconnectGoogle(activeHousehold.id);
      queryClient.invalidateQueries({ queryKey: ['googleStatus', activeHousehold.id] });
    } catch {
      alert('Error al desconectar la cuenta.');
    }
  };

  const handleManualSync = async () => {
    if (!activeHousehold) return;
    try {
      setIsSyncing(true);
      setSyncFeedback(null);
      const job = await integrationsApi.triggerSync(activeHousehold.id);
      setSyncFeedback(
        `Sincronización completada: ${job.receipts_imported} tickets importados, ${job.receipts_skipped} duplicados omitidos.`
      );
      queryClient.invalidateQueries({ queryKey: ['importJobs', activeHousehold.id] });
      queryClient.invalidateQueries({ queryKey: ['receipts'] });
      queryClient.invalidateQueries({ queryKey: ['analytics'] });
    } catch {
      setSyncFeedback('Error al iniciar la sincronización.');
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Monitor de Importaciones</h1>
          <p className="text-sm text-slate-500 mt-1">
            Supervisa las sincronizaciones de Gmail, historial de escaneos y prevención de duplicados.
          </p>
        </div>

        <button
          onClick={handleManualSync}
          disabled={isSyncing}
          className="inline-flex items-center space-x-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-4 py-2 rounded-xl text-sm shadow-sm transition disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isSyncing ? 'animate-spin' : ''}`} />
          <span>{isSyncing ? 'Sincronizando...' : 'Sincronizar Ahora'}</span>
        </button>
      </div>

      {syncFeedback && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 flex items-center space-x-2 text-emerald-800 text-xs">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <span>{syncFeedback}</span>
        </div>
      )}

      {/* Google Integration Status Card */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
        <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
          <Mail className="w-5 h-5 text-emerald-600" />
          <span>Conexión con Google Gmail</span>
        </h2>

        {googleConn ? (
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pt-2">
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <span className="font-semibold text-slate-800 text-sm">{googleConn.google_email}</span>
                <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>Conectado (Tokens AES-256)</span>
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Última sincronización: {googleConn.last_sync_at ? googleConn.last_sync_at.replace('T', ' ') : 'Pendiente'}
              </p>
            </div>

            <button
              onClick={handleDisconnectGoogle}
              className="text-xs font-semibold text-red-600 hover:text-red-700 bg-red-50 hover:bg-red-100 px-3 py-1.5 rounded-lg transition"
            >
              Desconectar Cuenta
            </button>
          </div>
        ) : (
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pt-2">
            <div className="space-y-1">
              <p className="text-sm font-medium text-slate-700">No hay cuenta de Gmail conectada a este hogar</p>
              <p className="text-xs text-slate-500">
                Conecta tu cuenta para detectar y extraer automáticamente los tickets digitales que recibes de Mercadona.
              </p>
            </div>

            <button
              onClick={handleConnectGoogle}
              className="inline-flex items-center space-x-2 bg-slate-900 hover:bg-slate-800 text-white font-medium px-4 py-2 rounded-xl text-sm transition"
            >
              <Mail className="w-4 h-4 text-emerald-400" />
              <span>Conectar con Google</span>
            </button>
          </div>
        )}
      </div>

      {/* Import Jobs History Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
        <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
          <Clock className="w-5 h-5 text-emerald-600" />
          <span>Historial de Trabajos de Importación</span>
        </h2>

        {loadingJobs ? (
          <div className="py-8 text-center text-slate-400">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-emerald-600" />
            <p className="text-xs">Cargando historial...</p>
          </div>
        ) : importJobs.length > 0 ? (
          <div className="border border-slate-200 rounded-2xl overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 font-semibold text-xs border-b border-slate-200 uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Origen</th>
                  <th className="py-3 px-4">Fecha y Hora</th>
                  <th className="py-3 px-4 text-center">Encontrados</th>
                  <th className="py-3 px-4 text-center">Importados</th>
                  <th className="py-3 px-4 text-center">Duplicados Omitidos</th>
                  <th className="py-3 px-4 text-center">Errores</th>
                  <th className="py-3 px-4 text-center">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {importJobs.map((job) => (
                  <tr key={job.id} className="hover:bg-slate-50/50">
                    <td className="py-3 px-4 font-semibold text-slate-900 text-xs">
                      {job.source_type}
                    </td>
                    <td className="py-3 px-4 text-slate-600 text-xs">
                      {job.started_at ? job.started_at.replace('T', ' ').substring(0, 19) : ''}
                    </td>
                    <td className="py-3 px-4 text-center text-xs font-semibold text-slate-800">
                      {job.messages_found}
                    </td>
                    <td className="py-3 px-4 text-center text-xs font-bold text-emerald-700">
                      +{job.receipts_imported}
                    </td>
                    <td className="py-3 px-4 text-center text-xs text-slate-500">
                      {job.receipts_skipped}
                    </td>
                    <td className="py-3 px-4 text-center text-xs text-slate-500">
                      {job.errors_count}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span
                        className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                          job.status === 'COMPLETED'
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : job.status === 'FAILED'
                            ? 'bg-red-50 text-red-700 border border-red-200'
                            : 'bg-blue-50 text-blue-700 border border-blue-200'
                        }`}
                      >
                        {job.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-10 text-center text-slate-400 space-y-2 border border-dashed border-slate-200 rounded-xl">
            <FileText className="w-8 h-8 text-slate-300 mx-auto" />
            <p className="text-sm">Aún no se han ejecutado trabajos de importación.</p>
          </div>
        )}
      </div>
    </div>
  );
};
