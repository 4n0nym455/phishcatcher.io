import { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import {
  Menu,
  X,
  Home,
  Shield,
  FileBarChart,
  Users,
  Settings,
  Bell,
  User,
  ChevronDown,
  LogOut,
  ShieldAlert,
  CheckCircle,
  AlertTriangle,
  Info,
  BarChart3,
  LayoutDashboard,
  Upload,
  FileText,
} from "lucide-react";
import { useNotifications } from './NotificationProvider';
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from './ThemeToggle';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator
} from "@/components/ui/dropdown-menu";
import { toast } from "sonner";
import { authApi } from "@/lib/api";
import { createSettingsUrl, createAdminUrl } from '@/utils/semanticUrls';

const userNavItems = [
  { path: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { path: "/upload", label: "Email Upload", icon: Upload },
  { path: "/analysis", label: "Analysis History", icon: FileText },
  { path: "/weekly-reports", label: "Weekly Reports", icon: FileBarChart },
  { path: createSettingsUrl(), label: "Settings", icon: Settings },
];

const adminNavItems = [
  { path: createAdminUrl(), label: "Admin Panel", icon: ShieldAlert },
];

export default function Layout({ children, onLogout, userRole = "user", userData = {} }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const { isSupported, isSubscribed } = useNotifications();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const isAdmin = userRole === "admin";
  const navItems = [...userNavItems, ...(isAdmin ? adminNavItems : [])];

  // Use real user data or fallback to defaults
  const userName = userData.full_name || userData.email?.split('@')[0] || 'User';
  const userEmail = userData.email || 'user@example.com';

  const handleLogout = async () => {
    try {
      await authApi.logout();
      onLogout();
      navigate("/login");
      toast.success("Logged out successfully");
    } catch (error) {
      // Even if logout API fails, clear local tokens and redirect
      onLogout();
      navigate("/login");
      toast.error("Logout completed with warnings");
    }
  };

  return (
    <div className="min-h-screen bg-primary-60 flex">
      {/* Sidebar - Mobile overlay */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-50 w-64 sm:w-72 bg-secondary-30/95 backdrop-blur-xl border-r border-slate-700/30 transition-transform duration-300 ${
          isSidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        {/* Logo */}
        <div className="h-16 flex items-center px-4 sm:px-6 border-b border-slate-700/30">
          <Link to="/dashboard" className="flex items-center gap-2 sm:gap-3">
            <div className="w-10 h-10 sm:w-14 sm:h-14 rounded-xl bg-primary-60 flex items-center justify-center shadow-glow flex-shrink-0 overflow-hidden">
              <img
                src="/phishcatcher.png"
                alt="PhishCatcher Logo"
                className="w-8 h-8 sm:w-12 sm:h-12 object-contain"
              />
            </div>
            <div className="hidden sm:block">
              <span className="text-lg font-heading font-bold text-white">
                PhishCatcher
              </span>
              {isAdmin && (
                <span className="block text-[10px] text-violet-400 uppercase tracking-wider">
                  Admin
                </span>
              )}
            </div>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="p-2 sm:p-4 space-y-1">
          {navItems.map((item) => {
            const isActive =
              location.pathname === item.path ||
              location.pathname.startsWith(item.path + "/");
            const Icon = item.icon;

            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-3 sm:px-4 py-2.5 sm:py-3 rounded-xl transition-all ${
                  isActive
                    ? "bg-violet-500/15 text-violet-400 border border-violet-500/25 shadow-lg"
                    : "text-muted-foreground hover:bg-violet-500/10 hover:text-white"
                }`}
                onClick={() => setIsSidebarOpen(false)}
              >
                <Icon className="w-4 h-4 sm:w-5 sm:h-5 flex-shrink-0" />
                <span className="font-medium text-sm sm:text-base">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Bottom Section */}
        <div className="absolute bottom-0 left-0 right-0 p-2 sm:p-4 border-t border-slate-700/30 bg-gradient-to-t from-secondary-30/50 to-transparent">
          <Link
            to="/settings"
            className={`flex items-center gap-3 px-3 sm:px-4 py-2.5 sm:py-3 rounded-xl text-muted-foreground hover:bg-violet-500/10 hover:text-white transition-all ${
              location.pathname === "/settings" &&
              "bg-violet-500/15 text-violet-400"
            }`}
          >
            <Settings className="w-4 h-4 sm:w-5 sm:h-5 flex-shrink-0" />
            <span className="font-medium text-sm sm:text-base">Settings</span>
          </Link>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="h-14 sm:h-16 bg-secondary-30/50 backdrop-blur-xl border-b border-slate-700/30 flex items-center justify-between px-3 sm:px-4 lg:px-8">
          {/* Left Section - Mobile Menu & Title */}
          <div className="flex items-center gap-2 sm:gap-4">
            {/* Mobile Menu Button */}
            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="lg:hidden p-1.5 sm:p-2 rounded-lg hover:bg-violet-500/10 text-muted-foreground hover:text-white transition-colors"
            >
              {isSidebarOpen ? (
                <X className="w-4 h-4 sm:w-5 sm:h-5" />
              ) : (
                <Menu className="w-4 h-4 sm:w-5 sm:h-5" />
              )}
            </button>

            {/* Page Title - Mobile */}
            <span className="lg:hidden font-heading font-semibold text-white text-sm sm:text-base">
              PhishCatcher
            </span>
          </div>

          {/* Right Section - Always at far right */}
          <div className="flex items-center gap-1 sm:gap-2 lg:gap-4 ml-auto">
            {/* Theme Toggle */}
            <ThemeToggle />

            {/* Notifications */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="relative p-1.5 sm:p-2 rounded-lg hover:bg-violet-500/10 text-muted-foreground hover:text-white transition-colors">
                  <Bell className="w-4 h-4 sm:w-5 sm:h-5" />
                  {unreadCount > 0 && (
                    <span className="absolute top-0.5 right-0.5 sm:top-1 sm:right-1 w-3 h-3 sm:w-4 sm:h-4 bg-pink-500 rounded-full text-[8px] sm:text-[10px] font-medium text-white flex items-center justify-center">
                      {unreadCount > 99 ? '99+' : unreadCount}
                    </span>
                  )}
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-80">
                <div className="flex items-center justify-between p-3 border-b border-slate-700/20">
                  <h3 className="font-semibold">Notifications</h3>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={() => navigate('/settings/notifications')}
                  >
                    Settings
                  </Button>
                </div>
                <div className="max-h-96 overflow-y-auto">
                  {notifications.length === 0 ? (
                    <div className="p-4 text-center text-muted-foreground">
                      <Bell className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      <p>No notifications yet</p>
                    </div>
                  ) : (
                    notifications.slice(0, 5).map((notification) => (
                      <DropdownMenuItem 
                        key={notification.id} 
                        className="flex items-start gap-3 p-3 cursor-pointer"
                        onClick={() => {
                          // Mark as read and navigate if needed
                          if (notification.onClick) {
                            notification.onClick();
                          }
                        }}
                      >
                        <div className="flex-shrink-0">
                          {notification.type === 'security' && <ShieldAlert className="w-4 h-4 text-rose-500" />}
                          {notification.type === 'phishing' && <AlertTriangle className="w-4 h-4 text-amber-500" />}
                          {notification.type === 'success' && <CheckCircle className="w-4 h-4 text-emerald-500" />}
                          {notification.type === 'info' && <Info className="w-4 h-4 text-blue-500" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm truncate">{notification.title}</p>
                          <p className="text-xs text-muted-foreground truncate">{notification.message}</p>
                          <p className="text-xs text-muted-foreground mt-1">
                            {new Date(notification.created_at).toLocaleTimeString()}
                          </p>
                        </div>
                        {!notification.is_read && (
                          <div className="w-2 h-2 bg-violet-500 rounded-full flex-shrink-0 mt-1" />
                        )}
                      </DropdownMenuItem>
                    ))
                  )}
                </div>
                {notifications.length > 5 && (
                  <div className="p-2 border-t border-slate-700/20">
                    <Button 
                      variant="ghost" 
                      className="w-full"
                      onClick={() => navigate('/notifications')}
                    >
                      View all notifications
                    </Button>
                  </div>
                )}
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Profile Dropdown */}
            <div className="relative">
              <button
                onClick={() => setIsProfileOpen(!isProfileOpen)}
                className="flex items-center gap-1.5 sm:gap-2 lg:gap-3 p-1.5 sm:p-2 rounded-xl hover:bg-violet-500/10 transition-colors"
              >
                <div className="w-6 h-6 sm:w-8 sm:h-8 rounded-full bg-violet-gradient flex items-center justify-center">
                  <User className="w-3 h-3 sm:w-4 sm:h-4 text-white" />
                </div>
                <div className="hidden lg:block text-left">
                  <span className="text-sm font-medium text-white block">
                    {userName}
                  </span>
                  {isAdmin && (
                    <span className="text-[10px] text-violet-400 uppercase">
                      Administrator
                    </span>
                  )}
                </div>
                <ChevronDown
                  className={`w-3 h-3 sm:w-4 sm:h-4 text-muted-foreground transition-transform hidden lg:block ${isProfileOpen ? "rotate-180" : ""}`}
                />
              </button>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto p-3 sm:p-4 lg:p-6 xl:p-8">
          {children}
        </main>
      </div>
      
      {/* Profile Dropdown - Rendered outside main content to avoid overflow clipping */}
      {isProfileOpen && (
        <>
          <div
            className="fixed inset-0 z-[999]"
            onClick={() => setIsProfileOpen(false)}
          />
          <div className="fixed right-2 sm:right-4 lg:right-8 top-14 sm:top-16 w-48 sm:w-56 bg-secondary-30 backdrop-blur-xl border border-slate-700/30 rounded-xl shadow-card-strong z-[9999] py-2">
            <div className="px-4 py-3 border-b border-slate-700/20 bg-gradient-to-r from-violet-500/5 to-transparent">
              <p className="text-sm font-medium text-white">{userName}</p>
              <p className="text-xs text-muted-foreground">
                {userEmail}
              </p>
              {isAdmin && (
                <Badge className="mt-1 bg-violet-500/20 text-violet-400 text-[10px]">
                  Administrator
                </Badge>
              )}
            </div>
            <Link
              to="/settings"
              className="flex items-center gap-3 px-4 py-2.5 text-sm text-muted-foreground hover:text-white hover:bg-violet-500/10 transition-colors"
              onClick={() => setIsProfileOpen(false)}
            >
              <Settings className="w-4 h-4" />
              Settings
            </Link>
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-pink-400 hover:text-pink-300 hover:bg-pink-500/10 transition-colors"
            >
              <LogOut className="w-4 h-4" />
              Log out
            </button>
          </div>
        </>
      )}
    </div>
  );
}
