import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useHousehold } from '../../context/HouseholdContext';
import { ShoppingBag, Home, LogOut, ChevronDown, User as UserIcon, Plus, ShieldAlert, Menu } from 'lucide-react';

interface NavbarProps {
  onToggleMobileMenu?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onToggleMobileMenu }) => {
  const { user, logout } = useAuth();
  const { households, activeHousehold, setActiveHousehold } = useHousehold();

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 w-full">
      <div className="max-w-7xl mx-auto px-2.5 sm:px-6 lg:px-8 h-14 sm:h-16 flex items-center justify-between gap-1.5 sm:gap-4 min-w-0">
        {/* Left: Hamburger (mobile) + Logo and Brand */}
        <div className="flex items-center space-x-1.5 sm:space-x-3 min-w-0 shrink-0">
          {onToggleMobileMenu && (
            <button
              type="button"
              onClick={onToggleMobileMenu}
              className="p-1.5 -ml-1 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg md:hidden transition shrink-0"
              aria-label="Abrir menú de navegación"
            >
              <Menu className="w-5 h-5" />
            </button>
          )}

          <Link to="/" className="flex items-center space-x-2 sm:space-x-3 group min-w-0 shrink-0">
            <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl bg-emerald-600 flex items-center justify-center text-white shadow-xs group-hover:bg-emerald-700 transition shrink-0">
              <ShoppingBag className="w-4 h-4 sm:w-6 sm:h-6" />
            </div>
            <div className="min-w-0 flex items-center">
              <span className="text-base sm:text-xl font-extrabold text-slate-900 tracking-tight shrink-0">SuperDato</span>
              <span className="hidden md:inline-block ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 shrink-0">
                Mercadona
              </span>
            </div>
          </Link>
        </div>

        {/* Right: Household Selector & User Controls */}
        <div className="flex items-center space-x-1 sm:space-x-2 md:space-x-3 shrink-0 min-w-0">
          {/* Household Selector */}
          {households.length > 0 ? (
            <div className="relative inline-block text-left shrink-0">
              <div className="flex items-center space-x-1 sm:space-x-1.5 bg-slate-50 border border-slate-200 rounded-xl px-2 sm:px-3 py-1 sm:py-1.5 text-xs sm:text-sm text-slate-700 hover:bg-slate-100 transition cursor-pointer max-w-[105px] xs:max-w-[135px] sm:max-w-[220px]">
                <Home className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                <select
                  value={activeHousehold?.id || ''}
                  onChange={(e) => {
                    const selected = households.find((h) => h.id === e.target.value);
                    if (selected) setActiveHousehold(selected);
                  }}
                  aria-label="Seleccionar hogar activo"
                  className="bg-transparent border-none text-slate-800 font-semibold focus:ring-0 focus:outline-none cursor-pointer pr-2 sm:pr-3 truncate text-[11px] sm:text-sm max-w-[65px] xs:max-w-[95px] sm:max-w-none"
                >
                  {households.map((h) => (
                    <option key={h.id} value={h.id}>
                      {h.name}
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-3 h-3 text-slate-400 pointer-events-none shrink-0" />
              </div>
            </div>
          ) : (
            <Link
              to="/settings"
              className="inline-flex items-center space-x-1 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg px-2 sm:px-2.5 py-1 text-xs font-semibold hover:bg-emerald-100 transition shrink-0"
            >
              <Plus className="w-3.5 h-3.5" />
              <span className="hidden xs:inline">Crear Hogar</span>
            </Link>
          )}

          {/* Superadmin Panel Link */}
          {user?.is_superuser && (
            <Link
              to="/admin"
              className="inline-flex items-center space-x-1 p-1.5 sm:px-2.5 sm:py-1.5 rounded-lg sm:rounded-xl bg-purple-50 text-purple-700 hover:bg-purple-100 border border-purple-200 text-xs font-bold transition shadow-xs shrink-0"
              title="Panel de Superadministración"
            >
              <ShieldAlert className="w-3.5 h-3.5 text-purple-600" />
              <span className="hidden md:inline">Admin</span>
            </Link>
          )}

          {/* User Profile and Logout */}
          <div className="flex items-center space-x-1 sm:space-x-2 border-l border-slate-200 pl-1.5 sm:pl-3 shrink-0">
            <div className="hidden md:flex items-center space-x-2">
              <div className="w-8 h-8 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-600">
                <UserIcon className="w-4 h-4" />
              </div>
              <span className="text-xs sm:text-sm font-semibold text-slate-700 hidden lg:inline max-w-[120px] truncate">
                {user?.full_name || user?.email}
              </span>
            </div>

            <button
              onClick={logout}
              title="Cerrar sesión"
              aria-label="Cerrar sesión"
              className="p-1.5 sm:p-2 text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition shrink-0"
            >
              <LogOut className="w-4 h-4 sm:w-5 sm:h-5" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};


