import React, { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { receiptsApi } from '../../api/receipts.api';
import { useHousehold } from '../../context/HouseholdContext';
import { ReceiptDetailModal } from '../../components/receipts/ReceiptDetailModal';
import type { Receipt } from '../../types';
import {
  ShoppingCart,
  TrendingUp,
  TrendingDown,
  Calendar,
  CreditCard,
  ShoppingBag,
  Award,
  ChevronRight,
  Package,
  CalendarRange,
  X,
  Filter,
  Building2,
  Clock,
  Sparkles,
  MapPin,
  Layers,
  AlertCircle,
  Target,
  Tag,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

type DatePreset = 'ALL' | '30D' | 'THIS_MONTH' | 'LAST_MONTH' | 'THIS_YEAR' | 'CUSTOM';

const CustomCategoryTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-white p-3 rounded-2xl shadow-xl border border-slate-200 text-xs min-w-[190px] space-y-1.5 animate-in fade-in zoom-in-95">
        <div className="flex items-center gap-2 font-bold text-slate-900 border-b border-slate-100 pb-1.5">
          <span
            className="w-2.5 h-2.5 rounded-full shrink-0"
            style={{ backgroundColor: data.color_hex }}
          />
          <span className="truncate">{data.category_name}</span>
        </div>
        <div className="flex items-center justify-between text-slate-600">
          <span>Gasto total:</span>
          <span className="font-bold text-slate-900">{Number(data.total_spend).toFixed(2)} €</span>
        </div>
        <div className="flex items-center justify-between text-slate-600">
          <span>Cuota del carrito:</span>
          <span className="font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded">
            {data.percentage}%
          </span>
        </div>
        {data.items_count !== undefined && data.items_count > 0 && (
          <div className="flex items-center justify-between text-slate-400 text-[11px] pt-0.5">
            <span>Artículos comprados:</span>
            <span className="font-medium text-slate-700">{data.items_count} ud</span>
          </div>
        )}
      </div>
    );
  }
  return null;
};

export const DashboardPage: React.FC = () => {
  const { activeHousehold } = useHousehold();
  const [preset, setPreset] = useState<DatePreset>('ALL');
  const [customStartDate, setCustomStartDate] = useState<string>('');
  const [customEndDate, setCustomEndDate] = useState<string>('');
  const [showCustomPicker, setShowCustomPicker] = useState<boolean>(false);
  const [selectedReceipt, setSelectedReceipt] = useState<Receipt | null>(null);

  // Unassigned receipts query to notify multi-household users
  const { data: pendingData } = useQuery({
    queryKey: ['pending-receipts-count'],
    queryFn: receiptsApi.getPendingCount,
    refetchInterval: 15000,
  });
  const pendingCount = pendingData?.count || 0;

  // Calculate start and end dates based on selected preset
  const dateRange = useMemo(() => {
    const today = new Date();
    const formatDate = (d: Date) => d.toISOString().split('T')[0];

    switch (preset) {
      case '30D': {
        const start = new Date();
        start.setDate(today.getDate() - 30);
        return { start_date: formatDate(start), end_date: formatDate(today) };
      }
      case 'THIS_MONTH': {
        const start = new Date(today.getFullYear(), today.getMonth(), 1);
        return { start_date: formatDate(start), end_date: formatDate(today) };
      }
      case 'LAST_MONTH': {
        const start = new Date(today.getFullYear(), today.getMonth() - 1, 1);
        const end = new Date(today.getFullYear(), today.getMonth(), 0);
        return { start_date: formatDate(start), end_date: formatDate(end) };
      }
      case 'THIS_YEAR': {
        const start = new Date(today.getFullYear(), 0, 1);
        return { start_date: formatDate(start), end_date: formatDate(today) };
      }
      case 'CUSTOM': {
        return {
          start_date: customStartDate || undefined,
          end_date: customEndDate || undefined,
        };
      }
      case 'ALL':
      default:
        return { start_date: undefined, end_date: undefined };
    }
  }, [preset, customStartDate, customEndDate]);

  const queryParams = useMemo(() => ({
    household_id: activeHousehold?.id,
    start_date: dateRange.start_date,
    end_date: dateRange.end_date,
  }), [activeHousehold?.id, dateRange]);

  // Queries for real data
  const { data: summary, isLoading: loadingSummary } = useQuery({
    queryKey: ['analytics', 'summary', queryParams],
    queryFn: () => receiptsApi.getAnalyticsSummary(queryParams),
  });

  const { data: categories = [] } = useQuery({
    queryKey: ['analytics', 'categories', queryParams],
    queryFn: () => receiptsApi.getCategoryDistribution(queryParams),
  });

  const { data: spendingHistory = [] } = useQuery({
    queryKey: ['analytics', 'history', queryParams],
    queryFn: () => receiptsApi.getSpendingEvolution(queryParams),
  });

  const [topProductsSort, setTopProductsSort] = useState<'spend' | 'purchases'>('spend');

  const { data: topProducts = [] } = useQuery({
    queryKey: ['analytics', 'topProducts', queryParams, topProductsSort],
    queryFn: () => receiptsApi.getTopProducts({ ...queryParams, limit: 6, sort_by: topProductsSort }),
  });

  const { data: habits } = useQuery({
    queryKey: ['analytics', 'habits', queryParams],
    queryFn: () => receiptsApi.getHabits(queryParams),
  });

  const { data: receipts = [] } = useQuery({
    queryKey: ['receipts', queryParams],
    queryFn: () => receiptsApi.getAll(queryParams),
  });

  const recentReceipts = receipts.slice(0, 5);

  const handleOpenReceiptDetail = async (receiptId: string) => {
    try {
      const full = await receiptsApi.getById(receiptId);
      setSelectedReceipt(full);
    } catch {
      alert('Error al cargar el detalle del ticket.');
    }
  };

  const handleSelectPreset = (p: DatePreset) => {
    setPreset(p);
    if (p !== 'CUSTOM') {
      setShowCustomPicker(false);
    }
  };

  const handleEnableCustomPicker = () => {
    setPreset('CUSTOM');
    setShowCustomPicker(true);
    if (!customStartDate || !customEndDate) {
      const today = new Date();
      const thirtyDaysAgo = new Date();
      thirtyDaysAgo.setDate(today.getDate() - 30);
      setCustomStartDate(thirtyDaysAgo.toISOString().split('T')[0]);
      setCustomEndDate(today.toISOString().split('T')[0]);
    }
  };

  const formatLastPurchase = (raw?: string | null) => {
    if (!raw) return { date: 'Sin compras', time: null };
    if (raw.includes(' ')) {
      const [d, t] = raw.split(' ');
      return { date: d, time: t };
    }
    return { date: raw, time: null };
  };

  const lastPurchase = formatLastPurchase(summary?.last_purchase_date);

  return (
    <div className="space-y-6">
      {/* Pending Unassigned Receipts Warning Alert Banner */}
      {pendingCount > 0 && (
        <div className="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200/90 rounded-2xl p-4 shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 animate-in fade-in">
          <div className="flex items-center space-x-3.5">
            <div className="w-10 h-10 rounded-xl bg-amber-500/15 text-amber-700 flex items-center justify-center flex-shrink-0">
              <AlertCircle className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-amber-950 flex items-center gap-2">
                <span>Tienes {pendingCount} {pendingCount === 1 ? 'ticket pendiente' : 'tickets pendientes'} de asignar</span>
                <span className="text-[11px] font-bold bg-amber-200/70 text-amber-800 px-2 py-0.5 rounded-full">
                  Acción requerida
                </span>
              </h4>
              <p className="text-xs text-amber-800/80 mt-0.5">
                Al pertenecer a más de un hogar, debes seleccionar el hogar de destino para tus tickets importados.
              </p>
            </div>
          </div>
          <Link
            to="/receipts?tab=pending"
            className="inline-flex items-center justify-center space-x-1.5 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold rounded-xl shadow-sm transition flex-shrink-0"
          >
            <span>Asignar ahora</span>
            <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
      )}

      {/* Page Header with Date Filter Controls */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Dashboard de Gastos</h1>
            <p className="text-sm text-slate-500 mt-1">
              Resumen contable y analítica de compras de{' '}
              <span className="font-semibold text-slate-800">
                {activeHousehold?.name || 'tu hogar'}
              </span>
            </p>
          </div>

          {/* Quick Preset Pills */}
          <div className="flex items-center flex-wrap bg-slate-100 p-1 rounded-2xl text-xs font-semibold text-slate-600 gap-1 border border-slate-200">
            <button
              onClick={() => handleSelectPreset('ALL')}
              className={`px-3 py-1.5 rounded-xl transition ${
                preset === 'ALL'
                  ? 'bg-white text-emerald-800 shadow-sm font-bold'
                  : 'hover:text-slate-900 text-slate-600'
              }`}
            >
              Histórico
            </button>
            <button
              onClick={() => handleSelectPreset('30D')}
              className={`px-3 py-1.5 rounded-xl transition ${
                preset === '30D'
                  ? 'bg-white text-emerald-800 shadow-sm font-bold'
                  : 'hover:text-slate-900 text-slate-600'
              }`}
            >
              30 Días
            </button>
            <button
              onClick={() => handleSelectPreset('THIS_MONTH')}
              className={`px-3 py-1.5 rounded-xl transition ${
                preset === 'THIS_MONTH'
                  ? 'bg-white text-emerald-800 shadow-sm font-bold'
                  : 'hover:text-slate-900 text-slate-600'
              }`}
            >
              Este Mes
            </button>
            <button
              onClick={() => handleSelectPreset('LAST_MONTH')}
              className={`px-3 py-1.5 rounded-xl transition ${
                preset === 'LAST_MONTH'
                  ? 'bg-white text-emerald-800 shadow-sm font-bold'
                  : 'hover:text-slate-900 text-slate-600'
              }`}
            >
              Mes Ant.
            </button>
            <button
              onClick={() => handleSelectPreset('THIS_YEAR')}
              className={`px-3 py-1.5 rounded-xl transition ${
                preset === 'THIS_YEAR'
                  ? 'bg-white text-emerald-800 shadow-sm font-bold'
                  : 'hover:text-slate-900 text-slate-600'
              }`}
            >
              Este Año
            </button>
            <button
              onClick={handleEnableCustomPicker}
              className={`inline-flex items-center space-x-1 px-3 py-1.5 rounded-xl transition ${
                preset === 'CUSTOM'
                  ? 'bg-emerald-600 text-white shadow-sm font-bold'
                  : 'hover:text-slate-900 text-slate-600'
              }`}
            >
              <CalendarRange className="w-3.5 h-3.5" />
              <span>Personalizado</span>
            </button>
          </div>
        </div>

        {/* Custom Calendar Date Picker Toolbar */}
        {(showCustomPicker || preset === 'CUSTOM') && (
          <div className="bg-emerald-50/60 border border-emerald-200/80 rounded-2xl p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 animate-in fade-in slide-in-from-top-2 duration-150">
            <div className="flex items-center space-x-2 text-xs font-semibold text-emerald-900">
              <Filter className="w-4 h-4 text-emerald-700" />
              <span>Rango de fechas personalizado:</span>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center space-x-2 text-xs">
                <label className="text-slate-600 font-medium">Desde:</label>
                <input
                  type="date"
                  value={customStartDate}
                  onChange={(e) => {
                    setCustomStartDate(e.target.value);
                    setPreset('CUSTOM');
                  }}
                  className="bg-white border border-slate-300 rounded-xl px-2.5 py-1 text-xs text-slate-800 font-medium shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="flex items-center space-x-2 text-xs">
                <label className="text-slate-600 font-medium">Hasta:</label>
                <input
                  type="date"
                  value={customEndDate}
                  onChange={(e) => {
                    setCustomEndDate(e.target.value);
                    setPreset('CUSTOM');
                  }}
                  className="bg-white border border-slate-300 rounded-xl px-2.5 py-1 text-xs text-slate-800 font-medium shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <button
                onClick={() => {
                  setCustomStartDate('');
                  setCustomEndDate('');
                  handleSelectPreset('ALL');
                }}
                className="inline-flex items-center space-x-1 text-[11px] font-semibold text-slate-500 hover:text-slate-800 px-2 py-1 rounded-lg hover:bg-slate-200/50 transition"
                title="Limpiar y volver a Histórico"
              >
                <X className="w-3.5 h-3.5" />
                <span>Restablecer</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Spend */}
        <div className="bg-white p-5 rounded-3xl border border-slate-200 shadow-sm space-y-2 relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase tracking-wider">
            <span>Gasto Acumulado</span>
            <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {loadingSummary ? '...' : `${summary?.total_spend?.toFixed(2) || '0.00'} €`}
          </div>

          <div className="pt-1 flex flex-col gap-0.5">
            {preset === 'ALL' || !dateRange.start_date ? null : summary?.previous_spend && summary.previous_spend > 0 ? (
              <div className="flex items-center gap-1.5 text-xs">
                <span
                  className={`inline-flex items-center font-bold px-2 py-0.5 rounded-full text-[11px] ${
                    summary.spend_variation_pct <= 0
                      ? 'bg-emerald-50 text-emerald-700'
                      : 'bg-rose-50 text-rose-700'
                  }`}
                >
                  {summary.spend_variation_pct <= 0 ? (
                    <TrendingDown className="w-3 h-3 mr-0.5" />
                  ) : (
                    <TrendingUp className="w-3 h-3 mr-0.5" />
                  )}
                  {summary.spend_variation_pct > 0 ? '+' : ''}
                  {summary.spend_variation_pct}%
                </span>
                <span className="text-slate-500 text-[11px] truncate" title={summary.comparison_label || ''}>
                  {summary.comparison_label || `vs ${summary.previous_spend.toFixed(2)} € ant.`}
                </span>
              </div>
            ) : summary?.comparison_label ? (
              <div className="flex items-center gap-1.5 text-xs text-slate-400">
                <span>{summary.comparison_label}</span>
              </div>
            ) : null}
          </div>
        </div>

        {/* Number of Receipts */}
        <div className="bg-white p-5 rounded-3xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase tracking-wider">
            <span>Tickets de Compra</span>
            <div className="w-8 h-8 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
              <ShoppingCart className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {loadingSummary ? '...' : summary?.receipt_count || 0}
          </div>
          <p className="text-xs text-slate-500 flex items-center gap-1">
            <Package className="w-3.5 h-3.5 text-blue-500" />
            <span>{summary?.total_items_count || 0} artículos adquiridos</span>
          </p>
        </div>

        {/* Average Ticket & Median */}
        <div className="bg-white p-5 rounded-3xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase tracking-wider">
            <span>Ticket Medio</span>
            <div className="w-8 h-8 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
              <CreditCard className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {loadingSummary ? '...' : `${summary?.average_ticket?.toFixed(2) || '0.00'} €`}
          </div>
          <p className="text-xs text-slate-500">
            Mediana contable: <span className="font-semibold text-slate-700">{summary?.median_ticket?.toFixed(2) || '0.00'} €</span>
          </p>
        </div>

        {/* Sync Status & Last Purchase with date and time */}
        <div className="bg-white p-5 rounded-3xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase tracking-wider">
            <span>Última Compra</span>
            <div className="w-8 h-8 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
              <Calendar className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-xl font-bold text-slate-900 tracking-tight">
              {lastPurchase.date}
            </span>
            {lastPurchase.time && (
              <span className="text-xs font-bold text-purple-700 bg-purple-50 px-2 py-0.5 rounded-md border border-purple-100">
                {lastPurchase.time}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 flex items-center gap-1.5 truncate">
            <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0"></span>
            <span>{summary?.last_sync_at || 'Al día'}</span>
          </p>
        </div>
      </div>

      {/* Quick Insights Highlights Bar */}
      {summary && (
        <div className="bg-gradient-to-r from-emerald-50/70 via-white to-blue-50/70 border border-slate-200/80 rounded-2xl p-3 px-4 shadow-2xs flex flex-wrap items-center justify-between gap-3 text-xs text-slate-700">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-600 shrink-0" />
            <span className="font-semibold text-slate-900">Datos Clave:</span>
          </div>

          <div className="flex flex-wrap items-center gap-4 sm:gap-6 text-xs">
            {typeof summary.max_ticket_amount === 'number' && summary.max_ticket_amount > 0 && (
              <div className="flex items-center gap-1.5">
                <span className="text-slate-400">Ticket Récord:</span>
                <span className="font-bold text-slate-900">{summary.max_ticket_amount.toFixed(2)} €</span>
                {typeof summary.min_ticket_amount === 'number' && summary.min_ticket_amount > 0 && (
                  <span className="text-slate-400 text-[11px]">(Mín: {summary.min_ticket_amount.toFixed(2)} €)</span>
                )}
              </div>
            )}

            {summary.shopping_frequency_days !== undefined && summary.shopping_frequency_days !== null && (
              <div className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                <span className="text-slate-400">Frecuencia:</span>
                <span className="font-bold text-slate-900">1 compra cada ~{summary.shopping_frequency_days} días</span>
              </div>
            )}

            {habits?.favorite_day && (
              <div className="flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-purple-500 shrink-0" />
                <span className="text-slate-400">Día preferido:</span>
                <span className="font-bold text-slate-900">{habits.favorite_day}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Monthly Budget Progress Widget */}
      {summary?.monthly_budget ? (
        <div className="bg-white p-5 rounded-3xl border border-slate-200 shadow-sm space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-emerald-50 text-emerald-700 flex items-center justify-center shrink-0 shadow-sm shadow-emerald-500/10">
                <Target className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-slate-900">
                    Presupuesto Mensual: {summary.monthly_budget.toFixed(2)} €
                  </h3>
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      (summary.budget_spent_pct || 0) > 100
                        ? 'bg-rose-100 text-rose-800'
                        : (summary.budget_spent_pct || 0) > 80
                        ? 'bg-amber-100 text-amber-800'
                        : 'bg-emerald-100 text-emerald-800'
                    }`}
                  >
                    {summary.budget_spent_pct || 0}% consumido
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Llevas gastados <strong className="text-slate-800 font-semibold">{summary.current_month_spend?.toFixed(2) || '0.00'} €</strong> en lo que va de mes
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4 text-xs bg-slate-50 px-3.5 py-2 rounded-2xl border border-slate-100">
              <div>
                <span className="text-slate-400 block text-[10px]">Proyección fin de mes</span>
                <span
                  className={`font-bold font-mono ${
                    (summary.projected_month_spend || 0) > summary.monthly_budget
                      ? 'text-rose-600'
                      : 'text-emerald-700'
                  }`}
                >
                  ~{summary.projected_month_spend?.toFixed(2) || '0.00'} €
                </span>
              </div>
              <div className="border-l border-slate-200 pl-4">
                <span className="text-slate-400 block text-[10px]">Restante disponible</span>
                <span
                  className={`font-bold font-mono ${
                    (summary.budget_remaining || 0) < 0 ? 'text-rose-600' : 'text-slate-800'
                  }`}
                >
                  {summary.budget_remaining?.toFixed(2) || '0.00'} €
                </span>
              </div>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                (summary.budget_spent_pct || 0) > 100
                  ? 'bg-rose-500'
                  : (summary.budget_spent_pct || 0) > 80
                  ? 'bg-amber-500'
                  : 'bg-emerald-500'
              }`}
              style={{ width: `${Math.min(100, Math.max(0, summary.budget_spent_pct || 0))}%` }}
            />
          </div>
        </div>
      ) : (
        <div className="bg-gradient-to-r from-emerald-50/70 to-teal-50/40 p-4 rounded-3xl border border-emerald-200/60 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-2xl bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
              <Target className="w-4 h-4" />
            </div>
            <div>
              <div className="text-xs font-bold text-slate-800">Fija un presupuesto mensual para tu hogar</div>
              <div className="text-[11px] text-slate-500">SuperDato proyectará tu consumo diario para mantener tus finanzas bajo control.</div>
            </div>
          </div>
          <Link
            to="/settings"
            className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold shadow-sm shrink-0 transition"
          >
            Configurar Presupuesto
          </Link>
        </div>
      )}

      {/* Main Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Spending History Chart */}
        <div className="lg:col-span-2 bg-white p-6 rounded-3xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-bold text-slate-900">Evolución de Compras</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Gasto por fecha de compra en euros (€)
              </p>
            </div>
            <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
              {spendingHistory.length} fechas registradas
            </span>
          </div>

          <div className="h-64 w-full">
            {spendingHistory.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={spendingHistory} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <XAxis
                    dataKey="date"
                    stroke="#94a3b8"
                    fontSize={11}
                    tickLine={false}
                    tickFormatter={(val) => val.slice(5)}
                  />
                  <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} unit="€" />
                  <Tooltip
                    formatter={(val: any) => [`${Number(val).toFixed(2)} €`, 'Importe']}
                    labelFormatter={(label) => `Fecha: ${label}`}
                    contentStyle={{ borderRadius: '16px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  />
                  <Bar dataKey="total_amount" fill="#007A3D" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-400 text-sm">
                No hay compras en el periodo seleccionado
              </div>
            )}
          </div>
        </div>

        {/* Category Distribution Donut Chart */}
        <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900 mb-0.5">Distribución por Categorías</h2>
            <p className="text-xs text-slate-500 mb-2">Porcentaje de gasto por sección</p>
          </div>

          <div className="h-44 w-full flex items-center justify-center">
            {categories.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={categories}
                    dataKey="total_spend"
                    nameKey="category_name"
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={70}
                    paddingAngle={3}
                  >
                    {categories.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color_hex} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomCategoryTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-slate-400 text-sm">Sin datos de categorías</div>
            )}
          </div>

          {/* Category Legend List */}
          <div className="space-y-1.5 mt-3 max-h-36 overflow-y-auto pr-1">
            {categories.slice(0, 5).map((cat) => (
              <div key={cat.category_name} className="flex items-center justify-between text-xs">
                <div className="flex items-center space-x-2">
                  <div
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: cat.color_hex }}
                  />
                  <span className="text-slate-700 font-medium truncate max-w-[130px]">
                    {cat.category_name}
                  </span>
                </div>
                <span className="font-semibold text-slate-900">
                  {cat.total_spend.toFixed(2)} € <span className="text-slate-400 text-[11px]">({cat.percentage}%)</span>
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom Section: Top Products & Recent Receipts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top 5 Products Table */}
        <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 flex flex-col justify-between">
          <div>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
              <div className="flex items-center space-x-2">
                <Award className="w-5 h-5 text-amber-500" />
                <h2 className="text-base font-bold text-slate-900">Top Productos</h2>
              </div>

              {/* Sort Switcher: Por Dinero vs Por Nº Compras */}
              <div className="flex items-center bg-slate-100 p-0.5 rounded-xl text-xs font-semibold self-start sm:self-center">
                <button
                  type="button"
                  onClick={() => setTopProductsSort('spend')}
                  className={`px-2.5 py-1 rounded-lg transition cursor-pointer ${
                    topProductsSort === 'spend'
                      ? 'bg-white text-emerald-800 shadow-xs font-bold'
                      : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  Por Dinero (€)
                </button>
                <button
                  type="button"
                  onClick={() => setTopProductsSort('purchases')}
                  className={`px-2.5 py-1 rounded-lg transition cursor-pointer ${
                    topProductsSort === 'purchases'
                      ? 'bg-white text-emerald-800 shadow-xs font-bold'
                      : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  Por Nº Compras
                </button>
              </div>
            </div>

            <div className="divide-y divide-slate-100">
              {topProducts.length > 0 ? (
                topProducts.map((p, idx) => (
                  <div key={p.product_id || p.product_name} className="py-3 flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      {p.image_url ? (
                        <img
                          src={p.image_url}
                          alt={p.product_name}
                          className="w-8 h-8 rounded-lg object-contain border border-slate-200 bg-white p-0.5 shrink-0"
                          loading="lazy"
                        />
                      ) : (
                        <div className="w-8 h-8 rounded-lg bg-slate-100 text-slate-600 font-bold text-xs flex items-center justify-center shrink-0">
                          #{idx + 1}
                        </div>
                      )}
                      <div>
                        <h4 className="text-xs font-semibold text-slate-900 truncate max-w-[180px] sm:max-w-[240px]">
                          {p.enriched_name || p.product_name}
                        </h4>
                        <div className="flex items-center space-x-2 text-[11px] text-slate-400 mt-0.5">
                          {p.brand && (
                            <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-emerald-50 text-emerald-700">
                              {p.brand}
                            </span>
                          )}
                          <span className="px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 font-medium">
                            {p.category_name}
                          </span>
                          <span>•</span>
                          <span>{p.purchases_count} compras ({p.total_quantity} ud/kg)</span>
                        </div>
                      </div>
                    </div>

                    <div className="text-right">
                      <div className="text-sm font-bold text-slate-900">
                        {p.total_spend.toFixed(2)} €
                      </div>
                      <span className="text-[11px] text-slate-400">
                        ~{p.average_price.toFixed(2)} €/ud
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="py-8 text-center text-slate-400 text-xs">
                  Sin productos registrados en este periodo
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Recent Purchases List */}
        <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2">
                <ShoppingBag className="w-5 h-5 text-emerald-600" />
                <h2 className="text-base font-bold text-slate-900">Tickets Recientes</h2>
              </div>
              <span className="text-xs text-slate-400">Haz clic para auditar</span>
            </div>

            <div className="divide-y divide-slate-100">
              {recentReceipts.length > 0 ? (
                recentReceipts.map((r) => (
                  <div
                    key={r.id}
                    onClick={() => handleOpenReceiptDetail(r.id)}
                    className="py-3 flex items-center justify-between hover:bg-slate-50/80 -mx-3 px-3 rounded-2xl cursor-pointer transition"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center">
                        <ShoppingBag className="w-4 h-4" />
                      </div>
                      <div>
                        <h4 className="text-xs font-bold text-slate-900">
                          Factura {r.invoice_number}
                        </h4>
                        <p className="text-[11px] text-slate-500 mt-0.5">
                          {r.store_address ? `${r.store_address}, ${r.store_city || ''}` : 'Mercadona'} • {r.lines_count || 0} art.
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-3">
                      <div className="text-right">
                        <div className="text-sm font-extrabold text-slate-900">
                          {r.total_amount.toFixed(2)} €
                        </div>
                        <span className="text-[11px] text-slate-400">{r.purchase_date}</span>
                      </div>
                      <ChevronRight className="w-4 h-4 text-slate-400" />
                    </div>
                  </div>
                ))
              ) : (
                <div className="py-8 text-center text-slate-400 text-xs">
                  No hay tickets en el periodo seleccionado
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Habits & Telemetry Section */}
      {habits && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div>
              <h2 className="text-lg font-bold text-slate-900 tracking-tight">Hábitos de Compra y Perfil del Hogar</h2>
              <p className="text-xs text-slate-500">Patrones semanales de compra, tiendas habituales y balance de la cesta familiar</p>
            </div>
            {habits.favorite_day && (
              <span className="text-xs font-semibold text-emerald-800 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200 self-start sm:self-auto">
                Día favorito: <strong className="text-emerald-950 font-bold">{habits.favorite_day}</strong>
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Weekdays Distribution Card */}
            <div className="bg-white p-5 rounded-3xl border border-slate-200 shadow-sm space-y-3 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
                      <Calendar className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-900">Días de la Semana</h3>
                      <p className="text-[11px] text-slate-400">Gasto según día de compra</p>
                    </div>
                  </div>
                </div>

                <div className="space-y-2.5">
                  {habits.weekday_distribution.map((w) => {
                    const isFav = w.day_name === habits.favorite_day;
                    return (
                      <div key={w.day_name} className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className={`font-medium ${isFav ? 'text-emerald-700 font-bold' : 'text-slate-700'}`}>
                            {w.day_name} {isFav && '★'}
                          </span>
                          <span className="text-slate-600 font-mono text-[11px]">
                            {w.total_spend.toFixed(2)} € <span className="text-slate-400">({w.percentage}%)</span>
                          </span>
                        </div>
                        <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-300 ${
                              isFav ? 'bg-emerald-600' : 'bg-purple-400'
                            }`}
                            style={{ width: `${Math.min(100, Math.max(0, w.percentage))}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="pt-2 border-t border-slate-100 text-[11px] text-slate-400">
                Los {habits.favorite_day || 'fines de semana'} concentran el mayor volumen de compras de tu hogar.
              </div>
            </div>

            {/* Top Stores Card */}
            <div className="bg-white p-5 rounded-3xl border border-slate-200 shadow-sm space-y-3 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
                      <Building2 className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-900">Supermercados Visitados</h3>
                      <p className="text-[11px] text-slate-400">Tiendas Mercadona más frecuentes</p>
                    </div>
                  </div>
                </div>

                <div className="space-y-2.5 divide-y divide-slate-50">
                  {habits.top_stores.length > 0 ? (
                    habits.top_stores.map((s) => (
                      <div key={s.store_name} className="pt-2 first:pt-0 flex items-start justify-between gap-2">
                        <div className="flex items-start gap-2 min-w-0">
                          <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
                          <div className="min-w-0">
                            <h4 className="text-xs font-semibold text-slate-900 truncate">
                              {s.store_name}
                            </h4>
                            <p className="text-[11px] text-slate-400">
                              {s.city || 'Mercadona'} • {s.receipt_count} {s.receipt_count === 1 ? 'compra' : 'compras'}
                            </p>
                          </div>
                        </div>

                        <div className="text-right shrink-0">
                          <span className="text-xs font-bold text-slate-900 block">
                            {s.total_spend.toFixed(2)} €
                          </span>
                          <span className="text-[10px] text-slate-400 font-medium">
                            {s.percentage}%
                          </span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-slate-400 py-4 text-center">
                      Sin datos de tiendas
                    </div>
                  )}
                </div>
              </div>

              <div className="pt-2 border-t border-slate-100 text-[11px] text-slate-400 flex items-center justify-between">
                <span>Tienda principal:</span>
                <span className="font-semibold text-slate-700 truncate max-w-[170px]">{habits.top_store_name || 'Mercadona'}</span>
              </div>
            </div>

            {/* Household Basket Composition Card */}
            <div className="bg-white p-5 rounded-3xl border border-slate-200 shadow-sm space-y-3 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                      <Layers className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-900">Perfil del Gasto Familiar</h3>
                      <p className="text-[11px] text-slate-400">Frescos, despensa, básicos y hogar</p>
                    </div>
                  </div>
                </div>

                <div className="space-y-2.5 pt-1">
                  {habits.basket_composition && habits.basket_composition.length > 0 ? (
                    habits.basket_composition.map((group) => (
                      <div key={group.group_name} className="bg-slate-50/70 p-2.5 rounded-2xl border border-slate-100 space-y-1.5">
                        <div className="flex items-center justify-between text-xs">
                          <div className="flex items-center gap-2 min-w-0">
                            <span
                              className="w-2.5 h-2.5 rounded-full shrink-0"
                              style={{ backgroundColor: group.color_hex }}
                            />
                            <span className="font-bold text-slate-800 truncate">{group.group_name}</span>
                          </div>
                          <div className="text-right shrink-0">
                            <span className="font-bold text-slate-900 font-mono">
                              {group.total_spend.toFixed(2)} €
                            </span>
                            <span className="text-[11px] text-slate-400 font-medium ml-1">
                              ({group.percentage}%)
                            </span>
                          </div>
                        </div>

                        {/* Progress bar */}
                        <div className="w-full bg-slate-200/70 h-1.5 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-300"
                            style={{
                              width: `${Math.min(100, Math.max(0, group.percentage))}%`,
                              backgroundColor: group.color_hex,
                            }}
                          />
                        </div>

                        <div className="flex items-center justify-between text-[11px] text-slate-400">
                          <span className="truncate max-w-[200px]">{group.description}</span>
                          <span className="shrink-0">{group.items_count} art.</span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-slate-400 py-4 text-center">
                      Sin datos de composición de cesta
                    </div>
                  )}
                </div>
              </div>

              <div className="pt-2 border-t border-slate-100 text-[11px] text-slate-500 flex items-center justify-between">
                <span>Alimentación fresca:</span>
                <span className="font-bold text-emerald-700">
                  {habits.basket_composition?.find((g) => g.group_name.includes('Frescos'))?.percentage || 0}% de tu presupuesto
                </span>
              </div>
            </div>

            {/* Brand Share Card: Hacendado vs Fabricante */}
            <div className="bg-white p-5 rounded-3xl border border-slate-200 shadow-sm space-y-3 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                      <Tag className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-900">Marcas Hacendado</h3>
                      <p className="text-[11px] text-slate-400">Marca propia vs fabricante</p>
                    </div>
                  </div>
                  {habits.own_brands_percentage !== undefined && habits.own_brands_percentage !== null && (
                    <span className="text-xs font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                      {habits.own_brands_percentage}% Hacendado
                    </span>
                  )}
                </div>

                <div className="space-y-3">
                  {habits.brand_share && habits.brand_share.length > 0 ? (
                    habits.brand_share.map((b) => (
                      <div key={b.brand_type} className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-semibold text-slate-800 truncate">{b.label}</span>
                          <span className="font-mono text-slate-600 shrink-0">
                            {b.total_spend.toFixed(2)} € ({b.percentage}%)
                          </span>
                        </div>
                        <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-300"
                            style={{
                              width: `${Math.min(100, Math.max(0, b.percentage))}%`,
                              backgroundColor: b.color_hex,
                            }}
                          />
                        </div>
                        <div className="text-[10px] text-slate-400 text-right">{b.items_count} artículos</div>
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-slate-400 py-4 text-center">Sin datos de marcas</div>
                  )}
                </div>
              </div>

              <div className="pt-2 border-t border-slate-100 text-[11px] text-slate-500">
                Priorizar marcas propias de Mercadona reduce el coste de tu cesta familiar de forma continuada.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Ticket Detail Modal */}
      {selectedReceipt && (
        <ReceiptDetailModal
          receipt={selectedReceipt}
          onClose={() => setSelectedReceipt(null)}
          onReceiptUpdated={(updated) => {
            setSelectedReceipt(updated);
          }}
        />
      )}
    </div>
  );
};
