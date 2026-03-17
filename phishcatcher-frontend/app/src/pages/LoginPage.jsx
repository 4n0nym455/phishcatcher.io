import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Shield,
  Mail,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { authApi, setTokens } from "@/lib/api"; // Import API
import { oauthService } from "@/lib/oauthService";
import { usePageVisitTracker } from "@/hooks/usePageVisitTracker";
import LoadingOrb from "@/components/LoadingOrb";

export default function LoginPage({ onLogin }) {
  const navigate = useNavigate();
  const { visitedPages, markPageVisited, hasVisitedBothPages } = usePageVisitTracker();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      // Step 1: Login with credentials - Backend sends OTP
      const response = await fetch('http://localhost:8000/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ username: email, password }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Login failed');
      }

      const data = await response.json();
      
      // Store email for OTP verification page
      localStorage.setItem("phishcatcher_email", email);
      localStorage.setItem("phishcatcher_mfa_required", data.mfa_required);
      
      toast.info(data.message || "Verification code sent to your email");
      navigate("/verify-otp");
    } catch (error) {
      toast.error(error.message || "Failed to login");
      console.error('Login error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    console.log('🔐 Starting optimized Google OAuth login...');
    setIsLoading(true);
    
    try {
      // Use optimized popup OAuth flow
      const result = await oauthService.initiateGoogleOAuth();
      
      if (result.activation_required) {
        // New OAuth user - needs activation
        toast.info(result.message || "Please check your email for activation instructions");
        navigate('/activation-pending', { 
          state: { 
            email: result.email, 
            full_name: result.full_name,
            message: result.message 
          } 
        });
        return;
      }
      
      if (result.success) {
        // Store tokens and user data
        if (result.access_token) {
          setTokens(result);
        }
        
        // Store user info in localStorage for immediate use
        if (result.user) {
          localStorage.setItem('phishcatcher_email', result.user.email);
          localStorage.setItem('phishcatcher_role', result.user.role || 'user');
          localStorage.setItem('phishcatcher_name', result.user.full_name || '');
        }
        
        toast.success("Successfully logged in with Google!");
        navigate('/dashboard');
        if (onLogin) onLogin();
      } else if (result.requiresMFA) {
        navigate('/mfa-verification');
      } else {
        throw new Error(result.message || 'Authentication failed');
      }
      
    } catch (error) {
      console.error('❌ Google OAuth failed:', error);
      
      // User-friendly error messages
      if (error.message.includes('popup')) {
        toast.error('Please allow popups for this site and try again.');
      } else if (error.message.includes('timed out')) {
        toast.error('Authentication timed out. Please try again.');
      } else if (error.message.includes('Network')) {
        toast.error('Network error. Please check your connection and try again.');
      } else if (error.message.includes('Authorization code is invalid or has expired')) {
        toast.error('OAuth code expired. Please try signing in again.');
      } else {
        toast.error(error.message || 'Google authentication failed');
      }
    } finally {
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
          <div className="w-11 sm:w-12 h-11 sm:h-12 rounded-xl bg-white/90 flex items-center justify-center shadow-glow">
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

        {/* Login Card - 30% secondary */}
        <div className="glass-card-strong rounded-2xl sm:rounded-3xl p-6 sm:p-8">
          <div className="text-center mb-6 sm:mb-8">
            <h1 className="text-xl sm:text-2xl font-heading font-bold text-white mb-2">
              Welcome back
            </h1>
            <p className="text-sm text-muted-foreground">
              Sign in to access your security dashboard
            </p>
          </div>

          {/* Google Login */}
          <Button
            variant="outline"
            className="w-full h-11 sm:h-12 bg-transparent border-violet-500/25 hover:bg-violet-500/10 hover:border-violet-500/40 text-white rounded-xl mb-5 sm:mb-6 text-sm sm:text-base"
            onClick={handleGoogleLogin}
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

          {/* Email Login Form */}
          <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-5">
            <div className="space-y-2">
              <Label htmlFor="email" className="text-sm text-muted-foreground">
                Email address
              </Label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-4 sm:w-5 h-4 sm:h-5 text-violet-400" />
                <Input
                  id="email"
                  type="email"
                  placeholder="you@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="h-11 sm:h-12 pl-11 sm:pl-12 border-violet-500/25 rounded-xl font-bold placeholder:text-gray-400 focus:border-violet-500 focus:ring-violet-500/20 text-sm sm:text-base backdrop-blur-sm"
                  style={{backgroundColor: 'rgba(30, 41, 59, 0.5) !important', color: 'white !important'}}
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label
                htmlFor="password"
                className="text-sm text-muted-foreground"
              >
                Password
              </Label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-4 sm:w-5 h-4 sm:h-5 text-violet-400" />
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="h-11 sm:h-12 pl-11 sm:pl-12 pr-11 sm:pr-12 border-violet-500/25 rounded-xl font-bold placeholder:text-gray-400 focus:border-violet-500 focus:ring-violet-500/20 text-sm sm:text-base backdrop-blur-sm"
                  style={{backgroundColor: 'rgba(30, 41, 59, 0.5) !important', color: 'white !important'}}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-white transition-colors"
                >
                  {showPassword ? (
                    <EyeOff className="w-4 sm:w-5 h-4 sm:h-5" />
                  ) : (
                    <Eye className="w-4 sm:w-5 h-4 sm:h-5" />
                  )}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between text-xs sm:text-sm">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  className="w-4 h-4 rounded border-violet-500/30 bg-slate-800/50 text-violet-500 focus:ring-violet-500/20"
                />
                <span className="text-muted-foreground">Remember me</span>
              </label>
              <Link
                to="/forgot-password"
                className="text-violet-400 hover:text-violet-300 transition-colors"
              >
                Forgot password?
              </Link>
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
                  Sign in
                  <ArrowRight className="w-4 sm:w-5 h-4 sm:h-5 ml-2" />
                </>
              )}
            </Button>
          </form>

          <div className="mt-5 sm:mt-6 text-center text-xs sm:text-sm">
            <span className="text-muted-foreground">
              Don't have an account?{" "}
            </span>
            <Link
              to="/register"
              className="text-violet-400 hover:text-violet-300 font-medium transition-colors"
            >
              Create account
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