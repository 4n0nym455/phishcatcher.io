import { useState } from 'react';
import { Key, AlertCircle, CheckCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';
import { authApi } from '@/lib/api';

export default function BackupCodeVerification({ onSuccess, onCancel }) {
  const [backupCode, setBackupCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!backupCode) {
      setError('Backup code is required');
      return;
    }

    // Normalize backup code (remove spaces, make uppercase)
    const normalizedCode = backupCode.replace(/\s/g, '').toUpperCase();
    
    if (normalizedCode.length !== 8) {
      setError('Backup code must be 8 characters');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await authApi.verifyBackupCode(normalizedCode);
      
      if (response.success) {
        toast.success(`Backup code verified successfully! ${response.remaining_backup_codes} codes remaining.`);
        
        // Store tokens and user data
        if (response.access_token && response.refresh_token) {
          localStorage.setItem('access_token', response.access_token);
          localStorage.setItem('refresh_token', response.refresh_token);
        }
        
        if (response.user) {
          localStorage.setItem('phishcatcher_email', response.user.email);
          localStorage.setItem('phishcatcher_role', response.user.role || 'user');
          localStorage.setItem('phishcatcher_name', response.user.full_name || '');
        }
        
        onSuccess(response);
      } else {
        setError('Invalid backup code');
      }
    } catch (error) {
      console.error('Backup code verification error:', error);
      setError(error.message || 'Invalid backup code');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const value = e.target.value;
    // Auto-format: uppercase and add spaces for readability
    const formatted = value.toUpperCase().replace(/[^A-Z0-9]/g, '');
    setBackupCode(formatted);
    setError('');
  };

  return (
    <Card className="w-full max-w-md mx-auto glass-card border-violet-500/25">
      <CardHeader className="text-center">
        <div className="mx-auto w-12 h-12 bg-yellow-500/20 rounded-full flex items-center justify-center mb-4">
          <Key className="w-6 h-6 text-yellow-400" />
        </div>
        <CardTitle className="text-white">Use Backup Code</CardTitle>
        <CardDescription className="text-muted-foreground">
          Enter one of your 8-character backup codes to access your account
        </CardDescription>
      </CardHeader>
      
      <CardContent className="space-y-4">
        <Alert>
          <AlertCircle className="w-4 h-4" />
          <AlertDescription>
            Backup codes are one-time use. Each code can only be used once.
            Keep your remaining codes in a safe place.
          </AlertDescription>
        </Alert>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="backup-code" className="text-white">Backup Code</Label>
            <Input
              id="backup-code"
              type="text"
              placeholder="Enter 8-character code"
              value={backupCode}
              onChange={handleInputChange}
              className="bg-black/30 border-violet-500/25 text-white placeholder:text-muted-foreground text-center text-lg font-mono tracking-widest"
              maxLength={8}
              autoComplete="off"
            />
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="w-4 h-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <Button
              type="submit"
              disabled={loading || backupCode.length !== 8}
              className="w-full bg-violet-500 hover:bg-violet-600"
            >
              {loading ? 'Verifying...' : 'Verify Backup Code'}
            </Button>

            <Button
              type="button"
              variant="outline"
              onClick={onCancel}
              className="w-full bg-transparent border-violet-500/25 text-violet-400 hover:bg-violet-500/10"
            >
              Back to Authenticator App
            </Button>
          </div>
        </form>

        <div className="text-center">
          <p className="text-xs text-muted-foreground">
            Lost all your backup codes? Contact support for account recovery.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
