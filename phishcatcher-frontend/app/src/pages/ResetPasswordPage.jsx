import { useState, useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Shield, Lock, Eye, EyeOff, CheckCircle, ArrowRight, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { authApi } from "@/lib/api";

export default function ResetPasswordPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [isValidToken, setIsValidToken] = useState(true);
  const [passwordStrength, setPasswordStrength] = useState({ score: 0, message: "" });

  useEffect(() => {
    if (!token) {
      setIsValidToken(false);
      toast.error("Invalid or missing reset token");
    }
  }, [token]);

  const validatePassword = (pass) => {
    const minLength = 8;
    const hasUpperCase = /[A-Z]/.test(pass);
    const hasLowerCase = /[a-z]/.test(pass);
    const hasNumbers = /\d/.test(pass);
    const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(pass);

    let score = 0;
    const requirements = [];

    if (pass.length >= minLength) {
      score += 1;
      requirements.push("✓ At least 8 characters");
    } else {
      requirements.push("✗ At least 8 characters");
    }

    if (hasUpperCase) {
      score += 1;
      requirements.push("✓ One uppercase letter");
    } else {
      requirements.push("✗ One uppercase letter");
    }

    if (hasLowerCase) {
      score += 1;
      requirements.push("✓ One lowercase letter");
    } else {
      requirements.push("✗ One lowercase letter");
    }

    if (hasNumbers) {
      score += 1;
      requirements.push("✓ One number");
    } else {
      requirements.push("✗ One number");
    }

    if (hasSpecialChar) {
      score += 1;
      requirements.push("✓ One special character");
    } else {
      requirements.push("✗ One special character");
    }

    const strength = {
      score,
      message: score === 5 ? "Strong password" : score >= 3 ? "Medium password" : "Weak password",
      requirements
    };

    setPasswordStrength(strength);

    if (score < 5) return "Password does not meet all requirements";
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!token) {
      toast.error("Invalid reset token");
      return;
    }

    if (password !== confirmPassword) {
      toast.error("Passwords do not match");
      return;
    }

    const validationError = validatePassword(password);
    if (validationError) {
      toast.error(validationError);
      return;
    }

    setIsLoading(true);

    try {
      await authApi.resetPassword(token, password);
      setIsSuccess(true);
      toast.success("Password reset successfully! A notification has been sent to your email.", {
        duration: 5000,
        description: "You can now log in with your new password."
      });
    } catch (error) {
      let errorMessage = "Failed to reset password. The link may have expired.";
      
      if (error.message) {
        if (error.message.includes("Invalid or expired reset token")) {
          errorMessage = "This reset link has expired or is invalid. Please request a new one.";
        } else if (error.message.includes("Reset token already used")) {
          errorMessage = "This reset link has already been used. Please request a new one.";
        } else if (error.message.includes("password")) {
          errorMessage = error.message; // This will include password strength or reuse errors
        } else {
          errorMessage = error.message;
        }
      }
      
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isValidToken) {
    return (
      <div className="min-h-screen bg-primary-60 flex items-center justify-center p-4 relative overflow-hidden">
        <div className="absolute inset-0 bg-radial-spotlight opacity-50" />
        
        <div className="w-full max-w-md relative z-10">
          <div className="glass-card-strong rounded-2xl sm:rounded-3xl p-6 sm:p-8 text-center">
            <div className="w-16 h-16 rounded-full bg-red-500/20 flex items-center justify-center mx-auto mb-4">
              <XCircle className="w-8 h-8 text-red-400" />
            </div>
            <h1 className="text-xl sm:text-2xl font-heading font-bold text-white mb-2">
              Invalid Link
            </h1>
            <p className="text-sm text-muted-foreground mb-6">
              This password reset link is invalid or has expired.
            </p>
            <Button
              onClick={() => navigate("/forgot-password")}
              className="w-full h-11 sm:h-12 bg-violet-gradient hover:opacity-90 text-white rounded-xl font-medium shadow-glow"
            >
              Request new link
              <ArrowRight className="w-4 sm:w-5 h-4 sm:h-5 ml-2" />
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (isSuccess) {
    return (
      <div className="min-h-screen bg-primary-60 flex items-center justify-center p-4 relative overflow-hidden">
        <div className="absolute inset-0 bg-radial-spotlight opacity-50" />
        
        <div className="w-full max-w-md relative z-10">
          <div className="glass-card-strong rounded-2xl sm:rounded-3xl p-6 sm:p-8 text-center">
            <div className="w-16 h-16 rounded-full bg-teal-500/20 flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="w-8 h-8 text-teal-400" />
            </div>
            <h1 className="text-xl sm:text-2xl font-heading font-bold text-white mb-2">
              Password reset!
            </h1>
            <p className="text-sm text-muted-foreground mb-6">
              Your password has been reset successfully. You can now log in with your new password.
            </p>
            <Button
              onClick={() => navigate("/login")}
              className="w-full h-11 sm:h-12 bg-violet-gradient hover:opacity-90 text-white rounded-xl font-medium shadow-glow"
            >
              Go to login
              <ArrowRight className="w-4 sm:w-5 h-4 sm:h-5 ml-2" />
            </Button>
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

  return (
    <div className="min-h-screen bg-primary-60 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background Effects */}
      <div className="absolute inset-0 bg-radial-spotlight opacity-50" />
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

        {/* Reset Password Card */}
        <div className="glass-card-strong rounded-2xl sm:rounded-3xl p-6 sm:p-8">
          <div className="text-center mb-6 sm:mb-8">
            <h1 className="text-xl sm:text-2xl font-heading font-bold text-white mb-2">
              Reset password
            </h1>
            <p className="text-sm text-muted-foreground">
              Create a new password for your account
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-5">
            <div className="space-y-2">
              <Label htmlFor="password" className="text-sm text-muted-foreground">
                New password
              </Label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-4 sm:w-5 h-4 sm:h-5 text-violet-400" />
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="h-11 sm:h-12 pl-11 sm:pl-12 pr-11 sm:pr-12 bg-slate-800/50 border-violet-500/25 rounded-xl text-white font-bold placeholder:text-gray-400 focus:border-violet-500 focus:ring-violet-500/20 text-sm sm:text-base backdrop-blur-sm"
                  required
                  minLength={8}
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
              <p className="text-xs text-muted-foreground">
                {passwordStrength.score === 5 ? (
                  <span className="text-green-400">Strong password</span>
                ) : passwordStrength.score >= 3 ? (
                  <span className="text-yellow-400">Medium password</span>
                ) : (
                  <span className="text-red-400">Weak password</span>
                )}
              </p>
              <div className="mt-2 space-y-1">
                {passwordStrength.requirements?.map((req, index) => (
                  <div key={index} className="text-xs text-muted-foreground">
                    {req}
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirmPassword" className="text-sm text-muted-foreground">
                Confirm new password
              </Label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-4 sm:w-5 h-4 sm:h-5 text-violet-400" />
                <Input
                  id="confirmPassword"
                  type={showConfirmPassword ? "text" : "password"}
                  placeholder="••••••••"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="h-11 sm:h-12 pl-11 sm:pl-12 pr-11 sm:pr-12 bg-slate-800/50 border-violet-500/25 rounded-xl text-white font-bold placeholder:text-gray-400 focus:border-violet-500 focus:ring-violet-500/20 text-sm sm:text-base backdrop-blur-sm"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-white transition-colors"
                >
                  {showConfirmPassword ? (
                    <EyeOff className="w-4 sm:w-5 h-4 sm:h-5" />
                  ) : (
                    <Eye className="w-4 sm:w-5 h-4 sm:h-5" />
                  )}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              className="w-full h-11 sm:h-12 bg-violet-gradient hover:opacity-90 text-white rounded-xl font-medium shadow-glow text-sm sm:text-base"
              disabled={isLoading}
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  Reset password
                  <ArrowRight className="w-4 sm:w-5 h-4 sm:h-5 ml-2" />
                </>
              )}
            </Button>
          </form>

          <div className="mt-5 sm:mt-6 text-center text-xs sm:text-sm">
            <span className="text-muted-foreground">Remember your password? </span>
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