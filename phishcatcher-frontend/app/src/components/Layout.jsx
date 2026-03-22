/**
 * Layout
 *
 * Modernized app shell — sidebar + top header.
 * Fully CSS-variable driven: works in both light and dark mode.
 */

import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import {
  Menu, X, LayoutDashboard, Upload, FileText, FileBarChart,
  Settings, User, ChevronDown, LogOut, ShieldAlert, Shield,
} from 'lucide-react';
import { useAuth }       from '@/context/AuthContext';
import { ThemeToggle }   from './ThemeToggle';
import { toast }         from 'sonner';

const USER_NAV = [
  { path: '/dashboard',      label: 'Dashboard',       icon: LayoutDashboard },
  { path: '/upload',         label: 'Email Upload',     icon: Upload },
  { path: '/analysis',       label: 'Analysis History', icon: FileText },
  { path: '/weekly-reports', label: 'Weekly Reports',   icon: FileBarChart },
  { path: '/settings',       label: 'Settings',         icon: Settings },
];
const ADMIN_NAV = [
  { path: '/admin', label: 'Admin Panel', icon: ShieldAlert },
];

export default function Layout({ children }) {
  const { user, isAdmin, logout } = useAuth();
  const location  = useLocation();
  const navigate  = useNavigate();
  const [sidebar, setSidebar] = useState(false);
  const [profile, setProfile] = useState(false);

  const navItems = [...USER_NAV, ...(isAdmin ? ADMIN_NAV : [])];

  const handleLogout = async () => {
    setProfile(false);
    await logout();
    toast.success('Logged out successfully');
    navigate('/login', { replace: true });
  };

  const isActive = (path) =>
    location.pathname === path || location.pathname.startsWith(path + '/');

  return (
    <div className="flex min-h-screen" style={{ background: 'var(--bg-base)', color: 'var(--text-primary)' }}>

      {/* Mobile overlay */}
      {sidebar && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setSidebar(false)}
        />
      )}

      {/* ── Sidebar ── */}
      <aside
        className={`
          fixed lg:static inset-y-0 left-0 z-50 w-64 flex flex-col
          transition-transform duration-300 ease-out
          ${sidebar ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
        style={{
          background: 'var(--sidebar-bg)',
          borderRight: '1px solid var(--sidebar-border)',
        }}
      >
        {/* Logo */}
        <div
          className="h-16 flex items-center px-5 shrink-0"
          style={{ borderBottom: '1px solid var(--sidebar-border)' }}
        >
          <Link
            to="/dashboard"
            className="flex items-center gap-3"
            onClick={() => setSidebar(false)}
          >
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
              style={{ background: 'var(--brand-dim)', color: 'var(--brand)' }}
            >
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <p className="font-heading font-700 text-sm leading-tight" style={{ color: 'var(--text-primary)' }}>
                PhishCatcher
              </p>
              {isAdmin && (
                <p className="text-[10px] font-600 uppercase tracking-widest" style={{ color: 'var(--brand)' }}>
                  Admin
                </p>
              )}
            </div>
          </Link>
        </div>

        {/* Nav items */}
        <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
          {navItems.map(({ path, label, icon: Icon }) => (
            <Link
              key={path}
              to={path}
              onClick={() => setSidebar(false)}
              className={`nav-item theme-transition ${isActive(path) ? 'active' : ''}`}
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span>{label}</span>
            </Link>
          ))}
        </nav>

        {/* User mini info at bottom */}
        <div
          className="p-4 shrink-0"
          style={{ borderTop: '1px solid var(--sidebar-border)' }}
        >
          <div className="flex items-center gap-3">
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
              style={{ background: 'var(--brand-dim)', color: 'var(--brand)' }}
            >
              {(user?.full_name || user?.email || 'U')[0].toUpperCase()}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-600 truncate" style={{ color: 'var(--text-primary)' }}>
                {user?.full_name || 'User'}
              </p>
              <p className="text-[11px] truncate" style={{ color: 'var(--text-muted)' }}>
                {user?.email}
              </p>
            </div>
          </div>
        </div>
      </aside>

      {/* ── Main area ── */}
      <div className="flex-1 flex flex-col min-w-0">

        {/* Header */}
        <header
          className="h-16 flex items-center justify-between px-4 lg:px-6 shrink-0 sticky top-0 z-30"
          style={{
            background: 'var(--bg-overlay)',
            backdropFilter: 'blur(12px)',
            borderBottom: '1px solid var(--border)',
          }}
        >
          {/* Hamburger (mobile) */}
          <button
            className="lg:hidden p-2 rounded-lg transition-colors"
            style={{ color: 'var(--text-muted)' }}
            onClick={() => setSidebar(v => !v)}
          >
            {sidebar ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>

          {/* Page breadcrumb (desktop) */}
          <div className="hidden lg:block">
            <p className="text-xs font-600 uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              {navItems.find(n => isActive(n.path))?.label ?? 'PhishCatcher'}
            </p>
          </div>

          {/* Right side */}
          <div className="flex items-center gap-2 ml-auto">
            <ThemeToggle />

            {/* Profile dropdown */}
            <div className="relative">
              <button
                onClick={() => setProfile(v => !v)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-xl transition-all"
                style={{
                  background: profile ? 'var(--brand-dim)' : 'transparent',
                  color: 'var(--text-primary)',
                }}
              >
                <div
                  className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold"
                  style={{ background: 'var(--brand-dim)', color: 'var(--brand)' }}
                >
                  {(user?.full_name || user?.email || 'U')[0].toUpperCase()}
                </div>
                <span className="hidden lg:block text-sm font-500">
                  {user?.full_name?.split(' ')[0] || user?.email?.split('@')[0] || 'User'}
                </span>
                <ChevronDown
                  className="w-3.5 h-3.5 hidden lg:block transition-transform duration-200"
                  style={{
                    color: 'var(--text-muted)',
                    transform: profile ? 'rotate(180deg)' : 'rotate(0deg)',
                  }}
                />
              </button>

              {profile && (
                <>
                  <div className="fixed inset-0 z-[98]" onClick={() => setProfile(false)} />
                  <div
                    className="absolute right-0 top-[calc(100%+8px)] w-52 rounded-2xl py-1.5 z-[99]"
                    style={{
                      background: 'var(--bg-surface)',
                      border: '1px solid var(--border)',
                      boxShadow: 'var(--shadow-lg)',
                    }}
                  >
                    {/* User info */}
                    <div
                      className="px-4 py-3 mb-1"
                      style={{ borderBottom: '1px solid var(--border)' }}
                    >
                      <p className="text-sm font-600" style={{ color: 'var(--text-primary)' }}>
                        {user?.full_name || 'User'}
                      </p>
                      <p className="text-xs mt-0.5 truncate" style={{ color: 'var(--text-muted)' }}>
                        {user?.email}
                      </p>
                      {isAdmin && (
                        <span className="badge badge-brand mt-1.5">Admin</span>
                      )}
                    </div>

                    <Link
                      to="/settings"
                      onClick={() => setProfile(false)}
                      className="flex items-center gap-3 px-4 py-2.5 text-sm transition-colors"
                      style={{ color: 'var(--text-secondary)' }}
                      onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-elevated)'}
                      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                    >
                      <Settings className="w-4 h-4" />
                      Settings
                    </Link>

                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors"
                      style={{ color: 'var(--danger)' }}
                      onMouseEnter={e => e.currentTarget.style.background = 'var(--danger-dim)'}
                      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                    >
                      <LogOut className="w-4 h-4" />
                      Log out
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto p-4 lg:p-8 animate-fade-in">
          {children}
        </main>
      </div>
    </div>
  );
}