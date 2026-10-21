import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { receiptsApi } from '../../api/receipts.api';
import type { Receipt } from '../../types';
import { ReceiptDetailModal } from '../../components/receipts/ReceiptDetailModal';
import {
  Receipt as ReceiptIcon,
  Search,
  UploadCloud,
  CheckCircle2,
  Calendar,
  MapPin,
  Eye,
  Loader2,
  AlertCircle
} from 'lucide-react';

export const ReceiptsListPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedReceipt, setSelectedReceipt] = useState<Receipt | null>(null);
  const [loadingDetailId, setLoadingDetailId] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  // Fetch receipts from API
  const { data: receipts = [], isLoading } = useQuery({
    queryKey: ['receipts'],
    queryFn: receiptsApi.getAll,
  });

  // Handle click on a receipt to view details
  const handleViewDetail = async (id: string) => {
    try {
      setLoadingDetailId(id);
      const detail = await receiptsApi.getById(id);
      setSelectedReceipt(detail);
    } catch (err: any) {
      alert('Error al cargar el detalle del ticket.');
    } finally {
      setLoadingDetailId(null);
    }
  };

  // Handle PDF upload
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploadError('Por favor, selecciona un archivo en formato PDF.');
      return;
    }

    try {
      setIsUploading(true);
      setUploadError(null);
      const newReceipt = await receiptsApi.uploadPdf(file);
      queryClient.invalidateQueries({ queryKey: ['receipts'] });
      queryClient.invalidateQueries({ queryKey: ['analytics'] });
      setSelectedReceipt(newReceipt);
    } catch (err: any) {
      setUploadError(err.response?.data?.detail || 'Error al procesar el archivo PDF.');
    } finally {
      setIsUploading(false);
      e.target.value = '';
    }
  };

  const filteredReceipts = receipts.filter((r) => {
    const term = searchTerm.toLowerCase();
    return (
      r.invoice_number.toLowerCase().includes(term) ||
      (r.store_address && r.store_address.toLowerCase().includes(term)) ||
      (r.store_city && r.store_city.toLowerCase().includes(term))
    );
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Histórico de Tickets</h1>
          <p className="text-sm text-slate-500 mt-1">
            Consulta, audita y desglosa los tickets digitales de Mercadona.
          </p>
        </div>

        {/* Upload Button */}
        <div>
          <label className="inline-flex items-center space-x-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-4 py-2.5 rounded-xl text-sm shadow-sm transition cursor-pointer">
            {isUploading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <UploadCloud className="w-4 h-4" />
            )}
            <span>{isUploading ? 'Extrayendo datos...' : 'Subir Ticket PDF'}</span>
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileUpload}
              className="hidden"
              disabled={isUploading}
            />
          </label>
        </div>
      </div>

      {uploadError && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-3 flex items-center space-x-2 text-red-700 text-xs">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{uploadError}</span>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Buscar por número de factura (ej: 4534) o localidad..."
            className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
        </div>
      </div>

      {/* Loading & Error States */}
      {isLoading && (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-500">
          <Loader2 className="w-8 h-8 animate-spin mx-auto text-emerald-600 mb-2" />
          <p className="text-sm">Cargando tickets de compra...</p>
        </div>
      )}

      {/* Receipts Table */}
      {!isLoading && filteredReceipts.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold text-xs uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Factura</th>
                  <th className="py-3 px-4">Fecha y Hora</th>
                  <th className="py-3 px-4">Tienda / Localidad</th>
                  <th className="py-3 px-4 text-center">Artículos</th>
                  <th className="py-3 px-4 text-right">Importe Total</th>
                  <th className="py-3 px-4 text-center">Estado</th>
                  <th className="py-3 px-4 text-center">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredReceipts.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50/70 transition">
                    <td className="py-3 px-4 font-bold text-slate-900">
                      <div className="flex items-center space-x-2">
                        <ReceiptIcon className="w-4 h-4 text-emerald-600" />
                        <span>{r.invoice_number}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-slate-600 text-xs">
                      <div className="flex items-center space-x-1.5">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" />
                        <span>{r.purchase_datetime.replace('T', ' ')}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-slate-600 text-xs">
                      <div className="flex items-center space-x-1.5">
                        <MapPin className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                        <span className="truncate max-w-xs">{r.store_address || 'Mercadona'}, {r.store_city || ''}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-center text-xs font-medium text-slate-700">
                      {r.lines_count} líneas
                    </td>
                    <td className="py-3 px-4 text-right font-extrabold text-slate-900 text-base">
                      {r.total_amount.toFixed(2)} €
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        <CheckCircle2 className="w-3 h-3" />
                        <span>Procesado</span>
                      </span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <button
                        onClick={() => handleViewDetail(r.id)}
                        disabled={loadingDetailId === r.id}
                        className="inline-flex items-center space-x-1 bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium px-3 py-1.5 rounded-lg text-xs transition"
                      >
                        {loadingDetailId === r.id ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Eye className="w-3.5 h-3.5" />
                        )}
                        <span>Ver Desglose</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && filteredReceipts.length === 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-12 text-center space-y-3">
          <div className="w-12 h-12 bg-slate-100 rounded-2xl flex items-center justify-center text-slate-400 mx-auto">
            <ReceiptIcon className="w-6 h-6" />
          </div>
          <h3 className="text-base font-semibold text-slate-900">No se encontraron tickets</h3>
          <p className="text-sm text-slate-500 max-w-sm mx-auto">
            Sube un archivo PDF o limpia los filtros de búsqueda.
          </p>
        </div>
      )}

      {/* Modal with Full Line Items and Taxes */}
      <ReceiptDetailModal
        receipt={selectedReceipt}
        onClose={() => setSelectedReceipt(null)}
      />
    </div>
  );
};
