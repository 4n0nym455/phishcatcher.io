import { useState, useEffect } from 'react';
import { Shield, Smartphone, Key, AlertCircle, CheckCircle, X, Copy, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { toast } from 'sonner';
import { authApi } from '@/lib/api';

export default function MFASettings({ embedded = false }) {
  const [mfaStatus, setMfaStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [setupData, setSetupData] = useState(null);
  const [verificationCode, setVerificationCode] = useState('');
  const [disableCode, setDisableCode] = useState('');
  const [disablePassword, setDisablePassword] = useState('');
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
      console.error('Failed to fetch MFA status:', error);
      toast.error('Failed to fetch MFA status');
    } finally {
      setLoading(false);
    }
  };

  const handleSetupMfa = async () => {
    try {
      toast.loading('Initiating MFA setup...', { id: 'mfa-setup' });
      const response = await authApi.setupMfa({});
      setSetupData(response);
      setMfaSessionToken(response.mfa_session_token);
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
      await authApi.verifyMfaSetup({
        mfa_session_token: mfaSessionToken,
        code: verificationCode
      });
      
      toast.success('MFA enabled successfully');
      setIsSetupDialogOpen(false);
      setSetupData(null);
      setVerificationCode('');
      setMfaSessionToken(null);
      fetchMfaStatus();
    } catch (error) {
      toast.error(error.message || 'Failed to verify MFA');
    }
  };

  const handleDisableMfa = async () => {
    if (!disableCode) {
      toast.error('Verification code is required');
      return;
    }
    if (!disablePassword) {
      toast.error('Password is required');
      return;
    }

    try {
      await authApi.disableMfa({
        token: disableCode,
        password: disablePassword
      });
      
      toast.success('MFA disabled successfully');
      setIsDisableDialogOpen(false);
      setDisableCode('');
      setDisablePassword('');
      fetchMfaStatus();
    } catch (error) {
      toast.error(error.message || 'Failed to disable MFA');
    }
  };

  const copyToClipboard = (text, type) => {
    navigator.clipboard.writeText(text).then(() => {
      toast.success(`${type} copied to clipboard`);
    }).catch(() => {
      toast.error('Failed to copy to clipboard');
    });
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
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-violet-500"></div>
      </div>
    );
  }

  if (embedded) {
    // Embedded version for settings page
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium text-white">Multi-Factor Authentication</h3>
            <p className="text-sm text-gray-400">Add an extra layer of security to your account</p>
          </div>
          <Badge className={mfaStatus?.enabled ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'}>
            {mfaStatus?.enabled ? 'Enabled' : 'Not Configured'}
          </Badge>
        </div>

        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-gray-300">Status</span>
            <span className={`px-2 py-1 rounded text-xs font-medium ${
              mfaStatus?.enabled 
                ? 'bg-green-500/20 text-green-400' 
                : 'bg-yellow-500/20 text-yellow-400'
            }`}>
              {mfaStatus?.enabled ? 'Enabled' : 'Not Configured'}
            </span>
          </div>
          
          <div className="flex justify-between items-center">
            <span className="text-gray-300">Setup Completed</span>
            <span className={`px-2 py-1 rounded text-xs font-medium ${
              mfaStatus?.setup_completed 
                ? 'bg-green-500/20 text-green-400' 
                : 'bg-gray-500/20 text-gray-400'
            }`}>
              {mfaStatus?.setup_completed ? 'Yes' : 'No'}
            </span>
          </div>
        </div>

        <div className="flex gap-3">
          {!mfaStatus?.enabled ? (
            <Button 
              onClick={handleSetupMfa}
              className="bg-violet-500 hover:bg-violet-600"
              size="sm"
            >
              <Smartphone className="w-4 h-4 mr-2" />
              Enable MFA
            </Button>
          ) : (
            <Button 
              onClick={() => setIsDisableDialogOpen(true)}
              variant="outline" 
              className="bg-transparent border-violet-500/25 text-violet-400 hover:bg-violet-500/10"
              size="sm"
            >
              <X className="w-4 h-4 mr-2" />
              Disable MFA
            </Button>
          )}
        </div>

        {/* Setup Dialog */}
        <Dialog open={isSetupDialogOpen} onOpenChange={setIsSetupDialogOpen}>
          <DialogContent className="glass-card border-violet-500/25 max-w-xl mx-4">
            <DialogHeader>
              <DialogTitle className="text-white flex items-center gap-2">
                <Shield className="w-5 h-5" />
                Setup Multi-Factor Authentication
              </DialogTitle>
              <DialogDescription className="text-muted-foreground">
                Scan the QR code with your authenticator app and enter the verification code
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-6">
              {/* QR Code */}
              <div className="flex justify-center">
                <div className="bg-white p-4 rounded-lg">
                  {setupData?.qr_code && (
                    <img 
                      src={`data:image/png;base64,${setupData.qr_code}`} 
                      alt="MFA QR Code" 
                      className="w-48 h-48"
                    />
                  )}
                </div>
              </div>
              
              {/* Secret Key */}
              <div className="space-y-2">
                <Label className="text-white">Secret Key</Label>
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-black/30 border border-violet-500/25 rounded px-3 py-2 font-mono text-sm text-white break-all">
                    {setupData?.secret}
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
                  {setupData?.backup_codes?.map((code, index) => (
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
                <p className="text-xs text-muted-foreground flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                  Save these backup codes in a secure location. Each code can only be used once to recover your account if you lose access to your authenticator app.
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
              
              <div className="flex flex-col sm:flex-row gap-2">
                <Button 
                  onClick={handleVerifyMfa}
                  disabled={!verificationCode || verificationCode.length !== 6}
                  className="w-full sm:flex-1 bg-violet-500 hover:bg-violet-600"
                >
                  Enable MFA
                </Button>
                <Button 
                  variant="outline" 
                  onClick={() => {
                    setIsSetupDialogOpen(false);
                    setSetupData(null);
                    setMfaSessionToken(null);
                    setVerificationCode('');
                  }}
                  className="w-full sm:flex-1 bg-transparent border-violet-500/25"
                >
                  Cancel
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>

        {/* Disable Dialog */}
        <Dialog open={isDisableDialogOpen} onOpenChange={setIsDisableDialogOpen}>
          <DialogContent className="glass-card border-violet-500/25 mx-4">
            <DialogHeader>
              <DialogTitle className="text-white flex items-center gap-2">
                <AlertCircle className="w-5 h-5" />
                Disable Multi-Factor Authentication
              </DialogTitle>
              <DialogDescription className="text-muted-foreground">
                This will remove the extra security layer from your account
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4">
              <Alert>
                <AlertCircle className="w-4 h-4" />
                <AlertDescription>
                  Disabling MFA will make your account less secure. You can always re-enable it later.
                </AlertDescription>
              </Alert>

              <div className="space-y-2">
                <Label htmlFor="disable-code" className="text-white">Verification Code</Label>
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

              <div className="space-y-2">
                <Label htmlFor="disable-password" className="text-white">Password</Label>
                <Input
                  id="disable-password"
                  type="password"
                  placeholder="Enter your password"
                  value={disablePassword}
                  onChange={(e) => setDisablePassword(e.target.value)}
                  className="bg-black/30 border-violet-500/25 text-white placeholder:text-muted-foreground"
                />
              </div>
              
              <div className="flex gap-2">
                <Button 
                  onClick={handleDisableMfa}
                  disabled={!disableCode || disableCode.length !== 6 || !disablePassword}
                  className="flex-1 bg-red-500 hover:bg-red-600"
                >
                  Disable MFA
                </Button>
                <Button 
                  variant="outline" 
                  onClick={() => {
                    setIsDisableDialogOpen(false);
                    setDisableCode('');
                    setDisablePassword('');
                  }}
                  className="flex-1 bg-transparent border-violet-500/25"
                >
                  Cancel
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    );
  }

  // Full page version (original)
  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-700 text-white mb-2">Multi-Factor Authentication</h1>
        <p className="text-gray-400">
          Add an extra layer of security to your account by requiring a verification code in addition to your password.
        </p>
      </div>

      <Card className="glass-card border-violet-500/25 mb-6">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Shield className="w-5 h-5" />
            MFA Status
          </CardTitle>
          <CardDescription className="text-muted-foreground">
            Current status of your multi-factor authentication
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-gray-300">Status</span>
            <Badge className={mfaStatus?.enabled ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'}>
              {mfaStatus?.enabled ? 'Enabled' : 'Not Configured'}
            </Badge>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-gray-300">Setup Completed</span>
            <Badge className={mfaStatus?.setup_completed ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'}>
              {mfaStatus?.setup_completed ? 'Yes' : 'No'}
            </Badge>
          </div>
        </CardContent>
      </Card>

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
          <Button 
            onClick={() => setIsDisableDialogOpen(true)}
            variant="outline" 
            className="bg-transparent border-violet-500/25 w-full sm:w-auto"
          >
            <X className="w-4 h-4 mr-2" />
            Disable MFA
          </Button>
        )}
      </div>

      {/* Setup Dialog */}
      <Dialog open={isSetupDialogOpen} onOpenChange={setIsSetupDialogOpen}>
        <DialogContent className="glass-card border-violet-500/25 max-w-xl mx-4">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <Shield className="w-5 h-5" />
              Setup Multi-Factor Authentication
            </DialogTitle>
            <DialogDescription className="text-muted-foreground">
              Scan the QR code with your authenticator app and enter the verification code
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-6">
            {/* QR Code */}
            <div className="flex justify-center">
              <div className="bg-white p-4 rounded-lg">
                {setupData?.qr_code && (
                  <img 
                    src={`data:image/png;base64,${setupData.qr_code}`} 
                    alt="MFA QR Code" 
                    className="w-48 h-48"
                  />
                )}
              </div>
            </div>
            
            {/* Secret Key */}
            <div className="space-y-2">
              <Label className="text-white">Secret Key</Label>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-black/30 border border-violet-500/25 rounded px-3 py-2 font-mono text-sm text-white break-all">
                  {setupData?.secret}
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
                {setupData?.backup_codes?.map((code, index) => (
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
<p className="text-xs text-muted-foreground flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                  Save these backup codes in a secure location. Each code can only be used once to recover your account if you lose access to your authenticator app.
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
            
            <div className="flex flex-col sm:flex-row gap-2">
              <Button 
                onClick={handleVerifyMfa}
                disabled={!verificationCode || verificationCode.length !== 6}
                className="w-full sm:flex-1 bg-violet-500 hover:bg-violet-600"
              >
                Enable MFA
              </Button>
              <Button 
                variant="outline" 
                onClick={() => {
                  setIsSetupDialogOpen(false);
                  setSetupData(null);
                  setMfaSessionToken(null);
                  setVerificationCode('');
                }}
                className="w-full sm:flex-1 bg-transparent border-violet-500/25"
              >
                Cancel
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Disable Dialog */}
      <Dialog open={isDisableDialogOpen} onOpenChange={setIsDisableDialogOpen}>
        <DialogContent className="glass-card border-violet-500/25 mx-4">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <AlertCircle className="w-5 h-5" />
              Disable Multi-Factor Authentication
            </DialogTitle>
            <DialogDescription className="text-muted-foreground">
              This will remove the extra security layer from your account
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <Alert>
              <AlertCircle className="w-4 h-4" />
              <AlertDescription>
                Disabling MFA will make your account less secure. You can always re-enable it later.
              </AlertDescription>
            </Alert>

            <div className="space-y-2">
              <Label htmlFor="disable-code" className="text-white">Verification Code</Label>
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
            
            <div className="flex gap-2">
              <Button 
                onClick={handleDisableMfa}
                disabled={!disableCode || disableCode.length !== 6}
                className="flex-1 bg-red-500 hover:bg-red-600"
              >
                Disable MFA
              </Button>
              <Button 
                variant="outline" 
                onClick={() => {
                  setIsDisableDialogOpen(false);
                  setDisableCode('');
                }}
                className="flex-1 bg-transparent border-violet-500/25"
              >
                Cancel
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
