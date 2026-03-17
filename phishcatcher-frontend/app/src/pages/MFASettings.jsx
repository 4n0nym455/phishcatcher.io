import { useState, useEffect } from 'react';
import { Shield, Smartphone, Key, AlertCircle, CheckCircle, X, Copy } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { toast } from 'sonner';
import { authApi } from '@/lib/api';

export default function MFASettings() {
  const [mfaStatus, setMfaStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [setupData, setSetupData] = useState(null);
  const [verificationCode, setVerificationCode] = useState('');
  const [disablePassword, setDisablePassword] = useState('');
  const [disableCode, setDisableCode] = useState('');
  const [isSetupDialogOpen, setIsSetupDialogOpen] = useState(false);
  const [isDisableDialogOpen, setIsDisableDialogOpen] = useState(false);
  const [mfaSessionToken, setMfaSessionToken] = useState(null);

  useEffect(() => {
    fetchMfaStatus();
  }, []);

  const fetchMfaStatus = async () => {
    try {
      const status = await authApi.getMfaStatus();
      setMfaStatus(status);
    } catch (error) {
      toast.error('Failed to fetch MFA status');
    } finally {
      setLoading(false);
    }
  };

  const handleSetupMfa = async () => {
    // MFA setup no longer requires password for any user
    // Security is maintained through MFA verification process
    try {
      toast.loading('Initiating MFA setup...', { id: 'mfa-setup' });
      const response = await authApi.setupMfa({});
      setSetupData(response);
      setMfaSessionToken(response.mfa_session_token); // Store session token
      setIsSetupDialogOpen(true);
      toast.success('MFA setup initiated', { id: 'mfa-setup' });
    } catch (error) {
      toast.error(error.message || 'Failed to setup MFA', { id: 'mfa-setup' });
    }
  };

  const handleVerifyMfa = async () => {
    if (!verificationCode || !setupData) {
      toast.error('Verification code is required');
      return;
    }

    try {
      await authApi.verifyMfa({
        token: verificationCode,
        secret: setupData.secret,
        backup_codes: setupData.backup_codes || [],
        mfa_session_token: mfaSessionToken
      });
      
      toast.success('MFA enabled successfully');
      setIsSetupDialogOpen(false);
      setSetupData(null);
      setVerificationCode('');
      setMfaSessionToken(null); // Clear session token
      fetchMfaStatus();
    } catch (error) {
      toast.error(error.message || 'Failed to verify MFA');
    }
  };

  const handleDisableMfa = async (e) => {
    e.preventDefault(); // Prevent any form submission
    
    // MFA verification code is always required for security
    if (!disableCode) {
      toast.error('Verification code from your authenticator app is required');
      return;
    }

    try {
      console.log('Attempting to disable MFA with:', {
        token: disableCode
      });
      
      // Only MFA code required - no password needed for any user
      const response = await authApi.disableMfa({
        token: disableCode
      });
      
      console.log('MFA disable response:', response);
      
      toast.success('MFA disabled successfully');
      setIsDisableDialogOpen(false);
      setDisablePassword('');
      setDisableCode('');
      fetchMfaStatus();
    } catch (error) {
      console.error('MFA disable error:', error);
      
      // Check if it's an authentication error
      if (error.message === 'Session expired') {
        toast.error('Your session has expired. Please log in again.');
        return;
      }
      
      toast.error(error.message || 'Failed to disable MFA');
    }
  };

  // Copy functions
  const copyToClipboard = async (text, type = 'code') => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success(`${type} copied to clipboard`);
    } catch (error) {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = text;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      toast.success(`${type} copied to clipboard`);
    }
  };

  const handleCopySecret = () => {
    if (setupData?.secret) {
      copyToClipboard(setupData.secret, 'Secret key');
    }
  };

  const handleCopyBackupCode = (code) => {
    copyToClipboard(code, 'Backup code');
  };

  const handleCopyAllBackupCodes = () => {
    if (setupData?.backup_codes) {
      const allCodes = setupData.backup_codes.join('\n');
      copyToClipboard(allCodes, 'All backup codes');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-violet-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-white">Multi-Factor Authentication</h1>
        <p className="text-muted-foreground mt-2 text-sm sm:text-base">
          Add an extra layer of security to your account with TOTP-based authentication
        </p>
      </div>

      {/* MFA Status Card */}
      <Card className="glass-card border-violet-500/25">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${
                mfaStatus?.enabled ? 'bg-green-500/20' : 'bg-yellow-500/20'
              }`}>
                <Shield className={`w-5 h-5 ${
                  mfaStatus?.enabled ? 'text-green-400' : 'text-yellow-400'
                }`} />
              </div>
              <div>
                <CardTitle className="text-white">MFA Status</CardTitle>
                <CardDescription className="text-muted-foreground">
                  Current status of your multi-factor authentication
                </CardDescription>
              </div>
            </div>
            <Badge className={
              mfaStatus?.enabled 
                ? 'bg-green-500/20 text-green-400 border-green-500/25' 
                : 'bg-yellow-500/20 text-yellow-400 border-yellow-500/25'
            }>
              {mfaStatus?.enabled ? 'Enabled' : 'Disabled'}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-sm">
            {mfaStatus?.enabled ? (
              <>
                <CheckCircle className="w-4 h-4 text-green-400" />
                <span className="text-green-400">Your account is protected with MFA</span>
              </>
            ) : (
              <>
                <AlertCircle className="w-4 h-4 text-yellow-400" />
                <span className="text-yellow-400">MFA is not enabled on your account</span>
              </>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Setup/Disable Actions */}
      <div className="flex flex-col sm:flex-row gap-3 sm:gap-4">
        {!mfaStatus?.enabled ? (
          <Button 
            onClick={handleSetupMfa}
            className="bg-violet-500 hover:bg-violet-600 w-full sm:w-auto"
          >
            <Smartphone className="w-4 h-4 mr-2" />
            Enable MFA
          </Button>
        ) : (
          <Dialog open={isDisableDialogOpen} onOpenChange={setIsDisableDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" className="bg-transparent border-violet-500/25 w-full sm:w-auto">
                <X className="w-4 h-4 mr-2" />
                Disable MFA
              </Button>
            </DialogTrigger>
            <DialogContent className="glass-card border-violet-500/25 mx-4">
              <DialogHeader>
                <DialogTitle className="text-white">Disable Multi-Factor Authentication</DialogTitle>
                <DialogDescription className="text-muted-foreground">
                  Remove MFA protection from your account
                </DialogDescription>
              </DialogHeader>
              
              <div className="space-y-4">
                <Alert>
                  <AlertCircle className="w-4 h-4" />
                  <AlertDescription>
                    Disabling MFA will make your account less secure. You must verify with your authenticator app to continue.
                  </AlertDescription>
                </Alert>
                
                <div className="space-y-2">
                  <Label htmlFor="disable-code" className="text-white">MFA Code</Label>
                  <Input
                    id="disable-code"
                    type="text"
                    placeholder="Enter 6-digit code"
                    value={disableCode}
                    onChange={(e) => setDisableCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    className="bg-black/30 border-violet-500/25 text-white placeholder:text-muted-foreground"
                    maxLength={6}
                  />
                </div>
                
                <div className="flex flex-col sm:flex-row gap-2">
                  <Button 
                    type="button"
                    onClick={handleDisableMfa}
                    disabled={!disableCode || disableCode.length !== 6}
                    variant="destructive"
                    className="w-full sm:flex-1 bg-pink-500/20 text-pink-400 border-pink-500/25 hover:bg-pink-500/30"
                  >
                    Disable MFA
                  </Button>
                  <Button 
                    type="button" 
                    variant="outline" 
                    onClick={() => {
                      setIsDisableDialogOpen(false);
                      setDisablePassword('');
                      setDisableCode('');
                    }}
                    className="w-full sm:flex-1 bg-transparent border-violet-500/25"
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* MFA Setup Dialog - Only shows after API call */}
      <Dialog open={isSetupDialogOpen} onOpenChange={setIsSetupDialogOpen}>
        <DialogContent className="glass-card border-violet-500/25 max-w-xl mx-4">
          <DialogHeader>
            <DialogTitle className="text-white">Setup Multi-Factor Authentication</DialogTitle>
            <DialogDescription className="text-muted-foreground">
              Secure your account with TOTP-based authentication
            </DialogDescription>
          </DialogHeader>
          
          {setupData ? (
            <div className="space-y-4">
              <Alert>
                <Smartphone className="w-4 h-4" />
                <AlertDescription>
                  Scan the QR code below with your authenticator app (Google Authenticator, Authy, etc.)
                </AlertDescription>
              </Alert>
              
              {/* QR Code */}
              <div className="flex justify-center">
                <div className="bg-white p-4 rounded-lg">
                  <img 
                    src={`data:image/png;base64,${setupData.qr_code}`}
                    alt="MFA QR Code"
                    className="w-48 h-48"
                  />
                </div>
              </div>
              
              {/* Secret Key */}
              <div className="space-y-2">
                <Label className="text-white">Secret Key</Label>
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-black/30 border border-violet-500/25 rounded px-3 py-2 font-mono text-sm text-white break-all">
                    {setupData.secret}
                  </div>
                  <button
                    onClick={handleCopySecret}
                    className="copy-button"
                    title="Copy secret key"
                  >
                    <Copy className="w-3 h-3" />
                    Copy
                  </button>
                </div>
              </div>
              
              {/* Backup Codes */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-white">Backup Codes</Label>
                  <button
                    onClick={handleCopyAllBackupCodes}
                    className="copy-button"
                    title="Copy all backup codes"
                  >
                    <Copy className="w-3 h-3" />
                    Copy All
                  </button>
                </div>
                <div className="backup-codes-grid">
                  {setupData.backup_codes.map((code, index) => (
                    <div
                      key={index}
                      onClick={() => handleCopyBackupCode(code)}
                      className="backup-code-item"
                      title={`Click to copy ${code}`}
                    >
                      {code}
                    </div>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground">
                  ⚠️ Save these backup codes in a secure location. Each code can only be used once to recover your account if you lose access to your authenticator app.
                </p>
              </div>
              
              {/* Verification Code */}
              <div className="space-y-2">
                <Label htmlFor="verification-code" className="text-white">Verification Code</Label>
                <Input
                  id="verification-code"
                  type="text"
                  placeholder="Enter 6-digit code"
                  value={verificationCode}
                  onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  className="bg-black/30 border-violet-500/25 text-white placeholder:text-muted-foreground"
                  maxLength={6}
                />
              </div>
              
              <Button 
                onClick={handleVerifyMfa}
                disabled={!verificationCode || verificationCode.length !== 6}
                className="w-full bg-violet-500 hover:bg-violet-600"
              >
                Enable MFA
              </Button>
            </div>
          ) : (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-violet-500"></div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
