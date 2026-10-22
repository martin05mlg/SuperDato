import React, { useMemo, useState } from 'react';
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

type DatePreset = 'ALL' | '30D' | 'THIS_MONTH' | 'LAST_MONTH' | 'THIS_YEAR';

export const DashboardPage: React.FC = () => {
  const { activeHousehold } = useHousehold();
  const [preset, setPreset] = useState<DatePreset>('ALL');
  const [selectedReceipt, setSelectedReceipt] = useState<Receipt | null>(null);

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
      case 'ALL':
      default:
        return { start_date: undefined, end_date: undefined };
    }
  }, [preset]);

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

  const { data: topProducts = [] } = useQuery({
    queryKey: ['analytics', 'topProducts', queryParams],
    queryFn: () => receiptsApi.getTopProducts({ ...queryParams, limit: 5 }),
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

  return (
    <div className="space-y-6">
      {/* Page Header with Date Filter Pills */}
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

        {/* Date Filter Pills */}
        <div className="flex items-center bg-slate-100 p-1 rounded-2xl text-xs font-semibold text-slate-600 space-x-1 border border-slate-200">
          <button
            onClick={() => setPreset('ALL')}
            className={`px-3 py-1.5 rounded-xl transition ${
              preset === 'ALL'
                ? 'bg-white text-emerald-800 shadow-sm font-bold'
                : 'hover:text-slate-900 text-slate-600'
            }`}
          >
            Histórico
          </button>
          <button
            onClick={() => setPreset('30D')}
            className={`px-3 py-1.5 rounded-xl transition ${
              preset === '30D'
                ? 'bg-white text-emerald-800 shadow-sm font-bold'
                : 'hover:text-slate-900 text-slate-600'
            }`}
          >
            30 Días
          </button>
          <button
            onClick={() => setPreset('THIS_MONTH')}
            className={`px-3 py-1.5 rounded-xl transition ${
              preset === 'THIS_MONTH'
                ? 'bg-white text-emerald-800 shadow-sm font-bold'
                : 'hover:text-slate-900 text-slate-600'
            }`}
          >
            Este Mes
          </button>
          <button
            onClick={() => setPreset('LAST_MONTH')}
            className={`px-3 py-1.5 rounded-xl transition ${
              preset === 'LAST_MONTH'
                ? 'bg-white text-emerald-800 shadow-sm font-bold'
                : 'hover:text-slate-900 text-slate-600'
            }`}
          >
            Mes Ant.
          </button>
          <button
            onClick={() => setPreset('THIS_YEAR')}
            className={`px-3 py-1.5 rounded-xl transition ${
              preset === 'THIS_YEAR'
                ? 'bg-white text-emerald-800 shadow-sm font-bold'
                : 'hover:text-slate-900 text-slate-600'
            }`}
          >
            Este Año
          </button>
        </div>
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

          <div className="flex items-center text-xs space-x-1.5 pt-1">
            {summary && summary.previous_spend > 0 ? (
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
            ) : (
              <span className="text-slate-400 text-xs">Sin periodo previo</span>
            )}
            <span className="text-slate-400 text-[11px] truncate">
              {summary?.previous_spend ? `vs ${summary.previous_spend.toFixed(2)} € ant.` : '100% verificado'}
            </span>
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

        {/* Sync Status & Last Purchase */}
        <div className="bg-white p-5 rounded-3xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase tracking-wider">
            <span>Última Compra</span>
            <div className="w-8 h-8 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
              <Calendar className="w-4 h-4" />
            </div>
          </div>
          <div className="text-xl font-bold text-slate-900 tracking-tight">
            {summary?.last_purchase_date || 'Sin compras'}
          </div>
          <p className="text-xs text-slate-500 flex items-center gap-1 truncate">
            <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0"></span>
            <span>{summary?.last_sync_at || 'Al día'}</span>
          </p>
        </div>
      </div>

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
                  <Tooltip
                    formatter={(val: any) => [`${Number(val).toFixed(2)} €`, 'Gasto']}
                    contentStyle={{ borderRadius: '14px', border: '1px solid #e2e8f0' }}
                  />
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
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2">
                <Award className="w-5 h-5 text-amber-500" />
                <h2 className="text-base font-bold text-slate-900">Top Productos Más Comprados</h2>
              </div>
              <span className="text-xs text-slate-400">Por volumen de gasto</span>
            </div>

            <div className="divide-y divide-slate-100">
              {topProducts.length > 0 ? (
                topProducts.map((p, idx) => (
                  <div key={p.product_id || p.product_name} className="py-3 flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-7 h-7 rounded-lg bg-slate-100 text-slate-600 font-bold text-xs flex items-center justify-center">
                        #{idx + 1}
                      </div>
                      <div>
                        <h4 className="text-xs font-semibold text-slate-900 truncate max-w-[180px] sm:max-w-[240px]">
                          {p.product_name}
                        </h4>
                        <div className="flex items-center space-x-2 text-[11px] text-slate-400 mt-0.5">
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
