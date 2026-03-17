import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Eye, EyeOff, Shield, Building2, Mail, Lock, User, Check, ExternalLink } from "lucide-react";
import { authApi, setTokens } from "@/lib/api"; 
import { usePageVisitTracker } from "@/hooks/usePageVisitTracker";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import LoadingOrb from "@/components/LoadingOrb";

export default function RegisterPage({ onLogin }) {
  const navigate = useNavigate();
   const { visitedPages, markPageVisited, hasVisitedBothPages } = usePageVisitTracker();
  
  // Temporarily use dummy values for testing
  // const visitedPages = { terms: true , privacy: true };
  // const markPageVisited = () => {};
  // const hasVisitedBothPages = true;
  const [formData, setFormData] = useState({
    fullName: "",
    email: "",
    company: "",
    password: "",
    confirmPassword: "",
    acceptTermsAndPrivacy: false,
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (formData.password !== formData.confirmPassword) {
      toast.error("Passwords do not match");
      return;
    }

    if (!formData.acceptTermsAndPrivacy) {
      toast.error("Please accept the Terms & Conditions and Privacy Policy");
      return;
    }

    if (!hasVisitedBothPages) {
      toast.error("Please read the Terms & Conditions and Privacy Policy before accepting");
      return;
    }

    setIsLoading(true);

    try {
      // Register user with backend
      const userData = await authApi.register({
        fullName: formData.fullName,
        email: formData.email,
        company: formData.company,
        password: formData.password,
        acceptTermsAndPrivacy: formData.acceptTermsAndPrivacy,
      });

      // Registration successful - redirect to login for OTP verification
      toast.success("Account created! Please log in to verify your email");
      navigate("/login");
    } catch (error) {
      toast.error(error.message || "Registration failed");
      console.error('Registration error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleSignup = async () => {
    setIsLoading(true);
    try {
      // Get Google OAuth URL from backend
      const data = await authApi.getGoogleAuthUrl();
      
      // Store state for verification
      localStorage.setItem('oauth_state', data.state);
      
      // Open Google OAuth in new window
      const popup = window.open(
        data.auth_url, 
        'google-auth', 
        'width=500,height=600,scrollbars=yes,resizable=yes,toolbar=no,menubar=no'
      );
      
      // Listen for messages from popup
      const messageHandler = async (event) => {
        // Verify message origin for security
        if (event.origin !== window.location.origin) return;
        
        if (event.data === 'google-auth-success') {
          window.removeEventListener('message', messageHandler);
          popup?.close();
          setIsLoading(false);
          toast.success("Successfully signed up with Google!");
          navigate('/dashboard');
        } else if (event.data === 'google-auth-error') {
          window.removeEventListener('message', messageHandler);
          popup?.close();
          setIsLoading(false);
          toast.error("Google authentication failed");
        }
      };
      
      window.addEventListener('message', messageHandler);
      
      // Fallback: Check popup status periodically
      const checkPopup = setInterval(() => {
        if (popup?.closed) {
          clearInterval(checkPopup);
          window.removeEventListener('message', messageHandler);
          setIsLoading(false);
        }
      }, 1000);
      
    } catch (error) {
      toast.error("Failed to initiate Google signup");
      console.error('Google signup error:', error);
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background Effects - 60% primary */}
      <div className="absolute inset-0 opacity-50" style={{
        background: 'radial-gradient(circle at 50% 40%, rgba(123, 97, 255, 0.08) 0%, #0f172a 70%)'
      }} />
      <div className="absolute top-1/4 left-1/4 w-72 sm:w-96 h-72 sm:h-96 bg-violet-500/8 rounded-full blur-3xl" />
      <div className="absolute bottom-1/4 right-1/4 w-72 sm:w-96 h-72 sm:h-96 bg-violet-600/8 rounded-full blur-3xl" />

      {/* Grid Pattern */}
      <div
        className="absolute inset-0 opacity-[0.02]"
        style={{
          backgroundImage: `linear-gradient(rgba(123, 97, 255, 0.5) 1px, transparent 1px),
                           linear-gradient(90deg, rgba(123, 97, 255, 0.5) 1px, transparent 1px)`,
          backgroundSize: "50px 50px",
        }}
      />

      <div className="w-full max-w-md relative z-10">
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-6 sm:mb-8">
          <div className="w-10 sm:w-12 h-10 sm:h-12 rounded-xl bg-white/90 flex items-center justify-center shadow-glow">
            <img
              src="/phishcatcher.png"
              alt="PhishCatcher Logo"
              className="w-8 h-8 object-contain"
            />
          </div>
          <span className="text-xl sm:text-2xl font-heading font-bold text-white">
            PhishCatcher
          </span>
        </div>

        {/* Register Card */}
        <div className="glass-card-strong rounded-2xl sm:rounded-3xl p-6 sm:p-8">
          <div className="text-center mb-6 sm:mb-8">
            <h1 className="text-xl sm:text-2xl font-heading font-bold text-white mb-2">
              Create your account
            </h1>
            <p className="text-sm text-muted-foreground">
              Start analyzing emails for threats
            </p>
          </div>

          {/* Google Signup */}
          <Button
            variant="outline"
            className="w-full h-11 sm:h-12 bg-transparent border-violet-500/25 hover:bg-violet-500/10 hover:border-violet-500/40 text-white rounded-xl mb-5 sm:mb-6 text-sm sm:text-base"
            onClick={handleGoogleSignup}
            disabled={isLoading}
          >
            <svg className="w-4 sm:w-5 h-4 sm:h-5 mr-2" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continue with Google
          </Button>

          <div className="flex items-center gap-4 mb-5 sm:mb-6">
            <Separator className="flex-1 bg-violet-500/15" />
            <span className="text-xs text-muted-foreground uppercase tracking-wider">
              or
            </span>
            <Separator className="flex-1 bg-violet-500/15" />
          </div>

          {/* Registration Form */}
          <form onSubmit={handleSubmit} className="space-y-3 sm:space-y-4">
            <div className="space-y-2">
              <Label
                htmlFor="fullName"
                className="text-sm text-muted-foreground"
              >
                Full name
              </Label>
              <div className="relative">
                <User className="absolute left-4 top-1/2 -translate-y-1/2 w-4 sm:w-5 h-4 sm:h-5 text-violet-400" />
                <Input
                  id="fullName"
                  name="fullName"
                  type="text"
                  placeholder="John Doe"
                  value={formData.fullName}
                  onChange={handleChange}
                  className="h-11 sm:h-12 pl-11 sm:pl-12 bg-slate-800/50 border-violet-500/25 rounded-xl text-white font-bold placeholder:text-gray-400 focus:border-violet-500 focus:ring-violet-500/20 text-sm sm:text-base backdrop-blur-sm"
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="email" className="text-sm text-muted-foreground">
                Email address
              </Label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-4 sm:w-5 h-4 sm:h-5 text-violet-400" />
                <Input
                  id="email"
                  name="email"
                  type="email"
                  placeholder="you@company.com"
                  value={formData.email}
                  onChange={handleChange}
                  className="h-11 sm:h-12 pl-11 sm:pl-12 bg-slate-800/50 border-violet-500/25 rounded-xl text-white font-bold placeholder:text-gray-400 focus:border-violet-500 focus:ring-violet-500/20 text-sm sm:text-base backdrop-blur-sm"
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="company" className="text-sm text-muted-foreground">
                Company (optional)
              </Label>
              <div className="relative">
                <Building2 className="absolute left-4 top-1/2 -translate-y-1/2 w-4 sm:w-5 h-4 sm:h-5 text-violet-400" />
                <Input
                  id="company"
                  name="company"
                  type="text"
                  placeholder="Acme Inc."
                  value={formData.company}
                  onChange={handleChange}
                  className="h-11 sm:h-12 pl-11 sm:pl-12 bg-slate-800/50 border-violet-500/25 rounded-xl text-white font-bold placeholder:text-gray-400 focus:border-violet-500 focus:ring-violet-500/20 text-sm sm:text-base backdrop-blur-sm"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-sm text-muted-foreground">
                Password
              </Label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-4 sm:w-5 h-4 sm:h-5 text-violet-400" />
                <Input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••••"
                  value={formData.password}
                  onChange={handleChange}
                  className="h-11 sm:h-12 pl-11 sm:pl-12 pr-11 sm:pr-12 bg-slate-800/50 border-violet-500/25 rounded-xl text-white font-bold placeholder:text-gray-400 focus:border-violet-500 focus:ring-violet-500/20 text-sm sm:text-base backdrop-blur-sm"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-white transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 sm:w-5 h-4 sm:h-5" /> : <Eye className="w-4 sm:w-5 h-4 sm:h-5" />}
                </button>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirmPassword" className="text-sm text-muted-foreground">
                Confirm Password
              </Label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-4 sm:w-5 h-4 sm:h-5 text-violet-400" />
                <Input
                  id="confirmPassword"
                  name="confirmPassword"
                  type={showConfirmPassword ? "text" : "password"}
                  placeholder="•••••••••"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  className="h-11 sm:h-12 pl-11 sm:pl-12 pr-11 sm:pr-12 bg-slate-800/50 border-violet-500/25 rounded-xl text-white font-bold placeholder:text-gray-400 focus:border-violet-500 focus:ring-violet-500/20 text-sm sm:text-base backdrop-blur-sm"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-white transition-colors"
                >
                  {showConfirmPassword ? <EyeOff className="w-4 sm:w-5 h-4 sm:h-5" /> : <Eye className="w-4 sm:w-5 h-4 sm:h-5" />}
                </button>
              </div>
            </div>

            <div className="space-y-3">
              {/* Terms & Conditions Link */}
              <div className="flex items-center justify-between text-xs sm:text-sm">
                <span className="text-muted-foreground">
                  Terms & Conditions
                </span>
                <Link
                  to="/terms"
                  onClick={() => markPageVisited('terms')}
                  className={`flex items-center gap-1 ${
                    visitedPages.terms 
                      ? 'text-green-400 hover:text-green-300' 
                      : 'text-violet-400 hover:text-violet-300'
                  }`}
                >
                  {visitedPages.terms ? (
                    <>
                      <Check className="w-3 h-3 sm:w-4 sm:h-4" />
                      Read
                    </>
                  ) : (
                    <>
                      <ExternalLink className="w-3 h-3 sm:w-4 sm:h-4" />
                      Read
                    </>
                  )}
                </Link>
              </div>

              {/* Privacy Policy Link */}
              <div className="flex items-center justify-between text-xs sm:text-sm">
                <span className="text-muted-foreground">
                  Privacy Policy
                </span>
                <Link
                  to="/privacy"
                  onClick={() => markPageVisited('privacy')}
                  className={`flex items-center gap-1 ${
                    visitedPages.privacy 
                      ? 'text-green-400 hover:text-green-300' 
                      : 'text-violet-400 hover:text-violet-300'
                  }`}
                >
                  {visitedPages.privacy ? (
                    <>
                      <Check className="w-3 h-3 sm:w-4 sm:h-4" />
                      Read
                    </>
                  ) : (
                    <>
                      <ExternalLink className="w-3 h-3 sm:w-4 sm:h-4" />
                      Read
                    </>
                  )}
                </Link>
              </div>

              {/* Agreement Checkbox */}
              <label className={`flex items-start gap-3 cursor-pointer ${
                !hasVisitedBothPages ? 'opacity-50 cursor-not-allowed' : ''
              }`}>
                <input
                  type="checkbox"
                  name="acceptTermsAndPrivacy"
                  checked={formData.acceptTermsAndPrivacy}
                  onChange={handleChange}
                  disabled={!hasVisitedBothPages}
                  className="w-4 h-4 mt-0.5 rounded border-violet-500/30 bg-slate-800/50 text-violet-500 focus:ring-violet-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <span className="text-xs sm:text-sm text-muted-foreground">
                  I have read and agree to the Terms & Conditions and Privacy Policy
                  {!hasVisitedBothPages && (
                    <span className="block text-amber-400 mt-1">
                      Please read both documents before accepting
                    </span>
                  )}
                </span>
              </label>
            </div>

            <Button
              type="submit"
              className="w-full h-11 sm:h-12 bg-violet-gradient hover:opacity-90 text-white rounded-xl font-medium shadow-glow text-sm sm:text-base"
              disabled={isLoading}
            >
              {isLoading ? (
                <LoadingOrb size="mini" text="" />
              ) : (
                <>
                  <Shield className="w-4 sm:w-5 h-4 sm:h-5 mr-2" />
                  Create Account
                </>
              )}
            </Button>
          </form>

          <div className="mt-5 sm:mt-6 text-center text-xs sm:text-sm">
            <span className="text-muted-foreground">
              Already have an account?{" "}
            </span>
            <Link
              to="/login"
              className="text-violet-400 hover:text-violet-300 font-medium transition-colors"
            >
              Sign in
            </Link>
          </div>
        </div>

        {/* Security Badge */}
        <div className="flex items-center justify-center gap-2 mt-6 sm:mt-8 text-xs text-muted-foreground">
          <Shield className="w-4 h-4 text-teal-400" />
          <span>Secured by LYNX</span>
        </div>
      </div>
    </div>
  );
}