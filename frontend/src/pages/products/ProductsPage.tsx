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
  Link2,
  Loader2,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
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
  const [selectedProductForLinking, setSelectedProductForLinking] = useState<Product | null>(null);
  const [isNewAliasModalOpen, setIsNewAliasModalOpen] = useState(false);
  const [newAliasText, setNewAliasText] = useState('');
  const [aliasError, setAliasError] = useState<string | null>(null);
  const [isSuggestionsModalOpen, setIsSuggestionsModalOpen] = useState(false);

  // Suggestions & manual link state
  const [customUrls, setCustomUrls] = useState<Record<string, string>>({});
  const [bindingCandidateId, setBindingCandidateId] = useState<string | null>(null);
  const [bindingProductId, setBindingProductId] = useState<string | null>(null);
  const [successFeedback, setSuccessFeedback] = useState<Record<string, string>>({});
  const [modalError, setModalError] = useState<string | null>(null);

  // Category & Product Editor Modal State
  const [selectedProductForEdit, setSelectedProductForEdit] = useState<Product | null>(null);
  const [editCanonicalName, setEditCanonicalName] = useState('');
  const [editCategoryId, setEditCategoryId] = useState('');
  const [editDefaultUnit, setEditDefaultUnit] = useState('ud');
  const [editError, setEditError] = useState<string | null>(null);
  const [recategorizeNotice, setRecategorizeNotice] = useState<string | null>(null);

  // Manual link modal search state
  const [manualLinkInput, setManualLinkInput] = useState('');
  const [linkSearchQuery, setLinkSearchQuery] = useState('');

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
    queryFn: () => catalogApi.getMercadonaSuggestions(30),
    enabled: isSuggestionsModalOpen,
  });

  const { data: searchResults = [], isLoading: isSearchingOnline } = useQuery({
    queryKey: ['mercadonaSearch', linkSearchQuery],
    queryFn: () => catalogApi.searchMercadonaOnline(linkSearchQuery),
    enabled: !!linkSearchQuery && linkSearchQuery.trim().length >= 2,
  });

  // Match mutations
  const confirmMatchMutation = useMutation({
    mutationFn: ({
      productId,
      onlineId,
      urlOrId,
    }: {
      productId: string;
      onlineId?: string;
      urlOrId?: string;
    }) =>
      catalogApi.confirmMercadonaMatch(productId, {
        mercadonaOnlineId: onlineId,
        urlOrId,
      }),
    onSuccess: (updatedProduct, variables) => {
      setSuccessFeedback((prev) => ({
        ...prev,
        [variables.productId]: `¡Vinculado con "${updatedProduct.enriched_name}"!`,
      }));
      setModalError(null);
      // Clean up custom url for this product
      setCustomUrls((prev) => {
        const next = { ...prev };
        delete next[variables.productId];
        return next;
      });
      queryClient.invalidateQueries({ queryKey: ['products'] });
      queryClient.invalidateQueries({ queryKey: ['mercadonaSuggestions'] });
      queryClient.invalidateQueries({ queryKey: ['receipts'] });
      queryClient.invalidateQueries({ queryKey: ['analytics'] });
      if (selectedProductForLinking) {
        setSelectedProductForLinking(null);
        setManualLinkInput('');
        setLinkSearchQuery('');
      }
    },
    onError: (err: any) => {
      setModalError(err.response?.data?.detail || 'Error al vincular el producto.');
    },
    onSettled: () => {
      setBindingCandidateId(null);
      setBindingProductId(null);
    },
  });

  const rejectMatchMutation = useMutation({
    mutationFn: (productId: string) => catalogApi.rejectMercadonaMatch(productId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      queryClient.invalidateQueries({ queryKey: ['mercadonaSuggestions'] });
    },
  });

  const handleConfirmMatch = (productId: string, onlineId?: string, urlOrId?: string) => {
    setBindingProductId(productId);
    if (onlineId) setBindingCandidateId(onlineId);
    setModalError(null);
    confirmMatchMutation.mutate({ productId, onlineId, urlOrId });
  };

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

  // Product & Category Update Mutation
  const updateProductMutation = useMutation({
    mutationFn: ({
      productId,
      data,
    }: {
      productId: string;
      data: { canonical_name?: string; category_id?: string; default_unit?: string };
    }) => catalogApi.updateProduct(productId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      queryClient.invalidateQueries({ queryKey: ['receipts'] });
      queryClient.invalidateQueries({ queryKey: ['analytics'] });
      setSelectedProductForEdit(null);
      setEditError(null);
    },
    onError: (err: any) => {
      setEditError(err.response?.data?.detail || 'Error al actualizar el producto');
    },
  });

  // Recategorize All Mutation
  const recategorizeMutation = useMutation({
    mutationFn: (onlyOtros: boolean) => catalogApi.recategorizeAll(onlyOtros),
    onSuccess: (data: any) => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      queryClient.invalidateQueries({ queryKey: ['receipts'] });
      queryClient.invalidateQueries({ queryKey: ['analytics'] });
      setRecategorizeNotice(`¡${data.recategorized_count} productos reclasificados automáticamente con éxito!`);
      setTimeout(() => setRecategorizeNotice(null), 6000);
    },
  });

  const handleOpenEditProduct = (prod: Product) => {
    setSelectedProductForEdit(prod);
    setEditCanonicalName(prod.canonical_name);
    setEditCategoryId(prod.category_id);
    setEditDefaultUnit(prod.default_unit || 'ud');
    setEditError(null);
  };

  // Sorting & quick filter state
  type SortField = 'name' | 'category' | 'price' | 'observations' | 'linked';
  type SortDirection = 'asc' | 'desc';

  const [sortField, setSortField] = useState<SortField>('name');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const [enrichmentFilter, setEnrichmentFilter] = useState<'all' | 'enriched' | 'pending'>('all');

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection(field === 'price' || field === 'observations' ? 'desc' : 'asc');
    }
  };

  const displayedProducts = React.useMemo(() => {
    let list = [...products];

    if (enrichmentFilter === 'enriched') {
      list = list.filter((p) => !!p.mercadona_online_id || !!p.image_url);
    } else if (enrichmentFilter === 'pending') {
      list = list.filter((p) => !p.mercadona_online_id && !p.image_url);
    }

    list.sort((a, b) => {
      let comparison = 0;
      switch (sortField) {
        case 'name': {
          const nameA = (a.enriched_name || a.canonical_name).toLowerCase();
          const nameB = (b.enriched_name || b.canonical_name).toLowerCase();
          comparison = nameA.localeCompare(nameB, 'es');
          break;
        }
        case 'category': {
          const catA = (a.category_name || '').toLowerCase();
          const catB = (b.category_name || '').toLowerCase();
          comparison = catA.localeCompare(catB, 'es');
          break;
        }
        case 'price': {
          const priceA = a.latest_price !== null && a.latest_price !== undefined ? a.latest_price : -1;
          const priceB = b.latest_price !== null && b.latest_price !== undefined ? b.latest_price : -1;
          comparison = priceA - priceB;
          break;
        }
        case 'observations': {
          const obsA = a.observations_count ?? 0;
          const obsB = b.observations_count ?? 0;
          comparison = obsA - obsB;
          break;
        }
        case 'linked': {
          const linkedA = a.mercadona_online_id ? 1 : 0;
          const linkedB = b.mercadona_online_id ? 1 : 0;
          comparison = linkedA - linkedB;
          break;
        }
      }
      return sortDirection === 'asc' ? comparison : -comparison;
    });

    return list;
  }, [products, sortField, sortDirection, enrichmentFilter]);

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
        <div className="flex items-center gap-2">
          <button
            onClick={() => recategorizeMutation.mutate(false)}
            disabled={recategorizeMutation.isPending}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold border border-slate-200 shadow-xs transition disabled:opacity-50"
            title="Reclasificar inteligentemente todos los productos con categorías oficiales y heurísticas avanzadas"
          >
            {recategorizeMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin text-emerald-600" />
            ) : (
              <Sparkles className="w-4 h-4 text-emerald-600" />
            )}
            <span>Reclasificar Categorías</span>
          </button>
        </div>
      </div>

      {/* Recategorize Notice Banner */}
      {recategorizeNotice && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-xl flex items-center justify-between text-sm animate-in fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
            <span className="font-medium">{recategorizeNotice}</span>
          </div>
          <button onClick={() => setRecategorizeNotice(null)} className="text-emerald-600 hover:text-emerald-800">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

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
        <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Buscar por nombre canónico o alias de ticket (ej: plátano, pechuga, deo aloe)..."
              className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>

          {/* Quick enrichment filter pills */}
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl text-xs font-semibold self-start sm:self-center">
            <button
              onClick={() => setEnrichmentFilter('all')}
              className={`px-3 py-1.5 rounded-lg transition ${
                enrichmentFilter === 'all'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              Todos ({products.length})
            </button>
            <button
              onClick={() => setEnrichmentFilter('enriched')}
              className={`px-3 py-1.5 rounded-lg transition flex items-center gap-1 ${
                enrichmentFilter === 'enriched'
                  ? 'bg-white text-emerald-700 shadow-sm'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
              <span>Con foto ({enrichedCount})</span>
            </button>
            <button
              onClick={() => setEnrichmentFilter('pending')}
              className={`px-3 py-1.5 rounded-lg transition ${
                enrichmentFilter === 'pending'
                  ? 'bg-white text-amber-700 shadow-sm'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              Pendientes ({products.length - enrichedCount})
            </button>
          </div>
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
        ) : displayedProducts.length === 0 ? (
          <div className="p-12 text-center">
            <Package className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <h3 className="text-base font-semibold text-slate-800">No se encontraron productos</h3>
            <p className="text-sm text-slate-500 mt-1 max-w-sm mx-auto">
              Prueba con otro término de búsqueda o cambia los filtros seleccionados.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-600 border-b border-slate-200 text-xs uppercase font-semibold">
                <tr>
                  <th
                    onClick={() => handleSort('name')}
                    className="px-6 py-3.5 cursor-pointer select-none hover:bg-slate-100/80 transition"
                  >
                    <div className="flex items-center gap-1.5 group">
                      <span>Producto Canónico</span>
                      {sortField === 'name' ? (
                        sortDirection === 'asc' ? (
                          <ArrowUp className="w-3.5 h-3.5 text-emerald-600" />
                        ) : (
                          <ArrowDown className="w-3.5 h-3.5 text-emerald-600" />
                        )
                      ) : (
                        <ArrowUpDown className="w-3.5 h-3.5 text-slate-300 group-hover:text-slate-500" />
                      )}
                    </div>
                  </th>
                  <th
                    onClick={() => handleSort('category')}
                    className="px-6 py-3.5 cursor-pointer select-none hover:bg-slate-100/80 transition"
                  >
                    <div className="flex items-center gap-1.5 group">
                      <span>Categoría</span>
                      {sortField === 'category' ? (
                        sortDirection === 'asc' ? (
                          <ArrowUp className="w-3.5 h-3.5 text-emerald-600" />
                        ) : (
                          <ArrowDown className="w-3.5 h-3.5 text-emerald-600" />
                        )
                      ) : (
                        <ArrowUpDown className="w-3.5 h-3.5 text-slate-300 group-hover:text-slate-500" />
                      )}
                    </div>
                  </th>
                  <th className="px-6 py-3.5 text-center">Unidad</th>
                  <th
                    onClick={() => handleSort('price')}
                    className="px-6 py-3.5 text-right cursor-pointer select-none hover:bg-slate-100/80 transition"
                  >
                    <div className="flex items-center justify-end gap-1.5 group">
                      <span>Último Precio</span>
                      {sortField === 'price' ? (
                        sortDirection === 'asc' ? (
                          <ArrowUp className="w-3.5 h-3.5 text-emerald-600" />
                        ) : (
                          <ArrowDown className="w-3.5 h-3.5 text-emerald-600" />
                        )
                      ) : (
                        <ArrowUpDown className="w-3.5 h-3.5 text-slate-300 group-hover:text-slate-500" />
                      )}
                    </div>
                  </th>
                  <th
                    onClick={() => handleSort('observations')}
                    className="px-6 py-3.5 text-center cursor-pointer select-none hover:bg-slate-100/80 transition"
                  >
                    <div className="flex items-center justify-center gap-1.5 group">
                      <span>Compras</span>
                      {sortField === 'observations' ? (
                        sortDirection === 'asc' ? (
                          <ArrowUp className="w-3.5 h-3.5 text-emerald-600" />
                        ) : (
                          <ArrowDown className="w-3.5 h-3.5 text-emerald-600" />
                        )
                      ) : (
                        <ArrowUpDown className="w-3.5 h-3.5 text-slate-300 group-hover:text-slate-500" />
                      )}
                    </div>
                  </th>
                  <th className="px-6 py-3.5 text-center">Evolución</th>
                  <th className="px-6 py-3.5 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {displayedProducts.map((p) => {
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
                        <button
                          type="button"
                          onClick={() => handleOpenEditProduct(p)}
                          className="group/cat inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition hover:ring-2 hover:ring-emerald-400 hover:shadow-xs cursor-pointer text-left"
                          style={{
                            backgroundColor: `${p.category_color || '#10B981'}15`,
                            color: p.category_color || '#10B981',
                          }}
                          title="Haz clic para cambiar la categoría o tipo de producto"
                        >
                          <span
                            className="w-1.5 h-1.5 rounded-full"
                            style={{ backgroundColor: p.category_color || '#10B981' }}
                          />
                          <span>{p.category_name}</span>
                          <span className="text-[10px] opacity-40 group-hover/cat:opacity-100 transition ml-0.5">✎</span>
                        </button>
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
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleOpenEditProduct(p)}
                            className="inline-flex items-center gap-1 text-xs font-semibold text-slate-600 hover:text-emerald-700 bg-slate-100 hover:bg-emerald-50 px-2.5 py-1.5 rounded-lg transition"
                            title="Editar categoría o tipo de producto"
                          >
                            <Layers className="w-3.5 h-3.5" />
                            <span>Categoría</span>
                          </button>
                          <button
                            onClick={() => {
                              setSelectedProductForLinking(p);
                              setManualLinkInput(p.mercadona_url || p.mercadona_online_id || '');
                              setLinkSearchQuery('');
                              setModalError(null);
                            }}
                            className={`inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1.5 rounded-lg transition ${
                              p.mercadona_online_id
                                ? 'text-slate-600 hover:text-emerald-700 bg-slate-100 hover:bg-emerald-50'
                                : 'text-amber-700 hover:text-amber-800 bg-amber-50 hover:bg-amber-100'
                            }`}
                            title={p.mercadona_online_id ? 'Editar enlace oficial de Mercadona' : 'Vincular producto con Mercadona Online'}
                          >
                            <Link2 className="w-3.5 h-3.5" />
                            <span>{p.mercadona_online_id ? 'Editar Enlace' : 'Vincular'}</span>
                          </button>
                          <button
                            onClick={() => setSelectedProductForHistory(p)}
                            className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-600 hover:text-emerald-700 bg-emerald-50 hover:bg-emerald-100 px-3 py-1.5 rounded-lg transition"
                          >
                            <BarChart3 className="w-3.5 h-3.5" />
                            <span>Histórico</span>
                          </button>
                        </div>
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
          <div className="bg-white rounded-3xl shadow-2xl border border-slate-200 max-w-3xl w-full max-h-[88vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Header */}
            <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center flex-shrink-0">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">Sugerencias de Vinculación Mercadona</h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Coincidencias encontradas combinando el texto de los tickets y la comparación de precios oficiales.
                  </p>
                </div>
              </div>
              <button
                onClick={() => {
                  setIsSuggestionsModalOpen(false);
                  setModalError(null);
                }}
                className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-xl transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Error Banner */}
            {modalError && (
              <div className="mx-6 mt-4 p-3 rounded-xl bg-red-50 border border-red-200 flex items-center gap-2 text-red-700 text-xs">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{modalError}</span>
              </div>
            )}

            {/* Content List */}
            <div className="p-6 overflow-y-auto space-y-6 flex-1">
              {isLoadingSuggestions ? (
                <div className="py-16 text-center space-y-3">
                  <Loader2 className="w-8 h-8 text-emerald-600 animate-spin mx-auto" />
                  <p className="text-sm font-medium text-slate-600">
                    Analizando catálogo y comparando precios con tus tickets...
                  </p>
                </div>
              ) : suggestions.length === 0 ? (
                <div className="py-16 text-center space-y-3">
                  <CheckCircle2 className="w-14 h-14 text-emerald-500 mx-auto" />
                  <h4 className="text-lg font-bold text-slate-800">¡Todo al día!</h4>
                  <p className="text-xs text-slate-500 max-w-md mx-auto">
                    No quedan sugerencias pendientes. Todos los artículos coincidentes han sido vinculados o confirmados en el catálogo.
                  </p>
                </div>
              ) : (
                suggestions.map(({ product, candidates }) => {
                  const ticketName =
                    product.aliases && product.aliases.length > 0
                      ? product.aliases[0]
                      : product.canonical_name;
                  const isBindingThisProduct = bindingProductId === product.id;
                  const feedback = successFeedback[product.id];

                  return (
                    <div
                      key={product.id}
                      className="p-5 rounded-2xl border border-slate-200 bg-white shadow-sm space-y-4 hover:border-slate-300 transition"
                    >
                      {/* Product Header in Ticket */}
                      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-3 border-b border-slate-100">
                        <div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-[11px] font-mono font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-200">
                              Ticket: {ticketName}
                            </span>
                            {product.canonical_name !== ticketName && (
                              <span className="text-xs text-slate-500 font-medium">
                                ({product.canonical_name})
                              </span>
                            )}
                            <span
                              className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                              style={{
                                backgroundColor: `${product.category_color || '#10B981'}15`,
                                color: product.category_color || '#10B981',
                              }}
                            >
                              {product.category_name}
                            </span>
                          </div>
                          <div className="text-xs text-slate-500 mt-1 flex items-center gap-3">
                            {product.latest_price !== null && product.latest_price !== undefined && (
                              <span>
                                Último precio pagado:{' '}
                                <strong className="text-slate-800">{product.latest_price.toFixed(2)} €</strong>
                              </span>
                            )}
                            {product.latest_date && (
                              <span className="text-slate-400">Fecha: {product.latest_date}</span>
                            )}
                          </div>
                        </div>

                        <button
                          onClick={() => rejectMatchMutation.mutate(product.id)}
                          disabled={rejectMatchMutation.isPending}
                          className="text-xs text-slate-400 hover:text-rose-600 transition self-start sm:self-center"
                          title="Ignorar sugerencias para este producto"
                        >
                          Descartar
                        </button>
                      </div>

                      {/* Success Feedback Banner */}
                      {feedback && (
                        <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center gap-2 text-emerald-800 text-xs font-semibold animate-in fade-in">
                          <Check className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                          <span>{feedback}</span>
                        </div>
                      )}

                      {/* Suggested Candidates */}
                      <div className="space-y-2">
                        <div className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
                          Productos oficiales sugeridos:
                        </div>
                        {candidates.map(({ mercadona_product, score, price_match }) => {
                          const isBindingCandidate = bindingCandidateId === mercadona_product.id;
                          const productUrl =
                            mercadona_product.share_url ||
                            `https://tienda.mercadona.es/product/${mercadona_product.id}`;

                          return (
                            <div
                              key={mercadona_product.id}
                              className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-xl bg-slate-50/80 hover:bg-amber-50/40 border border-slate-100 gap-3 transition"
                            >
                              <div className="flex items-center gap-3 min-w-0">
                                {mercadona_product.thumbnail_url ? (
                                  <img
                                    src={mercadona_product.thumbnail_url}
                                    alt={mercadona_product.display_name}
                                    className="w-12 h-12 object-contain rounded-xl border border-slate-200 bg-white p-0.5 flex-shrink-0"
                                    loading="lazy"
                                  />
                                ) : (
                                  <div className="w-12 h-12 rounded-xl bg-slate-200 flex items-center justify-center text-slate-400 flex-shrink-0">
                                    <Package className="w-6 h-6" />
                                  </div>
                                )}

                                <div className="min-w-0">
                                  <div className="font-semibold text-slate-900 text-xs flex items-center gap-1.5 flex-wrap">
                                    <span className="truncate">{mercadona_product.display_name}</span>
                                    {mercadona_product.brand && (
                                      <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 flex-shrink-0">
                                        {mercadona_product.brand}
                                      </span>
                                    )}
                                  </div>

                                  <div className="flex items-center gap-2 flex-wrap text-[11px] text-slate-500 mt-1">
                                    {mercadona_product.packaging && (
                                      <span>{mercadona_product.packaging}</span>
                                    )}
                                    {mercadona_product.unit_price !== null && (
                                      <span className="font-medium text-slate-700">
                                        Web: {mercadona_product.unit_price?.toFixed(2)} €
                                      </span>
                                    )}
                                    {price_match && (
                                      <span className="inline-flex items-center gap-0.5 text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">
                                        <Check className="w-3 h-3" />
                                        Precio idéntico
                                      </span>
                                    )}
                                    <span className="font-bold text-amber-700 text-[10px] bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
                                      {Math.round(score * 100)}% coincidencia
                                    </span>
                                  </div>

                                  {/* Direct Link to Mercadona Online */}
                                  <div className="mt-1">
                                    <a
                                      href={productUrl}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-600 hover:text-emerald-700 hover:underline"
                                    >
                                      <span>Ver ficha en Mercadona Online</span>
                                      <ExternalLink className="w-3 h-3" />
                                    </a>
                                  </div>
                                </div>
                              </div>

                              <button
                                disabled={confirmMatchMutation.isPending}
                                onClick={() => handleConfirmMatch(product.id, mercadona_product.id)}
                                className="inline-flex items-center justify-center gap-1 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-sm transition disabled:opacity-50 flex-shrink-0"
                              >
                                {isBindingCandidate ? (
                                  <>
                                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                    <span>Vinculando...</span>
                                  </>
                                ) : (
                                  <>
                                    <Check className="w-3.5 h-3.5" />
                                    <span>Vincular</span>
                                  </>
                                )}
                              </button>
                            </div>
                          );
                        })}
                      </div>

                      {/* Manual Link by URL or ID Input */}
                      <div className="pt-2">
                        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-2">
                          <label className="block text-slate-700 font-semibold">
                            ¿No es ninguno de estos? Introduce el enlace o ID oficial:
                          </label>
                          <div className="flex gap-2">
                            <input
                              type="text"
                              value={customUrls[product.id] || ''}
                              onChange={(e) =>
                                setCustomUrls((prev) => ({ ...prev, [product.id]: e.target.value }))
                              }
                              placeholder="Ej: https://tienda.mercadona.es/product/14344/... o 14344"
                              className="flex-1 px-3 py-1.5 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 font-mono"
                            />
                            <button
                              disabled={
                                !customUrls[product.id]?.trim() ||
                                (isBindingThisProduct && !bindingCandidateId)
                              }
                              onClick={() =>
                                handleConfirmMatch(product.id, undefined, customUrls[product.id])
                              }
                              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold shadow-sm transition disabled:opacity-50"
                            >
                              {isBindingThisProduct && !bindingCandidateId ? (
                                <>
                                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                  <span>Guardando...</span>
                                </>
                              ) : (
                                <>
                                  <Link2 className="w-3.5 h-3.5" />
                                  <span>Vincular Enlace</span>
                                </>
                              )}
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-slate-100 bg-slate-50 flex justify-end">
              <button
                onClick={() => {
                  setIsSuggestionsModalOpen(false);
                  setModalError(null);
                }}
                className="px-5 py-2 text-xs font-semibold text-slate-700 hover:text-slate-900 hover:bg-slate-200/60 rounded-xl transition"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Manual Link Modal for any product */}
      {selectedProductForLinking && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl shadow-2xl border border-slate-200 max-w-xl w-full max-h-[85vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Header */}
            <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center flex-shrink-0">
                  <Link2 className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">Vincular con Mercadona Online</h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Asocia este producto con su ficha oficial para obtener foto CDN, nombre y marca.
                  </p>
                </div>
              </div>
              <button
                onClick={() => {
                  setSelectedProductForLinking(null);
                  setModalError(null);
                }}
                className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-xl transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content */}
            <div className="p-6 space-y-5 overflow-y-auto flex-1">
              {/* Product Info */}
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-1">
                <div className="font-semibold text-slate-800">
                  Producto local: {selectedProductForLinking.canonical_name}
                </div>
                {selectedProductForLinking.aliases && selectedProductForLinking.aliases.length > 0 && (
                  <div className="text-slate-500 font-mono text-[11px]">
                    En tickets: {selectedProductForLinking.aliases.join(', ')}
                  </div>
                )}
                {selectedProductForLinking.enriched_name && (
                  <div className="text-emerald-700 font-medium">
                    Vinculación actual: {selectedProductForLinking.enriched_name}
                  </div>
                )}
              </div>

              {/* Error banner */}
              {modalError && (
                <div className="p-3 rounded-xl bg-red-50 border border-red-200 flex items-center gap-2 text-red-700 text-xs">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{modalError}</span>
                </div>
              )}

              {/* URL or ID input */}
              <div className="space-y-2">
                <label className="block text-xs font-bold text-slate-700">
                  Opción 1: Introduce URL o ID de Mercadona
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={manualLinkInput}
                    onChange={(e) => setManualLinkInput(e.target.value)}
                    placeholder="https://tienda.mercadona.es/product/14344/... o 14344"
                    className="flex-1 px-3 py-2 text-xs bg-white border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 font-mono"
                  />
                  <button
                    disabled={!manualLinkInput.trim() || confirmMatchMutation.isPending}
                    onClick={() =>
                      handleConfirmMatch(selectedProductForLinking.id, undefined, manualLinkInput)
                    }
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-xl shadow-sm transition disabled:opacity-50"
                  >
                    {confirmMatchMutation.isPending ? 'Guardando...' : 'Vincular'}
                  </button>
                </div>
              </div>

              {/* Catalog search */}
              <div className="space-y-2 pt-2 border-t border-slate-100">
                <label className="block text-xs font-bold text-slate-700">
                  Opción 2: Buscar en los 4.577 productos del catálogo
                </label>
                <div className="relative">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    value={linkSearchQuery}
                    onChange={(e) => setLinkSearchQuery(e.target.value)}
                    placeholder="Escribe el nombre del producto (ej: jamon serrano, tomate, tarta...)"
                    className="w-full pl-9 pr-3 py-2 text-xs bg-white border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                {/* Search Results Dropdown / List */}
                {isSearchingOnline && (
                  <div className="text-center py-4 text-xs text-slate-400 flex items-center justify-center gap-1.5">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Buscando en catálogo oficial...</span>
                  </div>
                )}

                {searchResults.length > 0 && (
                  <div className="max-h-60 overflow-y-auto space-y-1.5 border border-slate-200 rounded-xl p-2 bg-slate-50/50">
                    {searchResults.map((item) => (
                      <div
                        key={item.id}
                        className="flex items-center justify-between p-2 rounded-lg bg-white hover:bg-emerald-50/60 border border-slate-100 transition"
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          {item.thumbnail_url ? (
                            <img
                              src={item.thumbnail_url}
                              alt={item.display_name}
                              className="w-9 h-9 object-contain rounded-lg border border-slate-200 bg-white p-0.5 flex-shrink-0"
                            />
                          ) : (
                            <div className="w-9 h-9 rounded-lg bg-slate-200 flex items-center justify-center text-slate-400 flex-shrink-0">
                              <Package className="w-4 h-4" />
                            </div>
                          )}
                          <div className="min-w-0 text-xs">
                            <div className="font-semibold text-slate-800 truncate">
                              {item.display_name}
                            </div>
                            <div className="text-[11px] text-slate-400">
                              {item.brand && <span className="font-bold text-emerald-700 mr-1.5">{item.brand}</span>}
                              {item.unit_price && <span>{item.unit_price.toFixed(2)} €</span>}
                            </div>
                          </div>
                        </div>

                        <button
                          disabled={confirmMatchMutation.isPending}
                          onClick={() => handleConfirmMatch(selectedProductForLinking.id, item.id)}
                          className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-semibold rounded-lg shadow-sm transition disabled:opacity-50 flex-shrink-0"
                        >
                          Elegir
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-slate-100 bg-slate-50 flex justify-end">
              <button
                onClick={() => {
                  setSelectedProductForLinking(null);
                  setModalError(null);
                }}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 transition"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Product & Category Editor Modal */}
      {selectedProductForEdit && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 w-full max-w-xl max-h-[92vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="p-6 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-3 min-w-0">
                {selectedProductForEdit.image_url ? (
                  <img
                    src={selectedProductForEdit.image_url}
                    alt={selectedProductForEdit.canonical_name}
                    className="w-12 h-12 object-contain rounded-xl border border-slate-200 bg-white p-1 flex-shrink-0"
                  />
                ) : (
                  <div className="w-12 h-12 rounded-xl bg-slate-100 flex items-center justify-center text-slate-400 flex-shrink-0">
                    <Package className="w-6 h-6" />
                  </div>
                )}
                <div className="min-w-0">
                  <h3 className="text-base font-bold text-slate-900 leading-tight truncate">
                    {selectedProductForEdit.enriched_name || selectedProductForEdit.canonical_name}
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Modificar categoría y datos maestros del producto
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedProductForEdit(null)}
                className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-5">
              {editError && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{editError}</span>
                </div>
              )}

              {/* Canonical Name */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Nombre Canónico del Producto
                </label>
                <input
                  type="text"
                  value={editCanonicalName}
                  onChange={(e) => setEditCanonicalName(e.target.value)}
                  className="w-full px-3.5 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="Ej: Acelga Limpia, Solomillo de Pavo..."
                />
                {selectedProductForEdit.aliases && selectedProductForEdit.aliases.length > 0 && (
                  <p className="text-[11px] text-slate-400 mt-1">
                    Texto en tickets: <span className="font-mono text-slate-600">{selectedProductForEdit.aliases.join(', ')}</span>
                  </p>
                )}
              </div>

              {/* Default Unit */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Unidad de Medida
                </label>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setEditDefaultUnit('ud')}
                    className={`flex-1 py-2 px-3 text-xs font-semibold rounded-xl border transition cursor-pointer ${
                      editDefaultUnit === 'ud'
                        ? 'border-emerald-500 bg-emerald-50 text-emerald-800 ring-2 ring-emerald-500/20'
                        : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    Unidad (ud)
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditDefaultUnit('kg')}
                    className={`flex-1 py-2 px-3 text-xs font-semibold rounded-xl border transition cursor-pointer ${
                      editDefaultUnit === 'kg'
                        ? 'border-emerald-500 bg-emerald-50 text-emerald-800 ring-2 ring-emerald-500/20'
                        : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    Peso / Granel (kg)
                  </button>
                </div>
              </div>

              {/* Category Grid */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-2">
                  Categoría / Tipo de Producto <span className="text-emerald-600">*</span>
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {categories.map((cat) => {
                    const isSelected = cat.id === editCategoryId;
                    return (
                      <button
                        type="button"
                        key={cat.id}
                        onClick={() => setEditCategoryId(cat.id)}
                        className={`flex items-center gap-2.5 p-2.5 rounded-xl border text-left text-xs font-medium transition cursor-pointer ${
                          isSelected
                            ? 'border-emerald-500 bg-emerald-50/70 text-emerald-950 font-semibold ring-2 ring-emerald-500/20'
                            : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-700'
                        }`}
                      >
                        <span
                          className="w-3 h-3 rounded-full flex-shrink-0"
                          style={{ backgroundColor: cat.color_hex || '#10B981' }}
                        />
                        <span className="flex-1 truncate">{cat.name}</span>
                        {isSelected && <Check className="w-4 h-4 text-emerald-600 flex-shrink-0" />}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Persistence Notice */}
              <div className="p-3 bg-amber-50/80 border border-amber-200/80 rounded-xl text-xs text-amber-900 flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                <p>
                  <strong>Persistencia asegurada:</strong> Este cambio se guardará de forma permanente en la base de datos. Todas las compras pasadas y los futuros tickets que coincidan con los alias de este producto usarán esta categoría y nombre automáticamente.
                </p>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
              <button
                type="button"
                onClick={() => setSelectedProductForEdit(null)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 transition"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={updateProductMutation.isPending || !editCategoryId}
                onClick={() => {
                  if (!editCategoryId) return;
                  updateProductMutation.mutate({
                    productId: selectedProductForEdit.id,
                    data: {
                      canonical_name: editCanonicalName.trim() || selectedProductForEdit.canonical_name,
                      category_id: editCategoryId,
                      default_unit: editDefaultUnit,
                    },
                  });
                }}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-xl transition shadow-sm disabled:opacity-50 cursor-pointer"
              >
                {updateProductMutation.isPending ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Guardando...</span>
                  </>
                ) : (
                  <>
                    <Check className="w-3.5 h-3.5" />
                    <span>Guardar Cambios</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
