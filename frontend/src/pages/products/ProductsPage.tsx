import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { receiptsApi } from '../../api/receipts.api';
import { Search } from 'lucide-react';

export const ProductsPage: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');

  const { data: receipts = [] } = useQuery({
    queryKey: ['receipts'],
    queryFn: receiptsApi.getAll,
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Catálogo de Productos</h1>
          <p className="text-sm text-slate-500 mt-1">
            Histórico y evolución de precios de los artículos comprados en Mercadona.
          </p>
        </div>
      </div>

      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Buscar por nombre de producto (ej: plátano, pechuga, pizza)..."
            className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
        <h3 className="text-sm font-bold text-slate-800 mb-4 uppercase tracking-wider">
          Resumen de Compras por Tienda
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {receipts
            .filter((r) => !searchTerm || r.store_address?.toLowerCase().includes(searchTerm.toLowerCase()) || r.store_city?.toLowerCase().includes(searchTerm.toLowerCase()))
            .map((r) => (
            <div key={r.id} className="border border-slate-200 rounded-xl p-4 flex items-center justify-between hover:border-emerald-500 transition">
              <div>
                <h4 className="text-sm font-semibold text-slate-900">{r.company_name}</h4>
                <p className="text-xs text-slate-500">{r.store_address}, {r.store_city}</p>
                <span className="inline-block mt-2 text-[11px] font-medium bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-md">
                  Factura {r.invoice_number} ({r.lines_count} artículos)
                </span>
              </div>
              <div className="text-right">
                <div className="text-xl font-bold text-slate-900">{r.total_amount.toFixed(2)} €</div>
                <div className="text-xs text-slate-400">{r.purchase_date}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
