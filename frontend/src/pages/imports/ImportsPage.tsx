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
  AlertCircle,
  X,
  ExternalLink,
  Sparkles,
} from 'lucide-react';

export const ImportsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { activeHousehold } = useHousehold();
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncFeedback, setSyncFeedback] = useState<string | null>(null);
  const [isConnectModalOpen, setIsConnectModalOpen] = useState(false);
  const [mockEmail, setMockEmail] = useState('mi.cuenta.mercadona@gmail.com');
  const [connectingMock, setConnectingMock] = useState(false);

  // Queries
  const { data: googleConn, isLoading: loadingConn } = useQuery({
    queryKey: ['googleStatus', activeHousehold?.id],
    queryFn: () => (activeHousehold ? integrationsApi.getGoogleStatus(activeHousehold.id) : Promise.resolve(null)),
    enabled: !!activeHousehold,
  });

  const { data: importJobs = [], isLoading: loadingJobs } = useQuery({
    queryKey: ['importJobs', activeHousehold?.id],
    queryFn: () => (activeHousehold ? integrationsApi.getImportJobs(activeHousehold.id) : Promise.resolve([])),
    enabled: !!activeHousehold,
  });

  const handleConnectRealGoogle = async () => {
    if (!activeHousehold) return;
    try {
      const authUrl = await integrationsApi.getGoogleAuthUrl(activeHousehold.id);
      window.location.href = authUrl;
    } catch {
      alert('Error al generar la URL de autorización de Google. Verifica que la API esté activa.');
    }
  };

  const handleConnectMockGoogle = async () => {
    if (!activeHousehold) return;
    try {
      setConnectingMock(true);
      await integrationsApi.connectMockGoogle(activeHousehold.id, mockEmail);
      queryClient.invalidateQueries({ queryKey: ['googleStatus', activeHousehold.id] });
      setIsConnectModalOpen(false);
      setSyncFeedback(`Cuenta ${mockEmail} vinculada con éxito.`);
    } catch {
      alert('Error al simular la conexión de Google.');
    } finally {
      setConnectingMock(false);
    }
  };

  const handleDisconnectGoogle = async () => {
    if (!activeHousehold) return;
    if (!confirm('¿Deseas desconectar tu cuenta de Google y revocar el acceso?')) return;
    try {
      await integrationsApi.disconnectGoogle(activeHousehold.id);
      queryClient.invalidateQueries({ queryKey: ['googleStatus', activeHousehold.id] });
      setSyncFeedback('Cuenta de Google desconectada.');
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
        `Sincronización completada: ${job.receipts_imported} tickets nuevos importados, ${job.receipts_skipped} duplicados omitidos.`
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
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 flex items-center justify-between text-emerald-800 text-xs animate-in fade-in">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span>{syncFeedback}</span>
          </div>
          <button onClick={() => setSyncFeedback(null)} className="text-emerald-500 hover:text-emerald-700">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Google Integration Status Card */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
        <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
          <Mail className="w-5 h-5 text-emerald-600" />
          <span>Conexión con Google Gmail</span>
        </h2>

        {loadingConn ? (
          <div className="py-4 text-xs text-slate-400 flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-emerald-600" />
            <span>Consultando estado de conexión...</span>
          </div>
        ) : googleConn ? (
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
                Última sincronización: {googleConn.last_sync_at ? googleConn.last_sync_at.replace('T', ' ') : 'Recién vinculado'}
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleManualSync}
                disabled={isSyncing}
                className="text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 px-3 py-1.5 rounded-lg transition"
              >
                Escanear Correos
              </button>
              <button
                onClick={handleDisconnectGoogle}
                className="text-xs font-semibold text-rose-600 hover:text-rose-700 bg-rose-50 hover:bg-rose-100 px-3 py-1.5 rounded-lg transition"
              >
                Desconectar Cuenta
              </button>
            </div>
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
              onClick={() => setIsConnectModalOpen(true)}
              className="inline-flex items-center space-x-2 bg-slate-900 hover:bg-slate-800 text-white font-medium px-4 py-2 rounded-xl text-sm transition"
            >
              <Mail className="w-4 h-4 text-emerald-400" />
              <span>Conectar con Google</span>
            </button>
          </div>
        )}
      </div>

      {/* Import Jobs History Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-6 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-slate-900">Historial de Trabajos de Importación</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Auditoría de ejecuciones del pipeline de importación en segundo plano.
            </p>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 bg-slate-100 text-slate-600 rounded-lg">
            {importJobs.length} ejecuciones
          </span>
        </div>

        {loadingJobs ? (
          <div className="p-12 text-center text-slate-400 text-xs">Cargando historial de importaciones...</div>
        ) : importJobs.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <h4 className="text-sm font-semibold text-slate-800">No hay importaciones registradas</h4>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              Pulsa en "Sincronizar Ahora" o conecta tu cuenta de Gmail para comenzar a procesar tickets.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 border-b border-slate-200 font-semibold">
                <tr>
                  <th className="px-6 py-3.5">Fecha y Hora</th>
                  <th className="px-6 py-3.5">Origen</th>
                  <th className="px-6 py-3.5">Estado</th>
                  <th className="px-6 py-3.5 text-center">Mensajes Encontrados</th>
                  <th className="px-6 py-3.5 text-center">Tickets Importados</th>
                  <th className="px-6 py-3.5 text-center">Duplicados Omitidos</th>
                  <th className="px-6 py-3.5 text-center">Errores</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {importJobs.map((job) => (
                  <tr key={job.id} className="hover:bg-slate-50/70 transition">
                    <td className="px-6 py-4 font-mono text-slate-600">
                      {job.started_at ? job.started_at.replace('T', ' ').substring(0, 19) : '—'}
                    </td>
                    <td className="px-6 py-4 font-medium text-slate-800">
                      <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-mono text-[11px]">
                        {job.source_type}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {job.status === 'COMPLETED' ? (
                        <span className="inline-flex items-center space-x-1 text-emerald-600 font-semibold bg-emerald-50 px-2.5 py-0.5 rounded-full">
                          <CheckCircle2 className="w-3 h-3" />
                          <span>Completado</span>
                        </span>
                      ) : job.status === 'PROCESSING' ? (
                        <span className="inline-flex items-center space-x-1 text-blue-600 font-semibold bg-blue-50 px-2.5 py-0.5 rounded-full">
                          <Clock className="w-3 h-3 animate-pulse" />
                          <span>Procesando</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center space-x-1 text-rose-600 font-semibold bg-rose-50 px-2.5 py-0.5 rounded-full">
                          <AlertCircle className="w-3 h-3" />
                          <span>Error</span>
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-center font-mono font-medium text-slate-700">
                      {job.messages_found}
                    </td>
                    <td className="px-6 py-4 text-center font-mono font-bold text-emerald-600">
                      +{job.receipts_imported}
                    </td>
                    <td className="px-6 py-4 text-center font-mono text-slate-500">
                      {job.receipts_skipped}
                    </td>
                    <td className="px-6 py-4 text-center font-mono text-rose-500 font-semibold">
                      {job.errors_count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Connect Modal */}
      {isConnectModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl shadow-xl border border-slate-200 max-w-lg w-full p-6 space-y-6 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Vincular Cuenta de Gmail</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Elige el método de conexión para importar tickets de Mercadona.
                </p>
              </div>
              <button
                onClick={() => setIsConnectModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              {/* Option A: Real Google OAuth */}
              <div className="p-4 rounded-2xl border border-slate-200 hover:border-emerald-500 bg-slate-50/50 transition space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Mail className="w-5 h-5 text-emerald-600" />
                    <span className="text-sm font-bold text-slate-800">Conexión con Google OAuth 2.0 (Real)</span>
                  </div>
                  <span className="text-[10px] uppercase font-semibold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded">
                    Oficial
                  </span>
                </div>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Redirige a la pantalla de consentimiento de Google para autorizar lectura exclusiva de correos con tickets digitales de Mercadona.
                </p>
                <button
                  onClick={handleConnectRealGoogle}
                  className="w-full py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  <span>Ir a Autorizar en Google</span>
                </button>
              </div>

              {/* Option B: Simulation / Mock Mode */}
              <div className="p-4 rounded-2xl border border-emerald-200 bg-emerald-50/30 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-emerald-600" />
                    <span className="text-sm font-bold text-emerald-950">Simulación Gmail (Modo Desarrollo)</span>
                  </div>
                  <span className="text-[10px] uppercase font-semibold bg-emerald-200 text-emerald-900 px-2 py-0.5 rounded">
                    Sin credenciales externas
                  </span>
                </div>
                <p className="text-xs text-emerald-800/80 leading-relaxed">
                  Vincula una cuenta de prueba para probar inmediatamente la sincronización, el pipeline asíncrono y los reportes de importación sin necesidad de configurar Google Cloud Console.
                </p>
                <div className="space-y-2">
                  <input
                    type="email"
                    value={mockEmail}
                    onChange={(e) => setMockEmail(e.target.value)}
                    placeholder="ejemplo@gmail.com"
                    className="w-full px-3 py-1.5 border border-emerald-300 rounded-xl text-xs bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500 font-mono"
                  />
                  <button
                    disabled={connectingMock || !mockEmail.trim()}
                    onClick={handleConnectMockGoogle}
                    className="w-full py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition disabled:opacity-50"
                  >
                    {connectingMock ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <CheckCircle2 className="w-3.5 h-3.5" />
                    )}
                    <span>Vincular y Probar Inmediatamente</span>
                  </button>
                </div>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-[11px] text-slate-500 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
              <span>
                Para la conexión real con tu cuenta personal, recuerda configurar <code>GOOGLE_CLIENT_ID</code> y <code>GOOGLE_CLIENT_SECRET</code> en el archivo <code>backend/.env</code>.
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
