import React, { useState, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useHousehold } from '../../context/HouseholdContext';
import { shoppingApi } from '../../api/shopping.api';
import { catalogApi } from '../../api/catalog.api';
import type { Product, ShoppingItem } from '../../types';
import {
  ShoppingCart,
  Plus,
  Trash2,
  Sparkles,
  Search,
  Package,
  Check,
  Loader2,
  Smartphone,
  ShoppingBag,
} from 'lucide-react';

export const ShoppingListPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { activeHousehold } = useHousehold();

  // Mode: standard vs tactile "Modo Supermercado"
  const [isSupermarketMode, setIsSupermarketMode] = useState(false);

  // Quick add form state
  const [newItemName, setNewItemName] = useState('');
  const [newItemQty, setNewItemQty] = useState(1);
  const [newItemUnit, setNewItemUnit] = useState('ud');
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Product[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isAdding, setIsAdding] = useState(false);

  // Queries
  const { data: summary, isLoading } = useQuery({
    queryKey: ['shopping-list', activeHousehold?.id],
    queryFn: () => (activeHousehold ? shoppingApi.getList(activeHousehold.id) : null),
    enabled: !!activeHousehold,
  });

  const { data: suggestions = [] } = useQuery({
    queryKey: ['shopping-suggestions', activeHousehold?.id],
    queryFn: () => (activeHousehold ? shoppingApi.getSuggestions(activeHousehold.id) : []),
    enabled: !!activeHousehold,
    staleTime: 60000,
  });

  // Autocomplete search
  const handleSearchChange = async (query: string) => {
    setSearchQuery(query);
    setNewItemName(query);
    if (query.trim().length >= 2) {
      try {
        setIsSearching(true);
        const results = await catalogApi.getProducts({ search: query.trim(), limit: 5 });
        setSearchResults(results);
      } catch {
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    } else {
      setSearchResults([]);
    }
  };

  const handleSelectProduct = (prod: Product) => {
    setSelectedProduct(prod);
    setNewItemName(prod.canonical_name);
    setSearchQuery(prod.canonical_name);
    setNewItemUnit(prod.default_unit || 'ud');
    setSearchResults([]);
  };

  // Add Item Handler
  const handleAddItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeHousehold || !newItemName.trim()) return;

    try {
      setIsAdding(true);
      await shoppingApi.addItem({
        household_id: activeHousehold.id,
        name: newItemName.trim(),
        product_id: selectedProduct?.id || null,
        quantity: newItemQty,
        unit_of_measure: newItemUnit,
        estimated_unit_price: selectedProduct?.latest_price || null,
      });

      setNewItemName('');
      setSearchQuery('');
      setSelectedProduct(null);
      setNewItemQty(1);
      setNewItemUnit('ud');
      queryClient.invalidateQueries({ queryKey: ['shopping-list', activeHousehold.id] });
      queryClient.invalidateQueries({ queryKey: ['shopping-suggestions', activeHousehold.id] });
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Error al añadir artículo a la lista.');
    } finally {
      setIsAdding(false);
    }
  };

  // Quick Add from Predictive Suggestions
  const handleAddSuggestion = async (sug: typeof suggestions[0]) => {
    if (!activeHousehold) return;
    try {
      await shoppingApi.addItem({
        household_id: activeHousehold.id,
        name: sug.name,
        product_id: sug.product_id,
        quantity: 1,
        unit_of_measure: sug.unit_of_measure,
        estimated_unit_price: sug.latest_price,
      });
      queryClient.invalidateQueries({ queryKey: ['shopping-list', activeHousehold.id] });
      queryClient.invalidateQueries({ queryKey: ['shopping-suggestions', activeHousehold.id] });
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Error al añadir sugerencia.');
    }
  };

  // Toggle Check
  const handleToggleCheck = async (item: ShoppingItem) => {
    if (!activeHousehold) return;
    try {
      await shoppingApi.updateItem(item.id, activeHousehold.id, {
        is_checked: !item.is_checked,
      });
      queryClient.invalidateQueries({ queryKey: ['shopping-list', activeHousehold.id] });
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Error al actualizar artículo.');
    }
  };

  // Delete Item
  const handleDeleteItem = async (itemId: string) => {
    if (!activeHousehold) return;
    try {
      await shoppingApi.deleteItem(itemId, activeHousehold.id);
      queryClient.invalidateQueries({ queryKey: ['shopping-list', activeHousehold.id] });
      queryClient.invalidateQueries({ queryKey: ['shopping-suggestions', activeHousehold.id] });
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Error al eliminar artículo.');
    }
  };

  // Clear Checked
  const handleClearChecked = async () => {
    if (!activeHousehold) return;
    if (!confirm('¿Deseas eliminar de la lista todos los artículos marcados como comprados?')) return;
    try {
      await shoppingApi.clearChecked(activeHousehold.id);
      queryClient.invalidateQueries({ queryKey: ['shopping-list', activeHousehold.id] });
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Error al limpiar artículos comprados.');
    }
  };

  // Group items by category
  const groupedItems = useMemo(() => {
    const items = summary?.items || [];
    const groups: { [cat: string]: { color: string; items: ShoppingItem[] } } = {};

    items.forEach((item) => {
      const cat = item.category_name || 'Otros';
      if (!groups[cat]) {
        groups[cat] = { color: item.category_color || '#6B7280', items: [] };
      }
      groups[cat].items.push(item);
    });

    return groups;
  }, [summary?.items]);

  if (!activeHousehold) {
    return (
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-12 text-center space-y-4">
        <ShoppingCart className="w-12 h-12 text-slate-300 mx-auto" />
        <h2 className="text-xl font-bold text-slate-900">Selecciona un hogar activo</h2>
        <p className="text-sm text-slate-500 max-w-sm mx-auto">
          Para ver y gestionar la lista de la compra, selecciona o crea un hogar.
        </p>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${isSupermarketMode ? 'max-w-xl mx-auto' : ''}`}>
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Lista de la Compra</h1>
            {isSupermarketMode && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-900 animate-pulse">
                Modo Supermercado Activo
              </span>
            )}
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Organiza tus compras familiares con estimación de precios en directo y sugerencias predictivas.
          </p>
        </div>

        {/* Header Action Buttons */}
        <div className="flex items-center flex-wrap gap-2.5">
          <button
            type="button"
            onClick={() => setIsSupermarketMode((prev) => !prev)}
            className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition shadow-sm ${
              isSupermarketMode
                ? 'bg-amber-600 hover:bg-amber-700 text-white shadow-amber-600/20'
                : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-50'
            }`}
            title="Activar vista táctil para ir tachando cómodamente en el supermercado"
          >
            <Smartphone className="w-4 h-4" />
            <span>{isSupermarketMode ? 'Salir Modo Tienda' : 'Modo Supermercado'}</span>
          </button>

          {(summary?.checked_count || 0) > 0 && (
            <button
              type="button"
              onClick={handleClearChecked}
              className="inline-flex items-center gap-1.5 px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition"
              title="Borrar los artículos que ya has comprado"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Limpiar Comprados ({summary?.checked_count})</span>
            </button>
          )}
        </div>
      </div>

      {/* Cart Cost Summary Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 text-white rounded-3xl p-5 shadow-lg">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center justify-center shrink-0">
              <ShoppingCart className="w-6 h-6" />
            </div>
            <div>
              <div className="text-xs uppercase tracking-wider text-slate-400 font-semibold">
                Coste Estimado del Carrito
              </div>
              <div className="text-3xl font-black text-emerald-400 font-mono mt-0.5">
                {summary?.estimated_total_cost.toFixed(2) || '0.00'} €
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 border-t sm:border-t-0 sm:border-l border-slate-700 pt-3 sm:pt-0 sm:pl-6 text-xs">
            <div>
              <div className="text-slate-400 text-[11px]">En el Carrito</div>
              <div className="font-bold text-emerald-400 font-mono text-sm mt-0.5">
                {summary?.estimated_checked_cost.toFixed(2) || '0.00'} €
              </div>
              <div className="text-[10px] text-slate-500">{summary?.checked_count || 0} tachados</div>
            </div>

            <div>
              <div className="text-slate-400 text-[11px]">Por Coger</div>
              <div className="font-bold text-amber-400 font-mono text-sm mt-0.5">
                {summary?.estimated_pending_cost.toFixed(2) || '0.00'} €
              </div>
              <div className="text-[10px] text-slate-500">{summary?.pending_count || 0} pendientes</div>
            </div>

            <div className="col-span-2 sm:col-span-1">
              <div className="text-slate-400 text-[11px]">Progreso</div>
              <div className="font-bold text-slate-200 text-sm mt-0.5">
                {summary && summary.total_count > 0
                  ? Math.round((summary.checked_count / summary.total_count) * 100)
                  : 0}
                %
              </div>
              <div className="text-[10px] text-slate-500">
                {summary?.checked_count || 0}/{summary?.total_count || 0} artículos
              </div>
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        {summary && summary.total_count > 0 && (
          <div className="w-full bg-slate-700/80 h-1.5 rounded-full overflow-hidden mt-4">
            <div
              className="bg-emerald-500 h-full rounded-full transition-all duration-300"
              style={{ width: `${Math.round((summary.checked_count / summary.total_count) * 100)}%` }}
            />
          </div>
        )}
      </div>

      {/* Quick Add Form (Hidden in Supermarket Mode for maximum distraction-free shopping) */}
      {!isSupermarketMode && (
        <form
          onSubmit={handleAddItem}
          className="bg-white p-4 rounded-3xl border border-slate-200 shadow-sm space-y-3"
        >
          <div className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
            <Plus className="w-3.5 h-3.5 text-emerald-600" />
            <span>Añadir Producto a la Lista</span>
          </div>

          <div className="grid grid-cols-12 gap-2 sm:gap-3 relative">
            {/* Search Input with autocomplete */}
            <div className="col-span-12 sm:col-span-7 relative">
              <input
                type="text"
                placeholder="Buscar producto o escribir libre..."
                value={searchQuery}
                onChange={(e) => handleSearchChange(e.target.value)}
                required
                className="w-full pl-9 pr-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 outline-none transition"
              />
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              {isSearching && (
                <Loader2 className="w-4 h-4 text-emerald-600 animate-spin absolute right-3 top-2.5" />
              )}

              {/* Autocomplete Dropdown */}
              {searchResults.length > 0 && (
                <div className="absolute z-20 left-0 right-0 top-full mt-1 bg-white border border-slate-200 rounded-2xl shadow-xl max-h-52 overflow-y-auto divide-y divide-slate-100 animate-in fade-in zoom-in-95">
                  {searchResults.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => handleSelectProduct(p)}
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
                          <span className="font-semibold text-slate-800">{p.canonical_name}</span>
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

            {/* Quantity */}
            <div className="col-span-4 sm:col-span-2">
              <input
                type="number"
                step="0.5"
                min="0.1"
                value={newItemQty}
                onChange={(e) => setNewItemQty(parseFloat(e.target.value) || 1)}
                className="w-full px-2 sm:px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 outline-none text-center font-bold text-slate-800"
              />
            </div>

            {/* Unit */}
            <div className="col-span-3 sm:col-span-1">
              <select
                value={newItemUnit}
                onChange={(e) => setNewItemUnit(e.target.value)}
                className="w-full px-1.5 sm:px-2 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 outline-none font-semibold text-slate-700"
              >
                <option value="ud">ud</option>
                <option value="kg">kg</option>
                <option value="pack">pack</option>
                <option value="l">l</option>
              </select>
            </div>

            {/* Submit Button */}
            <div className="col-span-5 sm:col-span-2">
              <button
                type="submit"
                disabled={isAdding || !newItemName.trim()}
                className="w-full inline-flex items-center justify-center gap-1.5 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-xl text-xs font-bold shadow-sm transition"
              >
                {isAdding ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
                <span>Añadir</span>
              </button>
            </div>
          </div>
        </form>
      )}

      {/* AI Predictive Replenishment Suggestions ("Toca Reponer") */}
      {!isSupermarketMode && suggestions.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-lg bg-amber-50 text-amber-700 flex items-center justify-center">
                <Sparkles className="w-3.5 h-3.5" />
              </div>
              <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Sugerencias Inteligentes — Toca Reponer ({suggestions.length})
              </h2>
            </div>
            <span className="text-[11px] text-slate-400">Basado en tus ciclos de compra reales</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {suggestions.map((sug) => (
              <div
                key={sug.product_id}
                className="bg-white p-3 rounded-2xl border border-slate-200 shadow-sm hover:border-emerald-300 hover:shadow-md transition flex flex-col justify-between space-y-2.5"
              >
                <div className="flex items-start gap-2.5">
                  <div className="w-10 h-10 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-center shrink-0 overflow-hidden">
                    {sug.image_url ? (
                      <img src={sug.image_url} alt="" className="w-full h-full object-contain p-0.5" />
                    ) : (
                      <Package className="w-4 h-4 text-slate-400" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="text-xs font-bold text-slate-900 truncate" title={sug.name}>
                      {sug.name}
                    </h3>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.2 rounded">
                        {sug.latest_price ? `${sug.latest_price.toFixed(2)} €` : 'Mercadona'}
                      </span>
                      {sug.brand && (
                        <span className="text-[10px] text-slate-500 font-medium truncate">
                          {sug.brand}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="text-[11px] text-slate-500 bg-slate-50 p-2 rounded-xl border border-slate-100/80 leading-snug">
                  {sug.reason}
                </div>

                <button
                  type="button"
                  onClick={() => handleAddSuggestion(sug)}
                  className="w-full inline-flex items-center justify-center gap-1.5 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 rounded-xl text-xs font-bold transition"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Añadir a la Lista</span>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Shopping List Items Grouped by Category */}
      <div className="space-y-4">
        {isLoading ? (
          <div className="bg-white rounded-3xl border border-slate-200 p-12 text-center text-slate-400 flex items-center justify-center gap-2">
            <Loader2 className="w-5 h-5 animate-spin text-emerald-600" />
            <span>Cargando lista de la compra...</span>
          </div>
        ) : Object.keys(groupedItems).length === 0 ? (
          <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-12 text-center space-y-3">
            <div className="w-14 h-14 bg-emerald-50 text-emerald-600 rounded-3xl flex items-center justify-center mx-auto">
              <ShoppingBag className="w-7 h-7" />
            </div>
            <h3 className="text-base font-bold text-slate-900">Tu lista de la compra está vacía</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              Añade artículos con el buscador superior o pulsa en una de las sugerencias predictivas de reposición.
            </p>
          </div>
        ) : (
          Object.entries(groupedItems).map(([catName, group]) => (
            <div
              key={catName}
              className="bg-white rounded-3xl border border-slate-200/90 shadow-sm overflow-hidden"
            >
              {/* Category / Aisle Header */}
              <div className="px-5 py-3 bg-slate-50/70 border-b border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span
                    className="w-3 h-3 rounded-full shrink-0"
                    style={{ backgroundColor: group.color }}
                  />
                  <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                    {catName}
                  </h3>
                  <span className="text-[11px] text-slate-400 font-medium">
                    ({group.items.length} {group.items.length === 1 ? 'artículo' : 'artículos'})
                  </span>
                </div>

                <div className="text-xs font-mono font-bold text-slate-700">
                  {group.items
                    .reduce((acc, it) => acc + (it.estimated_total || 0), 0)
                    .toFixed(2)}{' '}
                  €
                </div>
              </div>

              {/* Items List */}
              <div className="divide-y divide-slate-100">
                {group.items.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => handleToggleCheck(item)}
                    className={`px-5 py-3.5 flex items-center justify-between gap-3 cursor-pointer transition select-none ${
                      item.is_checked
                        ? 'bg-slate-50/70 text-slate-400'
                        : 'hover:bg-slate-50/50 text-slate-800'
                    } ${isSupermarketMode ? 'py-4' : ''}`}
                  >
                    <div className="flex items-center gap-3.5 min-w-0">
                      {/* Big Tactile Checkbox */}
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleToggleCheck(item);
                        }}
                        className={`w-6 h-6 rounded-lg border flex items-center justify-center shrink-0 transition ${
                          item.is_checked
                            ? 'bg-emerald-600 border-emerald-600 text-white'
                            : 'border-slate-300 hover:border-emerald-500 bg-white text-transparent'
                        }`}
                      >
                        <Check className="w-4 h-4 stroke-[3]" />
                      </button>

                      {/* Thumbnail */}
                      <div className="w-10 h-10 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-center shrink-0 overflow-hidden">
                        {item.image_url ? (
                          <img
                            src={item.image_url}
                            alt=""
                            className="w-full h-full object-contain p-0.5"
                          />
                        ) : (
                          <Package className="w-4 h-4 text-slate-400" />
                        )}
                      </div>

                      {/* Name & Details */}
                      <div className="min-w-0">
                        <div
                          className={`text-sm font-semibold truncate ${
                            item.is_checked ? 'line-through text-slate-400' : 'text-slate-900'
                          } ${isSupermarketMode ? 'text-base font-bold' : ''}`}
                        >
                          {item.name}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-slate-400 mt-0.5">
                          <span className="font-bold text-slate-600">
                            {item.quantity} {item.unit_of_measure}
                          </span>
                          {item.brand && (
                            <span className="text-[10px] bg-emerald-50 text-emerald-700 font-semibold px-1.5 py-0.2 rounded">
                              {item.brand}
                            </span>
                          )}
                          {item.notes && <span className="italic text-slate-400">• {item.notes}</span>}
                        </div>
                      </div>
                    </div>

                    {/* Price and Delete Action */}
                    <div className="flex items-center gap-3 shrink-0">
                      <div className="text-right">
                        <div
                          className={`text-sm font-bold font-mono ${
                            item.is_checked ? 'text-slate-400' : 'text-slate-900'
                          }`}
                        >
                          {item.estimated_total > 0 ? `${item.estimated_total.toFixed(2)} €` : '—'}
                        </div>
                        {item.estimated_unit_price && (
                          <div className="text-[10px] text-slate-400">
                            ~{item.estimated_unit_price.toFixed(2)} €/{item.unit_of_measure}
                          </div>
                        )}
                      </div>

                      {!isSupermarketMode && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteItem(item.id);
                          }}
                          className="p-1.5 text-slate-300 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
                          title="Eliminar de la lista"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
