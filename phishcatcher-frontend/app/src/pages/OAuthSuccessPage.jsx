import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { authApi } from '@/lib/api';

export default function OAuthSuccessPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const tokenId = searchParams.get('token_id');

  useEffect(() => {
    if (!tokenId) {
      setError('No token provided');
      setIsLoading(false);
      return;
    }

    const retrieveTokens = async () => {
      try {
        console.log('🔄 Retrieving OAuth tokens...');
        
        // Get tokens from server
        const response = await authApi.getOAuthTokens(tokenId);
        
        console.log('✅ Tokens retrieved successfully');
        
        // Store tokens and user data
        if (response.access_token) {
          localStorage.setItem('access_token', response.access_token);
          localStorage.setItem('refresh_token', response.refresh_token);
        }
        
        // Store user info
        if (response.user) {
          localStorage.setItem('phishcatcher_email', response.user.email);
          localStorage.setItem('phishcatcher_role', response.user.role || 'user');
          localStorage.setItem('phishcatcher_name', response.user.full_name || '');
        }
        
        // Show success message
        toast.success('Successfully logged in with Google!');
        
        // Redirect to dashboard
        setTimeout(() => {
          navigate('/dashboard');
        }, 1000);
        
      } catch (error) {
        console.error('❌ Failed to retrieve tokens:', error);
        setError(error.message || 'Failed to complete authentication');
        toast.error(error.message || 'Failed to complete authentication');
      } finally {
        setIsLoading(false);
      }
    };

    retrieveTokens();
  }, [tokenId, navigate]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-violet-500 animate-spin mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-white mb-2">Completing Sign-In...</h1>
          <p className="text-gray-400">Please wait while we complete your authentication.</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-slate-800/50 backdrop-blur-xl border border-violet-500/20 rounded-2xl p-8 text-center">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-white mb-4">Authentication Failed</h1>
          <p className="text-gray-300 mb-6">{error}</p>
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
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="text-center">
        <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
        <h1 className="text-2xl font-bold text-white mb-2">Sign-In Successful!</h1>
        <p className="text-gray-400">Redirecting to dashboard...</p>
      </div>
    </div>
  );
}
