import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useQuery } from '@tanstack/react-query';
import { receiptsApi } from '../../api/receipts.api';
import {
  LayoutDashboard,
  Receipt,
  Package,
  ClipboardList,
  ArrowDownToLine,
  Settings,
  Sparkles,
  ShieldAlert,
} from 'lucide-react';

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/receipts', label: 'Tickets', icon: Receipt },
  { to: '/products', label: 'Productos y Precios', icon: Package },
  { to: '/shopping-list', label: 'Lista de la Compra', icon: ClipboardList },
  { to: '/imports', label: 'Importaciones y Gmail', icon: ArrowDownToLine },
  { to: '/settings', label: 'Ajustes del Hogar', icon: Settings },
];

export const Sidebar: React.FC = () => {
  const { user } = useAuth();

  const { data: pendingData } = useQuery({
    queryKey: ['pending-receipts-count'],
    queryFn: receiptsApi.getPendingCount,
    refetchInterval: 15000,
  });
  const pendingCount = pendingData?.count || 0;

  return (
    <aside className="w-64 bg-white border-r border-slate-200 min-h-[calc(100vh-4rem)] p-4 hidden md:flex flex-col justify-between">
      <nav className="space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isReceipts = item.to === '/receipts';

          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center justify-between px-3 py-2.5 rounded-xl font-medium text-sm transition-colors ${
                  isActive
                    ? 'bg-emerald-50 text-emerald-700 font-semibold'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`
              }
            >
              <div className="flex items-center space-x-3">
                <Icon className="w-5 h-5 flex-shrink-0" />
                <span>{item.label}</span>
              </div>
              {isReceipts && pendingCount > 0 && (
                <span className="text-[10px] font-bold bg-amber-500 text-white px-2 py-0.5 rounded-full shadow-xs">
                  {pendingCount}
                </span>
              )}
            </NavLink>
          );
        })}


        {user?.is_superuser && (
          <div className="pt-3 mt-3 border-t border-slate-100">
            <div className="px-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
              Administración
            </div>
            <NavLink
              to="/admin"
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3 py-2.5 rounded-xl font-medium text-sm transition-colors ${
                  isActive
                    ? 'bg-purple-50 text-purple-700 font-bold'
                    : 'text-slate-600 hover:bg-purple-50/50 hover:text-purple-900'
                }`
              }
            >
              <ShieldAlert className="w-5 h-5 text-purple-600 flex-shrink-0" />
              <span>Panel Superadmin</span>
            </NavLink>
          </div>
        )}
      </nav>

      {/* Footer Info Box */}
      <div className="bg-emerald-900/5 rounded-2xl p-4 border border-emerald-900/10 text-xs text-slate-600 space-y-2">
        <div className="flex items-center space-x-1.5 font-semibold text-emerald-800">
          <Sparkles className="w-4 h-4 text-emerald-600" />
          <span>SuperDato MVP</span>
        </div>
        <p className="text-slate-500 text-[11px] leading-relaxed">
          Sincronización digital y análisis contable de tickets de Mercadona.
        </p>
      </div>
    </aside>
  );
};

