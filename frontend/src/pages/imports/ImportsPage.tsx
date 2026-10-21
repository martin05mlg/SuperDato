import React from 'react';
import { RefreshCw, Mail } from 'lucide-react';

export const ImportsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Monitor de Importaciones</h1>
          <p className="text-sm text-slate-500 mt-1">
            Histórico de sincronizaciones con Gmail, tickets detectados y errores.
          </p>
        </div>

        <button className="inline-flex items-center space-x-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-4 py-2 rounded-xl text-sm shadow-sm transition">
          <RefreshCw className="w-4 h-4" />
          <span>Sincronizar Ahora</span>
        </button>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-8 space-y-4">
        <div className="flex items-start space-x-4">
          <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center text-slate-600">
            <Mail className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-slate-900">Estado de Gmail</h3>
            <p className="text-sm text-slate-500 mt-0.5">
              No tienes ninguna cuenta de Gmail conectada a este hogar actualmente.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
