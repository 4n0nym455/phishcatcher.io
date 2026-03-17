import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  Users, 
  Mail, 
  Shield, 
  TrendingUp, 
  AlertTriangle,
  CheckCircle,
  Search,
  Filter,
  MoreVertical,
  Ban,
  UserCheck,
  BarChart3,
  Activity,
  Server,
  Database,
  Loader2,
  RefreshCw,
  Settings,
  FileText,
  Brain
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { adminApi } from '@/lib/api';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

// Mock activity data for chart (will be replaced with real data when available)
const userActivityData = [
  { hour: '00:00', users: 120, analyses: 450 },
  { hour: '04:00', users: 80, analyses: 280 },
  { hour: '08:00', users: 340, analyses: 1200 },
  { hour: '12:00', users: 420, analyses: 1800 },
  { hour: '16:00', users: 380, analyses: 1500 },
  { hour: '20:00', users: 290, analyses: 980 },
  { hour: '23:59', users: 150, analyses: 520 },
];

const threatDistribution = [
  { name: 'Phishing', value: 45, color: '#7B61FF' },
  { name: 'Malware', value: 25, color: '#FF4D8D' },
  { name: 'Spoofing', value: 18, color: '#FFD166' },
  { name: 'Spam', value: 12, color: '#27D3C7' },
];

export default function AdminDashboard() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTab, setSelectedTab] = useState('overview');
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [modelInfo, setModelInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Fetch dashboard data
  const fetchData = async () => {
    try {
      setRefreshing(true);
      const [statsData, usersData, modelData] = await Promise.all([
        adminApi.getStats(),
        adminApi.listUsers({ page: 1, pageSize: 5 }),
        adminApi.getModelInfo().catch(() => null), // Model info might not be available
      ]);
      
      setStats(statsData);
      setUsers(usersData.items || []);
      setModelInfo(modelData);
    } catch (error) {
      toast.error('Failed to load admin data');
      console.error('Admin data fetch error:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRefresh = () => {
    fetchData();
  };

  const handleSuspendUser = async (userId) => {
    try {
      await adminApi.updateUser(userId, { is_active: false });
      toast.success('User suspended successfully');
      fetchData(); // Refresh data
    } catch (error) {
      toast.error('Failed to suspend user');
    }
  };

  const handleActivateUser = async (userId) => {
    try {
      await adminApi.updateUser(userId, { is_active: true });
      toast.success('User activated successfully');
      fetchData(); // Refresh data
    } catch (error) {
      toast.error('Failed to activate user');
    }
  };

  const handleRetrainModel = async () => {
    try {
      await adminApi.retrainModel();
      toast.success('Model retraining queued');
    } catch (error) {
      toast.error('Failed to queue model retraining');
    }
  };

  const getStatusBadge = (isActive) => {
    return isActive ? (
      <Badge className="status-safe">Active</Badge>
    ) : (
      <Badge className="status-danger">Inactive</Badge>
    );
  };

  const getRoleBadge = (role) => {
    switch (role) {
      case 'admin':
        return <Badge className="bg-violet-500/15 text-violet-400 border-violet-500/25">Admin</Badge>;
      case 'user':
        return <Badge className="bg-secondary-30 text-muted-foreground border-violet-500/15">User</Badge>;
      default:
        return null;
    }
  };

  // Format numbers
  const formatNumber = (num) => {
    if (num === undefined || num === null) return '0';
    return num.toLocaleString();
  };

  // Prepare stats for display
  const systemStats = stats ? [
    { 
      label: 'Total Users', 
      value: formatNumber(stats.users?.total), 
      icon: Users, 
      change: `+${formatNumber(stats.users?.new_today)} today` 
    },
    { 
      label: 'Active Users', 
      value: formatNumber(stats.users?.active), 
      icon: UserCheck, 
      change: `${Math.round((stats.users?.active / stats.users?.total) * 100) || 0}% of total` 
    },
    { 
      label: 'Analyses Today', 
      value: formatNumber(stats.analyses?.today), 
      icon: Mail, 
      change: `+${formatNumber(stats.analyses?.completed)} completed` 
    },
    { 
      label: 'Threats Detected', 
      value: formatNumber(stats.threats?.phishing_detected + stats.threats?.malware_detected), 
      icon: Shield, 
      change: `Risk: ${stats.threats?.average_risk_score || 0}` 
    },
  ] : [];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-violet-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-heading font-bold text-white">Admin Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1">System administration and monitoring</p>
        </div>
        <div className="flex items-center gap-3">
          <Button 
            variant="outline" 
            className="bg-transparent border-violet-500/25 text-white"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button variant="outline" className="bg-transparent border-violet-500/25 text-white" asChild>
            <Link to="/admin/users">
              <Users className="w-4 h-4 mr-2" />
              Manage Users
            </Link>
          </Button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {systemStats.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <div 
              key={index}
              className="glass-card rounded-xl sm:rounded-2xl p-4 sm:p-6"
            >
              <div className="flex items-start justify-between">
                <div className="w-10 sm:w-12 h-10 sm:h-12 rounded-xl bg-violet-500/15 flex items-center justify-center">
                  <Icon className="w-5 sm:w-6 h-5 sm:h-6 text-violet-400" />
                </div>
                <span className="text-xs text-muted-foreground">
                  {stat.change}
                </span>
              </div>
              <div className="mt-3 sm:mt-4">
                <p className="text-2xl sm:text-3xl font-mono font-bold text-white">{stat.value}</p>
                <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">{stat.label}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* User Activity Chart */}
        <div className="lg:col-span-2 glass-card rounded-2xl p-4 sm:p-6">
          <h3 className="text-base sm:text-lg font-heading font-semibold text-white mb-4">User Activity (24h)</h3>
          <div className="h-56 sm:h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={userActivityData}>
                <defs>
                  <linearGradient id="colorUsers" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#7B61FF" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#7B61FF" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorAnalyses" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#27D3C7" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#27D3C7" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="hour" stroke="hsl(var(--muted-foreground))" fontSize={11} />
                <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'hsl(var(--card))', 
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '12px'
                  }}
                />
                <Area type="monotone" dataKey="users" stroke="#7B61FF" fillOpacity={1} fill="url(#colorUsers)" />
                <Area type="monotone" dataKey="analyses" stroke="#27D3C7" fillOpacity={1} fill="url(#colorAnalyses)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Threat Distribution */}
        <div className="glass-card rounded-2xl p-4 sm:p-6">
          <h3 className="text-base sm:text-lg font-heading font-semibold text-white mb-4">Threat Distribution</h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={threatDistribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={70}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {threatDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'hsl(var(--card))', 
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '12px'
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-2 gap-2 mt-4">
            {threatDistribution.map((cat, index) => (
              <div key={index} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: cat.color }} />
                <span className="text-xs text-muted-foreground">{cat.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Link to="/admin/users" className="glass-card rounded-xl p-4 hover:bg-violet-500/5 transition-colors">
          <Users className="w-6 h-6 text-violet-400 mb-2" />
          <h4 className="font-medium text-white">User Management</h4>
          <p className="text-xs text-muted-foreground mt-1">Manage system users</p>
        </Link>
        <Link to="/admin/audit-logs" className="glass-card rounded-xl p-4 hover:bg-violet-500/5 transition-colors">
          <FileText className="w-6 h-6 text-teal-400 mb-2" />
          <h4 className="font-medium text-white">Audit Logs</h4>
          <p className="text-xs text-muted-foreground mt-1">View system activity</p>
        </Link>
        <Link to="/admin/model" className="glass-card rounded-xl p-4 hover:bg-violet-500/5 transition-colors">
          <Brain className="w-6 h-6 text-pink-400 mb-2" />
          <h4 className="font-medium text-white">ML Model</h4>
          <p className="text-xs text-muted-foreground mt-1">Model management</p>
        </Link>
        <Link to="/admin/settings" className="glass-card rounded-xl p-4 hover:bg-violet-500/5 transition-colors">
          <Settings className="w-6 h-6 text-amber-400 mb-2" />
          <h4 className="font-medium text-white">Settings</h4>
          <p className="text-xs text-muted-foreground mt-1">System configuration</p>
        </Link>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-violet-500/15">
        {['overview', 'users', 'model'].map((tab) => (
          <button
            key={tab}
            onClick={() => setSelectedTab(tab)}
            className={`px-4 py-2 text-sm font-medium capitalize transition-colors ${
              selectedTab === tab
                ? 'text-violet-400 border-b-2 border-violet-400'
                : 'text-muted-foreground hover:text-white'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Users Table */}
      {selectedTab === 'users' && (
        <div className="glass-card rounded-2xl p-4 sm:p-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
            <h3 className="text-base sm:text-lg font-heading font-semibold text-white">Recent Users</h3>
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  placeholder="Search users..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 w-full sm:w-64"
                />
              </div>
              <Button variant="outline" size="icon" className="bg-transparent border-violet-500/25">
                <Filter className="w-4 h-4" />
              </Button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-violet-500/15">
                  <th className="text-left py-3 px-4 text-xs font-medium text-muted-foreground">User</th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-muted-foreground">Role</th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-muted-foreground">Status</th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-muted-foreground">Joined</th>
                  <th className="text-right py-3 px-4 text-xs font-medium text-muted-foreground">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users
                  .filter(user => 
                    user.full_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
                    user.email?.toLowerCase().includes(searchQuery.toLowerCase())
                  )
                  .map((user) => (
                  <tr key={user.id} className="border-b border-violet-500/10 hover:bg-violet-500/5">
                    <td className="py-3 px-4">
                      <div>
                        <p className="text-sm font-medium text-white">{user.full_name || 'No name'}</p>
                        <p className="text-xs text-muted-foreground">{user.email}</p>
                      </div>
                    </td>
                    <td className="py-3 px-4">{getRoleBadge(user.role)}</td>
                    <td className="py-3 px-4">{getStatusBadge(user.is_active)}</td>
                    <td className="py-3 px-4">
                      <span className="text-xs text-muted-foreground">
                        {new Date(user.created_at).toLocaleDateString()}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {user.is_active ? (
                          <button 
                            onClick={() => handleSuspendUser(user.id)}
                            className="p-2 rounded-lg hover:bg-pink-500/10 text-muted-foreground hover:text-pink-400 transition-colors"
                            title="Suspend"
                          >
                            <Ban className="w-4 h-4" />
                          </button>
                        ) : (
                          <button 
                            onClick={() => handleActivateUser(user.id)}
                            className="p-2 rounded-lg hover:bg-teal-500/10 text-muted-foreground hover:text-teal-400 transition-colors"
                            title="Activate"
                          >
                            <UserCheck className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Overview Tab Content */}
      {selectedTab === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
          <div className="glass-card rounded-2xl p-4 sm:p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base sm:text-lg font-heading font-semibold text-white">ML Model Status</h3>
              <Button 
                variant="outline" 
                size="sm" 
                className="bg-transparent border-violet-500/25 text-white"
                onClick={handleRetrainModel}
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Retrain
              </Button>
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Status</span>
                <Badge className="status-safe">Active</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Total Analyses</span>
                <span className="text-sm font-mono text-white">{formatNumber(stats?.analyses?.total)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Phishing Detected</span>
                <span className="text-sm font-mono text-pink-400">{formatNumber(stats?.threats?.phishing_detected)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Malware Detected</span>
                <span className="text-sm font-mono text-amber-400">{formatNumber(stats?.threats?.malware_detected)}</span>
              </div>
            </div>
          </div>

          <div className="glass-card rounded-2xl p-4 sm:p-6">
            <h3 className="text-base sm:text-lg font-heading font-semibold text-white mb-4">System Overview</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Database Status</span>
                <Badge className="status-safe">Connected</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Email Service</span>
                <Badge className="status-safe">Operational</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">ML Service</span>
                <Badge className="status-safe">Operational</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Last Updated</span>
                <span className="text-sm text-muted-foreground">
                  {stats?.timestamp ? new Date(stats.timestamp).toLocaleString() : 'N/A'}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Model Tab */}
      {selectedTab === 'model' && (
        <div className="glass-card rounded-2xl p-4 sm:p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-base sm:text-lg font-heading font-semibold text-white">ML Model Information</h3>
            <Button 
              variant="outline" 
              className="bg-transparent border-violet-500/25 text-white"
              onClick={handleRetrainModel}
            >
              <Brain className="w-4 h-4 mr-2" />
              Retrain Model
            </Button>
          </div>
          
          {modelInfo ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 rounded-xl bg-violet-500/10">
                  <p className="text-xs text-muted-foreground mb-1">Model Version</p>
                  <p className="text-lg font-mono text-white">{modelInfo.version || 'N/A'}</p>
                </div>
                <div className="p-4 rounded-xl bg-teal-500/10">
                  <p className="text-xs text-muted-foreground mb-1">Accuracy</p>
                  <p className="text-lg font-mono text-teal-400">{modelInfo.accuracy ? `${(modelInfo.accuracy * 100).toFixed(1)}%` : 'N/A'}</p>
                </div>
                <div className="p-4 rounded-xl bg-pink-500/10">
                  <p className="text-xs text-muted-foreground mb-1">Training Samples</p>
                  <p className="text-lg font-mono text-pink-400">{formatNumber(modelInfo.training_samples)}</p>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-muted-foreground">Model information not available</p>
          )}
        </div>
      )}
    </div>
  );
}
