import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { useHousehold } from '../../context/HouseholdContext';
import { ShoppingBag, Home, LogOut, ChevronDown, User as UserIcon } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const { households, activeHousehold, setActiveHousehold } = useHousehold();

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Logo and Brand */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-600 flex items-center justify-center text-white shadow-sm">
            <ShoppingBag className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xl font-bold text-slate-900 tracking-tight">SuperDato</span>
            <span className="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
              Mercadona
            </span>
          </div>
        </div>

        {/* Household Selector & User Controls */}
        <div className="flex items-center space-x-4">
          {/* Household Selector */}
          {households.length > 0 && (
            <div className="relative inline-block text-left">
              <div className="flex items-center space-x-2 bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100 transition cursor-pointer">
                <Home className="w-4 h-4 text-emerald-600" />
                <select
                  value={activeHousehold?.id || ''}
                  onChange={(e) => {
                    const selected = households.find((h) => h.id === e.target.value);
                    if (selected) setActiveHousehold(selected);
                  }}
                  aria-label="Seleccionar hogar activo"
                  className="bg-transparent border-none text-slate-800 font-medium focus:ring-0 focus:outline-none cursor-pointer pr-4"
                >
                  {households.map((h) => (
                    <option key={h.id} value={h.id}>
                      {h.name} ({h.role})
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-4 h-4 text-slate-400 pointer-events-none" />
              </div>
            </div>
          )}

          {/* User Profile and Logout */}
          <div className="flex items-center space-x-3 border-l border-slate-200 pl-4">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-600">
                <UserIcon className="w-4 h-4" />
              </div>
              <span className="text-sm font-medium text-slate-700 hidden sm:inline">
                {user?.full_name || user?.email}
              </span>
            </div>

            <button
              onClick={logout}
              title="Cerrar sesión"
              className="p-2 text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};

