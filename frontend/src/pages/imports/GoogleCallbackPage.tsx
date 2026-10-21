import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { apiClient } from '../../api/client';
import { Loader2, CheckCircle2, AlertCircle } from 'lucide-react';

export const GoogleCallbackPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');

    if (!code || !state) {
      setStatus('error');
      setErrorMessage('Parámetros de autorización de Google no encontrados.');
      return;
    }

    const exchangeCode = async () => {
      try {
        await apiClient.get('/integrations/google/callback', {
          params: { code, state },
        });
        setStatus('success');
        setTimeout(() => {
          navigate('/imports');
        }, 1500);
      } catch (err: any) {
        setStatus('error');
        setErrorMessage(
          err.response?.data?.detail || 'Error al completar la vinculación con Google.'
        );
      }
    };

    exchangeCode();
  }, [searchParams, navigate]);

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="bg-white p-8 rounded-3xl shadow-sm border border-slate-200 max-w-md w-full text-center space-y-4">
        {status === 'processing' && (
          <>
            <Loader2 className="w-12 h-12 text-emerald-600 animate-spin mx-auto" />
            <h2 className="text-lg font-bold text-slate-900">Vinculando cuenta de Google...</h2>
            <p className="text-xs text-slate-500">
              Intercambiando credenciales de autorización y cifrando tokens de acceso.
            </p>
          </>
        )}

        {status === 'success' && (
          <>
            <CheckCircle2 className="w-12 h-12 text-emerald-600 mx-auto" />
            <h2 className="text-lg font-bold text-slate-900">¡Cuenta Conectada con Éxito!</h2>
            <p className="text-xs text-slate-500">
              Redirigiendo al monitor de importaciones...
            </p>
          </>
        )}

        {status === 'error' && (
          <>
            <AlertCircle className="w-12 h-12 text-rose-600 mx-auto" />
            <h2 className="text-lg font-bold text-slate-900">Error en la Conexión</h2>
            <p className="text-xs text-rose-600">{errorMessage}</p>
            <button
              onClick={() => navigate('/imports')}
              className="mt-4 px-4 py-2 bg-slate-900 text-white rounded-xl text-xs font-semibold hover:bg-slate-800 transition"
            >
              Volver a Importaciones
            </button>
          </>
        )}
      </div>
    </div>
  );
};
