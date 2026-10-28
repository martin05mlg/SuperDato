import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Navbar } from './Navbar';
import { Sidebar } from './Sidebar';
import { MobileDrawer, MobileBottomNav } from './MobileNav';

export const AppLayout: React.FC = () => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col w-full max-w-full overflow-x-hidden">
      <Navbar onToggleMobileMenu={() => setIsMobileMenuOpen((prev) => !prev)} />
      
      <div className="flex-1 flex min-w-0 max-w-full overflow-x-hidden">
        <Sidebar />
        <main className="flex-1 min-w-0 p-3 sm:p-5 md:p-6 pb-24 md:pb-8 max-w-7xl mx-auto w-full overflow-x-hidden">
          <Outlet />
        </main>
      </div>

      {/* Mobile Drawer (Menu) */}
      <MobileDrawer isOpen={isMobileMenuOpen} onClose={() => setIsMobileMenuOpen(false)} />

      {/* Mobile Bottom Navigation Bar */}
      <MobileBottomNav onOpenMore={() => setIsMobileMenuOpen(true)} />
    </div>
  );
};


