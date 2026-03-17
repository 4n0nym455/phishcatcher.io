import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Mail, Shield, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { authApi, setTokens } from '@/lib/api';

export default function ActivateAccountPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  // Get URL parameters
  const token = searchParams.get('token');
  const email = searchParams.get('email');
  
  // Form state
  const [activationCode, setActivationCode] = useState(['', '', '', '', '', '']);
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [privacyAccepted, setPrivacyAccepted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [tokenValid, setTokenValid] = useState(null);
  const [userInfo, setUserInfo] = useState(null);
  const [isActivating, setIsActivating] = useState(false);

  // Verify token on mount
  useEffect(() => {
    if (!token || !email) {
      toast.error('Invalid activation link');
      navigate('/login');
      return;
    }

    verifyToken();
  }, [token, email, navigate]);

  const verifyToken = async () => {
    try {
      const response = await authApi.verifyActivationToken(token, email);
      
      if (response.already_activated) {
        toast.success('Your account is already activated!');
        navigate('/login');
        return;
      }
      
      setTokenValid(true);
      setUserInfo(response.user);
    } catch (error) {
      setTokenValid(false);
      toast.error(error.message || 'Invalid or expired activation link');
    }
  };

  const handleCodeChange = (index, value) => {
    // Only allow numbers
    if (value && !/^\d$/.test(value)) return;
    
    const newCode = [...activationCode];
    newCode[index] = value;
    setActivationCode(newCode);
    
    // Auto-focus next input
    if (value && index < 5) {
      const nextInput = document.getElementById(`code-${index + 1}`);
      if (nextInput) nextInput.focus();
    }
  };

  const handleKeyDown = (index, e) => {
    // Handle backspace
    if (e.key === 'Backspace' && !activationCode[index] && index > 0) {
      const prevInput = document.getElementById(`code-${index - 1}`);
      if (prevInput) prevInput.focus();
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').trim();
    
    // Only allow 6-digit numbers
    if (/^\d{6}$/.test(pastedData)) {
      const newCode = pastedData.split('');
      setActivationCode(newCode);
      
      // Focus last input
      const lastInput = document.getElementById('code-5');
      if (lastInput) lastInput.focus();
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validation
    if (!termsAccepted || !privacyAccepted) {
      toast.error('You must accept both Terms & Conditions and Privacy Policy');
      return;
    }
    
    const code = activationCode.join('');
    if (code.length !== 6) {
      toast.error('Please enter the complete 6-digit activation code');
      return;
    }
    
    setIsActivating(true);
    
    try {
      const response = await authApi.completeActivation({
        token,
        email,
        code,
        terms_accepted: termsAccepted,
        privacy_accepted: privacyAccepted
      });
      
      if (response.already_activated) {
        toast.success('Your account is already activated!');
        navigate('/login');
      } else if (response.access_token) {
        // Auto-login after activation
        setTokens(response);
        
        // Store user info in localStorage
        if (response.user) {
          localStorage.setItem('phishcatcher_email', response.user.email);
          localStorage.setItem('phishcatcher_role', response.user.role || 'user');
          localStorage.setItem('phishcatcher_name', response.user.full_name || '');
          // Store login method for MFA detection
          localStorage.setItem('login_method', 'oauth');
        }
        
        toast.success('Account activated successfully! Redirecting to dashboard...');
        
        // Redirect to dashboard after a short delay
        setTimeout(() => {
          navigate('/dashboard');
        }, 1500);
      } else {
        toast.success('Account activated successfully! You can now login.');
        navigate('/login');
      }
    } catch (error) {
      toast.error(error.message || 'Failed to activate account');
    } finally {
      setIsActivating(false);
    }
  };

  if (tokenValid === null) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-violet-500 animate-spin mx-auto mb-4" />
          <p className="text-white">Verifying activation link...</p>
        </div>
      </div>
    );
  }

  if (tokenValid === false) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-slate-800/50 backdrop-blur-xl border border-violet-500/20 rounded-2xl p-8 text-center">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-white mb-4">Invalid Activation Link</h1>
          <p className="text-gray-300 mb-6">
            This activation link is invalid or has expired. Please request a new activation email.
          </p>
          <button
            onClick={() => navigate('/login')}
            className="w-full h-12 bg-violet-500 hover:bg-violet-600 text-white rounded-xl font-medium transition-all duration-200"
          >
            Back to Login
          </button>
        </div>
      </div>
    );
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
          {/* Shield Icon */}
          <div className="flex justify-center mb-6">
            <div className="w-16 h-16 bg-violet-500/20 rounded-full flex items-center justify-center">
              <Shield className="w-8 h-8 text-violet-400" />
            </div>
          </div>

          {/* Title */}
          <h1 className="text-2xl font-bold text-white text-center mb-2">
            Activate Your Account
          </h1>
          
          {/* User Info */}
          {userInfo && (
            <p className="text-gray-300 text-center mb-6">
              Welcome, {userInfo.full_name || userInfo.email.split('@')[0]}!
            </p>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Activation Code */}
            <div>
              <label className="block text-gray-300 text-sm font-medium mb-3">
                Enter 6-Digit Activation Code
              </label>
              <div className="flex gap-2 justify-center">
                {activationCode.map((digit, index) => (
                  <input
                    key={index}
                    id={`code-${index}`}
                    type="text"
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handleCodeChange(index, e.target.value)}
                    onKeyDown={(e) => handleKeyDown(index, e)}
                    onPaste={index === 0 ? handlePaste : undefined}
                    className="w-12 h-12 bg-slate-700/50 border border-violet-500/20 rounded-lg text-center text-white text-xl font-mono focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
                    required
                  />
                ))}
              </div>
            </div>

            {/* Terms and Privacy */}
            <div className="space-y-3">
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={termsAccepted}
                  onChange={(e) => setTermsAccepted(e.target.checked)}
                  className="w-4 h-4 mt-0.5 rounded border-violet-500/30 bg-slate-800/50 text-violet-500 focus:ring-violet-500/20"
                  required
                />
                <span className="text-gray-300 text-sm">
                  I have read and agree to the{' '}
                  <a 
                    href="/terms-of-service" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-violet-400 hover:text-violet-300 underline"
                  >
                    Terms & Conditions
                  </a>
                </span>
              </label>

              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={privacyAccepted}
                  onChange={(e) => setPrivacyAccepted(e.target.checked)}
                  className="w-4 h-4 mt-0.5 rounded border-violet-500/30 bg-slate-800/50 text-violet-500 focus:ring-violet-500/20"
                  required
                />
                <span className="text-gray-300 text-sm">
                  I have read and agree to the{' '}
                  <a 
                    href="/privacy-policy" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-violet-400 hover:text-violet-300 underline"
                  >
                    Privacy Policy
                  </a>
                </span>
              </label>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isActivating || !termsAccepted || !privacyAccepted}
              className="w-full h-12 bg-violet-500 hover:bg-violet-600 disabled:bg-violet-500/50 disabled:cursor-not-allowed text-white rounded-xl font-medium transition-all duration-200 flex items-center justify-center gap-2"
            >
              {isActivating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Activating...
                </>
              ) : (
                <>
                  <CheckCircle className="w-4 h-4" />
                  Activate Account
                </>
              )}
            </button>
          </form>

          {/* Help Text */}
          <div className="mt-6 text-center">
            <p className="text-gray-400 text-sm">
              Need help? Check your email for the activation code or contact support.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
