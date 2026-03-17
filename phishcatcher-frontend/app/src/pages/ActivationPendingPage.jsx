import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Mail, ArrowLeft, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { authApi } from '@/lib/api';

export default function ActivationPendingPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [isResending, setIsResending] = useState(false);
  
  // Get user info from URL parameters (server-side OAuth) or location state (popup flow)
  const searchParams = new URLSearchParams(location.search);
  const email = searchParams.get('email') || location.state?.email;
  const full_name = searchParams.get('full_name') || location.state?.full_name;
  const message = searchParams.get('message') || location.state?.message;
  
  useEffect(() => {
    if (!email) {
      // If no email provided, redirect to login
      navigate('/login');
    }
  }, [email, navigate]);

  const handleResendEmail = async () => {
    if (!email) return;
    
    setIsResending(true);
    try {
      const response = await authApi.resendActivation(email);
      toast.success('Activation email sent successfully!');
    } catch (error) {
      toast.error(error.message || 'Failed to resend activation email');
    } finally {
      setIsResending(false);
    }
  };

  const handleBackToLogin = () => {
    navigate('/login');
  };

  if (!email) {
    return null;
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background Effects */}
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
          <div className="w-10 h-10 bg-violet-500 rounded-xl flex items-center justify-center">
            <span className="text-white font-bold text-xl">🎯</span>
          </div>
          <span className="text-white font-bold text-xl">PhishCatcher</span>
        </div>

        {/* Main Card */}
        <div className="bg-slate-800/50 backdrop-blur-xl border border-violet-500/20 rounded-2xl p-6 sm:p-8 shadow-2xl">
          {/* Mail Icon */}
          <div className="flex justify-center mb-6">
            <div className="w-16 h-16 bg-violet-500/20 rounded-full flex items-center justify-center">
              <Mail className="w-8 h-8 text-violet-400" />
            </div>
          </div>

          {/* Title */}
          <h1 className="text-2xl font-bold text-white text-center mb-4">
            Check Your Email
          </h1>

          {/* Message */}
          <div className="text-center mb-6">
            <p className="text-gray-300 mb-2">
              Hi {full_name || email.split('@')[0]},
            </p>
            <p className="text-gray-300 text-sm">
              {message || "We've sent an activation email to your address. Please check your inbox and follow the instructions to activate your account."}
            </p>
          </div>

          {/* Email Display */}
          <div className="bg-slate-700/50 border border-violet-500/20 rounded-lg p-4 mb-6">
            <p className="text-gray-400 text-sm mb-1">Activation email sent to:</p>
            <p className="text-white font-medium">{email}</p>
          </div>

          {/* Instructions */}
          <div className="bg-violet-500/10 border border-violet-500/20 rounded-lg p-4 mb-6">
            <h3 className="text-violet-400 font-medium mb-2">Next Steps:</h3>
            <ol className="text-gray-300 text-sm space-y-1 list-decimal list-inside">
              <li>Open the activation email</li>
              <li>Copy the 6-digit activation code</li>
              <li>Click the activation link</li>
              <li>Enter the code and accept terms</li>
              <li>Enjoy full access to PhishCatcher!</li>
            </ol>
          </div>

          {/* Action Buttons */}
          <div className="space-y-3">
            <button
              onClick={handleResendEmail}
              disabled={isResending}
              className="w-full h-11 sm:h-12 bg-violet-500 hover:bg-violet-600 disabled:bg-violet-500/50 disabled:cursor-not-allowed text-white rounded-xl font-medium transition-all duration-200 flex items-center justify-center gap-2"
            >
              {isResending ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Sending...
                </>
              ) : (
                <>
                  <Mail className="w-4 h-4" />
                  Resend Email
                </>
              )}
            </button>

            <button
              onClick={handleBackToLogin}
              className="w-full h-11 sm:h-12 bg-transparent border border-violet-500/25 hover:bg-violet-500/10 hover:border-violet-500/40 text-white rounded-xl font-medium transition-all duration-200 flex items-center justify-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Login
            </button>
          </div>

          {/* Help Text */}
          <div className="mt-6 text-center">
            <p className="text-gray-400 text-sm">
              Didn't receive the email? Check your spam folder or click "Resend Email" above.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
