import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Search,
  TrendingUp,
  TrendingDown,
  Minus,
  Package,
  Layers,
  Plus,
  X,
  History,
  AlertCircle,
  BarChart3,
  ExternalLink,
  Sparkles,
  Check,
  CheckCircle2,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { catalogApi } from '../../api/catalog.api';
import type { Product } from '../../types';

export const ProductsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedProductForHistory, setSelectedProductForHistory] = useState<Product | null>(null);
  const [isNewAliasModalOpen, setIsNewAliasModalOpen] = useState(false);
  const [newAliasText, setNewAliasText] = useState('');
  const [aliasError, setAliasError] = useState<string | null>(null);
  const [isSuggestionsModalOpen, setIsSuggestionsModalOpen] = useState(false);

  // Queries
  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: catalogApi.getCategories,
  });

  const { data: products = [], isLoading: isLoadingProducts } = useQuery({
    queryKey: ['products', selectedCategory, searchTerm],
    queryFn: () =>
      catalogApi.getProducts({
        category_id: selectedCategory || undefined,
        search: searchTerm || undefined,
      }),
  });

  const { data: priceHistory, isLoading: isLoadingHistory } = useQuery({
    queryKey: ['priceHistory', selectedProductForHistory?.id],
    queryFn: () =>
      selectedProductForHistory
        ? catalogApi.getPriceHistory(selectedProductForHistory.id)
        : null,
    enabled: !!selectedProductForHistory,
  });

  const { data: suggestions = [], isLoading: isLoadingSuggestions } = useQuery({
    queryKey: ['mercadonaSuggestions'],
    queryFn: () => catalogApi.getMercadonaSuggestions(25),
    enabled: isSuggestionsModalOpen,
  });

  // Match mutations
  const confirmMatchMutation = useMutation({
    mutationFn: ({ productId, onlineId }: { productId: string; onlineId: string }) =>
      catalogApi.confirmMercadonaMatch(productId, onlineId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      queryClient.invalidateQueries({ queryKey: ['mercadonaSuggestions'] });
    },
  });

  const rejectMatchMutation = useMutation({
    mutationFn: (productId: string) => catalogApi.rejectMercadonaMatch(productId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      queryClient.invalidateQueries({ queryKey: ['mercadonaSuggestions'] });
    },
  });

  // Alias Mutation
  const addAliasMutation = useMutation({
    mutationFn: ({ productId, alias }: { productId: string; alias: string }) =>
      catalogApi.addAlias(productId, { raw_name_normalized: alias, source: 'MERCADONA' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      queryClient.invalidateQueries({ queryKey: ['priceHistory', selectedProductForHistory?.id] });
      setNewAliasText('');
      setIsNewAliasModalOpen(false);
      setAliasError(null);
    },
    onError: (err: any) => {
      setAliasError(err.response?.data?.detail || 'Error al vincular el alias');
    },
  });

  const totalObservations = products.reduce((acc, p) => acc + (p.observations_count || 0), 0);
  const enrichedCount = products.filter((p) => p.image_url || p.mercadona_online_id).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Catálogo de Productos</h1>
          <p className="text-sm text-slate-500 mt-1">
            Normalización automática de tickets de Mercadona, variantes y seguimiento histórico de precios.
          </p>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <Package className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Productos Normalizados</p>
            <h3 className="text-2xl font-bold text-slate-900 mt-0.5">{products.length}</h3>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
            <History className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Precios Observados</p>
            <h3 className="text-2xl font-bold text-slate-900 mt-0.5">{totalObservations}</h3>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
            <Layers className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Categorías Activas</p>
            <h3 className="text-2xl font-bold text-slate-900 mt-0.5">{categories.length}</h3>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Enriquecidos Online</p>
              <h3 className="text-2xl font-bold text-slate-900 mt-0.5">
                {enrichedCount}{' '}
                <span className="text-xs font-normal text-slate-400">/ {products.length}</span>
              </h3>
            </div>
          </div>
          <button
            onClick={() => setIsSuggestionsModalOpen(true)}
            className="px-2.5 py-1.5 rounded-xl bg-amber-50 hover:bg-amber-100 text-amber-800 text-[11px] font-semibold border border-amber-200 transition"
          >
            Sugerencias
          </button>
        </div>
      </div>

      {/* Filters and Search */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm space-y-3">
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Buscar por nombre canónico o alias de ticket (ej: plátano, pechuga, deo aloe)..."
            className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        {/* Category Pills */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
          <button
            onClick={() => setSelectedCategory(null)}
            className={`px-3 py-1.5 rounded-full font-medium transition whitespace-nowrap ${
              selectedCategory === null
                ? 'bg-slate-900 text-white shadow-sm'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            Todas las categorías
          </button>
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(selectedCategory === cat.id ? null : cat.id)}
              className={`px-3 py-1.5 rounded-full font-medium transition whitespace-nowrap flex items-center gap-1.5 ${
                selectedCategory === cat.id
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: cat.color_hex || '#10B981' }}
              />
              {cat.name}
              {cat.product_count !== undefined && cat.product_count > 0 && (
                <span className="text-[10px] opacity-75">({cat.product_count})</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Products Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {isLoadingProducts ? (
          <div className="p-8 text-center text-sm text-slate-400">Cargando catálogo maestro...</div>
        ) : products.length === 0 ? (
          <div className="p-12 text-center">
            <Package className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <h3 className="text-base font-semibold text-slate-800">No se encontraron productos</h3>
            <p className="text-sm text-slate-500 mt-1 max-w-sm mx-auto">
              Prueba con otro término de búsqueda o importa tickets para poblar el catálogo automáticamente.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-600 border-b border-slate-200 text-xs uppercase font-semibold">
                <tr>
                  <th className="px-6 py-3.5">Producto Canónico</th>
                  <th className="px-6 py-3.5">Categoría</th>
                  <th className="px-6 py-3.5 text-center">Unidad</th>
                  <th className="px-6 py-3.5 text-right">Último Precio</th>
                  <th className="px-6 py-3.5 text-center">Observaciones</th>
                  <th className="px-6 py-3.5 text-center">Evolución</th>
                  <th className="px-6 py-3.5 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {products.map((p) => {
                  const hasPriceChange = p.min_price !== null && p.max_price !== null && p.min_price !== p.max_price;
                  const isUp = hasPriceChange && (p.latest_price || 0) > (p.min_price || 0);

                  return (
                    <tr key={p.id} className="hover:bg-slate-50/70 transition">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          {p.image_url ? (
                            <img
                              src={p.image_url}
                              alt={p.canonical_name}
                              className="w-10 h-10 object-contain rounded-xl border border-slate-200 bg-white p-0.5 flex-shrink-0"
                              loading="lazy"
                            />
                          ) : (
                            <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center text-slate-400 flex-shrink-0">
                              <Package className="w-5 h-5" />
                            </div>
                          )}
                          <div className="min-w-0">
                            <div className="font-semibold text-slate-900 flex items-center gap-1.5 flex-wrap">
                              <span>{p.enriched_name || p.canonical_name}</span>
                              {p.brand && (
                                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 flex-shrink-0">
                                  {p.brand}
                                </span>
                              )}
                              {p.mercadona_url && (
                                <a
                                  href={p.mercadona_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-slate-400 hover:text-emerald-600 transition flex-shrink-0"
                                  title="Ver en Mercadona Online"
                                >
                                  <ExternalLink className="w-3.5 h-3.5" />
                                </a>
                              )}
                            </div>
                            {p.enriched_name && p.enriched_name !== p.canonical_name && (
                              <div className="text-[11px] text-slate-400 font-mono">
                                Ticket: {p.canonical_name}
                              </div>
                            )}
                            {p.packaging && (
                              <div className="text-xs text-slate-500">{p.packaging}</div>
                            )}
                            {p.aliases && p.aliases.length > 0 && (
                              <div className="flex flex-wrap gap-1 mt-1">
                                {p.aliases.map((a, idx) => (
                                  <span
                                    key={idx}
                                    className="text-[10px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded font-mono"
                                  >
                                    {a}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium"
                          style={{
                            backgroundColor: `${p.category_color || '#10B981'}15`,
                            color: p.category_color || '#10B981',
                          }}
                        >
                          <span
                            className="w-1.5 h-1.5 rounded-full"
                            style={{ backgroundColor: p.category_color || '#10B981' }}
                          />
                          {p.category_name}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-center">
                        <span className="text-xs font-mono font-medium bg-slate-100 text-slate-700 px-2 py-0.5 rounded">
                          {p.default_unit}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right font-mono font-bold text-slate-900">
                        {p.latest_price !== null && p.latest_price !== undefined ? (
                          <>
                            {p.latest_price.toFixed(2)} €
                            {p.latest_price_per_kg_or_l && p.default_unit === 'kg' && (
                              <span className="block text-[11px] font-normal text-slate-400">
                                {p.latest_price_per_kg_or_l.toFixed(2)} €/kg
                              </span>
                            )}
                          </>
                        ) : (
                          <span className="text-slate-400 font-normal italic">Sin compras</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-center font-mono text-xs text-slate-600">
                        {p.observations_count}
                      </td>
                      <td className="px-6 py-4 text-center">
                        {p.observations_count && p.observations_count > 1 ? (
                          hasPriceChange ? (
                            isUp ? (
                              <span className="inline-flex items-center gap-1 text-xs text-rose-600 font-semibold bg-rose-50 px-2 py-0.5 rounded-full">
                                <TrendingUp className="w-3 h-3" /> Subida
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-xs text-emerald-600 font-semibold bg-emerald-50 px-2 py-0.5 rounded-full">
                                <TrendingDown className="w-3 h-3" /> Bajada
                              </span>
                            )
                          ) : (
                            <span className="inline-flex items-center gap-1 text-xs text-slate-500 font-medium bg-slate-100 px-2 py-0.5 rounded-full">
                              <Minus className="w-3 h-3" /> Estable
                            </span>
                          )
                        ) : (
                          <span className="text-xs text-slate-400">—</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() => setSelectedProductForHistory(p)}
                          className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-600 hover:text-emerald-700 bg-emerald-50 hover:bg-emerald-100 px-3 py-1.5 rounded-lg transition"
                        >
                          <BarChart3 className="w-3.5 h-3.5" />
                          Histórico
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Price Evolution & History Modal */}
      {selectedProductForHistory && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 w-full max-w-3xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="p-6 border-b border-slate-100 flex items-start justify-between bg-slate-50/60">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-bold text-slate-900">
                    {selectedProductForHistory.canonical_name}
                  </h3>
                  <span
                    className="text-[11px] font-semibold px-2 py-0.5 rounded-full"
                    style={{
                      backgroundColor: `${selectedProductForHistory.category_color || '#10B981'}15`,
                      color: selectedProductForHistory.category_color || '#10B981',
                    }}
                  >
                    {selectedProductForHistory.category_name}
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Evolución cronológica de precios observados en los tickets digitales.
                </p>
              </div>
              <button
                onClick={() => setSelectedProductForHistory(null)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-6">
              {isLoadingHistory ? (
                <div className="py-12 text-center text-sm text-slate-400">
                  Cargando observaciones históricas...
                </div>
              ) : !priceHistory || priceHistory.observations.length === 0 ? (
                <div className="py-12 text-center text-slate-500">
                  <History className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                  <p className="text-sm">No hay observaciones de compra registradas para este producto aún.</p>
                </div>
              ) : (
                <>
                  {/* Summary Metric Cards */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                      <span className="text-[11px] font-medium text-slate-400 uppercase">Precio Actual</span>
                      <p className="text-lg font-bold text-slate-900 mt-0.5 font-mono">
                        {priceHistory.current_price?.toFixed(2)} €
                      </p>
                    </div>
                    <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                      <span className="text-[11px] font-medium text-slate-400 uppercase">Mínimo Observado</span>
                      <p className="text-lg font-bold text-emerald-600 mt-0.5 font-mono">
                        {priceHistory.min_price?.toFixed(2)} €
                      </p>
                    </div>
                    <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                      <span className="text-[11px] font-medium text-slate-400 uppercase">Máximo Observado</span>
                      <p className="text-lg font-bold text-rose-600 mt-0.5 font-mono">
                        {priceHistory.max_price?.toFixed(2)} €
                      </p>
                    </div>
                    <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                      <span className="text-[11px] font-medium text-slate-400 uppercase">Variación Inflación</span>
                      <p
                        className={`text-lg font-bold mt-0.5 font-mono ${
                          (priceHistory.price_change_pct || 0) > 0
                            ? 'text-rose-600'
                            : (priceHistory.price_change_pct || 0) < 0
                            ? 'text-emerald-600'
                            : 'text-slate-700'
                        }`}
                      >
                        {priceHistory.price_change_pct !== null && priceHistory.price_change_pct !== undefined ? (
                          <>
                            {priceHistory.price_change_pct > 0 ? '+' : ''}
                            {priceHistory.price_change_pct.toFixed(1)} %
                          </>
                        ) : (
                          '0.0 %'
                        )}
                      </p>
                    </div>
                  </div>

                  {/* Recharts Price Evolution Chart */}
                  <div className="bg-white p-4 rounded-xl border border-slate-200">
                    <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-3">
                      Gráfica de Variación de Precio (€)
                    </h4>
                    <div className="h-56 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart
                          data={priceHistory.observations.map((o) => ({
                            date: o.observed_date,
                            price: o.unit_price,
                            store: o.store_code || 'Tienda',
                          }))}
                          margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                        >
                          <defs>
                            <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#10B981" stopOpacity={0.4} />
                              <stop offset="95%" stopColor="#10B981" stopOpacity={0.0} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                          <XAxis
                            dataKey="date"
                            tick={{ fontSize: 11, fill: '#64748B' }}
                            stroke="#CBD5E1"
                          />
                          <YAxis
                            domain={['auto', 'auto']}
                            tick={{ fontSize: 11, fill: '#64748B' }}
                            stroke="#CBD5E1"
                            unit=" €"
                          />
                          <Tooltip
                            formatter={(value: any) => [`${Number(value).toFixed(2)} €`, 'Precio']}
                            labelFormatter={(label) => `Fecha: ${label}`}
                            contentStyle={{
                              borderRadius: '0.75rem',
                              border: '1px solid #E2E8F0',
                              boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                              fontSize: '12px',
                            }}
                          />
                          <Area
                            type="monotone"
                            dataKey="price"
                            stroke="#10B981"
                            strokeWidth={2.5}
                            fillOpacity={1}
                            fill="url(#colorPrice)"
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Detailed Observations List */}
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                        Histórico de Compras Registradas ({priceHistory.observations.length})
                      </h4>
                      <button
                        onClick={() => setIsNewAliasModalOpen(true)}
                        className="text-xs text-emerald-600 hover:text-emerald-700 font-semibold flex items-center gap-1"
                      >
                        <Plus className="w-3.5 h-3.5" /> Vincular Nuevo Alias
                      </button>
                    </div>

                    <div className="border border-slate-200 rounded-xl overflow-hidden">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-50 text-slate-600 border-b border-slate-200 font-semibold">
                          <tr>
                            <th className="px-4 py-2.5">Fecha</th>
                            <th className="px-4 py-2.5">Descripción en Ticket</th>
                            <th className="px-4 py-2.5 text-center">Tienda</th>
                            <th className="px-4 py-2.5 text-right">Precio Unitario</th>
                            <th className="px-4 py-2.5 text-right">€ / kg</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {priceHistory.observations.map((obs) => (
                            <tr key={obs.id} className="hover:bg-slate-50/50">
                              <td className="px-4 py-2.5 font-mono text-slate-600">
                                {obs.observed_date}
                              </td>
                              <td className="px-4 py-2.5 text-slate-900 font-medium">
                                {obs.raw_description || selectedProductForHistory.canonical_name}
                              </td>
                              <td className="px-4 py-2.5 text-center font-mono text-slate-500">
                                {obs.store_code || '—'}
                              </td>
                              <td className="px-4 py-2.5 text-right font-mono font-bold text-slate-900">
                                {obs.unit_price.toFixed(2)} €
                              </td>
                              <td className="px-4 py-2.5 text-right font-mono text-slate-500">
                                {obs.price_per_kg_or_l ? `${obs.price_per_kg_or_l.toFixed(2)} €/kg` : '—'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-100 bg-slate-50 flex justify-end">
              <button
                onClick={() => setSelectedProductForHistory(null)}
                className="px-4 py-2 text-sm font-semibold text-slate-600 hover:text-slate-800 transition"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Alias Modal */}
      {isNewAliasModalOpen && selectedProductForHistory && (
        <div className="fixed inset-0 z-60 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-md w-full p-6 animate-in fade-in zoom-in-95 duration-150">
            <h3 className="text-base font-bold text-slate-900">Vincular Alias de Ticket</h3>
            <p className="text-xs text-slate-500 mt-1">
              Introduce el texto exacto tal y como aparece en un ticket para mapearlo automáticamente a{' '}
              <strong className="text-slate-700">{selectedProductForHistory.canonical_name}</strong>.
            </p>

            {aliasError && (
              <div className="mt-3 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{aliasError}</span>
              </div>
            )}

            <div className="mt-4 space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Texto en el Ticket
                </label>
                <input
                  type="text"
                  value={newAliasText}
                  onChange={(e) => setNewAliasText(e.target.value.toUpperCase())}
                  placeholder="EJ: DEO ROLL ON ALOE VERA"
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm font-mono uppercase focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  setIsNewAliasModalOpen(false);
                  setAliasError(null);
                }}
                className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={!newAliasText.trim() || addAliasMutation.isPending}
                onClick={() =>
                  addAliasMutation.mutate({
                    productId: selectedProductForHistory.id,
                    alias: newAliasText.trim(),
                  })
                }
                className="px-4 py-2 text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl transition disabled:opacity-50"
              >
                {addAliasMutation.isPending ? 'Guardando...' : 'Guardar Alias'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Suggestions Modal */}
      {isSuggestionsModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl shadow-2xl border border-slate-200 max-w-2xl w-full max-h-[85vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">Sugerencias de Vinculación Mercadona</h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Coincidencias encontradas entre los nombres del ticket y el catálogo oficial.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsSuggestionsModalOpen(false)}
                className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-xl transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-4 flex-1">
              {isLoadingSuggestions ? (
                <div className="py-12 text-center text-sm text-slate-400">
                  Calculando sugerencias de fuzzy matching...
                </div>
              ) : suggestions.length === 0 ? (
                <div className="py-12 text-center space-y-2">
                  <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto" />
                  <h4 className="text-base font-semibold text-slate-800">¡Todo al día!</h4>
                  <p className="text-xs text-slate-500 max-w-sm mx-auto">
                    No hay sugerencias pendientes de vinculación manual. Los productos coincidentes ya han sido enlazados o descartados.
                  </p>
                </div>
              ) : (
                suggestions.map(({ product, candidates }) => (
                  <div
                    key={product.id}
                    className="p-4 rounded-2xl border border-slate-200 bg-white shadow-sm space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-900 text-sm">{product.canonical_name}</span>
                        <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                          {product.category_name}
                        </span>
                      </div>
                      <button
                        onClick={() => rejectMatchMutation.mutate(product.id)}
                        className="text-xs text-slate-400 hover:text-rose-600 transition"
                      >
                        Descartar
                      </button>
                    </div>

                    <div className="space-y-2 pt-1">
                      {candidates.map(({ mercadona_product, score }) => (
                        <div
                          key={mercadona_product.id}
                          className="flex items-center justify-between p-3 rounded-xl bg-slate-50 hover:bg-amber-50/50 border border-slate-100 transition"
                        >
                          <div className="flex items-center gap-3">
                            {mercadona_product.thumbnail_url ? (
                              <img
                                src={mercadona_product.thumbnail_url}
                                alt={mercadona_product.display_name}
                                className="w-11 h-11 object-contain rounded-lg border border-slate-200 bg-white p-0.5 flex-shrink-0"
                              />
                            ) : (
                              <div className="w-11 h-11 rounded-lg bg-slate-200 flex items-center justify-center text-slate-400">
                                <Package className="w-5 h-5" />
                              </div>
                            )}
                            <div>
                              <div className="font-medium text-slate-800 text-xs flex items-center gap-1.5">
                                <span>{mercadona_product.display_name}</span>
                                {mercadona_product.brand && (
                                  <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-emerald-50 text-emerald-700">
                                    {mercadona_product.brand}
                                  </span>
                                )}
                              </div>
                              <div className="text-[11px] text-slate-500 mt-0.5 flex items-center gap-2">
                                {mercadona_product.packaging && <span>{mercadona_product.packaging}</span>}
                                {mercadona_product.unit_price && (
                                  <span>{mercadona_product.unit_price.toFixed(2)} €</span>
                                )}
                                <span className="font-semibold text-amber-700">
                                  Coincidencia: {Math.round(score * 100)}%
                                </span>
                              </div>
                            </div>
                          </div>

                          <button
                            disabled={confirmMatchMutation.isPending}
                            onClick={() =>
                              confirmMatchMutation.mutate({
                                productId: product.id,
                                onlineId: mercadona_product.id,
                              })
                            }
                            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-sm transition disabled:opacity-50"
                          >
                            <Check className="w-3.5 h-3.5" />
                            <span>Vincular</span>
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="p-4 border-t border-slate-100 bg-slate-50 flex justify-end">
              <button
                onClick={() => setIsSuggestionsModalOpen(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 transition"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
