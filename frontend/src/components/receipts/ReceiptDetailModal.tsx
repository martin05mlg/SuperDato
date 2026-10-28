import React, { useState } from 'react';
import type { Receipt, ReceiptLine } from '../../types';
import {
  X,
  CheckCircle2,
  Calendar,
  MapPin,
  CreditCard,
  Receipt as ReceiptIcon,
  Edit2,
  Check,
  AlertCircle,
  Package,
  Trash2,
  Loader2,
  Home,
  ArrowRightLeft,
} from 'lucide-react';
import { receiptsApi } from '../../api/receipts.api';
import { useHousehold } from '../../context/HouseholdContext';

interface Props {
  receipt: Receipt | null;
  onClose: () => void;
  onReceiptUpdated?: (updated: Receipt) => void;
  onReceiptDeleted?: (receiptId: string) => void;
}

export const ReceiptDetailModal: React.FC<Props> = ({ receipt, onClose, onReceiptUpdated, onReceiptDeleted }) => {
  const [currentReceipt, setCurrentReceipt] = useState<Receipt | null>(receipt);
  const [editingLineId, setEditingLineId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [editForm, setEditForm] = useState<{
    raw_description: string;
    quantity: number;
    unit_price: number;
    line_total: number;
  }>({
    raw_description: '',
    quantity: 1,
    unit_price: 0,
    line_total: 0,
  });
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const { households, activeHousehold } = useHousehold();
  const [targetHouseholdId, setTargetHouseholdId] = useState<string>('');
  const [isMoving, setIsMoving] = useState(false);
  const [moveFeedback, setMoveFeedback] = useState<string | null>(null);

  const currentHousehold = households.find((h) => h.id === currentReceipt?.household_id);

  const handleMoveHousehold = async () => {
    if (!currentReceipt || !targetHouseholdId) return;
    try {
      setIsMoving(true);
      setMoveFeedback(null);
      await receiptsApi.assignHousehold(currentReceipt.id, targetHouseholdId);

      const targetName =
        targetHouseholdId === 'pending'
          ? 'Pendientes de asignar'
          : households.find((h) => h.id === targetHouseholdId)?.name || 'otro hogar';

      setMoveFeedback(`Ticket transferido con éxito a ${targetName}.`);

      if (onReceiptDeleted && targetHouseholdId !== activeHousehold?.id) {
        setTimeout(() => {
          onReceiptDeleted(currentReceipt.id);
          onClose();
        }, 1200);
      } else if (onReceiptUpdated) {
        onReceiptUpdated({
          ...currentReceipt,
          household_id: targetHouseholdId === 'pending' ? undefined : targetHouseholdId,
          assignment_status: targetHouseholdId === 'pending' ? 'PENDING_ASSIGNMENT' : 'ASSIGNED',
        });
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Error al mover el ticket de hogar.');
    } finally {
      setIsMoving(false);
    }
  };

  // Sync internal state when prop changes
  React.useEffect(() => {
    setCurrentReceipt(receipt);
    setEditingLineId(null);
  }, [receipt]);

  if (!currentReceipt) return null;

  const handleStartEdit = (line: ReceiptLine) => {
    setEditingLineId(line.id);
    setEditForm({
      raw_description: line.raw_description,
      quantity: line.quantity,
      unit_price: line.unit_price,
      line_total: line.line_total,
    });
    setSaveError(null);
  };

  const handleSaveLine = async (lineId: string) => {
    if (!currentReceipt) return;
    try {
      setIsSaving(true);
      setSaveError(null);

      const updatedLine = await receiptsApi.updateLine(currentReceipt.id, lineId, editForm);

      // Update in memory
      const updatedLines = (currentReceipt.lines || []).map((l) =>
        l.id === lineId ? { ...l, ...updatedLine } : l
      );
      const newTotal = updatedLines.reduce((acc, l) => acc + (l.line_total || 0), 0);

      const updatedReceipt: Receipt = {
        ...currentReceipt,
        is_manual_override: true,
        total_amount: Math.round(newTotal * 100) / 100,
        lines: updatedLines,
      };

      setCurrentReceipt(updatedReceipt);
      setEditingLineId(null);
      if (onReceiptUpdated) {
        onReceiptUpdated(updatedReceipt);
      }
    } catch (err: any) {
      setSaveError(err.response?.data?.detail || 'Error al guardar la corrección de la línea.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!currentReceipt) return;
    const confirmDelete = window.confirm(
      `¿Estás seguro de que deseas eliminar permanentemente el ticket ${currentReceipt.invoice_number}? Se borrarán también sus líneas y observaciones asociadas.`
    );
    if (!confirmDelete) return;

    try {
      setIsDeleting(true);
      await receiptsApi.deleteReceipt(currentReceipt.id);
      if (onReceiptDeleted) {
        onReceiptDeleted(currentReceipt.id);
      }
      onClose();
    } catch {
      alert('Error al eliminar el ticket. Comprueba que tengas permisos de Propietario o Administrador.');
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-2 sm:p-4">
      <div className="bg-white rounded-2xl sm:rounded-3xl shadow-xl max-w-3xl w-full max-h-[92vh] sm:max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in duration-200">
        {/* Header */}
        <div className="px-4 sm:px-6 py-3.5 sm:py-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center space-x-2.5 sm:space-x-3 min-w-0">
            <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-emerald-600 flex items-center justify-center text-white shrink-0">
              <ReceiptIcon className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                <h3 className="text-sm sm:text-base font-bold text-slate-900 truncate">
                  Factura {currentReceipt.invoice_number}
                </h3>
                <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[11px] sm:text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 shrink-0">
                  <CheckCircle2 className="w-3 h-3" />
                  <span>Procesado</span>
                </span>
                {currentReceipt.is_manual_override && (
                  <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[11px] sm:text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200 shrink-0">
                    <span>Manual</span>
                  </span>
                )}
              </div>
              <p className="text-[11px] sm:text-xs text-slate-500 mt-0.5 truncate">
                {currentReceipt.company_name} ({currentReceipt.company_cif})
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 sm:p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-xl transition shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Info Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 sm:gap-4 px-4 sm:px-6 py-2.5 sm:py-3.5 bg-slate-50/30 border-b border-slate-100 text-xs">
          <div className="flex items-center space-x-2 text-slate-600 truncate">
            <MapPin className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-emerald-600 shrink-0" />
            <span className="truncate">
              {currentReceipt.store_address
                ? `${currentReceipt.store_address}, ${currentReceipt.store_city || ''}`
                : 'Tienda Mercadona'}
            </span>
          </div>
          <div className="flex items-center space-x-2 text-slate-600">
            <Calendar className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-emerald-600 shrink-0" />
            <span>{currentReceipt.purchase_datetime.replace('T', ' ')}</span>
          </div>
          <div className="flex items-center space-x-2 text-slate-600">
            <CreditCard className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-emerald-600 shrink-0" />
            <span>
              {currentReceipt.payment_method || 'Tarjeta'}{' '}
              {currentReceipt.card_last_four ? `(**** ${currentReceipt.card_last_four})` : ''}
            </span>
          </div>
        </div>

        {/* Household Reassignment Box (Visible if multiple households exist) */}
        {households.length > 1 && (
          <div className="px-4 sm:px-6 py-2.5 sm:py-3 bg-purple-50/70 border-b border-purple-100 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2.5 text-xs">
            <div className="flex items-center space-x-2.5 min-w-0">
              <div className="w-7 h-7 rounded-lg bg-purple-100 text-purple-700 flex items-center justify-center shrink-0">
                <Home className="w-3.5 h-3.5" />
              </div>
              <div className="min-w-0">
                <span className="font-bold text-slate-800">Hogar: </span>
                <span className="font-semibold text-purple-700 truncate">
                  {currentHousehold?.name || (currentReceipt.household_id ? 'Hogar asignado' : 'Pendiente de asignar')}
                </span>
                {moveFeedback && (
                  <p className="text-emerald-600 font-medium text-[11px] animate-in fade-in">{moveFeedback}</p>
                )}
              </div>
            </div>

            <div className="flex items-center space-x-2 w-full sm:w-auto">
              <select
                value={targetHouseholdId}
                onChange={(e) => setTargetHouseholdId(e.target.value)}
                className="text-xs font-medium border border-purple-200 bg-white rounded-xl px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-purple-500 text-slate-700 flex-1 sm:flex-initial min-w-0 truncate"
              >
                <option value="">Mover ticket a...</option>
                {households
                  .filter((h) => h.id !== currentReceipt.household_id)
                  .map((h) => (
                    <option key={h.id} value={h.id}>
                      {h.name}
                    </option>
                  ))}
                {currentReceipt.household_id && (
                  <option value="pending">Desasignar (Mover a Pendientes)</option>
                )}
              </select>
              <button
                type="button"
                onClick={handleMoveHousehold}
                disabled={isMoving || !targetHouseholdId}
                className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white font-semibold rounded-xl text-xs transition disabled:opacity-50 flex items-center space-x-1 shrink-0"
              >
                {isMoving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ArrowRightLeft className="w-3.5 h-3.5" />}
                <span>Mover</span>
              </button>
            </div>
          </div>
        )}

        {/* Scrollable Line Items */}
        <div className="flex-1 overflow-y-auto px-3.5 sm:px-6 py-4 space-y-4 sm:space-y-6">
          {saveError && (
            <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{saveError}</span>
            </div>
          )}

          {/* Items Table */}
          <div>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-2.5">
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Líneas de Compra ({currentReceipt.lines?.length || 0} artículos)
              </h4>
              <span className="text-[10px] sm:text-[11px] text-slate-400 italic">
                Haz clic en el lápiz para corregir manualmente una línea
              </span>
            </div>

            <div className="border border-slate-200 rounded-2xl overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
                  <tr>
                    <th className="py-2.5 px-3">#</th>
                    <th className="py-2.5 px-3">Artículo</th>
                    <th className="py-2.5 px-3">Categoría</th>
                    <th className="py-2.5 px-3 text-right">Cant / Peso</th>
                    <th className="py-2.5 px-3 text-right">P. Unit</th>
                    <th className="py-2.5 px-3 text-right font-bold text-slate-800">Total</th>
                    <th className="py-2.5 px-3 text-right">Acción</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {currentReceipt.lines?.map((line) => {
                    const isEditing = editingLineId === line.id;

                    if (isEditing) {
                      return (
                        <tr key={line.id} className="bg-amber-50/50">
                          <td className="py-2 px-3 text-slate-400">{line.line_order}</td>
                          <td className="py-2 px-3">
                            <input
                              type="text"
                              value={editForm.raw_description}
                              onChange={(e) =>
                                setEditForm({ ...editForm, raw_description: e.target.value })
                              }
                              className="w-full px-2 py-1 text-xs border border-amber-300 rounded font-medium focus:outline-none focus:ring-1 focus:ring-amber-500"
                            />
                          </td>
                          <td className="py-2 px-3 text-slate-500">
                            {line.category_name || 'Alimentación'}
                          </td>
                          <td className="py-2 px-3 text-right">
                            <input
                              type="number"
                              step="0.001"
                              value={editForm.quantity}
                              onChange={(e) => {
                                const q = parseFloat(e.target.value) || 0;
                                const tot = Math.round(q * editForm.unit_price * 100) / 100;
                                setEditForm({ ...editForm, quantity: q, line_total: tot });
                              }}
                              className="w-16 px-1.5 py-1 text-xs border border-amber-300 rounded text-right focus:outline-none focus:ring-1 focus:ring-amber-500"
                            />
                          </td>
                          <td className="py-2 px-3 text-right">
                            <input
                              type="number"
                              step="0.01"
                              value={editForm.unit_price}
                              onChange={(e) => {
                                const p = parseFloat(e.target.value) || 0;
                                const tot = Math.round(editForm.quantity * p * 100) / 100;
                                setEditForm({ ...editForm, unit_price: p, line_total: tot });
                              }}
                              className="w-16 px-1.5 py-1 text-xs border border-amber-300 rounded text-right focus:outline-none focus:ring-1 focus:ring-amber-500"
                            />
                          </td>
                          <td className="py-2 px-3 text-right">
                            <input
                              type="number"
                              step="0.01"
                              value={editForm.line_total}
                              onChange={(e) =>
                                setEditForm({
                                  ...editForm,
                                  line_total: parseFloat(e.target.value) || 0,
                                })
                              }
                              className="w-16 px-1.5 py-1 text-xs border border-amber-300 rounded text-right font-bold focus:outline-none focus:ring-1 focus:ring-amber-500"
                            />
                          </td>
                          <td className="py-2 px-3 text-right space-x-1">
                            <button
                              disabled={isSaving}
                              onClick={() => handleSaveLine(line.id)}
                              className="p-1 text-emerald-600 hover:bg-emerald-100 rounded transition"
                              title="Guardar"
                            >
                              <Check className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => setEditingLineId(null)}
                              className="p-1 text-slate-400 hover:bg-slate-100 rounded transition"
                              title="Cancelar"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </td>
                        </tr>
                      );
                    }

                    return (
                      <tr key={line.id} className="hover:bg-slate-50/50">
                        <td className="py-2.5 px-3 text-slate-400">{line.line_order}</td>
                        <td className="py-2.5 px-3">
                          <div className="flex items-center gap-2.5">
                            {line.image_url ? (
                              <img
                                src={line.image_url}
                                alt={line.raw_description}
                                className="w-9 h-9 object-contain rounded-lg border border-slate-200 bg-white p-0.5 flex-shrink-0"
                                loading="lazy"
                              />
                            ) : (
                              <div className="w-9 h-9 rounded-lg bg-slate-100 flex items-center justify-center text-slate-400 flex-shrink-0">
                                <Package className="w-4 h-4" />
                              </div>
                            )}
                            <div className="min-w-0">
                              <div className="font-medium text-slate-800 flex items-center gap-1.5 flex-wrap">
                                <span>{line.enriched_name || line.product_name || line.raw_description}</span>
                                {line.brand && (
                                  <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 flex-shrink-0">
                                    {line.brand}
                                  </span>
                                )}
                                {line.is_weighed_item && (
                                  <span className="px-1.5 py-0.2 rounded text-[9px] bg-amber-50 text-amber-700 border border-amber-200 flex-shrink-0">
                                    Granel
                                  </span>
                                )}
                                {line.is_manual_override && (
                                  <span className="px-1.5 py-0.2 rounded text-[9px] bg-blue-50 text-blue-700 border border-blue-200 flex-shrink-0">
                                    Editado
                                  </span>
                                )}
                              </div>
                              {line.enriched_name && line.enriched_name !== line.raw_description && (
                                <div className="text-[10px] text-slate-400 font-mono">
                                  Ticket: {line.raw_description}
                                </div>
                              )}
                              {line.packaging && (
                                <div className="text-[10px] text-slate-400">{line.packaging}</div>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="py-2 px-3">
                          <span className="inline-block px-2 py-0.5 rounded-md text-[11px] bg-slate-100 text-slate-700">
                            {line.category_name || 'Alimentación'}
                          </span>
                        </td>
                        <td className="py-2 px-3 text-right text-slate-600">
                          {line.quantity} {line.unit_of_measure}
                        </td>
                        <td className="py-2 px-3 text-right text-slate-600">
                          <div>{line.unit_price.toFixed(2)} €</div>
                          {line.price_change_pct !== undefined && line.price_change_pct !== null && (
                            <span
                              className={`inline-block px-1 py-0.5 rounded text-[9px] font-bold mt-0.5 ${
                                line.price_change_pct > 0
                                  ? 'bg-rose-50 text-rose-700 border border-rose-200'
                                  : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              }`}
                              title={
                                line.previous_unit_price
                                  ? `Precio anterior registrado: ${line.previous_unit_price.toFixed(2)} € (${line.price_change_pct > 0 ? '+' : ''}${line.price_change_pct}%)`
                                  : undefined
                              }
                            >
                              {line.price_change_pct > 0 ? `↑ +${line.price_change_pct}%` : `↓ ${line.price_change_pct}%`}
                            </span>
                          )}
                        </td>
                        <td className="py-2 px-3 text-right font-bold text-slate-900">
                          {line.line_total.toFixed(2)} €
                        </td>
                        <td className="py-2 px-3 text-right">
                          <button
                            onClick={() => handleStartEdit(line)}
                            className="p-1 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 rounded transition"
                            title="Editar línea"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Tax Breakdown */}
          {currentReceipt.tax_lines && currentReceipt.tax_lines.length > 0 && (
            <div>
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-3">
                Desglose Fiscal (IVA)
              </h4>
              <div className="border border-slate-200 rounded-2xl overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
                    <tr>
                      <th className="py-2 px-3">Tipo IVA</th>
                      <th className="py-2 px-3 text-right">Base Imponible</th>
                      <th className="py-2 px-3 text-right">Cuota IVA</th>
                      <th className="py-2 px-3 text-right font-bold text-slate-800">Total con IVA</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {currentReceipt.tax_lines.map((tax) => (
                      <tr key={tax.id}>
                        <td className="py-2 px-3 font-semibold text-slate-800">
                          {tax.tax_rate_percent}%
                        </td>
                        <td className="py-2 px-3 text-right text-slate-600">
                          {tax.taxable_base.toFixed(2)} €
                        </td>
                        <td className="py-2 px-3 text-right text-slate-600">
                          {tax.tax_amount.toFixed(2)} €
                        </td>
                        <td className="py-2 px-3 text-right font-bold text-slate-900">
                          {tax.total_with_tax.toFixed(2)} €
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Footer with Totals */}
        <div className="px-4 sm:px-6 py-3 sm:py-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between gap-3">
          <div className="flex items-center space-x-2 sm:space-x-3">
            <button
              onClick={handleDelete}
              disabled={isDeleting}
              className="inline-flex items-center space-x-1 sm:space-x-1.5 px-2.5 sm:px-3 py-1.5 text-xs font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 rounded-lg transition disabled:opacity-50"
            >
              {isDeleting ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Trash2 className="w-3.5 h-3.5" />
              )}
              <span className="hidden xs:inline">Eliminar</span>
            </button>
            <div className="text-xs text-slate-500 hidden sm:flex items-center space-x-1">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>Conciliado</span>
            </div>
          </div>

          <div className="flex items-center space-x-2 sm:space-x-3">
            <span className="text-xs sm:text-sm text-slate-600">Total:</span>
            <span className="text-lg sm:text-2xl font-black text-slate-900">
              {currentReceipt.total_amount.toFixed(2)} €
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
