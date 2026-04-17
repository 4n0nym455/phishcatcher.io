/**
 * Layout
 *
 * Modernized app shell — sidebar + top header.
 * Fully CSS-variable driven: works in both light and dark mode.
 */

import { useState, useEffect, useRef } from 'react';
import { Link, useLocation, useNavigate, Outlet } from 'react-router-dom';
import {
  Menu, X, Home, Upload, FileText, Calendar, Settings,
  LogOut, User, ChevronDown, Bell, Search, Filter,
  Shield, AlertTriangle, CheckCircle, Clock, TrendingUp,
  Users, BarChart3, Lock, Eye, EyeOff, Loader2,
  Database, Mail, Smartphone, Globe, Cpu, HardDrive, FileBarChart, ShieldAlert
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { ThemeToggle }   from './ThemeToggle';
import { toast }         from 'sonner';

function getAvatarUrlWithTimestamp(avatarUrl, avatarUpdatedAt) {
  if (!avatarUrl) return null;
  if (!avatarUpdatedAt) return avatarUrl;
  
  // Parse ISO timestamp and convert to Unix timestamp
  try {
    const date = new Date(avatarUpdatedAt);
    if (isNaN(date.getTime())) return avatarUrl;
    const timestamp = Math.floor(date.getTime() / 1000);
    return `${avatarUrl}?t=${timestamp}`;
  } catch {
    return avatarUrl;
  }
}

const USER_NAV = [
  { path: '/dashboard',      label: 'Dashboard',       icon: Home },
  { path: '/upload',         label: 'Email Upload',     icon: Upload },
  { path: '/analysis',       label: 'Analysis', icon: FileText },
  { path: '/reports',        label: 'Reports',          icon: FileBarChart },
  { path: '/settings',       label: 'Settings',         icon: Settings },
];
const ADMIN_NAV = [
  { path: '/admin', label: 'Admin Panel', icon: ShieldAlert },
];

export default function Layout() {
  const { user, logout, refreshUser, isAdmin } = useAuth();
  const location  = useLocation();
  const navigate  = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [profile, setProfile] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [notifications, setNotifications] = useState([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const searchRef = useRef(null);

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
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ── Sidebar ── */}
      <aside
        className={`
          fixed lg:static inset-y-0 left-0 z-50 w-64 flex flex-col
          transition-transform duration-300 ease-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
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
            onClick={() => setSidebarOpen(false)}
          >
            <img
              src="/phishcatcher-logo.png"
              alt="PhishCatcher"
              className="w-7 h-7 shrink-0"
            />
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
              onClick={() => setSidebarOpen(false)}
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
            <div className="w-10 h-10 rounded-full overflow-hidden shrink-0">
              {user?.avatar_url ? (
                <img src={getAvatarUrlWithTimestamp(user.avatar_url, user.avatar_updated_at)} alt="Profile avatar" className="w-full h-full object-cover" />
              ) : (
                <div
                  className="w-full h-full flex items-center justify-center text-xs font-700"
                  style={{ background: 'var(--brand-dim)', color: 'var(--brand)' }}
                >
                  {(user?.full_name || user?.email || 'U')[0].toUpperCase()}
                </div>
              )}
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
            onClick={() => setSidebarOpen(v => !v)}
          >
            {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
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
                <div className="w-8 h-8 rounded-full overflow-hidden flex items-center justify-center text-xs font-700">
                {user?.avatar_url ? (
                  <img src={getAvatarUrlWithTimestamp(user.avatar_url, user.avatar_updated_at)} alt="Profile avatar" className="w-full h-full object-cover" />
                ) : (
                  <div style={{ background: 'var(--brand-dim)', color: 'var(--brand)' }}>
                    {(user?.full_name || user?.email || 'U')[0].toUpperCase()}
                  </div>
                )}
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
          <Outlet />
        </main>
      </div>
    </div>
  );
}