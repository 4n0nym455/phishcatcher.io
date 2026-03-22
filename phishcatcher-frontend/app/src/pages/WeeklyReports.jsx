import { useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  Calendar, 
  TrendingUp, 
  TrendingDown, 
  AlertTriangle, 
  CheckCircle, 
  Shield,
  Mail,
  FileText,
  Download,
  ChevronLeft,
  ChevronRight,
  BarChart3,
  Eye
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { generateUUIDs } from '@/lib/uuid';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

// Weekly data
const weeklyData = [
  { day: 'Mon', analyzed: 420, threats: 18, suspicious: 45 },
  { day: 'Tue', analyzed: 380, threats: 12, suspicious: 38 },
  { day: 'Wed', analyzed: 450, threats: 22, suspicious: 52 },
  { day: 'Thu', analyzed: 510, threats: 28, suspicious: 61 },
  { day: 'Fri', analyzed: 390, threats: 15, suspicious: 42 },
  { day: 'Sat', analyzed: 280, threats: 8, suspicious: 25 },
  { day: 'Sun', analyzed: 320, threats: 10, suspicious: 31 },
];

const threatCategories = [
  { name: 'Phishing', value: 45, color: '#7B61FF' },
  { name: 'Malware', value: 25, color: '#FF4D8D' },
  { name: 'Spoofing', value: 18, color: '#FFD166' },
  { name: 'Spam', value: 12, color: '#27D3C7' },
];

const topThreats = [
  { 
    id: generateUUIDs(1)[0], 
    subject: 'Urgent: Verify your bank account', 
    sender: 'security@fake-bank-secure.com', 
    count: 47,
    trend: 'up',
    riskScore: 94 
  },
  { 
    id: generateUUIDs(1)[0], 
    subject: 'Invoice payment required', 
    sender: 'billing@fake-invoice.net', 
    count: 32,
    trend: 'up',
    riskScore: 88 
  },
  { 
    id: generateUUIDs(1)[0], 
    subject: 'Your package delivery failed', 
    sender: 'shipping@fake-delivery.com', 
    count: 28,
    trend: 'down',
    riskScore: 76 
  },
  { 
    id: generateUUIDs(1)[0], 
    subject: 'Action required: Tax refund', 
    sender: 'refunds@fake-tax.gov', 
    count: 21,
    trend: 'up',
    riskScore: 91 
  },
  { 
    id: generateUUIDs(1)[0], 
    subject: 'Free gift card claim', 
    sender: 'rewards@fake-gifts.com', 
    count: 19,
    trend: 'down',
    riskScore: 82 
  }
];

const weeklyStats = [
  { label: 'Total Analyzed', value: '2,750', change: '+12%', trend: 'up' },
  { label: 'Threats Detected', value: '113', change: '+8%', trend: 'up' },
  { label: 'Suspicious', value: '294', change: '-3%', trend: 'down' },
  { label: 'Detection Rate', value: '98.2%', change: '+0.5%', trend: 'up' },
];

export default function WeeklyReports() {
  const [currentWeek, setCurrentWeek] = useState('Jan 13 - Jan 19, 2026');
  const [showSensitive, setShowSensitive] = useState(false);

  const handleDownload = () => {
    toast.success('Weekly report downloaded');
  };

  const handlePreviousWeek = () => {
    toast.info('Loading previous week data...');
  };

  const handleNextWeek = () => {
    toast.info('Loading next week data...');
  };

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-heading font-bold text-white">Weekly Reports</h1>
          <p className="text-sm text-muted-foreground mt-1">Phishing threat intelligence summary</p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            className="bg-transparent border-violet-500/25 hover:bg-violet-500/10 text-white"
            onClick={() => setShowSensitive(!showSensitive)}
          >
            <Eye className="w-4 h-4 mr-2" />
            {showSensitive ? 'Hide Sensitive' : 'Show Sensitive'}
          </Button>
          <Button
            className="bg-violet-gradient hover:opacity-90 text-white shadow-glow"
            onClick={handleDownload}
          >
            <Download className="w-4 h-4 mr-2" />
            Download Report
          </Button>
        </div>
      </div>

      {/* Week Navigation */}
      <div className="glass-card rounded-2xl p-4 flex items-center justify-between">
        <button 
          onClick={handlePreviousWeek}
          className="p-2 rounded-lg hover:bg-violet-500/10 text-muted-foreground hover:text-white transition-colors"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-3">
          <Calendar className="w-5 h-5 text-violet-400" />
          <span className="text-white font-medium">{currentWeek}</span>
        </div>
        <button 
          onClick={handleNextWeek}
          className="p-2 rounded-lg hover:bg-violet-500/10 text-muted-foreground hover:text-white transition-colors"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {weeklyStats.map((stat, index) => {
          const TrendIcon = stat.trend === 'up' ? TrendingUp : TrendingDown;
          return (
            <div 
              key={index}
              className="glass-card rounded-xl sm:rounded-2xl p-4 sm:p-6"
            >
              <p className="text-xs sm:text-sm text-muted-foreground mb-1">{stat.label}</p>
              <div className="flex items-end justify-between">
                <p className="text-xl sm:text-2xl font-mono font-bold text-white">{stat.value}</p>
                <div className={`flex items-center gap-1 text-xs ${stat.trend === 'up' ? 'text-teal-400' : 'text-pink-400'}`}>
                  <TrendIcon className="w-3 h-3" />
                  {stat.change}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* Daily Analysis Chart */}
        <div className="lg:col-span-2 glass-card rounded-2xl p-4 sm:p-6">
          <h3 className="text-base sm:text-lg font-heading font-semibold text-white mb-4">Daily Analysis Activity</h3>
          <div className="h-56 sm:h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={weeklyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="day" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'hsl(var(--card))', 
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '12px'
                  }}
                />
                <Bar dataKey="analyzed" fill="#7B61FF" radius={[4, 4, 0, 0]} />
                <Bar dataKey="threats" fill="#FF4D8D" radius={[4, 4, 0, 0]} />
                <Bar dataKey="suspicious" fill="#FFD166" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="flex items-center gap-4 mt-4 justify-center">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-violet-500" />
              <span className="text-xs text-muted-foreground">Analyzed</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-pink-500" />
              <span className="text-xs text-muted-foreground">Threats</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-amber-400" />
              <span className="text-xs text-muted-foreground">Suspicious</span>
            </div>
          </div>
        </div>

        {/* Threat Categories */}
        <div className="glass-card rounded-2xl p-4 sm:p-6">
          <h3 className="text-base sm:text-lg font-heading font-semibold text-white mb-4">Threat Categories</h3>
          <div className="h-48 sm:h-56">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={threatCategories}
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={70}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {threatCategories.map((entry, index) => (
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
            {threatCategories.map((cat, index) => (
              <div key={index} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: cat.color }} />
                <span className="text-xs text-muted-foreground">{cat.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Top Threats This Week */}
      <div className="glass-card rounded-2xl p-4 sm:p-6">
        <h3 className="text-base sm:text-lg font-heading font-semibold text-white mb-4">Top Threats This Week</h3>
        <div className="space-y-3">
          {topThreats.map((threat, index) => (
            <Link
              key={threat.id}
              to={`/analysis/${threat.id}`}
              className="flex items-center gap-3 sm:gap-4 p-3 rounded-xl hover:bg-violet-500/10 transition-colors group"
            >
              <div className="w-8 h-8 rounded-lg bg-pink-500/15 flex items-center justify-center flex-shrink-0">
                <span className="text-sm font-mono font-bold text-pink-400">#{index + 1}</span>
              </div>
              <div className="flex-1 min-w-0">
                <p className={`text-sm font-medium text-white truncate group-hover:text-violet-400 transition-colors ${!showSensitive && 'blur-sensitive'}`}>
                  {threat.subject}
                </p>
                <p className={`text-xs text-muted-foreground truncate ${!showSensitive && 'blur-sensitive'}`}>
                  {threat.sender}
                </p>
              </div>
              <div className="flex items-center gap-3 sm:gap-4">
                <div className="text-right">
                  <p className="text-sm font-mono font-medium text-white">{threat.count}</p>
                  <p className="text-[10px] text-muted-foreground">reports</p>
                </div>
                <Badge className="status-danger text-xs">
                  {threat.riskScore}%
                </Badge>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Key Insights */}
      <div className="glass-card rounded-2xl p-4 sm:p-6">
        <h3 className="text-base sm:text-lg font-heading font-semibold text-white mb-4">Key Insights</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="flex items-start gap-3 p-4 rounded-xl bg-violet-500/10 border border-violet-500/20">
            <TrendingUp className="w-5 h-5 text-violet-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-white">Phishing attempts increased by 15%</p>
              <p className="text-xs text-muted-foreground mt-1">
                Most targeting financial institutions with fake login pages
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-4 rounded-xl bg-teal-500/10 border border-teal-500/20">
            <Shield className="w-5 h-5 text-teal-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-white">New threat signatures detected</p>
              <p className="text-xs text-muted-foreground mt-1">
                12 new phishing patterns identified and added to detection rules
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-4 rounded-xl bg-amber-500/10 border border-amber-500/20">
            <AlertTriangle className="w-5 h-5 text-amber-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-white">Invoice scam campaigns active</p>
              <p className="text-xs text-muted-foreground mt-1">
                Multiple campaigns using compromised vendor email accounts
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-4 rounded-xl bg-pink-500/10 border border-pink-500/20">
            <Mail className="w-5 h-5 text-pink-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-white">Spoofed sender domains on the rise</p>
              <p className="text-xs text-muted-foreground mt-1">
                23 new lookalike domains detected this week
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
