import React, { useState, useEffect, useMemo } from 'react';
import {
  X,
  Plus,
  Trash2,
  Calendar,
  Store,
  CreditCard,
  Search,
  Scale,
  Package,
  Check,
  Loader2,
  FileText,
  AlertCircle,
} from 'lucide-react';
import { catalogApi } from '../../api/catalog.api';
import { receiptsApi } from '../../api/receipts.api';
import type { Product, ManualReceiptCreate, ManualReceiptLineCreate } from '../../types';

interface ManualReceiptModalProps {
  isOpen: boolean;
  onClose: () => void;
  householdId: string;
  onSuccess: (receiptId: string) => void;
}

interface FormLine extends ManualReceiptLineCreate {
  tempId: string;
  searchQuery: string;
  isSearching: boolean;
  searchResults: Product[];
  selectedProduct?: Product | null;
}

export const ManualReceiptModal: React.FC<ManualReceiptModalProps> = ({
  isOpen,
  onClose,
  householdId,
  onSuccess,
}) => {
  // Form header fields
  const now = new Date();
  const defaultDateTime = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(
    now.getDate()
  ).padStart(2, '0')}T${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

  const [purchaseDatetime, setPurchaseDatetime] = useState<string>(defaultDateTime);
  const [storeAddress, setStoreAddress] = useState<string>('');
  const [storeCity, setStoreCity] = useState<string>('');
  const [storePostalCode, setStorePostalCode] = useState<string>('');
  const [paymentMethod, setPaymentMethod] = useState<string>('TARJETA');
  const [invoiceNumber, setInvoiceNumber] = useState<string>('');

  // Lines
  const [lines, setLines] = useState<FormLine[]>([
    {
      tempId: 'line-1',
      raw_description: '',
      product_id: null,
      quantity: 1,
      unit_of_measure: 'ud',
      unit_price: 0,
      discount_amount: 0,
      tax_rate_percent: 10,
      is_weighed_item: false,
      weight_in_kg: null,
      searchQuery: '',
      isSearching: false,
      searchResults: [],
      selectedProduct: null,
    },
  ]);

  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Reset modal when opened
  useEffect(() => {
    if (isOpen) {
      const currentNow = new Date();
      const dt = `${currentNow.getFullYear()}-${String(currentNow.getMonth() + 1).padStart(2, '0')}-${String(
        currentNow.getDate()
      ).padStart(2, '0')}T${String(currentNow.getHours()).padStart(2, '0')}:${String(
        currentNow.getMinutes()
      ).padStart(2, '0')}`;
      setPurchaseDatetime(dt);
      setStoreAddress('');
      setStoreCity('');
      setStorePostalCode('');
      setPaymentMethod('TARJETA');
      setInvoiceNumber('');
      setErrorMessage(null);
      setLines([
        {
          tempId: `line-${Date.now()}`,
          raw_description: '',
          product_id: null,
          quantity: 1,
          unit_of_measure: 'ud',
          unit_price: 0,
          discount_amount: 0,
          tax_rate_percent: 10,
          is_weighed_item: false,
          weight_in_kg: null,
          searchQuery: '',
          isSearching: false,
          searchResults: [],
          selectedProduct: null,
        },
      ]);
    }
  }, [isOpen]);

  // Handle product live search per line
  const handleLineSearch = async (tempId: string, query: string) => {
    setLines((prev) =>
      prev.map((l) => (l.tempId === tempId ? { ...l, searchQuery: query, isSearching: true } : l))
    );

    if (query.trim().length >= 2) {
      try {
        const results = await catalogApi.getProducts({ search: query.trim(), limit: 6 });
        setLines((prev) =>
          prev.map((l) =>
            l.tempId === tempId ? { ...l, searchResults: results, isSearching: false } : l
          )
        );
      } catch (err) {
        setLines((prev) =>
          prev.map((l) => (l.tempId === tempId ? { ...l, searchResults: [], isSearching: false } : l))
        );
      }
    } else {
      setLines((prev) =>
        prev.map((l) => (l.tempId === tempId ? { ...l, searchResults: [], isSearching: false } : l))
      );
    }
  };

  const handleSelectProduct = (tempId: string, prod: Product) => {
    setLines((prev) =>
      prev.map((l) => {
        if (l.tempId !== tempId) return l;
        const isWeighed = prod.default_unit?.toLowerCase() === 'kg';
        // Auto-infer likely tax: Fruits, veggies, dairy, bread -> 4%, meat, fish -> 10%
        let suggestedTax = 10;
        const catSlug = prod.category_name?.toLowerCase() || '';
        if (
          catSlug.includes('fruta') ||
          catSlug.includes('verdura') ||
          catSlug.includes('lacteo') ||
          catSlug.includes('pan') ||
          catSlug.includes('huevo')
        ) {
          suggestedTax = 4;
        } else if (
          catSlug.includes('limpieza') ||
          catSlug.includes('cuidado') ||
          catSlug.includes('drogueria') ||
          catSlug.includes('hogar')
        ) {
          suggestedTax = 21;
        }

        return {
          ...l,
          raw_description: prod.canonical_name,
          product_id: prod.id,
          unit_price: prod.latest_price || 0,
          unit_of_measure: prod.default_unit || (isWeighed ? 'kg' : 'ud'),
          is_weighed_item: isWeighed,
          weight_in_kg: isWeighed ? l.quantity : null,
          tax_rate_percent: suggestedTax,
          searchQuery: prod.canonical_name,
          searchResults: [],
          selectedProduct: prod,
          image_url: prod.image_url,
          brand: prod.brand,
        };
      })
    );
  };

  const updateLineField = (tempId: string, field: keyof FormLine, value: any) => {
    setLines((prev) =>
      prev.map((l) => {
        if (l.tempId !== tempId) return l;
        const updated = { ...l, [field]: value };
        if (field === 'is_weighed_item') {
          if (value === true) {
            updated.unit_of_measure = 'kg';
            updated.weight_in_kg = updated.quantity;
          } else {
            updated.unit_of_measure = 'ud';
            updated.weight_in_kg = null;
          }
        }
        if (field === 'quantity' && updated.is_weighed_item) {
          updated.weight_in_kg = Number(value);
        }
        return updated;
      })
    );
  };

  const addLine = () => {
    setLines((prev) => [
      ...prev,
      {
        tempId: `line-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        raw_description: '',
        product_id: null,
        quantity: 1,
        unit_of_measure: 'ud',
        unit_price: 0,
        discount_amount: 0,
        tax_rate_percent: 10,
        is_weighed_item: false,
        weight_in_kg: null,
        searchQuery: '',
        isSearching: false,
        searchResults: [],
        selectedProduct: null,
      },
    ]);
  };

  const removeLine = (tempId: string) => {
    if (lines.length <= 1) {
      // Clear line instead of removing last one
      setLines([
        {
          tempId: `line-${Date.now()}`,
          raw_description: '',
          product_id: null,
          quantity: 1,
          unit_of_measure: 'ud',
          unit_price: 0,
          discount_amount: 0,
          tax_rate_percent: 10,
          is_weighed_item: false,
          weight_in_kg: null,
          searchQuery: '',
          isSearching: false,
          searchResults: [],
          selectedProduct: null,
        },
      ]);
      return;
    }
    setLines((prev) => prev.filter((l) => l.tempId !== tempId));
  };

  // Live accounting calculation
  const accounting = useMemo(() => {
    let total = 0;
    const taxes: { [rate: number]: { base: number; tax: number; total: number } } = {};

    lines.forEach((l) => {
      const q = Number(l.quantity) || 0;
      const p = Number(l.unit_price) || 0;
      const d = Number(l.discount_amount) || 0;
      const lineTotal = Math.max(0, q * p - d);
      total += lineTotal;

      const rate = Number(l.tax_rate_percent) || 10;
      if (!taxes[rate]) {
        taxes[rate] = { base: 0, tax: 0, total: 0 };
      }
      const base = lineTotal / (1 + rate / 100);
      const taxAmt = lineTotal - base;

      taxes[rate].base += base;
      taxes[rate].tax += taxAmt;
      taxes[rate].total += lineTotal;
    });

    return {
      total,
      taxes,
    };
  }, [lines]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    // Validation
    const validLines = lines.filter((l) => l.raw_description.trim().length > 0 && l.unit_price > 0);
    if (validLines.length === 0) {
      setErrorMessage('Debes añadir al menos un producto con descripción y precio válido.');
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: ManualReceiptCreate = {
        household_id: householdId,
        purchase_datetime: purchaseDatetime ? new Date(purchaseDatetime).toISOString() : undefined,
        store_address: storeAddress.trim() || undefined,
        store_city: storeCity.trim() || undefined,
        store_postal_code: storePostalCode.trim() || undefined,
        payment_method: paymentMethod,
        invoice_number: invoiceNumber.trim() || undefined,
        lines: validLines.map((l) => ({
          raw_description: l.raw_description.trim(),
          product_id: l.product_id,
          quantity: Number(l.quantity) || 1,
          unit_of_measure: l.unit_of_measure,
          unit_price: Number(l.unit_price) || 0,
          discount_amount: Number(l.discount_amount) || 0,
          tax_rate_percent: Number(l.tax_rate_percent) || 10,
          is_weighed_item: l.is_weighed_item,
          weight_in_kg: l.is_weighed_item ? Number(l.quantity) : null,
        })),
      };

      const result = await receiptsApi.createManualReceipt(payload);
      setIsSubmitting(false);
      onSuccess(result.id);
      onClose();
    } catch (err: any) {
      setIsSubmitting(false);
      const detail = err.response?.data?.detail;
      setErrorMessage(
        typeof detail === 'string' ? detail : 'Ocurrió un error al guardar el ticket manual.'
      );
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-6 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl sm:rounded-3xl shadow-2xl border border-slate-100 flex flex-col w-full max-w-4xl max-h-[94vh] sm:max-h-[92vh] overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-4 sm:px-6 py-3.5 sm:py-5 border-b border-slate-100 bg-slate-50/50">
          <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
            <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-2xl bg-emerald-100 flex items-center justify-center text-emerald-700 shadow-sm shadow-emerald-500/10 shrink-0">
              <FileText className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <h2 className="text-base sm:text-xl font-bold text-slate-900 truncate">Añadir Ticket Manual</h2>
              <p className="text-[11px] sm:text-xs text-slate-500 truncate">
                Registra compras físicas artículo a artículo
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 sm:p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100 transition shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-3.5 sm:p-6 space-y-4 sm:space-y-6">
          {errorMessage && (
            <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 flex items-center gap-3 text-rose-700 text-sm">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* General Ticket Metadata */}
          <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200/60 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5 flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-slate-500" />
                Fecha y Hora *
              </label>
              <input
                type="datetime-local"
                value={purchaseDatetime}
                onChange={(e) => setPurchaseDatetime(e.target.value)}
                required
                className="w-full px-3 py-2 text-xs bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 outline-none transition"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5 flex items-center gap-1.5">
                <Store className="w-3.5 h-3.5 text-slate-500" />
                Tienda / Dirección
              </label>
              <input
                type="text"
                placeholder="Ej: C/ San Vicente Mártir"
                value={storeAddress}
                onChange={(e) => setStoreAddress(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 outline-none transition"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5 flex items-center gap-1.5">
                <CreditCard className="w-3.5 h-3.5 text-slate-500" />
                Método de Pago
              </label>
              <select
                value={paymentMethod}
                onChange={(e) => setPaymentMethod(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 outline-none transition"
              >
                <option value="TARJETA">💳 Tarjeta Bancaria</option>
                <option value="EFECTIVO">💵 Efectivo</option>
                <option value="BIZUM">📱 Bizum / Móvil</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Nº Factura (Opcional)
              </label>
              <input
                type="text"
                placeholder="Auto-generado si está vacío"
                value={invoiceNumber}
                onChange={(e) => setInvoiceNumber(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 outline-none transition"
              />
            </div>
          </div>

          {/* Line Items Table */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Package className="w-4 h-4 text-emerald-600" />
                Artículos del Ticket ({lines.length})
              </h3>
              <button
                type="button"
                onClick={addLine}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 rounded-xl text-xs font-semibold transition"
              >
                <Plus className="w-3.5 h-3.5" />
                Añadir Artículo
              </button>
            </div>

            <div className="space-y-2.5">
              {lines.map((line, idx) => {
                const lineSubtotal = Math.max(
                  0,
                  (Number(line.quantity) || 0) * (Number(line.unit_price) || 0) -
                    (Number(line.discount_amount) || 0)
                );

                return (
                  <div
                    key={line.tempId}
                    className="p-3.5 bg-white border border-slate-200/90 rounded-2xl shadow-sm hover:border-slate-300 transition space-y-2.5 relative"
                  >
                    <div className="flex items-start gap-3">
                      {/* Product Thumbnail / Placeholder */}
                      <div className="w-10 h-10 rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center shrink-0 overflow-hidden mt-0.5">
                        {line.image_url ? (
                          <img
                            src={line.image_url}
                            alt=""
                            className="w-full h-full object-contain p-0.5"
                          />
                        ) : (
                          <Package className="w-5 h-5 text-slate-400" />
                        )}
                      </div>

                      {/* Product description & Autocomplete */}
                      <div className="flex-1 relative">
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                          Producto / Nombre en Ticket #{idx + 1}
                        </label>
                        <div className="relative">
                          <input
                            type="text"
                            placeholder="Buscar en catálogo Mercadona o escribir nombre libre..."
                            value={line.raw_description}
                            onChange={(e) => {
                              const val = e.target.value;
                              updateLineField(line.tempId, 'raw_description', val);
                              handleLineSearch(line.tempId, val);
                            }}
                            className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50/50 border border-slate-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 outline-none transition"
                          />
                          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
                          {line.isSearching && (
                            <Loader2 className="w-3.5 h-3.5 text-emerald-500 animate-spin absolute right-2.5 top-2.5" />
                          )}
                        </div>

                        {/* Search Suggestions Dropdown */}
                        {line.searchResults.length > 0 && (
                          <div className="absolute z-20 left-0 right-0 top-full mt-1 bg-white border border-slate-200 rounded-2xl shadow-xl max-h-48 overflow-y-auto divide-y divide-slate-100 animate-in fade-in zoom-in-95">
                            {line.searchResults.map((p) => (
                              <button
                                key={p.id}
                                type="button"
                                onClick={() => handleSelectProduct(line.tempId, p)}
                                className="w-full px-3 py-2 text-left hover:bg-emerald-50/60 flex items-center justify-between text-xs transition"
                              >
                                <div className="flex items-center gap-2.5 truncate">
                                  {p.image_url ? (
                                    <img
                                      src={p.image_url}
                                      alt=""
                                      className="w-6 h-6 object-contain rounded shrink-0 bg-white border border-slate-100"
                                    />
                                  ) : (
                                    <div className="w-6 h-6 rounded bg-slate-100 flex items-center justify-center shrink-0">
                                      <Package className="w-3.5 h-3.5 text-slate-400" />
                                    </div>
                                  )}
                                  <div className="truncate">
                                    <span className="font-semibold text-slate-800">
                                      {p.canonical_name}
                                    </span>
                                    {p.brand && (
                                      <span className="ml-1.5 text-[10px] text-emerald-700 bg-emerald-50 px-1 py-0.2 rounded font-medium">
                                        {p.brand}
                                      </span>
                                    )}
                                  </div>
                                </div>
                                <div className="text-right shrink-0 ml-2">
                                  {p.latest_price && (
                                    <span className="font-bold text-slate-900">
                                      {p.latest_price.toFixed(2)} €
                                    </span>
                                  )}
                                  <span className="text-[10px] text-slate-400 ml-1">
                                    /{p.default_unit || 'ud'}
                                  </span>
                                </div>
                              </button>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Weighed Item Toggle */}
                      <div className="shrink-0 pt-5">
                        <button
                          type="button"
                          onClick={() =>
                            updateLineField(line.tempId, 'is_weighed_item', !line.is_weighed_item)
                          }
                          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl border text-xs font-medium transition ${
                            line.is_weighed_item
                              ? 'bg-amber-50 border-amber-300 text-amber-800'
                              : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                          }`}
                          title="Alternar entre venta por unidades o venta al peso (kg)"
                        >
                          <Scale className="w-3.5 h-3.5" />
                          <span>{line.is_weighed_item ? 'Al peso (kg)' : 'Unidades'}</span>
                        </button>
                      </div>

                      {/* Remove Line Button */}
                      <button
                        type="button"
                        onClick={() => removeLine(line.tempId)}
                        className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition mt-5"
                        title="Eliminar artículo"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>

                    {/* Numeric Row: Quantity, Unit Price, Tax, Subtotal */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-1 border-t border-slate-100/80">
                      <div>
                        <label className="block text-[11px] text-slate-500 mb-1">
                          {line.is_weighed_item ? 'Peso (kg)' : 'Cantidad (ud)'}
                        </label>
                        <input
                          type="number"
                          step={line.is_weighed_item ? '0.001' : '1'}
                          min="0.001"
                          value={line.quantity}
                          onChange={(e) =>
                            updateLineField(line.tempId, 'quantity', parseFloat(e.target.value) || 0)
                          }
                          className="w-full px-2.5 py-1 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:bg-white focus:ring-1 focus:ring-emerald-500 outline-none"
                        />
                      </div>

                      <div>
                        <label className="block text-[11px] text-slate-500 mb-1">
                          {line.is_weighed_item ? 'Precio / kg (€)' : 'Precio unitario (€)'}
                        </label>
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          value={line.unit_price}
                          onChange={(e) =>
                            updateLineField(line.tempId, 'unit_price', parseFloat(e.target.value) || 0)
                          }
                          className="w-full px-2.5 py-1 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:bg-white focus:ring-1 focus:ring-emerald-500 outline-none font-semibold text-slate-900"
                        />
                      </div>

                      <div>
                        <label className="block text-[11px] text-slate-500 mb-1">Tipo de IVA</label>
                        <select
                          value={line.tax_rate_percent}
                          onChange={(e) =>
                            updateLineField(
                              line.tempId,
                              'tax_rate_percent',
                              parseFloat(e.target.value) || 10
                            )
                          }
                          className="w-full px-2 py-1 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:bg-white focus:ring-1 focus:ring-emerald-500 outline-none"
                        >
                          <option value="4">4% (Superreducido)</option>
                          <option value="10">10% (Reducido)</option>
                          <option value="21">21% (General)</option>
                          <option value="0">0% (Exento)</option>
                        </select>
                      </div>

                      <div className="text-right">
                        <label className="block text-[11px] text-slate-500 mb-1">Subtotal línea</label>
                        <div className="py-1 text-xs font-bold text-emerald-800">
                          {lineSubtotal.toFixed(2)} €
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Real-time Accounting Box */}
          <div className="bg-gradient-to-br from-slate-900 to-slate-800 text-white rounded-3xl p-5 shadow-lg space-y-4">
            <div className="flex items-center justify-between border-b border-slate-700/60 pb-3">
              <span className="text-xs uppercase tracking-wider text-slate-400 font-semibold">
                Resumen Contable en Directo
              </span>
              <span className="text-xs text-slate-400">
                {lines.filter((l) => l.raw_description.trim().length > 0).length} artículos registrados
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              {Object.entries(accounting.taxes).map(([rate, t]) => (
                <div key={rate} className="bg-slate-800/80 p-2.5 rounded-xl border border-slate-700">
                  <div className="text-[11px] text-emerald-400 font-medium">IVA {rate}%</div>
                  <div className="text-slate-300 mt-1">Base: {t.base.toFixed(2)} €</div>
                  <div className="text-slate-400 text-[10px]">Cuota: {t.tax.toFixed(2)} €</div>
                </div>
              ))}
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-slate-700/60">
              <span className="text-sm font-semibold text-slate-300">TOTAL TICKET:</span>
              <span className="text-2xl font-black text-emerald-400">
                {accounting.total.toFixed(2)} €
              </span>
            </div>
          </div>
        </form>

        {/* Modal Footer Actions */}
        <div className="px-4 sm:px-6 py-3 sm:py-4 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 hover:bg-slate-200/60 rounded-xl transition"
          >
            Cancelar
          </button>

          <button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting || accounting.total <= 0}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl text-xs font-bold shadow-md shadow-emerald-600/20 transition"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Guardando ticket...
              </>
            ) : (
              <>
                <Check className="w-4 h-4" />
                Guardar Ticket ({accounting.total.toFixed(2)} €)
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
