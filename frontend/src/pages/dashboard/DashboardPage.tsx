import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { receiptsApi } from '../../api/receipts.api';
import { useHousehold } from '../../context/HouseholdContext';
import {
  ShoppingCart,
  TrendingUp,
  Calendar,
  CreditCard,
  ShoppingBag
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
  Cell
} from 'recharts';

export const DashboardPage: React.FC = () => {
  const { activeHousehold } = useHousehold();

  // Queries for real data
  const { data: summary, isLoading: loadingSummary } = useQuery({
    queryKey: ['analytics', 'summary'],
    queryFn: receiptsApi.getAnalyticsSummary,
  });

  const { data: categories = [] } = useQuery({
    queryKey: ['analytics', 'categories'],
    queryFn: receiptsApi.getCategoryDistribution,
  });

  const { data: spendingHistory = [] } = useQuery({
    queryKey: ['analytics', 'history'],
    queryFn: receiptsApi.getSpendingEvolution,
  });

  const { data: receipts = [] } = useQuery({
    queryKey: ['receipts'],
    queryFn: receiptsApi.getAll,
  });

  const recentReceipts = receipts.slice(0, 5);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Dashboard de Gastos</h1>
          <p className="text-sm text-slate-500 mt-1">
            Resumen contable y estadísticas de compra de{' '}
            <span className="font-semibold text-slate-800">
              {activeHousehold?.name || 'tu hogar'}
            </span>
          </p>
        </div>

        {/* Date Filter Indicator */}
        <div className="flex items-center space-x-2 bg-white border border-slate-200 px-3 py-1.5 rounded-xl text-xs font-medium text-slate-600 shadow-sm">
          <Calendar className="w-4 h-4 text-emerald-600" />
          <span>Histórico completo</span>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Spend */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium uppercase tracking-wider">
            <span>Gasto Acumulado</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {loadingSummary ? '...' : `${summary?.total_spend?.toFixed(2) || '0.00'} €`}
          </div>
          <div className="flex items-center text-xs text-slate-500 space-x-1">
            <span className="text-emerald-600 font-semibold flex items-center">
              100% verificado
            </span>
            <span>con tickets de compra</span>
          </div>
        </div>

        {/* Number of Receipts */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium uppercase tracking-wider">
            <span>Tickets Importados</span>
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <ShoppingCart className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {loadingSummary ? '...' : summary?.receipt_count || 0}
          </div>
          <p className="text-xs text-slate-500">Tickets procesados de Mercadona</p>
        </div>

        {/* Average Ticket */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium uppercase tracking-wider">
            <span>Ticket Medio</span>
            <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
              <CreditCard className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {loadingSummary ? '...' : `${summary?.average_ticket?.toFixed(2) || '0.00'} €`}
          </div>
          <p className="text-xs text-slate-500">
            Mediana: {summary?.median_ticket?.toFixed(2) || '0.00'} €
          </p>
        </div>

        {/* Sync Status */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium uppercase tracking-wider">
            <span>Sincronización</span>
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              Activo
            </span>
          </div>
          <div className="text-base font-semibold text-slate-800">
            {summary?.last_sync_at || 'Al día'}
          </div>
          <p className="text-xs text-slate-500">
            Última compra: {summary?.last_purchase_date || 'Sin datos'}
          </p>
        </div>
      </div>

      {/* Main Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Spending History Chart */}
        <div className="lg:col-span-2 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900 mb-1">Evolución de Compras</h2>
            <p className="text-xs text-slate-500 mb-4">Gasto por fecha de compra en euros (€)</p>
          </div>

          <div className="h-64 w-full">
            {spendingHistory.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={spendingHistory}>
                  <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} tickLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} unit="€" />
                  <Tooltip
                    formatter={(val: any) => [`${Number(val).toFixed(2)} €`, 'Total']}
                    contentStyle={{ borderRadius: '12px', border: '1px solid #e2e8f0' }}
                  />
                  <Bar dataKey="total_amount" fill="#007A3D" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-400 text-sm">
                Sin datos de evolución
              </div>
            )}
          </div>
        </div>

        {/* Category Distribution Donut Chart */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900 mb-1">Distribución por Categorías</h2>
            <p className="text-xs text-slate-500 mb-4">Porcentaje de gasto por sección</p>
          </div>

          <div className="h-48 w-full flex items-center justify-center">
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
                    outerRadius={75}
                    paddingAngle={3}
                  >
                    {categories.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color_hex} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(val: any) => [`${Number(val).toFixed(2)} €`, 'Gasto']}
                    contentStyle={{ borderRadius: '12px', border: '1px solid #e2e8f0' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-slate-400 text-sm">Sin datos de categorías</div>
            )}
          </div>

          {/* Category Legend List */}
          <div className="space-y-1.5 mt-2 max-h-36 overflow-y-auto pr-1">
            {categories.slice(0, 4).map((cat) => (
              <div key={cat.category_name} className="flex items-center justify-between text-xs">
                <div className="flex items-center space-x-2">
                  <div
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ backgroundColor: cat.color_hex }}
                  />
                  <span className="text-slate-700 font-medium truncate max-w-[120px]">
                    {cat.category_name}
                  </span>
                </div>
                <span className="font-semibold text-slate-900">
                  {cat.total_spend.toFixed(2)} € ({cat.percentage}%)
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Purchases List */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
        <h2 className="text-base font-bold text-slate-900 mb-4">Compras Recientes</h2>
        <div className="divide-y divide-slate-100">
          {recentReceipts.map((r) => (
            <div key={r.id} className="py-3 flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center text-slate-600">
                  <ShoppingBag className="w-5 h-5 text-emerald-600" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-slate-900">
                    Factura {r.invoice_number}
                  </h4>
                  <p className="text-xs text-slate-500">
                    {r.store_address ? `${r.store_address}, ${r.store_city || ''}` : 'Mercadona'} • {r.lines_count} artículos
                  </p>
                </div>
              </div>

              <div className="text-right">
                <div className="text-base font-extrabold text-slate-900">
                  {r.total_amount.toFixed(2)} €
                </div>
                <span className="text-xs text-slate-400">{r.purchase_date}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
