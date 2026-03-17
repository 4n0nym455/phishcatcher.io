import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { 
  Shield, 
  ArrowRight, 
  Link as LinkIcon,
  FileWarning,
  UserX,
  Lock,
  Brain,
  FileText,
  Globe,
  Zap,
  Check,
  Mail,
  AlertTriangle,
  Upload,
  Eye,
  FileSearch,
  TrendingUp,
  CheckCircle,
  XCircle,
  Info,
  LogOut,
  User
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { getTokens, clearTokens } from '@/lib/api';

gsap.registerPlugin(ScrollTrigger);

// Threat detection features
const threatFeatures = [
  { icon: LinkIcon, title: 'Phishing Links', description: 'Detect deceptive URLs and malicious redirects in email content.' },
  { icon: FileWarning, title: 'Malicious Attachments', description: 'Identify suspicious file types and embedded malware.' },
  { icon: UserX, title: 'Spoofed Senders', description: 'Detect display-name spoofing and lookalike domains.' },
  { icon: Lock, title: 'Credential Theft', description: 'Spot password-grabbing forms and credential harvesting attempts.' },
  { icon: Brain, title: 'Social Engineering', description: 'Flag urgency tactics, authority tricks, and manipulation patterns.' },
  { icon: FileText, title: 'Fake Invoices', description: 'Identify fraudulent payment requests and billing scams.' },
  { icon: Globe, title: 'Domain Impersonation', description: 'Compare DNS records and detect brand impersonation.' },
  { icon: Zap, title: 'Zero-Day Threats', description: 'Behavioral detection for unknown and emerging threats.' },
];

// How it works steps
const steps = [
  {
    number: '01',
    title: 'Upload Email',
    description: 'Upload .eml, .txt, or .msg files directly through our secure web interface. No installation required.',
    icon: Upload,
  },
  {
    number: '02',
    title: 'ML Analysis',
    description: 'Our machine learning models analyze headers, content, links, and attachments using multiple threat intelligence sources.',
    icon: FileSearch,
  },
  {
    number: '03',
    title: 'Get Report',
    description: 'Receive a comprehensive analysis report with risk scores, findings, and actionable recommendations.',
    icon: Eye,
  },
];

// Stats
const stats = [
  { value: '10M+', label: 'Emails Analyzed' },
  { value: '99.7%', label: 'Detection Rate' },
  { value: '18ms', label: 'Avg Analysis Time' },
  { value: '50+', label: 'Threat Indicators' },
];

export default function LandingPage() {
  const navigate = useNavigate();
  const heroRef = useRef(null);
  const orbRef = useRef(null);
  const headlineRef = useRef(null);
  const subheadlineRef = useRef(null);
  const ctaRef = useRef(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userData, setUserData] = useState(null);

  useEffect(() => {
    // Check authentication status
    const { accessToken } = getTokens();
    if (accessToken) {
      setIsAuthenticated(true);
      // Get user data from localStorage
      const email = localStorage.getItem('phishcatcher_email');
      const role = localStorage.getItem('phishcatcher_role');
      setUserData({ email, role });
    }
  }, []);

  const handleLogout = () => {
    clearTokens();
    setIsAuthenticated(false);
    setUserData(null);
    toast.success('Logged out successfully');
  };

  useEffect(() => {
    const ctx = gsap.context(() => {
      const tl = gsap.timeline({ defaults: { ease: 'power2.out' } });
      
      tl.fromTo(orbRef.current,
        { opacity: 0, scale: 0.85, y: 40 },
        { opacity: 1, scale: 1, y: 0, duration: 1 }
      )
      .fromTo(headlineRef.current,
        { opacity: 0, y: 24 },
        { opacity: 1, y: 0, duration: 0.8 },
        '-=0.6'
      )
      .fromTo(subheadlineRef.current,
        { opacity: 0, y: 16 },
        { opacity: 1, y: 0, duration: 0.6 },
        '-=0.4'
      )
      .fromTo(ctaRef.current,
        { opacity: 0, y: 16 },
        { opacity: 1, y: 0, duration: 0.6 },
        '-=0.3'
      );

      gsap.to(orbRef.current, {
        y: -10,
        duration: 4,
        repeat: -1,
        yoyo: true,
        ease: 'sine.inOut'
      });
    }, heroRef);

    return () => ctx.revert();
  }, []);

  const handleViewDemo = () => {
    toast.info('Demo coming soon!');
  };

  return (
    <div className="min-h-screen bg-primary-60">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-primary-60/80 backdrop-blur-xl border-b border-violet-500/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14 sm:h-16">
            <Link to="/" className="flex items-center gap-2 sm:gap-3">
              <div className="w-15 sm:w-13 h-15 sm:h-13 rounded-xl bg-primary-60 flex items-center justify-center shadow-glow">
                <img 
                  src="/phishcatcher.png"
                  alt="PhishCatcher Logo" 
                  className="w-12 h-12 object-contain"
                />
              </div>
              <span className="text-lg sm:text-xl font-heading font-bold text-white">PhishCatcher</span>
            </Link>
            
            <div className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-sm text-muted-foreground hover:text-white transition-colors">Features</a>
              <a href="#how-it-works" className="text-sm text-muted-foreground hover:text-white transition-colors">How it Works</a>
            </div>

            <div className="flex items-center gap-2 sm:gap-4">
              {isAuthenticated ? (
                <>
                  <div className="hidden sm:flex items-center gap-2 text-sm text-muted-foreground">
                    <User className="w-4 h-4" />
                    <span>{userData?.email}</span>
                  </div>
                  <Button 
                    variant="outline"
                    className="bg-transparent border-violet-500/25 hover:bg-violet-500/10 h-8 sm:h-10 text-xs sm:text-sm px-3 sm:px-4"
                    onClick={() => navigate('/dashboard')}
                  >
                    Dashboard
                  </Button>
                  <Button 
                    variant="outline"
                    className="bg-transparent border-violet-500/25 hover:bg-violet-500/10 h-8 sm:h-10 text-xs sm:text-sm px-3 sm:px-4"
                    onClick={handleLogout}
                  >
                    <LogOut className="w-4 h-4 mr-2" />
                    Logout
                  </Button>
                </>
              ) : (
                <>
                  <Link to="/login" className="hidden sm:block text-sm text-muted-foreground hover:text-white transition-colors">
                    Sign In
                  </Link>
                  <Button 
                    className="bg-violet-gradient hover:opacity-90 text-white shadow-glow h-8 sm:h-10 text-xs sm:text-sm px-3 sm:px-4"
                    asChild
                  >
                    <Link to="/register">Get Started</Link>
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section ref={heroRef} className="relative min-h-screen flex items-center justify-center pt-20 sm:pt-24 pb-16 overflow-hidden">
        {/* Background Effects */}
        <div className="absolute inset-0 bg-radial-spotlight" />
        <div className="absolute top-1/4 left-1/4 w-64 sm:w-96 h-64 sm:h-96 bg-violet-500/6 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-64 sm:w-96 h-64 sm:h-96 bg-violet-600/6 rounded-full blur-3xl" />
        
        {/* Grid Pattern */}
        <div 
          className="absolute inset-0 opacity-[0.02]"
          style={{
            backgroundImage: `linear-gradient(rgba(123, 97, 255, 0.5) 1px, transparent 1px),
                             linear-gradient(90deg, rgba(123, 97, 255, 0.5) 1px, transparent 1px)`,
            backgroundSize: '50px 50px'
          }}
        />

        <div className="relative z-10 text-center px-4 max-w-5xl mx-auto">
          {/* Orb */}
          <div className="mb-6 sm:mb-8">
            <img 
              ref={orbRef}
              src="/orb_glow_sphere.png" 
              alt="Security Orb" 
              className="w-32 h-32 sm:w-48 sm:h-48 md:w-56 md:h-56 mx-auto"
            />
          </div>

          {/* Headline */}
          <h1 
            ref={headlineRef}
            className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-heading font-bold text-white mb-4 sm:mb-6"
          >
            ML-Based Email{' '}
            <span className="text-gradient">Phishing Detection</span>
          </h1>

          {/* Subheadline */}
          <p 
            ref={subheadlineRef}
            className="text-base sm:text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-6 sm:mb-8 px-4"
          >
            Upload email files and get instant machine learning-powered analysis. 
            Detect phishing, malware, and social engineering with comprehensive threat reports.
          </p>

          {/* CTAs */}
          <div ref={ctaRef} className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 mb-6 sm:mb-8">
            <Button 
              size="lg"
              className="bg-violet-gradient hover:opacity-90 text-white rounded-xl px-6 sm:px-8 shadow-glow w-full sm:w-auto h-11 sm:h-12"
              asChild
            >
              <Link to="/register">
                Start analyzing free
                <ArrowRight className="w-4 sm:w-5 h-4 sm:h-5 ml-2" />
              </Link>
            </Button>
            <Button 
              size="lg"
              variant="outline"
              className="bg-transparent border-violet-500/25 hover:bg-violet-500/10 text-white rounded-xl px-6 sm:px-8 w-full sm:w-auto h-11 sm:h-12"
              onClick={handleViewDemo}
            >
              View demo
            </Button>
          </div>

          <p className="text-xs sm:text-sm text-muted-foreground">
            No credit card required • Free tier available
          </p>

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-8 mt-12 sm:mt-16 max-w-3xl mx-auto">
            {stats.map((stat, index) => (
              <div key={index} className="text-center">
                <p className="text-2xl sm:text-3xl md:text-4xl font-mono font-bold text-white">{stat.value}</p>
                <p className="text-xs sm:text-sm text-muted-foreground mt-1">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="relative py-20 sm:py-32 overflow-hidden">
        <div className="absolute inset-0 bg-radial-violet" />
        
        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12 sm:mb-16">
            <Badge className="bg-violet-500/15 text-violet-400 border-violet-500/25 mb-3 sm:mb-4">
              Comprehensive Detection
            </Badge>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-heading font-bold text-white mb-3 sm:mb-4">
              Eight Layers of Threat Detection
            </h2>
            <p className="text-base sm:text-lg text-muted-foreground max-w-2xl mx-auto px-4">
              Our ML models analyze multiple threat vectors to give you a complete security picture
            </p>
          </div>

          {/* Features Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
            {threatFeatures.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <div 
                  key={index}
                  className="glass-card rounded-2xl p-5 sm:p-6 hover:border-violet-500/30 transition-all"
                >
                  <div className="w-10 sm:w-12 h-10 sm:h-12 rounded-xl bg-violet-500/15 flex items-center justify-center mb-3 sm:mb-4">
                    <Icon className="w-5 sm:w-6 h-5 sm:h-6 text-violet-400" />
                  </div>
                  <h3 className="text-base sm:text-lg font-heading font-semibold text-white mb-1.5 sm:mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-xs sm:text-sm text-muted-foreground">
                    {feature.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="relative py-20 sm:py-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12 sm:mb-16">
            <Badge className="bg-violet-500/15 text-violet-400 border-violet-500/25 mb-3 sm:mb-4">
              How It Works
            </Badge>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-heading font-bold text-white mb-3 sm:mb-4">
              Analyze in Three Simple Steps
            </h2>
            <p className="text-base sm:text-lg text-muted-foreground max-w-2xl mx-auto px-4">
              No installation required. Upload and analyze directly from your browser.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8">
            {steps.map((step, index) => {
              const Icon = step.icon;
              return (
                <div 
                  key={index}
                  className="glass-card rounded-2xl sm:rounded-3xl p-6 sm:p-8 hover:border-violet-500/30 transition-all text-center"
                >
                  <div className="w-14 sm:w-16 h-14 sm:h-16 rounded-2xl bg-violet-500/15 flex items-center justify-center mx-auto mb-4 sm:mb-6">
                    <Icon className="w-7 sm:w-8 h-7 sm:h-8 text-violet-400" />
                  </div>
                  <span className="text-3xl sm:text-4xl font-mono font-bold text-violet-500/30">
                    {step.number}
                  </span>
                  <h3 className="text-lg sm:text-xl font-heading font-semibold text-white mt-3 sm:mt-4 mb-2 sm:mb-3">
                    {step.title}
                  </h3>
                  <p className="text-sm sm:text-base text-muted-foreground">
                    {step.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Analysis Preview Section */}
      <section className="relative py-20 sm:py-32 overflow-hidden">
        <div className="absolute inset-0 bg-radial-violet" />
        
        <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-10 sm:mb-12">
            <Badge className="bg-violet-500/15 text-violet-400 border-violet-500/25 mb-3 sm:mb-4">
              Sample Report
            </Badge>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-heading font-bold text-white mb-3 sm:mb-4">
              Comprehensive Analysis Reports
            </h2>
            <p className="text-base sm:text-lg text-muted-foreground max-w-2xl mx-auto px-4">
              Get detailed insights with risk scores, threat indicators, and actionable recommendations
            </p>
          </div>

          {/* Sample Report Card */}
          <div className="glass-card-strong rounded-2xl sm:rounded-3xl p-5 sm:p-8">
            <div className="flex flex-col lg:flex-row gap-6 sm:gap-8">
              {/* Left: Email Info */}
              <div className="flex-1">
                <div className="flex items-start gap-3 sm:gap-4 mb-5 sm:mb-6">
                  <div className="w-10 sm:w-12 h-10 sm:h-12 rounded-xl bg-pink-500/15 flex items-center justify-center flex-shrink-0">
                    <Mail className="w-5 sm:w-6 h-5 sm:h-6 text-pink-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-base sm:text-lg font-heading font-semibold text-white mb-0.5 sm:mb-1">
                      Reset your password immediately
                    </h3>
                    <p className="text-xs sm:text-sm text-muted-foreground truncate">
                      security-notice@service-alerts.com
                    </p>
                  </div>
                </div>

                {/* Risk Score */}
                <div className="flex items-center gap-3 sm:gap-4 mb-5 sm:mb-6">
                  <div className="w-16 sm:w-20 h-16 sm:h-20 rounded-2xl bg-pink-500/15 border-2 border-pink-500/25 flex flex-col items-center justify-center">
                    <span className="text-xl sm:text-2xl font-mono font-bold text-pink-400">92%</span>
                    <span className="text-[10px] sm:text-xs text-pink-400">Risk</span>
                  </div>
                  <div>
                    <Badge className="status-danger mb-1.5 sm:mb-2 text-xs">High Risk</Badge>
                    <p className="text-xs sm:text-sm text-muted-foreground">
                      Multiple threat indicators detected
                    </p>
                  </div>
                </div>

                {/* Findings */}
                <div className="space-y-2 sm:space-y-3">
                  <div className="flex items-start gap-2 sm:gap-3">
                    <XCircle className="w-4 sm:w-5 h-4 sm:h-5 text-pink-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm text-white">Suspicious Domain Age</p>
                      <p className="text-xs text-muted-foreground">Domain registered 3 days ago</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2 sm:gap-3">
                    <XCircle className="w-4 sm:w-5 h-4 sm:h-5 text-pink-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm text-white">Suspicious Link Detected</p>
                      <p className="text-xs text-muted-foreground">Link points to known phishing domain</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2 sm:gap-3">
                    <AlertTriangle className="w-4 sm:w-5 h-4 sm:h-5 text-amber-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm text-white">Urgency Tactics</p>
                      <p className="text-xs text-muted-foreground">Pressure language detected</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right: Chart Placeholder */}
              <div className="lg:w-56 xl:w-64 flex items-center justify-center">
                <div className="relative w-40 h-40 sm:w-48 sm:h-48">
                  <svg className="w-full h-full -rotate-90">
                    <circle
                      cx="50%"
                      cy="50%"
                      r="42%"
                      fill="none"
                      stroke="rgba(123, 97, 255, 0.15)"
                      strokeWidth="10"
                    />
                    <circle
                      cx="50%"
                      cy="50%"
                      r="42%"
                      fill="none"
                      stroke="#FF4D8D"
                      strokeWidth="10"
                      strokeLinecap="round"
                      strokeDasharray={`${2 * Math.PI * 42 * 0.92}% ${2 * Math.PI * 42}%`}
                      style={{ transformOrigin: 'center' }}
                    />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-2xl sm:text-3xl font-mono font-bold text-pink-400">92%</span>
                    <span className="text-xs text-pink-400">Threat Score</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative py-20 sm:py-32 overflow-hidden">
        <div className="absolute inset-0 bg-radial-violet" />
        
        <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="glass-card-strong rounded-2xl sm:rounded-3xl p-8 sm:p-12 text-center">
            <img 
              src="/shield_icon.png" 
              alt="Shield" 
              className="w-16 h-16 sm:w-24 sm:h-24 mx-auto mb-5 sm:mb-8"
            />
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-heading font-bold text-white mb-3 sm:mb-4">
              {isAuthenticated ? 'Welcome Back to PhishCatcher' : 'Start Protecting Your Inbox Today'}
            </h2>
            <p className="text-base sm:text-lg text-muted-foreground mb-6 sm:mb-8 max-w-xl mx-auto px-4">
              {isAuthenticated 
                ? `Ready to continue analyzing emails, ${userData?.email}?`
                : 'Join thousands of users who trust PhishCatcher for email security analysis'
              }
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4">
              {isAuthenticated ? (
                <>
                  <Button 
                    size="lg"
                    className="bg-violet-gradient hover:opacity-90 text-white rounded-xl px-6 sm:px-8 shadow-glow w-full sm:w-auto h-11 sm:h-12"
                    onClick={() => navigate('/dashboard')}
                  >
                    Go to Dashboard
                    <ArrowRight className="w-4 sm:w-5 h-4 sm:h-5 ml-2" />
                  </Button>
                  <Button 
                    variant="outline"
                    size="lg"
                    className="bg-transparent border-violet-500/25 hover:bg-violet-500/10 text-white rounded-xl px-6 sm:px-8 w-full sm:w-auto h-11 sm:h-12"
                    onClick={handleLogout}
                  >
                    <LogOut className="w-4 sm:w-5 h-4 sm:h-5 mr-2" />
                    Logout
                  </Button>
                </>
              ) : (
                <Button 
                  size="lg"
                  className="bg-violet-gradient hover:opacity-90 text-white rounded-xl px-6 sm:px-8 shadow-glow w-full sm:w-auto h-11 sm:h-12"
                  asChild
                >
                  <Link to="/register">
                    Get started free
                    <ArrowRight className="w-4 sm:w-5 h-4 sm:h-5 ml-2" />
                  </Link>
                </Button>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-violet-500/15 py-12 sm:py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 sm:gap-8 mb-10 sm:mb-12">
            <div>
              <h4 className="font-medium text-white mb-3 sm:mb-4">Product</h4>
              <ul className="space-y-2">
                <li><Link to="/dashboard" className="text-xs sm:text-sm text-muted-foreground hover:text-white transition-colors">Dashboard</Link></li>
                <li><a href="#" className="text-xs sm:text-sm text-muted-foreground hover:text-white transition-colors">API</a></li>
                <li><a href="#" className="text-xs sm:text-sm text-muted-foreground hover:text-white transition-colors">Status</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-white mb-3 sm:mb-4">Resources</h4>
              <ul className="space-y-2">
                <li><a href="#" className="text-xs sm:text-sm text-muted-foreground hover:text-white transition-colors">Docs</a></li>
                <li><a href="#" className="text-xs sm:text-sm text-muted-foreground hover:text-white transition-colors">Blog</a></li>
                <li><a href="#" className="text-xs sm:text-sm text-muted-foreground hover:text-white transition-colors">Support</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-white mb-3 sm:mb-4">Company</h4>
              <ul className="space-y-2">
                <li><a href="#" className="text-xs sm:text-sm text-muted-foreground hover:text-white transition-colors">About</a></li>
                <li><a href="#" className="text-xs sm:text-sm text-muted-foreground hover:text-white transition-colors">Careers</a></li>
                <li><a href="#" className="text-xs sm:text-sm text-muted-foreground hover:text-white transition-colors">Contact</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-white mb-3 sm:mb-4">Legal</h4>
              <ul className="space-y-2">
                <li><Link to="/privacy" className="text-xs sm:text-sm text-muted-foreground hover:text-white transition-colors">Privacy Policy</Link></li>
                <li><Link to="/terms" className="text-xs sm:text-sm text-muted-foreground hover:text-white transition-colors">Terms of Service</Link></li>
              </ul>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between pt-6 sm:pt-8 border-t border-violet-500/15 gap-4">
            <div className="flex items-center gap-2 sm:gap-3">
              <div className="w-12 h-12 rounded-lg bg-primary-60/70 flex items-center justify-center">
                <img 
                  src="/phishcatcher.png" 
                  alt="PhishCatcher Logo" 
                  className="w-11 h-11 object-contain"
                />
              </div>
              <span className="font-heading font-bold text-white">PhishCatcher</span>
            </div>
            <p className="text-xs text-muted-foreground text-center sm:text-right">
              © 2026 PhishCatcher. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
