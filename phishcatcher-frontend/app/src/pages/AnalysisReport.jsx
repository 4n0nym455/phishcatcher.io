import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  ArrowLeft, 
  Mail, 
  AlertTriangle, 
  Link as LinkIcon,
  FileText,
  Globe,
  Clock,
  User,
  Download,
  Share2,
  Flag,
  CheckCircle,
  XCircle,
  Info,
  ChevronDown,
  ChevronUp,
  Paperclip,
  ExternalLink,
  Eye,
  EyeOff,
  Printer
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';

// Mock analysis data
const analysisData = {
  id: 1,
  subject: 'Reset your password immediately',
  sender: 'security-notice@service-alerts.com',
  displayName: 'Security Team',
  recipient: 'john@company.com',
  receivedAt: '2024-01-15 14:32:18',
  analyzedAt: '2024-01-15 14:32:19',
  fileType: 'eml',
  fileSize: '12.4 KB',
  riskScore: 92,
  status: 'danger',
  category: 'Phishing',
  
  // Risk breakdown for radar chart
  riskFactors: [
    { factor: 'Domain Age', score: 95, fullMark: 100 },
    { factor: 'Sender Rep', score: 88, fullMark: 100 },
    { factor: 'Link Safety', score: 94, fullMark: 100 },
    { factor: 'Content', score: 91, fullMark: 100 },
    { factor: 'Attachments', score: 45, fullMark: 100 },
    { factor: 'Urgency', score: 98, fullMark: 100 },
  ],

  // Detailed findings
  findings: [
    {
      id: 1,
      type: 'domain',
      severity: 'critical',
      title: 'Suspicious Domain Age',
      description: 'The sender domain was registered only 3 days ago. Legitimate security teams typically use established domains.',
      recommendation: 'Verify the sender through an official channel before taking any action.',
    },
    {
      id: 2,
      type: 'content',
      severity: 'high',
      title: 'Urgency Tactics Detected',
      description: 'Email uses phrases like "immediately" and "urgent action required" to create pressure.',
      recommendation: 'Take time to verify requests independently of the email.',
    },
    {
      id: 3,
      type: 'link',
      severity: 'critical',
      title: 'Suspicious Link Detected',
      description: 'The reset link points to a domain that mimics legitimate services but has slight variations.',
      recommendation: 'Never click links in suspicious emails. Navigate directly to the official website.',
    },
    {
      id: 4,
      type: 'sender',
      severity: 'high',
      title: 'Display Name Spoofing',
      description: 'The display name "Security Team" does not match the actual sender domain.',
      recommendation: 'Always check the actual email address, not just the display name.',
    },
  ],

  // Links analysis
  links: [
    { url: 'https://service-alerts-reset.com/verify', status: 'suspicious', category: 'Phishing' },
    { url: 'https://legitimate-cdn.com/image.png', status: 'safe', category: 'Image' },
  ],

  // Attachments
  attachments: [
    { name: 'document.pdf', size: '245 KB', status: 'safe' },
  ],

  // Email headers
  headers: {
    'From': 'security-notice@service-alerts.com',
    'Reply-To': 'support@fake-support.com',
    'Return-Path': '<bounced@service-alerts.com>',
    'SPF': 'fail',
    'DKIM': 'fail',
    'DMARC': 'fail',
  },

  // Similar threats
  similarThreats: [
    { id: 101, subject: 'Urgent: Account suspension warning', date: '2 days ago', score: 89 },
    { id: 102, subject: 'Verify your identity now', date: '3 days ago', score: 94 },
    { id: 103, subject: 'Security alert: Unauthorized access', date: '5 days ago', score: 87 },
  ],
};

// Risk score color helper
const getRiskColor = (score) => {
  if (score < 30) return { bg: 'bg-teal-500/15', text: 'text-teal-400', border: 'border-teal-500/25', label: 'Low Risk' };
  if (score < 70) return { bg: 'bg-amber-500/15', text: 'text-amber-400', border: 'border-amber-500/25', label: 'Medium Risk' };
  return { bg: 'bg-pink-500/15', text: 'text-pink-400', border: 'border-pink-500/25', label: 'High Risk' };
};

const severityColors = {
  critical: 'bg-pink-500/15 text-pink-400 border-pink-500/25',
  high: 'bg-amber-500/15 text-amber-400 border-amber-500/25',
  medium: 'bg-violet-500/15 text-violet-400 border-violet-500/25',
  low: 'bg-teal-500/15 text-teal-400 border-teal-500/25',
};

export default function AnalysisReport() {
  const { id } = useParams();
  const [expandedFinding, setExpandedFinding] = useState(1);
  const [showHeaders, setShowHeaders] = useState(false);
  const [blurSensitive, setBlurSensitive] = useState(true);

  const riskColors = getRiskColor(analysisData.riskScore);

  const handleExport = () => {
    // Create report content
    const reportContent = `
PHISHCATCHER ANALYSIS REPORT
============================

Report ID: ${id}
Generated: ${new Date().toISOString()}

EMAIL DETAILS
-------------
Subject: ${analysisData.subject}
From: ${analysisData.displayName} <${analysisData.sender}>
To: ${analysisData.recipient}
Analyzed: ${analysisData.analyzedAt}

RISK ASSESSMENT
---------------
Risk Score: ${analysisData.riskScore}%
Status: ${riskColors.label}

FINDINGS
--------
${analysisData.findings.map(f => `
[${f.severity.toUpperCase()}] ${f.title}
${f.description}
Recommendation: ${f.recommendation}
`).join('\n')}

DISCLAIMER
----------
This report is generated by PhishCatcher's ML-based analysis system.
Results should be reviewed by security professionals before taking action.
`;

    // Create and download file
    const blob = new Blob([reportContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `phishcatcher-report-${id}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    toast.success('Report downloaded successfully');
  };

  const handleDownloadPDF = () => {
    toast.info('PDF export coming soon! For now, use the text export.');
  };

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href);
    toast.success('Link copied to clipboard');
  };

  const handleFlag = () => {
    toast.success('Email flagged for security team review');
  };

  const handlePrint = () => {
    window.print();
  };

  const SensitiveText = ({ children, className = '' }) => (
    <span className={`${blurSensitive ? 'blur-sensitive' : ''} ${className}`}>
      {children}
    </span>
  );

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div className="flex items-center gap-3 sm:gap-4">
          <Button
            variant="outline"
            size="icon"
            className="bg-transparent border-violet-500/25 hover:bg-violet-500/10 h-9 w-9 sm:h-10 sm:w-10"
            asChild
          >
            <Link to="/dashboard">
              <ArrowLeft className="w-4 sm:w-5 h-4 sm:h-5" />
            </Link>
          </Button>
          <div>
            <h1 className="text-xl sm:text-2xl font-heading font-bold text-white">Analysis Report</h1>
            <p className="text-xs sm:text-sm text-muted-foreground">ID: {id} • Analyzed {analysisData.analyzedAt}</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          {/* Blur Toggle */}
          <Button
            variant="outline"
            className="bg-transparent border-violet-500/25 hover:bg-violet-500/10 text-white h-9 sm:h-10 text-xs sm:text-sm"
            onClick={() => setBlurSensitive(!blurSensitive)}
          >
            {blurSensitive ? <EyeOff className="w-4 h-4 mr-1.5" /> : <Eye className="w-4 h-4 mr-1.5" />}
            {blurSensitive ? 'Show' : 'Hide'}
          </Button>
          
          <Button
            variant="outline"
            className="bg-transparent border-violet-500/25 hover:bg-violet-500/10 text-white h-9 sm:h-10 text-xs sm:text-sm"
            onClick={handleShare}
          >
            <Share2 className="w-4 h-4 mr-1.5" />
            <span className="hidden sm:inline">Share</span>
          </Button>
          
          <Button
            variant="outline"
            className="bg-transparent border-violet-500/25 hover:bg-violet-500/10 text-white h-9 sm:h-10 text-xs sm:text-sm"
            onClick={handlePrint}
          >
            <Printer className="w-4 h-4 mr-1.5" />
            <span className="hidden sm:inline">Print</span>
          </Button>
          
          <Button
            variant="outline"
            className="bg-transparent border-violet-500/25 hover:bg-violet-500/10 text-white h-9 sm:h-10 text-xs sm:text-sm"
            onClick={handleExport}
          >
            <Download className="w-4 h-4 mr-1.5" />
            <span className="hidden sm:inline">Export</span>
          </Button>
          
          <Button
            className="bg-pink-500/15 hover:bg-pink-500/25 text-pink-400 border border-pink-500/25 h-9 sm:h-10 text-xs sm:text-sm"
            onClick={handleFlag}
          >
            <Flag className="w-4 h-4 mr-1.5" />
            Flag
          </Button>
        </div>
      </div>

      {/* Main Analysis Card */}
      <div className="glass-card-strong rounded-2xl p-5 sm:p-8">
        <div className="flex flex-col lg:flex-row gap-6 sm:gap-8">
          {/* Left: Email Info */}
          <div className="flex-1">
            {/* Email Header */}
            <div className="flex items-start gap-3 sm:gap-4 mb-5 sm:mb-6">
              <div className="w-11 sm:w-14 h-11 sm:h-14 rounded-xl bg-pink-500/15 flex items-center justify-center flex-shrink-0">
                <Mail className="w-5 sm:w-7 h-5 sm:h-7 text-pink-400" />
              </div>
              <div className="flex-1 min-w-0">
                <h2 className="text-base sm:text-xl font-heading font-semibold text-white mb-1">
                  <SensitiveText>{analysisData.subject}</SensitiveText>
                </h2>
                <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 text-xs sm:text-sm">
                  <span className="text-muted-foreground">From:</span>
                  <span className="text-white"><SensitiveText>{analysisData.displayName}</SensitiveText></span>
                  <span className="text-muted-foreground truncate"><SensitiveText>&lt;{analysisData.sender}&gt;</SensitiveText></span>
                </div>
                <div className="flex items-center gap-1.5 sm:gap-2 text-xs sm:text-sm mt-0.5">
                  <span className="text-muted-foreground">To:</span>
                  <span className="text-white"><SensitiveText>{analysisData.recipient}</SensitiveText></span>
                </div>
                <div className="flex items-center gap-2 mt-2">
                  <Badge className="bg-violet-500/15 text-violet-400 border-violet-500/25 text-xs">
                    {analysisData.fileType.toUpperCase()}
                  </Badge>
                  <span className="text-xs text-muted-foreground">{analysisData.fileSize}</span>
                </div>
              </div>
            </div>

            <Separator className="bg-violet-500/15 mb-5 sm:mb-6" />

            {/* Risk Score Display */}
            <div className="flex flex-col sm:flex-row items-center gap-4 sm:gap-6 mb-5 sm:mb-6">
              <div className={`w-20 sm:w-24 h-20 sm:h-24 rounded-2xl ${riskColors.bg} border-2 ${riskColors.border} flex flex-col items-center justify-center flex-shrink-0`}>
                <span className={`text-2xl sm:text-3xl font-mono font-bold ${riskColors.text}`}>
                  {analysisData.riskScore}%
                </span>
                <span className={`text-xs ${riskColors.text} mt-0.5`}>Risk</span>
              </div>
              <div className="text-center sm:text-left">
                <Badge className={`${riskColors.bg} ${riskColors.text} ${riskColors.border} mb-2`}>
                  {riskColors.label}
                </Badge>
                <p className="text-xs sm:text-sm text-muted-foreground max-w-md">
                  This email exhibits multiple characteristics commonly associated with phishing attempts. 
                  Review the findings below and take appropriate precautions.
                </p>
              </div>
            </div>

            {/* Quick Stats */}
            <div className="grid grid-cols-3 gap-2 sm:gap-4">
              <div className="p-3 sm:p-4 rounded-xl bg-secondary-30/50 border border-violet-500/15">
                <div className="flex items-center gap-1.5 sm:gap-2 mb-1.5 sm:mb-2">
                  <Globe className="w-3.5 sm:w-4 h-3.5 sm:h-4 text-violet-400" />
                  <span className="text-[10px] sm:text-xs text-muted-foreground">Domain Age</span>
                </div>
                <p className="text-sm sm:text-lg font-mono font-medium text-pink-400">3 days</p>
              </div>
              <div className="p-3 sm:p-4 rounded-xl bg-secondary-30/50 border border-violet-500/15">
                <div className="flex items-center gap-1.5 sm:gap-2 mb-1.5 sm:mb-2">
                  <LinkIcon className="w-3.5 sm:w-4 h-3.5 sm:h-4 text-violet-400" />
                  <span className="text-[10px] sm:text-xs text-muted-foreground">Links</span>
                </div>
                <p className="text-sm sm:text-lg font-mono font-medium text-pink-400">1 suspicious</p>
              </div>
              <div className="p-3 sm:p-4 rounded-xl bg-secondary-30/50 border border-violet-500/15">
                <div className="flex items-center gap-1.5 sm:gap-2 mb-1.5 sm:mb-2">
                  <Clock className="w-3.5 sm:w-4 h-3.5 sm:h-4 text-violet-400" />
                  <span className="text-[10px] sm:text-xs text-muted-foreground">Analysis Time</span>
                </div>
                <p className="text-sm sm:text-lg font-mono font-medium text-teal-400">18ms</p>
              </div>
            </div>
          </div>

          {/* Right: Radar Chart */}
          <div className="lg:w-56 xl:w-64">
            <h3 className="text-xs sm:text-sm font-medium text-muted-foreground mb-3 sm:mb-4">Risk Factor Analysis</h3>
            <div className="h-48 sm:h-56 lg:h-64">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={analysisData.riskFactors}>
                  <PolarGrid stroke="hsl(var(--border))" />
                  <PolarAngleAxis 
                    dataKey="factor" 
                    tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }}
                  />
                  <PolarRadiusAxis 
                    angle={90} 
                    domain={[0, 100]} 
                    tick={false}
                    axisLine={false}
                  />
                  <Radar
                    name="Risk Score"
                    dataKey="score"
                    stroke="hsl(var(--primary))"
                    strokeWidth={2}
                    fill="hsl(var(--primary))"
                    fillOpacity={0.25}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'hsl(var(--card))', 
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '12px'
                    }}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* Detailed Findings */}
      <div className="glass-card rounded-2xl p-4 sm:p-6">
        <h3 className="text-base sm:text-lg font-heading font-semibold text-white mb-4 sm:mb-6">Detailed Findings</h3>
        <div className="space-y-3 sm:space-y-4">
          {analysisData.findings.map((finding) => (
            <div 
              key={finding.id}
              className="border border-violet-500/15 rounded-xl overflow-hidden"
            >
              <button
                onClick={() => setExpandedFinding(expandedFinding === finding.id ? null : finding.id)}
                className="w-full flex items-center gap-3 sm:gap-4 p-3 sm:p-4 hover:bg-violet-500/5 transition-colors text-left"
              >
                <div className={`w-8 sm:w-10 h-8 sm:h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  finding.severity === 'critical' ? 'bg-pink-500/15' :
                  finding.severity === 'high' ? 'bg-amber-500/15' :
                  'bg-violet-500/15'
                }`}>
                  {finding.type === 'domain' && <Globe className={`w-4 sm:w-5 h-4 sm:h-5 ${
                    finding.severity === 'critical' ? 'text-pink-400' :
                    finding.severity === 'high' ? 'text-amber-400' :
                    'text-violet-400'
                  }`} />}
                  {finding.type === 'content' && <FileText className={`w-4 sm:w-5 h-4 sm:h-5 ${
                    finding.severity === 'critical' ? 'text-pink-400' :
                    finding.severity === 'high' ? 'text-amber-400' :
                    'text-violet-400'
                  }`} />}
                  {finding.type === 'link' && <LinkIcon className={`w-4 sm:w-5 h-4 sm:h-5 ${
                    finding.severity === 'critical' ? 'text-pink-400' :
                    finding.severity === 'high' ? 'text-amber-400' :
                    'text-violet-400'
                  }`} />}
                  {finding.type === 'sender' && <User className={`w-4 sm:w-5 h-4 sm:h-5 ${
                    finding.severity === 'critical' ? 'text-pink-400' :
                    finding.severity === 'high' ? 'text-amber-400' :
                    'text-violet-400'
                  }`} />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h4 className="font-medium text-white text-sm sm:text-base">{finding.title}</h4>
                    <Badge className={`${severityColors[finding.severity]} text-xs`}>
                      {finding.severity}
                    </Badge>
                  </div>
                  <p className="text-xs sm:text-sm text-muted-foreground mt-0.5 line-clamp-1">{finding.description}</p>
                </div>
                {expandedFinding === finding.id ? (
                  <ChevronUp className="w-4 sm:w-5 h-4 sm:h-5 text-muted-foreground flex-shrink-0" />
                ) : (
                  <ChevronDown className="w-4 sm:w-5 h-4 sm:h-5 text-muted-foreground flex-shrink-0" />
                )}
              </button>
              
              {expandedFinding === finding.id && (
                <div className="px-3 sm:px-4 pb-3 sm:pb-4 pt-2 bg-violet-500/5 border-t border-violet-500/15">
                  <div className="flex items-start gap-2 sm:gap-3">
                    <Info className="w-4 sm:w-5 h-4 sm:h-5 text-violet-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-xs sm:text-sm text-white mb-2">{finding.description}</p>
                      <div className="flex items-start gap-2">
                        <CheckCircle className="w-3.5 sm:w-4 h-3.5 sm:h-4 text-teal-400 mt-0.5 flex-shrink-0" />
                        <p className="text-xs sm:text-sm text-muted-foreground">
                          <span className="text-teal-400 font-medium">Recommendation: </span>
                          {finding.recommendation}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Links Analysis & Attachments */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {/* Links Analysis */}
        <div className="glass-card rounded-2xl p-4 sm:p-6">
          <h3 className="text-base sm:text-lg font-heading font-semibold text-white mb-3 sm:mb-4">Link Analysis</h3>
          <div className="space-y-2 sm:space-y-3">
            {analysisData.links.map((link, index) => (
              <div 
                key={index}
                className="flex items-center gap-3 sm:gap-4 p-3 sm:p-4 rounded-xl bg-secondary-30/50 border border-violet-500/15"
              >
                <div className={`w-8 sm:w-10 h-8 sm:h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  link.status === 'suspicious' ? 'bg-pink-500/15' : 'bg-teal-500/15'
                }`}>
                  {link.status === 'suspicious' ? (
                    <AlertTriangle className="w-4 sm:w-5 h-4 sm:h-5 text-pink-400" />
                  ) : (
                    <CheckCircle className="w-4 sm:w-5 h-4 sm:h-5 text-teal-400" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs sm:text-sm text-white truncate font-mono">
                    <SensitiveText>{link.url}</SensitiveText>
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <Badge className={link.status === 'suspicious' ? 'status-danger text-xs' : 'status-safe text-xs'}>
                      {link.status}
                    </Badge>
                    <span className="text-[10px] sm:text-xs text-muted-foreground">{link.category}</span>
                  </div>
                </div>
                <button className="p-1.5 sm:p-2 rounded-lg hover:bg-violet-500/10 text-muted-foreground hover:text-violet-400 transition-colors">
                  <ExternalLink className="w-3.5 sm:w-4 h-3.5 sm:h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Attachments */}
        <div className="glass-card rounded-2xl p-4 sm:p-6">
          <h3 className="text-base sm:text-lg font-heading font-semibold text-white mb-3 sm:mb-4">Attachments</h3>
          <div className="space-y-2 sm:space-y-3">
            {analysisData.attachments.map((attachment, index) => (
              <div 
                key={index}
                className="flex items-center gap-3 sm:gap-4 p-3 sm:p-4 rounded-xl bg-secondary-30/50 border border-violet-500/15"
              >
                <div className="w-8 sm:w-10 h-8 sm:h-10 rounded-lg bg-teal-500/15 flex items-center justify-center flex-shrink-0">
                  <Paperclip className="w-4 sm:w-5 h-4 sm:h-5 text-teal-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs sm:text-sm text-white truncate">
                    <SensitiveText>{attachment.name}</SensitiveText>
                  </p>
                  <p className="text-[10px] sm:text-xs text-muted-foreground">{attachment.size}</p>
                </div>
                <Badge className="status-safe text-xs">
                  {attachment.status}
                </Badge>
                <button className="p-1.5 sm:p-2 rounded-lg hover:bg-violet-500/10 text-muted-foreground hover:text-violet-400 transition-colors">
                  <Eye className="w-3.5 sm:w-4 h-3.5 sm:h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Email Headers */}
      <div className="glass-card rounded-2xl p-4 sm:p-6">
        <button
          onClick={() => setShowHeaders(!showHeaders)}
          className="w-full flex items-center justify-between"
        >
          <h3 className="text-base sm:text-lg font-heading font-semibold text-white">Email Headers</h3>
          {showHeaders ? (
            <ChevronUp className="w-4 sm:w-5 h-4 sm:h-5 text-muted-foreground" />
          ) : (
            <ChevronDown className="w-4 sm:w-5 h-4 sm:h-5 text-muted-foreground" />
          )}
        </button>
        
        {showHeaders && (
          <div className="mt-3 sm:mt-4 space-y-2 sm:space-y-3">
            {Object.entries(analysisData.headers).map(([key, value]) => (
              <div key={key} className="flex flex-col sm:flex-row sm:items-start gap-1 sm:gap-3">
                <span className="text-xs font-mono text-violet-400 w-24 sm:w-28 flex-shrink-0">{key}:</span>
                <span className={`text-xs sm:text-sm font-mono break-all ${
                  value === 'fail' ? 'text-pink-400' :
                  value === 'pass' ? 'text-teal-400' :
                  'text-white'
                }`}>
                  <SensitiveText>{value}</SensitiveText>
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Similar Threats */}
      <div className="glass-card rounded-2xl p-4 sm:p-6">
        <h3 className="text-base sm:text-lg font-heading font-semibold text-white mb-3 sm:mb-4">Similar Threats</h3>
        <div className="space-y-2 sm:space-y-3">
          {analysisData.similarThreats.map((threat) => (
            <Link
              key={threat.id}
              to={`/analysis/${threat.id}`}
              className="flex items-center gap-3 sm:gap-4 p-3 rounded-xl hover:bg-violet-500/10 transition-colors group"
            >
              <div className="w-8 sm:w-10 h-8 sm:h-10 rounded-lg bg-pink-500/15 flex items-center justify-center flex-shrink-0">
                <AlertTriangle className="w-4 sm:w-5 h-4 sm:h-5 text-pink-400" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate group-hover:text-violet-400 transition-colors">
                  <SensitiveText>{threat.subject}</SensitiveText>
                </p>
                <p className="text-xs text-muted-foreground">{threat.date}</p>
              </div>
              <span className="text-sm font-mono font-medium text-pink-400">
                {threat.score}%
              </span>
            </Link>
          ))}
        </div>
      </div>

      {/* Disclaimer */}
      <div className="p-4 sm:p-6 rounded-2xl bg-amber-500/10 border border-amber-500/25">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-amber-400 mt-0.5 flex-shrink-0" />
          <div>
            <h4 className="font-medium text-amber-400 mb-1">Important Notice</h4>
            <p className="text-xs sm:text-sm text-muted-foreground">
              PhishCatcher provides ML-based analysis and alerts only. We do not block or modify any emails. 
              Please review the findings carefully and take appropriate action based on your organization's security policies.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
