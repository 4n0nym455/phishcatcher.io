import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Shield, Key, ArrowRight, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { authApi, setTokens } from "@/lib/api"; // Add this import
import LoadingOrb from "@/components/LoadingOrb";

export default function OTPPage({ onVerify }) {
  const navigate = useNavigate();
  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [isLoading, setIsLoading] = useState(false);
  const [countdown, setCountdown] = useState(60);
  const [canResend, setCanResend] = useState(false);
  const inputRefs = useRef([]);

  const email = localStorage.getItem("phishcatcher_email") || "your email";

  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    } else {
      setCanResend(true);
    }
  }, [countdown]);

  useEffect(() => {
    inputRefs.current[0]?.focus();
  }, []);

  const handleChange = (index, value) => {
    if (value.length > 1) return;

    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);

    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }

    if (index === 5 && value) {
      const fullOtp = [...newOtp.slice(0, 5), value].join("");
      if (fullOtp.length === 6) {
        handleVerify(fullOtp);
      }
    }
  };

  const handleKeyDown = (index, e) => {
    if (e.key === "Backspace" && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').trim().toUpperCase();
    
    // Remove any non-alphanumeric characters and take first 6 characters
    const cleanOtp = pastedData.replace(/[^A-Z0-9]/g, '').slice(0, 6);
    
    if (cleanOtp.length === 6) {
      // Fill all inputs with the pasted OTP
      const newOtp = cleanOtp.split('');
      setOtp(newOtp);
      
      // Focus the last input
      inputRefs.current[5]?.focus();
      
      // Auto-verify the pasted OTP
      handleVerify(cleanOtp);
    } else if (cleanOtp.length > 0) {
      // Fill available inputs with pasted characters
      const newOtp = [...otp];
      for (let i = 0; i < Math.min(cleanOtp.length, 6); i++) {
        newOtp[i] = cleanOtp[i];
      }
      setOtp(newOtp);
      
      // Focus the next empty input or the last filled one
      const nextEmptyIndex = newOtp.findIndex(digit => !digit);
      const focusIndex = nextEmptyIndex === -1 ? 5 : nextEmptyIndex;
      inputRefs.current[focusIndex]?.focus();
    }
  };

  const handleVerify = async (code) => {
    setIsLoading(true);

    try {
      // Call backend to verify OTP
      const data = await authApi.verifyOTP(email, code);
      
      // Check if MFA is required
      if (data.mfa_required) {
        // Store MFA session token and redirect to MFA verification
        localStorage.setItem('mfa_session_token', data.mfa_session_token);
        localStorage.setItem('mfa_user', JSON.stringify(data.user));
        toast.success("OTP verified! Please enter your MFA code.");
        navigate("/mfa-verification");
        return;
      }
      
      // Store tokens (non-MFA users)
      if (data.access_token) {
        // Store tokens
        setTokens(data);
        
        // Store user data in localStorage for App.jsx to pick up
        localStorage.setItem('phishcatcher_role', data.user.role);
        localStorage.setItem('phishcatcher_email', data.user.email);
        
        // Trigger App.jsx loading state
        window.dispatchEvent(new CustomEvent('auth-success'));
        
        toast.success("Successfully logged in!");
        navigate('/dashboard');
      }
      onVerify?.(); // Call to parent handler to update auth state
      navigate("/dashboard");
    } catch (error) {
      toast.error(error.message || "Invalid verification code");
      // Clear inputs on error
      setOtp(["", "", "", "", "", ""]);
      inputRefs.current[0]?.focus();
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const code = otp.join("");
    if (code.length === 6) {
      handleVerify(code);
    } else {
      toast.error("Please enter all 6 characters");
    }
  };

  const handleResend = async () => {
    if (!canResend) return;

    try {
      setIsLoading(true);
      await authApi.resendOTP(email);
      toast.success("New code sent to your email");
      
      // Reset countdown
      setCountdown(60);
      setCanResend(false);
      
      // Clear current OTP
      setOtp(["", "", "", "", "", ""]);
      if (inputRefs.current[0]) {
        inputRefs.current[0].focus();
      }
    } catch (error) {
      if (error.message?.includes("No active login session found")) {
        toast.error("Your session has expired. Please login again.");
        navigate("/login");
      } else {
        toast.error(error.message || "Failed to resend code");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-primary-60 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background Effects */}
      <div className="absolute inset-0 bg-radial-spotlight opacity-50" />
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-72 sm:w-96 h-72 sm:h-96 bg-violet-500/8 rounded-full blur-3xl" />

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
          <div className="w-11 sm:w-12 h-11 sm:h-12 rounded-xl bg-white/80 flex items-center justify-center shadow-glow">
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

        {/* OTP Card */}
        <div className="glass-card-strong rounded-2xl sm:rounded-3xl p-6 sm:p-8">
          <div className="text-center mb-6 sm:mb-8">
            <div className="w-14 sm:w-16 h-14 sm:h-16 rounded-2xl bg-violet-500/20 flex items-center justify-center mx-auto mb-4">
              <Key className="w-7 sm:w-8 h-7 sm:h-8 text-violet-400" />
            </div>
            <h1 className="text-xl sm:text-2xl font-heading font-bold text-white/80 mb-2">
              Verify your email
            </h1>
            <p className="text-sm text-muted-foreground">
              We've sent a 6-character code to
              <br />
              <span className="text-violet-400 font-medium break-all px-2">
                {email}
              </span>
            </p>
          </div>

          {/* OTP Form */}
          <form onSubmit={handleSubmit} className="space-y-5 sm:space-y-6" onPaste={handlePaste}>
            <div className="flex justify-center gap-2 sm:gap-3">
              {otp.map((digit, index) => (
                <input
                  key={index}
                  ref={(el) => {
                    inputRefs.current[index] = el;
                  }}
                  type="text"
                  inputMode="text"
                  maxLength={1}
                  value={digit}
                  onChange={(e) =>
                    handleChange(index, e.target.value.toUpperCase())
                  }
                  onKeyDown={(e) => handleKeyDown(index, e)}
                  className="w-10 sm:w-14 h-12 sm:h-16 text-center text-xl sm:text-2xl font-mono font-bold bg-slate-800/50 border-2 border-violet-500/25 rounded-xl text-white placeholder:text-gray-400 focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 transition-all disabled:opacity-50 backdrop-blur-sm"
                  disabled={isLoading}
                />
              ))}
            </div>

            <Button
              type="submit"
              className="w-full h-11 sm:h-12 bg-violet-gradient hover:opacity-90 text-white font-bold rounded-xl font-medium shadow-glow text-sm sm:text-base"
              disabled={isLoading || otp.join("").length !== 6}
            >
              {isLoading ? (
                <LoadingOrb size="mini" text="" />
              ) : (
                <>
                  Verify code
                  <ArrowRight className="w-4 sm:w-5 h-4 sm:h-5 ml-2" />
                </>
              )}
            </Button>
          </form>

          {/* Resend Section */}
          <div className="mt-5 sm:mt-6 text-center">
            <p className="text-sm text-muted-foreground mb-2">
              Didn't receive the code?
            </p>
            <button
              onClick={handleResend}
              disabled={!canResend}
              className={`inline-flex items-center gap-2 text-sm font-medium transition-colors ${
                canResend
                  ? "text-violet-400 hover:text-violet-300"
                  : "text-muted-foreground cursor-not-allowed"
              }`}
            >
              <RefreshCw
                className={`w-4 h-4 ${!canResend && "animate-spin"}`}
              />
              {canResend ? "Resend code" : `Resend in ${countdown}s`}
            </button>
          </div>
        </div>

        {/* Security Info */}
        <div className="mt-6 sm:mt-8 text-center">
          <p className="text-xs text-muted-foreground">
            For your security, this code will expire in 10 minutes
          </p>
        </div>
      </div>
    </div>
  );
}