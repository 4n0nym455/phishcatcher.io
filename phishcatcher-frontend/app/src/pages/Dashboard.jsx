import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  Mail, 
  Upload, 
  FileText, 
  AlertTriangle, 
  CheckCircle, 
  TrendingUp, 
  TrendingDown,
  Clock,
  ArrowRight,
  Search,
  Shield,
  Link as LinkIcon
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

// Mock data for charts
const emailTrendData = [
  { time: '00:00', scanned: 1200, threats: 45 },
  { time: '04:00', scanned: 800, threats: 23 },
  { time: '08:00', scanned: 2400, threats: 89 },
  { time: '12:00', scanned: 3200, threats: 134 },
  { time: '16:00', scanned: 2800, threats: 98 },
  { time: '20:00', scanned: 1900, threats: 67 },
  { time: '23:59', scanned: 1100, threats: 34 },
];

const threatTypeData = [
  { name: 'Phishing', value: 45, color: '#7B61FF' },
  { name: 'Malware', value: 25, color: '#FF4D8D' },
  { name: 'Spoofing', value: 20, color: '#FFD166' },
  { name: 'Spam', value: 10, color: '#27D3C7' },
];

// Mock recent analyses
const recentAnalyses = [
  { id: 1, subject: 'Reset your password immediately', sender: 'security@fake-bank.com', time: '2 min ago', status: 'danger', score: 92, type: 'email' },
  { id: 2, subject: 'Invoice #9921 from Acme Corp', sender: 'billing@acmecorp.com', time: '5 min ago', status: 'safe', score: 12, type: 'email' },
  { id: 3, subject: 'Urgent: Verify your account', sender: 'support@amaz0n-security.com', time: '12 min ago', status: 'danger', score: 88, type: 'txt' },
  { id: 4, subject: 'Team meeting notes', sender: 'sarah@company.com', time: '18 min ago', status: 'safe', score: 5, type: 'email' },
  { id: 5, subject: 'Your package delivery failed', sender: 'shipping@dhl-express.net', time: '25 min ago', status: 'warning', score: 67, type: 'eml' },
  { id: 6, subject: 'Shared document: Q3 Review', sender: 'mike@company.com', time: '32 min ago', status: 'safe', score: 8, type: 'email' },
  { id: 7, subject: 'Action required: Tax statement', sender: 'irs@gov-tax.org', time: '45 min ago', status: 'danger', score: 95, type: 'txt' },
  { id: 8, subject: 'IT: Scheduled maintenance', sender: 'it@company.com', time: '1 hour ago', status: 'safe', score: 3, type: 'email' },
];

// Stats cards data
const statsCards = [
  { 
    title: 'Emails Analyzed', 
    value: '2,847', 
    change: '+12%', 
    trend: 'up',
    icon: Mail,
    color: 'violet'
  },
  { 
    title: 'Threats Detected', 
    value: '147', 
    change: '+8%', 
    trend: 'up',
    icon: AlertTriangle,
    color: 'pink'
  },
  { 
    title: 'Suspicious Flagged', 
    value: '389', 
    change: '-5%', 
    trend: 'down',
    icon: Shield,
    color: 'amber'
  },
  { 
    title: 'Safe Emails', 
    value: '2,311', 
    change: '+15%', 
    trend: 'up',
    icon: CheckCircle,
    color: 'teal'
  },
];

export default function Dashboard() {
  const [searchQuery, setSearchQuery] = useState('');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const getStatusBadge = (status) => {
    switch (status) {
      case 'safe':
        return <span className="status-safe">Safe</span>;
      case 'warning':
        return <span className="status-warning">Suspicious</span>;
      case 'danger':
        return <span className="status-danger">Threat Detected</span>;
      default:
        return null;
    }
  };

  const getScoreColor = (score) => {
    if (score >= 70) return 'text-pink-400';
    if (score >= 40) return 'text-amber-400';
    return 'text-teal-400';
  };

  const getFileIcon = (type) => {
    switch (type) {
      case 'eml':
        return <Mail className="w-4 h-4" />;
      case 'txt':
        return <FileText className="w-4 h-4" />;
      default:
        return <Mail className="w-4 h-4" />;
    }
  };

  if (!mounted) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="w-12 h-12 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-heading font-bold text-white">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1">Monitor your email security and analysis results</p>
        </div>
        <Link to="/upload">
          <Button className="btn btn-primary">
            <Upload className="w-4 h-4" />
            Upload Email
          </Button>
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {statsCards.map((stat, index) => {
          const Icon = stat.icon;
          const TrendIcon = stat.trend === 'up' ? TrendingUp : TrendingDown;
          
          return (
            <div 
              key={index}
              className="glass-card rounded-xl sm:rounded-2xl p-4 sm:p-6"
            >
              <div className="flex items-start justify-between">
                <div className="w-9 sm:w-12 h-9 sm:h-12 rounded-lg sm:rounded-xl bg-violet-500/15 flex items-center justify-center">
                  <Icon className="w-4 sm:w-6 h-4 sm:h-6 text-violet-400" />
                </div>
                <div className={`flex items-center gap-1 text-xs sm:text-sm ${stat.trend === 'up' ? 'text-teal-400' : 'text-pink-400'}`}>
                  <TrendIcon className="w-3 sm:w-4 h-3 sm:h-4" />
                  {stat.change}
                </div>
              </div>
              <div className="mt-3 sm:mt-4">
                <p className="text-xl sm:text-3xl font-mono font-medium text-white">{stat.value}</p>
                <p className="text-xs sm:text-sm text-muted-foreground">{stat.label}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* Email Trend Chart */}
        <div className="lg:col-span-2 glass-card rounded-2xl p-4 sm:p-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4 sm:mb-6">
            <div>
              <h3 className="text-base sm:text-lg font-heading font-semibold text-white">Analysis Trend</h3>
              <p className="text-xs sm:text-sm text-muted-foreground">Last 24 hours</p>
            </div>
            <div className="flex items-center gap-3 sm:gap-4 text-xs sm:text-sm">
              <div className="flex items-center gap-1.5 sm:gap-2">
                <div className="w-2.5 sm:w-3 h-2.5 sm:h-3 rounded-full bg-violet-500" />
                <span className="text-muted-foreground">Scanned</span>
              </div>
              <div className="flex items-center gap-1.5 sm:gap-2">
                <div className="w-2.5 sm:w-3 h-2.5 sm:h-3 rounded-full bg-pink-500" />
                <span className="text-muted-foreground">Threats</span>
              </div>
            </div>
          </div>
          <div className="h-48 sm:h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={emailTrendData}>
                <defs>
                  <linearGradient id="colorScanned" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#7B61FF" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#7B61FF" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorThreats" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#FF4D8D" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#FF4D8D" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(123, 97, 255, 0.08)" />
                <XAxis 
                  dataKey="time" 
                  stroke="#A7B0D5" 
                  fontSize={11}
                  tickLine={false}
                />
                <YAxis 
                  stroke="#A7B0D5" 
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#0F1635', 
                    border: '1px solid rgba(123, 97, 255, 0.25)',
                    borderRadius: '12px'
                  }}
                />
                <Area 
                  type="monotone" 
                  dataKey="scanned" 
                  stroke="#7B61FF" 
                  strokeWidth={2}
                  fillOpacity={1} 
                  fill="url(#colorScanned)" 
                />
                <Area 
                  type="monotone" 
                  dataKey="threats" 
                  stroke="#FF4D8D" 
                  strokeWidth={2}
                  fillOpacity={1} 
                  fill="url(#colorThreats)" 
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Threat Types Pie Chart */}
        <div className="glass-card rounded-2xl p-4 sm:p-6">
          <h3 className="text-base sm:text-lg font-heading font-semibold text-white mb-1 sm:mb-2">Threat Types</h3>
          <p className="text-xs sm:text-sm text-muted-foreground mb-4 sm:mb-6">Distribution by category</p>
          <div className="h-40 sm:h-48">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={threatTypeData}
                  cx="50%"
                  cy="50%"
                  innerRadius={35}
                  outerRadius={65}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {threatTypeData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#0F1635', 
                    border: '1px solid rgba(123, 97, 255, 0.25)',
                    borderRadius: '12px'
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-2 gap-2 mt-3 sm:mt-4">
            {threatTypeData.map((type, index) => (
              <div key={index} className="flex items-center gap-2">
                <div className="w-2.5 sm:w-3 h-2.5 sm:h-3 rounded-full" style={{ backgroundColor: type.color }} />
                <span className="text-xs text-muted-foreground">{type.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Analyses */}
      <div className="glass-card rounded-2xl p-4 sm:p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4 mb-4 sm:mb-6">
          <div>
            <h3 className="text-base sm:text-lg font-heading font-semibold text-white">Recent Analyses</h3>
            <p className="text-xs sm:text-sm text-muted-foreground">Last analyzed emails</p>
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search analyses..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full sm:w-48 pl-9 h-9 sm:h-10 text-black font-semibold bg-secondary-30/50 border-violet-500/20 rounded-lg text-sm"
            />
          </div>
        </div>

        <div className="space-y-2 sm:space-y-3">
          {recentAnalyses
            .filter(analysis => 
              analysis.subject.toLowerCase().includes(searchQuery.toLowerCase()) ||
              analysis.sender.toLowerCase().includes(searchQuery.toLowerCase())
            )
            .slice(0, 6)
            .map((analysis) => (
            <Link
              key={analysis.id}
              to={`/analysis/${analysis.id}`}
              className="flex items-center gap-3 sm:gap-4 p-3 rounded-xl hover:bg-violet-500/10 transition-colors group"
            >
              <div className={`w-9 sm:w-10 h-9 sm:h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                analysis.status === 'safe' ? 'bg-teal-500/15' :
                analysis.status === 'warning' ? 'bg-amber-500/15' :
                'bg-pink-500/15'
              }`}>
                {getFileIcon(analysis.type)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate group-hover:text-violet-400 transition-colors">
                  {analysis.subject}
                </p>
                <p className="text-xs text-muted-foreground truncate">{analysis.sender}</p>
              </div>
              <div className="flex items-center gap-2 sm:gap-3">
                {getStatusBadge(analysis.status)}
                <span className={`text-sm font-mono font-medium ${getScoreColor(analysis.score)}`}>
                  {analysis.score}%
                </span>
                <ArrowRight className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity hidden sm:block" />
              </div>
            </Link>
          ))}
        </div>

        <Button 
          variant="ghost" 
          className="w-full mt-4 sm:mt-6 text-violet-400 hover:text-violet-300 hover:bg-violet-500/10 text-sm sm:text-base"
          asChild
        >
          <Link to="/analysis">
            View all analyses
            <ArrowRight className="w-4 h-4 ml-2" />
          </Link>
        </Button>
      </div>

      {/* System Status */}
      <div className="glass-card rounded-2xl p-4 sm:p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-3 sm:gap-4">
            <div className="w-10 sm:w-12 h-10 sm:h-12 rounded-xl bg-teal-500/15 flex items-center justify-center">
              <Clock className="w-5 sm:w-6 h-5 sm:h-6 text-teal-400" />
            </div>
            <div>
              <h3 className="text-base sm:text-lg font-heading font-semibold text-white">System Status</h3>
              <p className="text-xs sm:text-sm text-muted-foreground">All systems operational</p>
            </div>
          </div>
          <div className="flex items-center gap-4 sm:gap-6">
            <div className="text-center">
              <p className="text-xl sm:text-2xl font-mono font-medium text-teal-400">99.9%</p>
              <p className="text-xs text-muted-foreground">Uptime</p>
            </div>
            <div className="text-center">
              <p className="text-xl sm:text-2xl font-mono font-medium text-violet-400">18ms</p>
              <p className="text-xs text-muted-foreground">Avg Analysis</p>
            </div>
            <div className="text-center hidden sm:block">
              <p className="text-xl sm:text-2xl font-mono font-medium text-amber-400">0.3%</p>
              <p className="text-xs text-muted-foreground">False Positive</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
