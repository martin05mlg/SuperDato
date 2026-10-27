import React, { useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useHousehold } from '../../context/HouseholdContext';
import { useQuery } from '@tanstack/react-query';
import { receiptsApi } from '../../api/receipts.api';
import {
  LayoutDashboard,
  Receipt,
  Package,
  ClipboardList,
  ArrowDownToLine,
  Settings,
  ShieldAlert,
  Sparkles,
  X,
  Home,
  LogOut,
  User as UserIcon,
  Menu,
  ChevronDown,
  ShoppingBag,
} from 'lucide-react';

interface MobileDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export const MobileDrawer: React.FC<MobileDrawerProps> = ({ isOpen, onClose }) => {
  const { user, logout } = useAuth();
  const { households, activeHousehold, setActiveHousehold } = useHousehold();
  const location = useLocation();

  // Close drawer on route change
  useEffect(() => {
    onClose();
  }, [location.pathname]);

  // Query pending unassigned tickets count
  const { data: pendingData } = useQuery({
    queryKey: ['pending-receipts-count'],
    queryFn: receiptsApi.getPendingCount,
    refetchInterval: 15000,
  });
  const pendingCount = pendingData?.count || 0;

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 md:hidden animate-in fade-in duration-200">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer Panel */}
      <div className="fixed inset-y-0 left-0 max-w-[280px] w-full bg-white shadow-2xl flex flex-col justify-between p-4 z-50 overflow-y-auto transform transition-transform ease-out">
        <div>
          {/* Drawer Header */}
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <div className="flex items-center space-x-2.5">
              <div className="w-9 h-9 rounded-xl bg-emerald-600 flex items-center justify-center text-white shadow-sm">
                <ShoppingBag className="w-5 h-5" />
              </div>
              <div>
                <span className="font-bold text-slate-900 text-lg tracking-tight">SuperDato</span>
                <span className="ml-1.5 text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                  Mercadona
                </span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition"
              aria-label="Cerrar menú"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Active Household Switcher in Drawer */}
          {households.length > 0 && (
            <div className="my-3.5 p-2.5 bg-slate-50 border border-slate-200 rounded-xl">
              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1 flex items-center justify-between">
                <span>Hogar Activo</span>
                <Home className="w-3.5 h-3.5 text-emerald-600" />
              </div>
              <div className="relative">
                <select
                  value={activeHousehold?.id || ''}
                  onChange={(e) => {
                    const selected = households.find((h) => h.id === e.target.value);
                    if (selected) setActiveHousehold(selected);
                  }}
                  className="w-full bg-white border border-slate-200 text-slate-800 text-xs font-semibold rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-emerald-500 cursor-pointer pr-6"
                >
                  {households.map((h) => (
                    <option key={h.id} value={h.id}>
                      {h.name} ({h.role})
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2 top-2.5 pointer-events-none" />
              </div>
            </div>
          )}

          {/* Navigation Links */}
          <nav className="space-y-1 mt-2">
            <NavLink
              to="/"
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3 py-2.5 rounded-xl font-medium text-sm transition-colors ${
                  isActive
                    ? 'bg-emerald-50 text-emerald-700 font-semibold'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`
              }
            >
              <LayoutDashboard className="w-5 h-5 flex-shrink-0" />
              <span>Dashboard</span>
            </NavLink>

            <NavLink
              to="/receipts"
              className={({ isActive }) =>
                `flex items-center justify-between px-3 py-2.5 rounded-xl font-medium text-sm transition-colors ${
                  isActive
                    ? 'bg-emerald-50 text-emerald-700 font-semibold'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`
              }
            >
              <div className="flex items-center space-x-3">
                <Receipt className="w-5 h-5 flex-shrink-0" />
                <span>Tickets</span>
              </div>
              {pendingCount > 0 && (
                <span className="text-[10px] font-bold bg-amber-500 text-white px-2 py-0.5 rounded-full shadow-xs">
                  {pendingCount}
                </span>
              )}
            </NavLink>

            <NavLink
              to="/products"
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3 py-2.5 rounded-xl font-medium text-sm transition-colors ${
                  isActive
                    ? 'bg-emerald-50 text-emerald-700 font-semibold'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`
              }
            >
              <Package className="w-5 h-5 flex-shrink-0" />
              <span>Productos y Precios</span>
            </NavLink>

            <NavLink
              to="/shopping-list"
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3 py-2.5 rounded-xl font-medium text-sm transition-colors ${
                  isActive
                    ? 'bg-emerald-50 text-emerald-700 font-semibold'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`
              }
            >
              <ClipboardList className="w-5 h-5 flex-shrink-0" />
              <span>Lista de la Compra</span>
            </NavLink>

            <NavLink
              to="/imports"
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3 py-2.5 rounded-xl font-medium text-sm transition-colors ${
                  isActive
                    ? 'bg-emerald-50 text-emerald-700 font-semibold'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`
              }
            >
              <ArrowDownToLine className="w-5 h-5 flex-shrink-0" />
              <span>Importaciones y Gmail</span>
            </NavLink>

            <NavLink
              to="/settings"
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3 py-2.5 rounded-xl font-medium text-sm transition-colors ${
                  isActive
                    ? 'bg-emerald-50 text-emerald-700 font-semibold'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`
              }
            >
              <Settings className="w-5 h-5 flex-shrink-0" />
              <span>Ajustes del Hogar</span>
            </NavLink>

            {user?.is_superuser && (
              <div className="pt-2 mt-2 border-t border-slate-100">
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
        </div>

        {/* Drawer Footer: User Profile & Logout */}
        <div className="pt-4 border-t border-slate-100 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2.5 min-w-0">
              <div className="w-9 h-9 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-600 shrink-0">
                <UserIcon className="w-4 h-4" />
              </div>
              <div className="min-w-0">
                <div className="text-xs font-bold text-slate-800 truncate">
                  {user?.full_name || 'Usuario'}
                </div>
                <div className="text-[11px] text-slate-400 truncate">{user?.email}</div>
              </div>
            </div>

            <button
              onClick={logout}
              title="Cerrar sesión"
              className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>

          <div className="bg-emerald-900/5 rounded-xl p-2.5 border border-emerald-900/10 text-[11px] text-slate-500 space-y-1">
            <div className="flex items-center space-x-1.5 font-semibold text-emerald-800">
              <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
              <span>SuperDato Mercadona</span>
            </div>
            <p className="text-[10px] text-slate-500 leading-tight">
              Sincronización digital y analítica inteligente de tickets.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

interface MobileBottomNavProps {
  onOpenMore: () => void;
}

export const MobileBottomNav: React.FC<MobileBottomNavProps> = ({ onOpenMore }) => {
  const { data: pendingData } = useQuery({
    queryKey: ['pending-receipts-count'],
    queryFn: receiptsApi.getPendingCount,
    refetchInterval: 15000,
  });
  const pendingCount = pendingData?.count || 0;

  return (
    <nav
      aria-label="Navegación móvil"
      className="fixed bottom-0 inset-x-0 z-40 bg-white/95 backdrop-blur-md border-t border-slate-200 py-1.5 px-3 md:hidden flex items-center justify-around shadow-lg"
    >
      <NavLink
        to="/"
        className={({ isActive }) =>
          `flex flex-col items-center justify-center py-1 px-2 rounded-xl transition ${
            isActive ? 'text-emerald-700 font-bold' : 'text-slate-500 hover:text-slate-800'
          }`
        }
      >
        <LayoutDashboard className="w-5 h-5 mb-0.5" />
        <span className="text-[10px]">Dashboard</span>
      </NavLink>

      <NavLink
        to="/receipts"
        className={({ isActive }) =>
          `flex flex-col items-center justify-center py-1 px-2 rounded-xl transition relative ${
            isActive ? 'text-emerald-700 font-bold' : 'text-slate-500 hover:text-slate-800'
          }`
        }
      >
        <div className="relative">
          <Receipt className="w-5 h-5 mb-0.5" />
          {pendingCount > 0 && (
            <span className="absolute -top-1 -right-2 bg-amber-500 text-white text-[9px] font-extrabold w-4 h-4 rounded-full flex items-center justify-center shadow-xs">
              {pendingCount > 9 ? '9+' : pendingCount}
            </span>
          )}
        </div>
        <span className="text-[10px]">Tickets</span>
      </NavLink>

      <NavLink
        to="/products"
        className={({ isActive }) =>
          `flex flex-col items-center justify-center py-1 px-2 rounded-xl transition ${
            isActive ? 'text-emerald-700 font-bold' : 'text-slate-500 hover:text-slate-800'
          }`
        }
      >
        <Package className="w-5 h-5 mb-0.5" />
        <span className="text-[10px]">Productos</span>
      </NavLink>

      <NavLink
        to="/shopping-list"
        className={({ isActive }) =>
          `flex flex-col items-center justify-center py-1 px-2 rounded-xl transition ${
            isActive ? 'text-emerald-700 font-bold' : 'text-slate-500 hover:text-slate-800'
          }`
        }
      >
        <ClipboardList className="w-5 h-5 mb-0.5" />
        <span className="text-[10px]">Lista</span>
      </NavLink>

      <button
        type="button"
        onClick={onOpenMore}
        className="flex flex-col items-center justify-center py-1 px-2 rounded-xl text-slate-500 hover:text-slate-800 transition"
      >
        <Menu className="w-5 h-5 mb-0.5" />
        <span className="text-[10px]">Más</span>
      </button>
    </nav>
  );
};
