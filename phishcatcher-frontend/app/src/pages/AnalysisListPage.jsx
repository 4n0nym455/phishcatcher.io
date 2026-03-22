import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  Search, 
  Filter, 
  FileText, 
  Shield, 
  AlertTriangle, 
  CheckCircle, 
  ArrowRight,
  Calendar,
  TrendingUp,
  TrendingDown,
  Eye
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';

// Mock data for analyses
const mockAnalyses = [
  {
    id: '1',
    subject: 'Urgent: Account Verification Required',
    sender: 'security@paypal.com',
    status: 'danger',
    score: 92,
    type: 'eml',
    date: '2024-03-22T10:30:00Z',
    threatType: 'phishing'
  },
  {
    id: '2', 
    subject: 'Weekly Team Meeting Notes',
    sender: 'manager@company.com',
    status: 'safe',
    score: 15,
    type: 'eml',
    date: '2024-03-22T09:15:00Z',
    threatType: 'none'
  },
  {
    id: '3',
    subject: 'Suspicious Login Attempt Detected',
    sender: 'alerts@github.com',
    status: 'warning',
    score: 67,
    type: 'txt',
    date: '2024-03-22T08:45:00Z',
    threatType: 'suspicious'
  },
  {
    id: '4',
    subject: 'Invoice #12345 - Payment Due',
    sender: 'billing@fake-invoice.com',
    status: 'danger',
    score: 88,
    type: 'msg',
    date: '2024-03-22T07:20:00Z',
    threatType: 'phishing'
  },
  {
    id: '5',
    subject: 'Project Update - Q1 Review',
    sender: 'team@company.com',
    status: 'safe',
    score: 8,
    type: 'eml',
    date: '2024-03-21T16:30:00Z',
    threatType: 'none'
  },
  {
    id: '6',
    subject: 'Your Package Has Been Delivered',
    sender: 'delivery@tracking-service.com',
    status: 'warning',
    score: 45,
    type: 'eml',
    date: '2024-03-21T14:10:00Z',
    threatType: 'suspicious'
  }
];

export default function AnalysisListPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [analyses, setAnalyses] = useState(mockAnalyses);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // In a real implementation, this would fetch data from your API
    setIsLoading(true);
    setTimeout(() => {
      setAnalyses(mockAnalyses);
      setIsLoading(false);
    }, 500);
  }, []);

  const getFileIcon = (type) => {
    switch (type) {
      case 'eml':
        return <FileText className="w-5 h-5" />;
      case 'txt':
        return <FileText className="w-5 h-5" />;
      case 'msg':
        return <FileText className="w-5 h-5" />;
      default:
        return <FileText className="w-5 h-5" />;
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'safe':
        return <Badge className="bg-teal-500/20 text-teal-400 border-teal-500/30">Safe</Badge>;
      case 'warning':
        return <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/30">Suspicious</Badge>;
      case 'danger':
        return <Badge className="bg-pink-500/20 text-pink-400 border-pink-500/30">Threat</Badge>;
      default:
        return null;
    }
  };

  const getScoreColor = (score) => {
    if (score >= 70) return 'text-pink-400';
    if (score >= 40) return 'text-amber-400';
    return 'text-teal-400';
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'safe':
        return <CheckCircle className="w-5 h-5 text-teal-400" />;
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-amber-400" />;
      case 'danger':
        return <Shield className="w-5 h-5 text-pink-400" />;
      default:
        return null;
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  };

  const filteredAnalyses = analyses.filter(analysis => {
    const matchesSearch = 
      analysis.subject.toLowerCase().includes(searchQuery.toLowerCase()) ||
      analysis.sender.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesFilter = filterStatus === 'all' || analysis.status === filterStatus;
    
    return matchesSearch && matchesFilter;
  });

  const stats = {
    total: analyses.length,
    safe: analyses.filter(a => a.status === 'safe').length,
    warning: analyses.filter(a => a.status === 'warning').length,
    danger: analyses.filter(a => a.status === 'danger').length
  };

  return (
    <div className="min-h-screen bg-slate-900 p-4 sm:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Analysis History</h1>
          <p className="text-gray-400">View and manage all your email analysis results</p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6 sm:mb-8">
          <div className="glass-card rounded-xl sm:rounded-2xl p-4 sm:p-6 hover:border-violet-500/30 transition-colors">
            <div className="flex items-start justify-between">
              <div className="w-9 sm:w-12 h-9 sm:h-12 rounded-lg sm:rounded-xl bg-violet-500/15 flex items-center justify-center">
                <FileText className="w-4 sm:w-6 h-4 sm:h-6 text-violet-400" />
              </div>
            </div>
            <div className="mt-3 sm:mt-4">
              <p className="text-xl sm:text-3xl font-mono font-medium text-white">{stats.total}</p>
              <p className="text-xs sm:text-sm text-muted-foreground">Total Analyses</p>
            </div>
          </div>

          <div className="glass-card rounded-xl sm:rounded-2xl p-4 sm:p-6 hover:border-violet-500/30 transition-colors">
            <div className="flex items-start justify-between">
              <div className="w-9 sm:w-12 h-9 sm:h-12 rounded-lg sm:rounded-xl bg-teal-500/15 flex items-center justify-center">
                <CheckCircle className="w-4 sm:w-6 h-4 sm:h-6 text-teal-400" />
              </div>
            </div>
            <div className="mt-3 sm:mt-4">
              <p className="text-xl sm:text-3xl font-mono font-medium text-teal-400">{stats.safe}</p>
              <p className="text-xs sm:text-sm text-muted-foreground">Safe Emails</p>
            </div>
          </div>

          <div className="glass-card rounded-xl sm:rounded-2xl p-4 sm:p-6 hover:border-violet-500/30 transition-colors">
            <div className="flex items-start justify-between">
              <div className="w-9 sm:w-12 h-9 sm:h-12 rounded-lg sm:rounded-xl bg-amber-500/15 flex items-center justify-center">
                <AlertTriangle className="w-4 sm:w-6 h-4 sm:h-6 text-amber-400" />
              </div>
            </div>
            <div className="mt-3 sm:mt-4">
              <p className="text-xl sm:text-3xl font-mono font-medium text-amber-400">{stats.warning}</p>
              <p className="text-xs sm:text-sm text-muted-foreground">Suspicious</p>
            </div>
          </div>

          <div className="glass-card rounded-xl sm:rounded-2xl p-4 sm:p-6 hover:border-violet-500/30 transition-colors">
            <div className="flex items-start justify-between">
              <div className="w-9 sm:w-12 h-9 sm:h-12 rounded-lg sm:rounded-xl bg-pink-500/15 flex items-center justify-center">
                <Shield className="w-4 sm:w-6 h-4 sm:h-6 text-pink-400" />
              </div>
            </div>
            <div className="mt-3 sm:mt-4">
              <p className="text-xl sm:text-3xl font-mono font-medium text-pink-400">{stats.danger}</p>
              <p className="text-xs sm:text-sm text-muted-foreground">Threats Detected</p>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="glass-card rounded-xl sm:rounded-2xl p-4 sm:p-6 mb-6">
          <div className="flex flex-col lg:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-5 h-5" />
                <Input
                  placeholder="Search by subject or sender..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 bg-slate-800/50 border-violet-500/30 text-white placeholder-muted-foreground"
                />
              </div>
            </div>
            
            <div className="flex gap-2">
              <Button
                variant={filterStatus === 'all' ? 'default' : 'outline'}
                onClick={() => setFilterStatus('all')}
                className={filterStatus === 'all' ? 'bg-violet-500 hover:bg-violet-600' : 'border-violet-500/30 text-violet-400 hover:bg-violet-500/10'}
              >
                All
              </Button>
              <Button
                variant={filterStatus === 'safe' ? 'default' : 'outline'}
                onClick={() => setFilterStatus('safe')}
                className={filterStatus === 'safe' ? 'bg-teal-500 hover:bg-teal-600' : 'border-teal-500/30 text-teal-400 hover:bg-teal-500/10'}
              >
                Safe
              </Button>
              <Button
                variant={filterStatus === 'warning' ? 'default' : 'outline'}
                onClick={() => setFilterStatus('warning')}
                className={filterStatus === 'warning' ? 'bg-amber-500 hover:bg-amber-600' : 'border-amber-500/30 text-amber-400 hover:bg-amber-500/10'}
              >
                Suspicious
              </Button>
              <Button
                variant={filterStatus === 'danger' ? 'default' : 'outline'}
                onClick={() => setFilterStatus('danger')}
                className={filterStatus === 'danger' ? 'bg-pink-500 hover:bg-pink-600' : 'border-pink-500/30 text-pink-400 hover:bg-pink-500/10'}
              >
                Threats
              </Button>
            </div>
          </div>
        </div>

        {/* Analyses List */}
        <div className="glass-card rounded-xl sm:rounded-2xl">
          {isLoading ? (
            <div className="p-12 text-center">
              <div className="w-8 h-8 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin mx-auto mb-4"></div>
              <p className="text-muted-foreground">Loading analyses...</p>
            </div>
          ) : filteredAnalyses.length === 0 ? (
            <div className="p-12 text-center">
              <div className="w-16 h-16 rounded-2xl bg-violet-500/15 flex items-center justify-center mx-auto mb-4">
                <FileText className="w-8 h-8 text-violet-400" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">No analyses found</h3>
              <p className="text-muted-foreground mb-6">
                {searchQuery || filterStatus !== 'all' 
                  ? 'Try adjusting your search or filters' 
                  : 'Upload your first email to start analyzing'
                }
              </p>
              {(searchQuery || filterStatus !== 'all') && (
                <Button
                  variant="outline"
                  onClick={() => {
                    setSearchQuery('');
                    setFilterStatus('all');
                  }}
                  className="border-violet-500/30 text-violet-400 hover:bg-violet-500/10"
                >
                  Clear Filters
                </Button>
              )}
            </div>
          ) : (
            <div className="divide-y divide-violet-500/10">
              {filteredAnalyses.map((analysis) => (
                <Link
                  key={analysis.id}
                  to={`/analysis/${analysis.id}`}
                  className="flex items-center gap-3 sm:gap-4 p-3 sm:p-4 hover:bg-violet-500/5 transition-colors group"
                >
                  <div className={`w-9 sm:w-10 h-9 sm:h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                    analysis.status === 'safe' ? 'bg-teal-500/15' :
                    analysis.status === 'warning' ? 'bg-amber-500/15' :
                    'bg-pink-500/15'
                  }`}>
                    {getStatusIcon(analysis.status)}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-3 sm:gap-4">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-white truncate group-hover:text-violet-400 transition-colors mb-1">
                          {analysis.subject}
                        </p>
                        <div className="flex items-center gap-3 sm:gap-4 text-xs sm:text-sm text-muted-foreground">
                          <span>{analysis.sender}</span>
                          <span>•</span>
                          <span>{formatDate(analysis.date)}</span>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
                        {getStatusBadge(analysis.status)}
                        <span className={`text-sm font-mono font-medium ${getScoreColor(analysis.score)}`}>
                          {analysis.score}%
                        </span>
                        <ArrowRight className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity hidden sm:block" />
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      <style jsx>{`
        .glass-card {
          background: rgba(255, 255, 255, 0.05);
          backdrop-filter: blur(10px);
          border: 1px solid rgba(139, 92, 246, 0.2);
        }
      `}</style>
    </div>
  );
}
