import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Shield, Mail, ArrowLeft, CheckCircle, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { authApi } from "@/lib/api";

export default function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await authApi.forgotPassword(email);
      setIsSubmitted(true);
      toast.success("If the email exists, a reset link has been sent");
    } catch (error) {
      // Still show success to prevent email enumeration
      setIsSubmitted(true);
      toast.success("If the email exists, a reset link has been sent");
    } finally {
      setIsLoading(false);
    }
  };

  if (isSubmitted) {
    return (
      <div className="min-h-screen bg-primary-60 flex items-center justify-center p-4 relative overflow-hidden">
        {/* Background Effects */}
        <div className="absolute inset-0 bg-radial-spotlight opacity-50" />
        <div className="absolute top-1/4 left-1/4 w-72 sm:w-96 h-72 sm:h-96 bg-violet-500/8 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-72 sm:w-96 h-72 sm:h-96 bg-violet-600/8 rounded-full blur-3xl" />

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

          <div className="glass-card-strong rounded-2xl sm:rounded-3xl p-6 sm:p-8 text-center">
            <div className="w-16 h-16 rounded-full bg-teal-500/20 flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="w-8 h-8 text-teal-400" />
            </div>
            <h1 className="text-xl sm:text-2xl font-heading font-bold text-white mb-2">
              Check your email
            </h1>
            <p className="text-sm text-muted-foreground mb-6">
              We've sent a password reset link to<br />
              <span className="text-violet-400 font-medium">{email}</span>
            </p>
            <p className="text-xs text-muted-foreground mb-6">
              The link will expire in 1 hour. If you don't see the email, check your spam folder.
            </p>
            <Button
              onClick={() => navigate("/login")}
              className="w-full h-11 sm:h-12 bg-violet-gradient hover:opacity-90 text-white rounded-xl font-medium shadow-glow"
            >
              Back to login
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
        {/* Back Button */}
        <button
          onClick={() => navigate("/login")}
          className="flex items-center gap-2 text-muted-foreground hover:text-white mb-6 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to login
        </button>

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

        {/* Forgot Password Card */}
        <div className="glass-card-strong rounded-2xl sm:rounded-3xl p-6 sm:p-8">
          <div className="text-center mb-6 sm:mb-8">
            <h1 className="text-xl sm:text-2xl font-heading font-bold text-white mb-2">
              Forgot password?
            </h1>
            <p className="text-sm text-muted-foreground">
              Enter your email and we'll send you a reset link
            </p>
          </div>

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
                  className="h-11 sm:h-12 pl-11 sm:pl-12 bg-slate-800/50 border-violet-500/25 rounded-xl text-white font-bold placeholder:text-gray-400 focus:border-violet-500 focus:ring-violet-500/20 text-sm sm:text-base backdrop-blur-sm"
                  required
                />
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
                  Send reset link
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