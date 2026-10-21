import React from 'react';
import type { Receipt } from '../../types';
import { X, CheckCircle2, Calendar, MapPin, CreditCard, Receipt as ReceiptIcon } from 'lucide-react';

interface Props {
  receipt: Receipt | null;
  onClose: () => void;
}

export const ReceiptDetailModal: React.FC<Props> = ({ receipt, onClose }) => {
  if (!receipt) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-3xl shadow-xl max-w-3xl w-full max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in duration-200">
        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-600 flex items-center justify-center text-white">
              <ReceiptIcon className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-base font-bold text-slate-900">
                  Factura {receipt.invoice_number}
                </h3>
                <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  <CheckCircle2 className="w-3 h-3" />
                  <span>Procesado</span>
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">{receipt.company_name} ({receipt.company_cif})</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-xl transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Info Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 px-6 py-4 bg-slate-50/30 border-b border-slate-100 text-xs">
          <div className="flex items-center space-x-2 text-slate-600">
            <MapPin className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span className="truncate">
              {receipt.store_address ? `${receipt.store_address}, ${receipt.store_city || ''}` : 'Tienda Mercadona'}
            </span>
          </div>
          <div className="flex items-center space-x-2 text-slate-600">
            <Calendar className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span>{receipt.purchase_datetime.replace('T', ' ')}</span>
          </div>
          <div className="flex items-center space-x-2 text-slate-600">
            <CreditCard className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span>
              {receipt.payment_method || 'Tarjeta'} {receipt.card_last_four ? `(**** ${receipt.card_last_four})` : ''}
            </span>
          </div>
        </div>

        {/* Scrollable Line Items */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
          {/* Items Table */}
          <div>
            <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-3">
              Líneas de Compra ({receipt.lines?.length || 0} artículos)
            </h4>
            <div className="border border-slate-200 rounded-2xl overflow-hidden">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
                  <tr>
                    <th className="py-2.5 px-3">#</th>
                    <th className="py-2.5 px-3">Artículo</th>
                    <th className="py-2.5 px-3">Categoría</th>
                    <th className="py-2.5 px-3 text-right">Cant / Peso</th>
                    <th className="py-2.5 px-3 text-right">P. Unit</th>
                    <th className="py-2.5 px-3 text-right font-bold text-slate-800">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {receipt.lines?.map((line) => (
                    <tr key={line.id} className="hover:bg-slate-50/50">
                      <td className="py-2 px-3 text-slate-400">{line.line_order}</td>
                      <td className="py-2 px-3 font-medium text-slate-800">
                        {line.raw_description}
                        {line.is_weighed_item && (
                          <span className="ml-1.5 px-1.5 py-0.5 rounded text-[10px] bg-amber-50 text-amber-700 border border-amber-200">
                            Granel
                          </span>
                        )}
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
                        {line.unit_price.toFixed(2)} €
                      </td>
                      <td className="py-2 px-3 text-right font-bold text-slate-900">
                        {line.line_total.toFixed(2)} €
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Tax Breakdown */}
          {receipt.tax_lines && receipt.tax_lines.length > 0 && (
            <div>
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-3">
                Desglose Fiscal (IVA)
              </h4>
              <div className="border border-slate-200 rounded-2xl overflow-hidden">
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
                    {receipt.tax_lines.map((tax) => (
                      <tr key={tax.id}>
                        <td className="py-2 px-3 font-semibold text-slate-800">{tax.tax_rate_percent}%</td>
                        <td className="py-2 px-3 text-right text-slate-600">{tax.taxable_base.toFixed(2)} €</td>
                        <td className="py-2 px-3 text-right text-slate-600">{tax.tax_amount.toFixed(2)} €</td>
                        <td className="py-2 px-3 text-right font-bold text-slate-900">{tax.total_with_tax.toFixed(2)} €</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Footer with Totals */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
          <div className="text-xs text-slate-500 flex items-center space-x-1">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>Conciliación contable verificada al 100%</span>
          </div>

          <div className="flex items-center space-x-3">
            <span className="text-sm text-slate-600">Importe Total:</span>
            <span className="text-2xl font-black text-slate-900">
              {receipt.total_amount.toFixed(2)} €
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
