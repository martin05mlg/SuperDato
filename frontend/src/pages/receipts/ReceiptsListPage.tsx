import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { receiptsApi } from '../../api/receipts.api';
import { useHousehold } from '../../context/HouseholdContext';
import type { Receipt } from '../../types';
import { ReceiptDetailModal } from '../../components/receipts/ReceiptDetailModal';
import { ManualReceiptModal } from '../../components/receipts/ManualReceiptModal';
import {
  exportReceiptsSummaryCsv,
  exportFullReceiptLinesCsv,
  exportReceiptsJson,
} from '../../utils/export';
import {
  Receipt as ReceiptIcon,
  Search,
  UploadCloud,
  CheckCircle2,
  Calendar,
  MapPin,
  Eye,
  Loader2,
  AlertCircle,
  Home,
  Clock,
  ArrowRight,
  CheckCheck,
  Plus,
  Download,
  FileSpreadsheet,
  FileJson,
  ChevronDown,
  Trash2,
  User,
  ArrowRightLeft,
  X,
} from 'lucide-react';

export const ReceiptsListPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const currentTab = searchParams.get('tab') === 'pending' ? 'pending' : 'household';

  const { activeHousehold, households } = useHousehold();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedReceipt, setSelectedReceipt] = useState<Receipt | null>(null);
  const [loadingDetailId, setLoadingDetailId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isManualModalOpen, setIsManualModalOpen] = useState(false);
  const [isExportMenuOpen, setIsExportMenuOpen] = useState(false);
  const [isExportingLines, setIsExportingLines] = useState(false);

  // Assignment states
  const [assigningId, setAssigningId] = useState<string | null>(null);
  const [rowSelectedHouseholds, setRowSelectedHouseholds] = useState<Record<string, string>>({});
  const [selectedPendingIds, setSelectedPendingIds] = useState<string[]>([]);
  const [bulkTargetHousehold, setBulkTargetHousehold] = useState<string>('');
  const [isBulkAssigning, setIsBulkAssigning] = useState(false);
  const [quickMoveReceipt, setQuickMoveReceipt] = useState<Receipt | null>(null);
  const [quickMoveTarget, setQuickMoveTarget] = useState<string>('');
  const [isQuickMoving, setIsQuickMoving] = useState(false);

  // Fetch receipts scoped to active household
  const { data: receipts = [], isLoading: isLoadingReceipts } = useQuery<Receipt[]>({
    queryKey: ['receipts', activeHousehold?.id],
    queryFn: () => receiptsApi.getAll({ household_id: activeHousehold?.id }),
    enabled: currentTab === 'household',
  });

  // Fetch unassigned pending receipts
  const { data: pendingReceipts = [], isLoading: isLoadingPending } = useQuery<Receipt[]>({
    queryKey: ['pending-receipts'],
    queryFn: receiptsApi.getPending,
    refetchInterval: 15000,
  });

  const pendingCount = pendingReceipts.length;

  const handleTabChange = (tab: 'household' | 'pending') => {
    setSelectedPendingIds([]);
    setBulkTargetHousehold('');
    if (tab === 'pending') {
      setSearchParams({ tab: 'pending' });
    } else {
      setSearchParams({});
    }
  };

  // Handle click on a receipt to view details
  const handleViewDetail = async (id: string) => {
    try {
      setLoadingDetailId(id);
      const detail = await receiptsApi.getById(id);
      setSelectedReceipt(detail);
    } catch {
      alert('Error al cargar el detalle del ticket.');
    } finally {
      setLoadingDetailId(null);
    }
  };

  // Handle receipt deletion
  const handleDeleteReceipt = async (receipt: Receipt) => {
    const confirmDelete = window.confirm(
      `¿Estás seguro de que deseas eliminar permanentemente el ticket ${receipt.invoice_number} (${receipt.total_amount.toFixed(2)} €)? Se eliminarán sus artículos y el histórico asociado.`
    );
    if (!confirmDelete) return;

    try {
      setDeletingId(receipt.id);
      await receiptsApi.deleteReceipt(receipt.id);
      queryClient.invalidateQueries({ queryKey: ['receipts'] });
      queryClient.invalidateQueries({ queryKey: ['pending-receipts'] });
      queryClient.invalidateQueries({ queryKey: ['pending-receipts-count'] });
      queryClient.invalidateQueries({ queryKey: ['analytics'] });
      queryClient.invalidateQueries({ queryKey: ['catalog-products'] });
    } catch {
      alert('Error al eliminar el ticket. Comprueba que tengas permisos de Propietario o Administrador.');
    } finally {
      setDeletingId(null);
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
      const newReceipt = await receiptsApi.uploadPdf(file, activeHousehold?.id);
      queryClient.invalidateQueries({ queryKey: ['receipts'] });
      queryClient.invalidateQueries({ queryKey: ['pending-receipts'] });
      queryClient.invalidateQueries({ queryKey: ['pending-receipts-count'] });
      queryClient.invalidateQueries({ queryKey: ['analytics'] });
      setSelectedReceipt(newReceipt);
    } catch (err: any) {
      setUploadError(err.response?.data?.detail || 'Error al procesar el archivo PDF.');
    } finally {
      setIsUploading(false);
      e.target.value = '';
    }
  };

  // Assign single receipt to a household
  const handleAssignSingle = async (receiptId: string) => {
    const targetHh = rowSelectedHouseholds[receiptId] || activeHousehold?.id || (households[0] ? households[0].id : '');
    if (!targetHh) {
      alert('Por favor selecciona un hogar destino.');
      return;
    }

    try {
      setAssigningId(receiptId);
      await receiptsApi.assignHousehold(receiptId, targetHh);
      await queryClient.invalidateQueries({ queryKey: ['pending-receipts'] });
      await queryClient.invalidateQueries({ queryKey: ['pending-receipts-count'] });
      await queryClient.invalidateQueries({ queryKey: ['receipts'] });
      await queryClient.invalidateQueries({ queryKey: ['analytics'] });
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Error al asignar el ticket al hogar.');
    } finally {
      setAssigningId(null);
    }
  };

  // Bulk assign multiple receipts
  const handleBulkAssign = async () => {
    if (!bulkTargetHousehold) {
      alert('Selecciona un hogar para asignar los tickets seleccionados.');
      return;
    }
    if (selectedPendingIds.length === 0) return;

    try {
      setIsBulkAssigning(true);
      await receiptsApi.bulkAssign(selectedPendingIds, bulkTargetHousehold);
      setSelectedPendingIds([]);
      await queryClient.invalidateQueries({ queryKey: ['pending-receipts'] });
      await queryClient.invalidateQueries({ queryKey: ['pending-receipts-count'] });
      await queryClient.invalidateQueries({ queryKey: ['receipts'] });
      await queryClient.invalidateQueries({ queryKey: ['analytics'] });
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Error al asignar tickets en bloque.');
    } finally {
      setIsBulkAssigning(false);
    }
  };

  const currentList = currentTab === 'household' ? receipts : pendingReceipts;
  const isLoading = currentTab === 'household' ? isLoadingReceipts : isLoadingPending;

  const filteredReceipts = currentList.filter((r) => {
    const term = searchTerm.toLowerCase();
    return (
      (r.invoice_number && r.invoice_number.toLowerCase().includes(term)) ||
      (r.store_address && r.store_address.toLowerCase().includes(term)) ||
      (r.store_city && r.store_city.toLowerCase().includes(term))
    );
  });

  const handleExportFullLines = async () => {
    try {
      setIsExportingLines(true);
      setIsExportMenuOpen(false);
      const detailedReceipts = await Promise.all(
        filteredReceipts.map(async (r) => {
          if (r.lines && r.lines.length > 0) return r;
          try {
            return await receiptsApi.getById(r.id);
          } catch {
            return r;
          }
        })
      );
      exportFullReceiptLinesCsv(detailedReceipts, activeHousehold?.name || 'hogar');
    } catch (err) {
      alert('Error al exportar las líneas de tickets.');
    } finally {
      setIsExportingLines(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Histórico de Tickets</h1>
          <p className="text-sm text-slate-500 mt-1">
            Consulta, audita y asigna los tickets digitales de Mercadona a tus hogares.
          </p>
        </div>

        {/* Action Buttons: Manual, Upload, Export */}
        <div className="flex items-center flex-wrap gap-2">
          {/* Export Dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setIsExportMenuOpen((prev) => !prev)}
              disabled={filteredReceipts.length === 0 || isExportingLines}
              className="inline-flex items-center gap-1.5 px-3 py-2 sm:px-3.5 sm:py-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold rounded-xl text-xs shadow-sm transition disabled:opacity-50 disabled:cursor-not-allowed"
              title="Exportar datos a Excel o JSON"
            >
              {isExportingLines ? (
                <Loader2 className="w-3.5 h-3.5 sm:w-4 sm:h-4 animate-spin text-emerald-600" />
              ) : (
                <Download className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-slate-500" />
              )}
              <span>Exportar</span>
              <ChevronDown className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-slate-400" />
            </button>

            {isExportMenuOpen && (
              <div className="absolute left-0 sm:left-auto sm:right-0 mt-1.5 w-60 bg-white border border-slate-200 rounded-2xl shadow-xl z-20 py-1.5 divide-y divide-slate-100 animate-in fade-in zoom-in-95">
                <button
                  type="button"
                  onClick={() => {
                    setIsExportMenuOpen(false);
                    exportReceiptsSummaryCsv(filteredReceipts, activeHousehold?.name || 'hogar');
                  }}
                  className="w-full px-3.5 py-2 text-left hover:bg-slate-50 flex items-center gap-2.5 text-xs text-slate-700 transition"
                >
                  <FileSpreadsheet className="w-4 h-4 text-emerald-600 shrink-0" />
                  <div>
                    <div className="font-semibold text-slate-800">Excel — Resumen de Tickets</div>
                    <div className="text-[10px] text-slate-400">1 fila por ticket (fecha, tienda, total)</div>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={handleExportFullLines}
                  className="w-full px-3.5 py-2 text-left hover:bg-slate-50 flex items-center gap-2.5 text-xs text-slate-700 transition"
                >
                  <FileSpreadsheet className="w-4 h-4 text-emerald-600 shrink-0" />
                  <div>
                    <div className="font-semibold text-slate-800">Excel — Detalle de Artículos</div>
                    <div className="text-[10px] text-slate-400">Desglose completo producto a producto</div>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setIsExportMenuOpen(false);
                    exportReceiptsJson(filteredReceipts, activeHousehold?.name || 'hogar');
                  }}
                  className="w-full px-3.5 py-2 text-left hover:bg-slate-50 flex items-center gap-2.5 text-xs text-slate-700 transition"
                >
                  <FileJson className="w-4 h-4 text-amber-600 shrink-0" />
                  <div>
                    <div className="font-semibold text-slate-800">Copia de Seguridad JSON</div>
                    <div className="text-[10px] text-slate-400">Formato para archivo o migración</div>
                  </div>
                </button>
              </div>
            )}
          </div>

          {/* New Manual Receipt Button */}
          {activeHousehold && (
            <button
              type="button"
              onClick={() => setIsManualModalOpen(true)}
              className="inline-flex items-center gap-1.5 bg-slate-900 hover:bg-slate-800 text-white font-semibold px-3 py-2 sm:px-4 sm:py-2.5 rounded-xl text-xs shadow-sm transition"
            >
              <Plus className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-emerald-400" />
              <span>+ Manual</span>
            </button>
          )}

          {/* Upload PDF Button */}
          <label className="inline-flex items-center space-x-1.5 sm:space-x-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-3 py-2 sm:px-4 sm:py-2.5 rounded-xl text-xs sm:text-sm shadow-sm transition cursor-pointer">
            {isUploading ? (
              <Loader2 className="w-3.5 h-3.5 sm:w-4 sm:h-4 animate-spin" />
            ) : (
              <UploadCloud className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
            )}
            <span>{isUploading ? 'Extrayendo...' : 'Subir Ticket PDF'}</span>
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

      {/* Tabs Switcher */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-2 overflow-x-auto no-scrollbar">
        <button
          type="button"
          onClick={() => handleTabChange('household')}
          className={`flex items-center justify-center space-x-2 px-3 sm:px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition whitespace-nowrap flex-1 sm:flex-initial ${
            currentTab === 'household'
              ? 'bg-slate-900 text-white shadow-sm'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <Home className="w-4 h-4 shrink-0" />
          <span className="truncate">Tickets de {activeHousehold?.name || 'este Hogar'}</span>
          <span
            className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${
              currentTab === 'household'
                ? 'bg-slate-800 text-slate-200'
                : 'bg-slate-200 text-slate-700'
            }`}
          >
            {receipts.length}
          </span>
        </button>

        <button
          type="button"
          onClick={() => handleTabChange('pending')}
          className={`relative flex items-center justify-center space-x-2 px-3 sm:px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition whitespace-nowrap flex-1 sm:flex-initial ${
            currentTab === 'pending'
              ? 'bg-amber-600 text-white shadow-sm'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <Clock className="w-4 h-4 shrink-0" />
          <span>Pendientes</span>
          {pendingCount > 0 ? (
            <span
              className={`text-xs px-2 py-0.5 rounded-full font-bold shrink-0 ${
                currentTab === 'pending'
                  ? 'bg-amber-800 text-white'
                  : 'bg-amber-100 text-amber-800 border border-amber-300'
              }`}
            >
              {pendingCount}
            </span>
          ) : (
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-200 text-slate-600 shrink-0">0</span>
          )}
        </button>
      </div>

      {/* Household Move Batch Action Bar */}
      {currentTab === 'household' && households.length > 1 && selectedPendingIds.length > 0 && (
        <div className="bg-purple-50 border border-purple-200 rounded-2xl p-3 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 animate-in fade-in">
          <div className="flex items-center space-x-2 text-xs font-semibold text-purple-900">
            <ArrowRightLeft className="w-4 h-4 text-purple-600 shrink-0" />
            <span>{selectedPendingIds.length} tickets seleccionados para mover</span>
          </div>

          <div className="flex flex-col xs:flex-row items-stretch xs:items-center gap-2 w-full sm:w-auto">
            <select
              value={bulkTargetHousehold}
              onChange={(e) => setBulkTargetHousehold(e.target.value)}
              className="text-xs font-medium border border-purple-300 bg-white rounded-xl px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-purple-500 w-full xs:w-auto min-w-0 flex-1 truncate"
            >
              <option value="">Selecciona hogar destino...</option>
              {households
                .filter((h) => h.id !== activeHousehold?.id)
                .map((h) => (
                  <option key={h.id} value={h.id}>
                    {h.name}
                  </option>
                ))}
              <option value="pending">Desasignar (Mover a Pendientes de Asignar)</option>
            </select>

            <button
              type="button"
              onClick={handleBulkAssign}
              disabled={isBulkAssigning || !bulkTargetHousehold}
              className="px-3.5 py-1.5 bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold rounded-xl transition disabled:opacity-50 flex items-center justify-center space-x-1 shrink-0"
            >
              {isBulkAssigning ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <ArrowRightLeft className="w-3.5 h-3.5" />
              )}
              <span>Mover en bloque</span>
            </button>
          </div>
        </div>
      )}

      {/* Pending Batch Action Bar */}
      {currentTab === 'pending' && selectedPendingIds.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-3 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 animate-in fade-in">
          <div className="flex items-center space-x-2 text-xs font-semibold text-amber-900">
            <CheckCheck className="w-4 h-4 text-amber-600 shrink-0" />
            <span>{selectedPendingIds.length} tickets seleccionados</span>
          </div>

          <div className="flex flex-col xs:flex-row items-stretch xs:items-center gap-2 w-full sm:w-auto">
            <select
              value={bulkTargetHousehold}
              onChange={(e) => setBulkTargetHousehold(e.target.value)}
              className="text-xs font-medium border border-amber-300 bg-white rounded-xl px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-amber-500 w-full xs:w-auto min-w-0 flex-1 truncate"
            >
              <option value="">Selecciona hogar destino...</option>
              {households.map((h) => (
                <option key={h.id} value={h.id}>
                  {h.name}
                </option>
              ))}
            </select>

            <button
              type="button"
              onClick={handleBulkAssign}
              disabled={isBulkAssigning || !bulkTargetHousehold}
              className="px-3.5 py-1.5 bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold rounded-xl transition disabled:opacity-50 flex items-center justify-center space-x-1 shrink-0"
            >
              {isBulkAssigning ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <ArrowRight className="w-3.5 h-3.5" />
              )}
              <span>Asignar en bloque</span>
            </button>
          </div>
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

      {/* Loading States */}
      {isLoading && (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-500">
          <Loader2 className="w-8 h-8 animate-spin mx-auto text-emerald-600 mb-2" />
          <p className="text-sm">Cargando tickets...</p>
        </div>
      )}

      {/* Receipts Display: Mobile Cards + Desktop Table */}
      {!isLoading && filteredReceipts.length > 0 && (
        <>
          {/* Mobile Card List (visible on screens < md) */}
          <div className="md:hidden space-y-2.5">
            {filteredReceipts.map((r) => (
              <div
                key={r.id}
                onClick={() => handleViewDetail(r.id)}
                className="bg-white rounded-xl border border-slate-200/90 shadow-2xs p-3 space-y-2 hover:border-slate-300 transition cursor-pointer active:bg-slate-50/60"
              >
                {/* Top Row: Checkbox + Invoice + Amount */}
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center space-x-2 min-w-0">
                    {(currentTab === 'pending' || households.length > 1) && (
                      <input
                        type="checkbox"
                        checked={selectedPendingIds.includes(r.id)}
                        onClick={(e) => e.stopPropagation()}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedPendingIds([...selectedPendingIds, r.id]);
                          } else {
                            setSelectedPendingIds(selectedPendingIds.filter((id) => id !== r.id));
                          }
                        }}
                        className={`rounded border-slate-300 w-4 h-4 shrink-0 ${
                          currentTab === 'pending'
                            ? 'text-amber-600 focus:ring-amber-500'
                            : 'text-purple-600 focus:ring-purple-500'
                        }`}
                      />
                    )}
                    <div className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center shrink-0">
                      <ReceiptIcon className="w-3.5 h-3.5" />
                    </div>
                    <div className="min-w-0">
                      <div className="font-bold text-slate-900 text-xs sm:text-sm truncate">
                        Factura {r.invoice_number}
                      </div>
                      {r.imported_by_name && (
                        <div className="text-[10px] text-slate-400 truncate leading-none mt-0.5">
                          {r.imported_by_name}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="text-right shrink-0">
                    <div className="text-sm font-extrabold text-slate-900 tracking-tight">
                      {r.total_amount.toFixed(2)} €
                    </div>
                    <span className="text-[10px] text-slate-400 font-medium">
                      {r.lines_count} art.
                    </span>
                  </div>
                </div>

                {/* Middle Row: Date & Store in one compact line */}
                <div className="flex items-center justify-between text-[11px] text-slate-500 gap-2 pt-1 border-t border-slate-100">
                  <span className="flex items-center gap-1 shrink-0">
                    <Calendar className="w-3 h-3 text-slate-400 shrink-0" />
                    <span>{r.purchase_datetime ? r.purchase_datetime.replace('T', ' ').slice(0, 16) : ''}</span>
                  </span>
                  <span className="truncate flex items-center gap-1 min-w-0 text-slate-600">
                    <MapPin className="w-3 h-3 text-slate-400 shrink-0" />
                    <span className="truncate">{r.store_address ? `${r.store_address}, ${r.store_city || ''}` : 'Mercadona'}</span>
                  </span>
                </div>

                {/* Bottom Row: Pending controls OR detail & move actions */}
                {currentTab === 'pending' ? (
                  <div
                    className="pt-1.5 border-t border-slate-100 flex items-center justify-between gap-1.5"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <select
                      value={
                        rowSelectedHouseholds[r.id] ||
                        activeHousehold?.id ||
                        (households[0] ? households[0].id : '')
                      }
                      onChange={(e) =>
                        setRowSelectedHouseholds({
                          ...rowSelectedHouseholds,
                          [r.id]: e.target.value,
                        })
                      }
                      className="text-xs font-semibold border border-amber-200 bg-amber-50/50 text-slate-800 rounded-lg px-2 py-1 focus:outline-none focus:ring-1 focus:ring-amber-500 flex-1 min-w-0 truncate"
                    >
                      {households.map((h) => (
                        <option key={h.id} value={h.id}>
                          {h.name}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      onClick={() => handleAssignSingle(r.id)}
                      disabled={assigningId === r.id}
                      className="inline-flex items-center space-x-1 bg-amber-600 hover:bg-amber-700 text-white font-semibold px-2.5 py-1 rounded-lg text-xs transition disabled:opacity-50 shrink-0 shadow-xs"
                    >
                      {assigningId === r.id ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <ArrowRight className="w-3 h-3" />
                      )}
                      <span>Asignar</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleViewDetail(r.id)}
                      disabled={loadingDetailId === r.id}
                      className="p-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs transition shrink-0"
                      title="Ver desglose"
                    >
                      <Eye className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ) : (
                  <div
                    className="pt-1.5 border-t border-slate-100 flex items-center justify-between gap-1.5"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <span className="inline-flex items-center space-x-1 text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full text-[10px] font-semibold border border-emerald-200">
                      <CheckCircle2 className="w-2.5 h-2.5 shrink-0" />
                      <span>Procesado</span>
                    </span>

                    <div className="flex items-center space-x-1 shrink-0">
                      {households.length > 1 && (
                        <button
                          onClick={() => {
                            setQuickMoveReceipt(r);
                            setQuickMoveTarget('');
                          }}
                          className="inline-flex items-center space-x-1 bg-purple-50 hover:bg-purple-100 text-purple-700 font-semibold px-2 py-1 rounded-lg text-[11px] transition border border-purple-200"
                        >
                          <ArrowRightLeft className="w-3 h-3 text-purple-600" />
                          <span>Mover</span>
                        </button>
                      )}

                      <button
                        onClick={() => handleViewDetail(r.id)}
                        disabled={loadingDetailId === r.id}
                        className="inline-flex items-center space-x-1 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold px-2.5 py-1 rounded-lg text-[11px] transition"
                      >
                        {loadingDetailId === r.id ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          <Eye className="w-3 h-3" />
                        )}
                        <span>Detalle</span>
                      </button>

                      <button
                        onClick={() => handleDeleteReceipt(r)}
                        disabled={deletingId === r.id}
                        className="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
                        title="Eliminar ticket"
                      >
                        {deletingId === r.id ? (
                          <Loader2 className="w-3 h-3 animate-spin text-rose-600" />
                        ) : (
                          <Trash2 className="w-3 h-3" />
                        )}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Desktop Table (hidden on mobile, visible on md+) */}
          <div className="hidden md:block bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold text-xs uppercase tracking-wider">
                  <tr>
                    {(currentTab === 'pending' || households.length > 1) && (
                      <th className="py-3 px-3 w-10 text-center">
                        <input
                          type="checkbox"
                          checked={
                            filteredReceipts.length > 0 &&
                            selectedPendingIds.length === filteredReceipts.length
                          }
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedPendingIds(filteredReceipts.map((r) => r.id));
                            } else {
                              setSelectedPendingIds([]);
                            }
                          }}
                          className={`rounded border-slate-300 ${
                            currentTab === 'pending'
                              ? 'text-amber-600 focus:ring-amber-500'
                              : 'text-purple-600 focus:ring-purple-500'
                          }`}
                        />
                      </th>
                    )}
                    <th className="py-3 px-4">Factura</th>
                    <th className="py-3 px-4">Fecha y Hora</th>
                    <th className="py-3 px-4">Tienda / Localidad</th>
                    <th className="py-3 px-4 text-center">Artículos</th>
                    <th className="py-3 px-4 text-right">Importe Total</th>
                    <th className="py-3 px-4 text-center">
                      {currentTab === 'pending' ? 'Destino / Asignación' : 'Estado'}
                    </th>
                    <th className="py-3 px-4 text-center">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredReceipts.map((r) => (
                    <tr key={r.id} className="hover:bg-slate-50/70 transition">
                      {(currentTab === 'pending' || households.length > 1) && (
                        <td className="py-3 px-3 text-center">
                          <input
                            type="checkbox"
                            checked={selectedPendingIds.includes(r.id)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setSelectedPendingIds([...selectedPendingIds, r.id]);
                              } else {
                                setSelectedPendingIds(selectedPendingIds.filter((id) => id !== r.id));
                              }
                            }}
                            className={`rounded border-slate-300 ${
                              currentTab === 'pending'
                                ? 'text-amber-600 focus:ring-amber-500'
                                : 'text-purple-600 focus:ring-purple-500'
                            }`}
                          />
                        </td>
                      )}
                      <td className="py-3 px-4 font-bold text-slate-900">
                        <div className="flex items-center space-x-2">
                          <ReceiptIcon
                            className={`w-4 h-4 ${
                              currentTab === 'pending' ? 'text-amber-600' : 'text-emerald-600'
                            }`}
                          />
                          <span>{r.invoice_number}</span>
                        </div>
                        {r.imported_by_name && (
                          <div className="flex items-center space-x-1 text-[11px] text-slate-500 font-normal mt-0.5">
                            <User className="w-3 h-3 text-slate-400" />
                            <span>{r.imported_by_name}</span>
                          </div>
                        )}
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
                          <span className="truncate max-w-xs">
                            {r.store_address || 'Mercadona'}, {r.store_city || ''}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-center text-xs font-medium text-slate-700">
                        {r.lines_count} líneas
                      </td>
                      <td className="py-3 px-4 text-right font-extrabold text-slate-900 text-base">
                        {r.total_amount.toFixed(2)} €
                      </td>

                      {/* Status or Assignment Control */}
                      <td className="py-3 px-4 text-center">
                        {currentTab === 'pending' ? (
                          <div className="flex items-center justify-center space-x-2">
                            <select
                              value={
                                rowSelectedHouseholds[r.id] ||
                                activeHousehold?.id ||
                                (households[0] ? households[0].id : '')
                              }
                              onChange={(e) =>
                                setRowSelectedHouseholds({
                                 ...rowSelectedHouseholds,
                                  [r.id]: e.target.value,
                                })
                              }
                              className="text-xs font-medium border border-slate-200 bg-white rounded-lg px-2.5 py-1 focus:outline-none focus:ring-2 focus:ring-amber-500"
                            >
                              {households.map((h) => (
                                <option key={h.id} value={h.id}>
                                  {h.name}
                                </option>
                              ))}
                            </select>
                            <button
                              type="button"
                              onClick={() => handleAssignSingle(r.id)}
                              disabled={assigningId === r.id}
                              className="inline-flex items-center space-x-1 bg-amber-600 hover:bg-amber-700 text-white font-semibold px-2.5 py-1 rounded-lg text-xs transition disabled:opacity-50"
                            >
                              {assigningId === r.id ? (
                                <Loader2 className="w-3 h-3 animate-spin" />
                              ) : (
                                <ArrowRight className="w-3 h-3" />
                              )}
                              <span>Asignar</span>
                            </button>
                          </div>
                        ) : (
                          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            <CheckCircle2 className="w-3 h-3" />
                            <span>Procesado</span>
                          </span>
                        )}
                      </td>

                      <td className="py-3 px-4 text-center">
                        <div className="flex items-center justify-center space-x-1.5">
                          {households.length > 1 && currentTab === 'household' && (
                            <button
                              onClick={() => {
                                setQuickMoveReceipt(r);
                                setQuickMoveTarget('');
                              }}
                              className="inline-flex items-center space-x-1 bg-purple-50 hover:bg-purple-100 text-purple-700 font-medium px-2.5 py-1.5 rounded-lg text-xs transition border border-purple-200"
                              title="Mover ticket a otro hogar"
                            >
                              <ArrowRightLeft className="w-3.5 h-3.5 text-purple-600" />
                              <span>Mover</span>
                            </button>
                          )}

                          <button
                            onClick={() => handleViewDetail(r.id)}
                            disabled={loadingDetailId === r.id}
                            className="inline-flex items-center space-x-1 bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium px-3 py-1.5 rounded-lg text-xs transition"
                            title="Ver desglose detallado"
                          >
                            {loadingDetailId === r.id ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            ) : (
                              <Eye className="w-3.5 h-3.5" />
                            )}
                            <span>Ver Desglose</span>
                          </button>

                          <button
                            onClick={() => handleDeleteReceipt(r)}
                            disabled={deletingId === r.id}
                            className="inline-flex items-center justify-center p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition disabled:opacity-50"
                            title="Eliminar ticket"
                          >
                            {deletingId === r.id ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin text-rose-600" />
                            ) : (
                              <Trash2 className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* Empty State */}
      {!isLoading && filteredReceipts.length === 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-12 text-center space-y-3">
          <div className="w-12 h-12 bg-slate-100 rounded-2xl flex items-center justify-center text-slate-400 mx-auto">
            {currentTab === 'pending' ? (
              <Clock className="w-6 h-6 text-amber-500" />
            ) : (
              <ReceiptIcon className="w-6 h-6" />
            )}
          </div>
          <h3 className="text-base font-semibold text-slate-900">
            {currentTab === 'pending'
              ? 'No tienes tickets pendientes de asignar'
              : 'No se encontraron tickets'}
          </h3>
          <p className="text-sm text-slate-500 max-w-sm mx-auto">
            {currentTab === 'pending'
              ? 'Todos tus tickets importados están asignados correctamente a sus hogares.'
              : searchTerm
              ? 'Limpia los filtros de búsqueda para ver más tickets.'
              : `Aún no hay tickets registrados en ${activeHousehold?.name || 'este hogar'}. Sube tu primer ticket en PDF con el botón superior.`}
          </p>
        </div>
      )}

      {/* Manual Receipt Modal */}
      {activeHousehold && (
        <ManualReceiptModal
          isOpen={isManualModalOpen}
          onClose={() => setIsManualModalOpen(false)}
          householdId={activeHousehold.id}
          onSuccess={(receiptId) => {
            queryClient.invalidateQueries({ queryKey: ['receipts'] });
            queryClient.invalidateQueries({ queryKey: ['analytics'] });
            queryClient.invalidateQueries({ queryKey: ['catalog-products'] });
            handleViewDetail(receiptId);
          }}
        />
      )}

      {/* Quick Move Single Receipt Modal */}
      {quickMoveReceipt && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6 animate-in fade-in duration-150">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
              <div className="flex items-center space-x-2 text-slate-800 font-bold text-sm">
                <ArrowRightLeft className="w-4 h-4 text-purple-600" />
                <span>Mover Ticket de Hogar</span>
              </div>
              <button
                onClick={() => {
                  setQuickMoveReceipt(null);
                  setQuickMoveTarget('');
                }}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-600 mb-4">
              Vas a mover el ticket <strong>{quickMoveReceipt.invoice_number}</strong> por importe de{' '}
              <strong>{quickMoveReceipt.total_amount.toFixed(2)} €</strong>.
            </p>

            <div className="mb-5">
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                Hogar de destino
              </label>
              <select
                value={quickMoveTarget}
                onChange={(e) => setQuickMoveTarget(e.target.value)}
                className="w-full text-xs font-medium border border-slate-200 bg-white rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
              >
                <option value="">Selecciona el hogar destino...</option>
                {households
                  .filter((h) => h.id !== quickMoveReceipt.household_id)
                  .map((h) => (
                    <option key={h.id} value={h.id}>
                      {h.name}
                    </option>
                  ))}
                {quickMoveReceipt.household_id && (
                  <option value="pending">Desasignar (Mover a Pendientes de Asignar)</option>
                )}
              </select>
            </div>

            <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => {
                  setQuickMoveReceipt(null);
                  setQuickMoveTarget('');
                }}
                className="px-3.5 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={!quickMoveTarget || isQuickMoving}
                onClick={async () => {
                  if (!quickMoveReceipt || !quickMoveTarget) return;
                  try {
                    setIsQuickMoving(true);
                    await receiptsApi.assignHousehold(quickMoveReceipt.id, quickMoveTarget);
                    await queryClient.invalidateQueries({ queryKey: ['receipts'] });
                    await queryClient.invalidateQueries({ queryKey: ['pending-receipts'] });
                    await queryClient.invalidateQueries({ queryKey: ['pending-receipts-count'] });
                    await queryClient.invalidateQueries({ queryKey: ['analytics'] });
                    setQuickMoveReceipt(null);
                    setQuickMoveTarget('');
                  } catch (err: any) {
                    alert(err.response?.data?.detail || 'Error al mover el ticket.');
                  } finally {
                    setIsQuickMoving(false);
                  }
                }}
                className="px-4 py-2 text-xs font-semibold bg-purple-600 hover:bg-purple-700 text-white rounded-xl transition disabled:opacity-50 flex items-center space-x-1.5"
              >
                {isQuickMoving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ArrowRightLeft className="w-3.5 h-3.5" />}
                <span>Mover Ticket</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal with Full Line Items and Taxes */}
      <ReceiptDetailModal
        receipt={selectedReceipt}
        onClose={() => setSelectedReceipt(null)}
        onReceiptDeleted={() => {
          setSelectedReceipt(null);
          queryClient.invalidateQueries({ queryKey: ['receipts'] });
          queryClient.invalidateQueries({ queryKey: ['pending-receipts'] });
          queryClient.invalidateQueries({ queryKey: ['pending-receipts-count'] });
          queryClient.invalidateQueries({ queryKey: ['analytics'] });
          queryClient.invalidateQueries({ queryKey: ['catalog-products'] });
        }}
        onReceiptUpdated={() => {
          queryClient.invalidateQueries({ queryKey: ['receipts'] });
          queryClient.invalidateQueries({ queryKey: ['analytics'] });
        }}
      />
    </div>
  );
};
