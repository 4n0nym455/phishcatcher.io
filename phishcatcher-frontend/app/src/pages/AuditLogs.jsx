import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { 
  FileText, 
  Search,
  Filter,
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  Loader2,
  RefreshCw,
  User,
  Shield,
  Mail,
  Trash2,
  Edit2,
  LogIn,
  LogOut,
  AlertTriangle
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { adminApi } from '@/lib/api';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const actionIcons = {
  'LOGIN': LogIn,
  'LOGOUT': LogOut,
  'USER_CREATED': User,
  'USER_UPDATED': Edit2,
  'USER_DELETED': Trash2,
  'ANALYSIS_CREATED': FileText,
  'ANALYSIS_COMPLETED': Shield,
  'EMAIL_SCANNED': Mail,
  'SUSPICIOUS_EMAIL_DETECTED': AlertTriangle,
};

const actionColors = {
  'LOGIN': 'bg-teal-500/15 text-teal-400',
  'LOGOUT': 'bg-muted text-muted-foreground',
  'USER_CREATED': 'bg-violet-500/15 text-violet-400',
  'USER_UPDATED': 'bg-blue-500/15 text-blue-400',
  'USER_DELETED': 'bg-pink-500/15 text-pink-400',
  'ANALYSIS_CREATED': 'bg-amber-500/15 text-amber-400',
  'ANALYSIS_COMPLETED': 'bg-green-500/15 text-green-400',
  'EMAIL_SCANNED': 'bg-cyan-500/15 text-cyan-400',
  'SUSPICIOUS_EMAIL_DETECTED': 'bg-red-500/15 text-red-400',
};

export default function AuditLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [totalPages, setTotalPages] = useState(1);
  const [totalLogs, setTotalLogs] = useState(0);
  const [actionFilter, setActionFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [userFilter, setUserFilter] = useState('all');
  const [days, setDays] = useState(7);
  const [users, setUsers] = useState([]);
  const [logsCache, setLogsCache] = useState(new Map()); // Cache for logs
  const [lastFetchTime, setLastFetchTime] = useState(0); // Track last fetch time

  // Helper function to validate UUID format
  const isValidUUID = (uuid) => {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    return uuidRegex.test(uuid);
  };

  // Generate cache key for current filters
  const getCacheKey = () => {
    return `${page}-${pageSize}-${actionFilter}-${statusFilter}-${userFilter}-${days}-${searchQuery}`;
  };

  // Check if cache is valid (5 minutes)
  const isCacheValid = (cacheEntry) => {
    return Date.now() - cacheEntry.timestamp < 5 * 60 * 1000; // 5 minutes
  };

  const fetchLogs = async () => {
    try {
      setLoading(true);
      
      // Check cache first
      const cacheKey = getCacheKey();
      const cachedEntry = logsCache.get(cacheKey);
      
      if (cachedEntry && isCacheValid(cachedEntry)) {
        console.log('Using cached data for:', cacheKey);
        setLogs(cachedEntry.data.items || []);
        setTotalPages(cachedEntry.data.pages || 1);
        setTotalLogs(cachedEntry.data.total || 0);
        
        // Extract users from cached data if needed
        if (cachedEntry.data.items && cachedEntry.data.items.length > 0) {
          const uniqueUsers = [...new Set(cachedEntry.data.items.map(log => log.user_id).filter(Boolean))]
            .map(userId => ({ 
              id: userId, 
              email: cachedEntry.data.items.find(log => log.user_id === userId)?.user_email || 'Unknown User'
            }))
            .sort((a, b) => a.email.localeCompare(b.email));
          setUsers(uniqueUsers);
        }
        setLoading(false);
        return;
      }
      
      // Debug: Log current userFilter and users
      console.log('Debug - userFilter:', userFilter);
      console.log('Debug - users:', users);
      console.log('Debug - userFilter is valid UUID:', userFilter !== 'all' && isValidUUID(userFilter));
      
      // Validate userFilter is a valid UUID if not 'all'
      const validUserId = userFilter === 'all' ? undefined : 
        (isValidUUID(userFilter) && users.some(u => u.id === userFilter) ? userFilter : undefined);
      
      // Debug: Log validation result
      console.log('Debug - validUserId:', validUserId);
      
      const params = {
        page,
        pageSize,
        days,
        action: actionFilter === 'all' ? undefined : actionFilter,
        status: statusFilter === 'all' ? undefined : statusFilter,
        userId: validUserId,
        search: searchQuery.trim() || undefined,
      };
      
      const data = await adminApi.getAuditLogs(params);
      setLogs(data.items || []);
      setTotalPages(data.pages || 1);
      setTotalLogs(data.total || 0);
      
      // Cache the results
      const newCacheEntry = {
        data: data,
        timestamp: Date.now()
      };
      
      // Limit cache size to prevent memory issues
      if (logsCache.size >= 50) {
        // Remove oldest entry
        const oldestKey = logsCache.keys().next().value;
        const newCache = new Map(logsCache);
        newCache.delete(oldestKey);
        setLogsCache(newCache);
      }
      
      setLogsCache(prev => new Map(prev).set(cacheKey, newCacheEntry));
      setLastFetchTime(Date.now());
      
      // Extract unique users from the logs for the user filter
      if (data.items && data.items.length > 0) {
        // Extract unique users from logs for filtering - use actual user_id
        const uniqueUsers = [...new Set(data.items.map(log => log.user_id).filter(Boolean))]
          .map(userId => ({ 
            id: userId, 
            email: data.items.find(log => log.user_id === userId)?.user_email || 'Unknown User'
          }))
          .sort((a, b) => a.email.localeCompare(b.email));
        setUsers(uniqueUsers);
        
        // Debug: Check if current userFilter is invalid (contains email)
        if (userFilter !== 'all' && !uniqueUsers.some(u => u.id === userFilter)) {
          console.log('Debug - Resetting invalid userFilter to "all"');
          setUserFilter('all');
        }
      }
    } catch (error) {
      toast.error('Failed to load audit logs');
      console.error('Error fetching audit logs:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [page, pageSize, actionFilter, statusFilter, userFilter, days, searchQuery]);

  // Clear cache and force refresh
  const clearCacheAndRefresh = () => {
    setLogsCache(new Map());
    setLastFetchTime(0);
    fetchLogs();
  };

  // Reset userFilter if it contains invalid format (email) on component mount
  useEffect(() => {
    if (userFilter !== 'all' && !isValidUUID(userFilter)) {
      console.log('Debug - Invalid userFilter detected on mount, resetting to "all":', userFilter);
      setUserFilter('all');
    }
  }, []); // Only run on mount

  // Debounced search with optimized timing and cache invalidation
  const debouncedSearch = useCallback(
    (query) => {
      // Clear cache when searching to ensure fresh results
      if (query.trim()) {
        setLogsCache(new Map());
      setLastFetchTime(0);
      setPage(1); // Reset to first page when searching
      setSearchQuery(query);
    } else {
        setSearchQuery(query);
      }
    },
    [clearCacheAndRefresh] // Dependency on cache clearing function
  );

  const handleSearchChange = (e) => {
    const query = e.target.value;
    setSearchQuery(query); // Update local state immediately for responsive UI
    debouncedSearch(query); // Debounced API call
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const getActionIcon = (action) => {
    const Icon = actionIcons[action] || FileText;
    return <Icon className="w-4 h-4" />;
  };

  const getActionBadgeClass = (action) => {
    return actionColors[action] || 'bg-violet-500/15 text-violet-400';
  };

  if (loading && logs.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-violet-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="icon" className="bg-transparent border-violet-500/25" asChild>
            <Link to="/admin">
              <ArrowLeft className="w-4 h-4" />
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl sm:text-3xl font-heading font-bold text-white">Audit Logs</h1>
            <p className="text-sm text-muted-foreground mt-1">
              {totalLogs.toLocaleString()} total events
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button 
            variant="outline" 
            className="bg-transparent border-violet-500/25 text-white"
            onClick={clearCacheAndRefresh}
            disabled={loading}
            title={logsCache.size > 0 ? `Clear cache (${logsCache.size} cached)` : 'Refresh'}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
            {logsCache.size > 0 && (
              <span className="ml-1 text-xs bg-violet-500/20 px-1 rounded">
                {logsCache.size}
              </span>
            )}
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col lg:flex-row gap-4">
        <div className="relative flex-1 lg:flex-none lg:w-80">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search logs by user, action, or IP address..."
            value={searchQuery}
            onChange={handleSearchChange}
            className="pl-9 text-black font-bold"
          />
        </div>
        
        <div className="flex flex-wrap gap-2">
          <Select value={actionFilter} onValueChange={(value) => {
            setActionFilter(value);
            setPage(1); // Reset to first page when filtering
          }}>
            <SelectTrigger className="w-[180px] bg-transparent border-violet-500/25">
              <Filter className="w-4 h-4 mr-2" />
              <SelectValue placeholder="Filter by action" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Actions</SelectItem>
              <SelectItem value="login">Login</SelectItem>
              <SelectItem value="logout">Logout</SelectItem>
              <SelectItem value="user_registered">User Registered</SelectItem>
              <SelectItem value="user_updated">User Updated</SelectItem>
              <SelectItem value="user_deleted">User Deleted</SelectItem>
              <SelectItem value="password_changed">Password Changed</SelectItem>
              <SelectItem value="mfa_setup_initiated">MFA Setup Initiated</SelectItem>
              <SelectItem value="mfa_enabled">MFA Enabled</SelectItem>
              <SelectItem value="mfa_disabled">MFA Disabled</SelectItem>
              <SelectItem value="mfa_challenge">MFA Challenge</SelectItem>
              <SelectItem value="mfa_success">MFA Success</SelectItem>
              <SelectItem value="mfa_failure">MFA Failure</SelectItem>
              <SelectItem value="mfa_backup_code_used">MFA Backup Code Used</SelectItem>
              <SelectItem value="account_locked">Account Locked</SelectItem>
              <SelectItem value="account_unlocked">Account Unlocked</SelectItem>
              <SelectItem value="analysis_created">Analysis Created</SelectItem>
              <SelectItem value="analysis_completed">Analysis Completed</SelectItem>
              <SelectItem value="email_scanned">Email Scanned</SelectItem>
              <SelectItem value="suspicious_email_detected">Suspicious Email</SelectItem>
            </SelectContent>
          </Select>

          <Select value={statusFilter} onValueChange={(value) => {
            setStatusFilter(value);
            setPage(1); // Reset to first page when filtering
          }}>
            <SelectTrigger className="w-[140px] bg-transparent border-violet-500/25">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="success">Success</SelectItem>
              <SelectItem value="failure">Failure</SelectItem>
            </SelectContent>
          </Select>

          <Select value={userFilter} onValueChange={(value) => {
            // Only allow valid UUIDs or 'all'
            const isValidSelection = value === 'all' || (isValidUUID(value) && users.some(u => u.id === value));
            console.log('Debug - User selection change:', value, 'isValid:', isValidSelection);
            if (isValidSelection) {
              setUserFilter(value);
              setPage(1); // Reset to first page when filtering
            } else {
              // Reset to 'all' if invalid selection
              console.log('Debug - Invalid selection, resetting to "all"');
              setUserFilter('all');
              setPage(1);
            }
          }}>
            <SelectTrigger className="w-[200px] bg-transparent border-violet-500/25">
              <User className="w-4 h-4 mr-2" />
              <SelectValue placeholder="Filter by user" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Users</SelectItem>
              {users.map((user) => (
                <SelectItem key={user.id} value={user.id}>
                  {user.email}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={days.toString()} onValueChange={(value) => {
            setDays(parseInt(value));
            setPage(1); // Reset to first page when changing time period
          }}>
            <SelectTrigger className="w-[150px] bg-transparent border-violet-500/25">
              <SelectValue placeholder="Time period" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1">Last 24 hours</SelectItem>
              <SelectItem value="7">Last 7 days</SelectItem>
              <SelectItem value="30">Last 30 days</SelectItem>
              <SelectItem value="90">Last 90 days</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Active Filters Display */}
      {(actionFilter !== 'all' || statusFilter !== 'all' || userFilter !== 'all' || searchQuery) && (
        <div className="flex items-center justify-between bg-violet-900/20 rounded-lg border border-violet-500/25 p-3">
          <div className="flex flex-wrap gap-2 items-center">
            <span className="text-sm text-muted-foreground">Active filters:</span>
            {searchQuery && (
              <Badge variant="secondary" className="bg-violet-500/20 text-violet-300">
                Search: "{searchQuery}"
              </Badge>
            )}
            {actionFilter !== 'all' && (
              <Badge variant="secondary" className="bg-violet-500/20 text-violet-300">
                Action: {actionFilter}
              </Badge>
            )}
            {statusFilter !== 'all' && (
              <Badge variant="secondary" className="bg-violet-500/20 text-violet-300">
                Status: {statusFilter}
              </Badge>
            )}
            {userFilter !== 'all' && (
              <Badge variant="secondary" className="bg-violet-500/20 text-violet-300">
                User: {users.find(u => u.id === userFilter)?.email || userFilter}
              </Badge>
            )}
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setSearchQuery('');
              setActionFilter('all');
              setStatusFilter('all');
              setUserFilter('all');
              setDays(7);
              setPage(1);
            }}
            className="text-violet-400 hover:text-violet-300"
          >
            Clear All
          </Button>
        </div>
      )}

      {/* Logs Table */}
      <div className="glass-card rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-violet-500/15 bg-violet-500/5">
                <th className="text-left py-4 px-4 text-xs font-medium text-muted-foreground">Action</th>
                <th className="text-left py-4 px-4 text-xs font-medium text-muted-foreground">User</th>
                <th className="text-left py-4 px-4 text-xs font-medium text-muted-foreground">Resource</th>
                <th className="text-left py-4 px-4 text-xs font-medium text-muted-foreground">Status</th>
                <th className="text-left py-4 px-4 text-xs font-medium text-muted-foreground">IP Address</th>
                <th className="text-left py-4 px-4 text-xs font-medium text-muted-foreground">Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id} className="border-b border-violet-500/10 hover:bg-violet-500/5 transition-colors">
                  <td className="py-4 px-4">
                    <div className="flex items-center gap-3">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${getActionBadgeClass(log.action)}`}>
                        {getActionIcon(log.action)}
                      </div>
                      <span className="text-sm font-medium text-white">{log.action}</span>
                    </div>
                  </td>
                  <td className="py-4 px-4">
                    <div>
                      <p className="text-sm text-white">{log.user_email || 'Unknown'}</p>
                      <p className="text-xs text-muted-foreground">{log.user_id?.slice(0, 8)}...</p>
                    </div>
                  </td>
                  <td className="py-4 px-4">
                    <div>
                      <p className="text-sm text-white">{log.resource_type}</p>
                      <p className="text-xs text-muted-foreground">{log.resource_id?.slice(0, 8)}...</p>
                    </div>
                  </td>
                  <td className="py-4 px-4">
                    <Badge className={log.status === 'success' ? 'status-safe' : log.status === 'failed' ? 'status-danger' : 'bg-amber-500/15 text-amber-400'}>
                      {log.status}
                    </Badge>
                  </td>
                  <td className="py-4 px-4">
                    <span className="text-sm text-muted-foreground font-mono">
                      {log.ip_address || 'N/A'}
                    </span>
                  </td>
                  <td className="py-4 px-4">
                    <span className="text-sm text-muted-foreground">
                      {formatDate(log.created_at)}
                    </span>
                  </td>
                </tr>
              ))}
              
              {logs.length === 0 && !loading && (
                <tr>
                  <td colSpan={6} className="py-12 text-center">
                    <FileText className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                    <p className="text-muted-foreground mb-2">
                      {searchQuery || actionFilter !== 'all' || statusFilter !== 'all' || userFilter !== 'all' 
                        ? 'No audit logs match your filters' 
                        : 'No audit logs found'
                      }
                    </p>
                    {(searchQuery || actionFilter !== 'all' || statusFilter !== 'all' || userFilter !== 'all') && (
                      <p className="text-sm text-muted-foreground">
                        Try adjusting your filters or <button 
                          onClick={() => {
                            setSearchQuery('');
                            setActionFilter('all');
                            setStatusFilter('all');
                            setUserFilter('all');
                            setPage(1);
                          }}
                          className="text-violet-400 hover:text-violet-300 underline"
                        >
                          clear all filters
                        </button>
                      </p>
                    )}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between px-4 py-4 border-t border-violet-500/15">
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              Page {page} of {totalPages}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="bg-transparent border-violet-500/25"
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1 || loading}
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="bg-transparent border-violet-500/25"
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages || loading}
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
