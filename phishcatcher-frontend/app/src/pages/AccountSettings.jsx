import { useState, useEffect } from "react";
import { toast } from "sonner";
import { User, Mail, Building2, Lock, Shield, Bell, Eye, EyeOff, ExternalLink, RefreshCw, AlertTriangle, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from '@/components/ui/separator';
import { authApi } from '@/lib/api';
import { securityService } from '@/lib/securityService';
import MFASettings from '@/components/MFASettings';

export default function AccountSettings() {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  
  // Gmail integration state
  const [gmailStatus, setGmailStatus] = useState(null);
  const [isScanning, setIsScanning] = useState(false);
  const [scanResults, setScanResults] = useState(null);
  
  // Delete account state
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  
  const [profileForm, setProfileForm] = useState({
    fullName: "",
    email: "",
    company: "",
  });
  
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  });

  useEffect(() => {
    loadUserProfile();
    loadGmailStatus();
  }, []);

  const loadGmailStatus = async () => {
    try {
      const status = await authApi.gmail.getStatus();
      setGmailStatus(status);
    } catch (error) {
      console.error('Failed to load Gmail status:', error);
    }
  };

  const loadUserProfile = async () => {
    try {
      const userData = await authApi.getMe();
      setUser(userData);
      setProfileForm({
        fullName: userData.full_name || "",
        email: userData.email || "",
        company: userData.company || "",
      });
    } catch (error) {
      toast.error("Failed to load profile");
    }
  };

  const handleProfileUpdate = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await authApi.updateProfile({
        full_name: profileForm.fullName,
        company: profileForm.company,
      });
      toast.success("Profile updated successfully");
      loadUserProfile();
    } catch (error) {
      toast.error(error.message || "Failed to update profile");
    } finally {
      setIsLoading(false);
    }
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();

    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      toast.error("New passwords do not match");
      return;
    }

    if (passwordForm.currentPassword === passwordForm.newPassword) {
      toast.error("New password must be different from current password");
      return;
    }

    setIsLoading(true);

    try {
      console.log('Attempting password change with:', {
        currentPassword: passwordForm.currentPassword,
        newPassword: passwordForm.newPassword,
        confirmPassword: passwordForm.confirmPassword,
        newPasswordLength: passwordForm.newPassword.length
      });
      
      await authApi.changePassword(
        passwordForm.currentPassword, 
        passwordForm.newPassword, 
        passwordForm.confirmPassword
      );
      
      // Success flow
      toast.success("Password changed successfully! A notification has been sent to your email.", {
        duration: 5000,
        description: "For security purposes, you've been logged out from other devices."
      });
      
      // Clear form
      setPasswordForm({
        currentPassword: "",
        newPassword: "",
        confirmPassword: "",
      });
      
      // Reload user data to update any password-related timestamps
      await loadUserProfile();
      
    } catch (error) {
      console.error('Password change failed:', error);
      
      // Handle specific error messages
      let errorMessage = "Failed to change password";
      if (error.message) {
        if (error.message.includes("current_password")) {
          errorMessage = "Current password is incorrect";
        } else if (error.message.includes("new_password")) {
          errorMessage = error.message; // This will include strength validation or reuse errors
        } else {
          errorMessage = error.message;
        }
      }
      
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // Gmail Integration Handlers
  const handleConnectGmail = async () => {
    try {
      const { auth_url } = await authApi.gmail.getAuthUrl();
      window.location.href = auth_url;
    } catch (error) {
      toast.error("Failed to get Gmail authorization URL");
    }
  };

  const handleDisconnectGmail = async () => {
    try {
      await authApi.gmail.disconnect();
      toast.success("Gmail account disconnected");
      loadGmailStatus();
    } catch (error) {
      toast.error("Failed to disconnect Gmail account");
    }
  };

  const handleToggleAutoScan = async (enabled) => {
    try {
      await authApi.gmail.toggleAutoScan(enabled);
      toast.success(`Auto-scan ${enabled ? 'enabled' : 'disabled'}`);
      loadGmailStatus();
    } catch (error) {
      toast.error("Failed to update auto-scan settings");
    }
  };

  const handleScanEmails = async () => {
    setIsScanning(true);
    try {
      const results = await authApi.gmail.scanEmails(20);
      setScanResults(results);
      toast.success(`Scanned ${results.scanned} emails, found ${results.threats_found} threats`);
    } catch (error) {
      toast.error("Failed to scan emails");
    } finally {
      setIsScanning(false);
    }
  };

  const handleMarkSafe = async (messageId) => {
    try {
      await authApi.gmail.markSafe(messageId);
      toast.success("Email marked as safe");
      if (scanResults) {
        setScanResults(prev => ({
          ...prev,
          emails: prev.emails.map(email => 
            email.id === messageId 
              ? { ...email, marked_safe: true }
              : email
          )
        }));
      }
    } catch (error) {
      toast.error("Failed to mark email as safe");
    }
  };

  const handleReportPhishing = async (messageId) => {
    try {
      await authApi.gmail.reportPhishing(messageId);
      toast.success("Email reported as phishing");
      if (scanResults) {
        setScanResults(prev => ({
          ...prev,
          emails: prev.emails.map(email => 
            email.id === messageId 
              ? { ...email, reported_phishing: true }
              : email
          )
        }));
      }
    } catch (error) {
      toast.error("Failed to report email as phishing");
    }
  };

  // Delete Account Handlers
  const handleDeleteAccount = async () => {
    try {
      setIsDeleting(true);
      
      // Get security requirements for delete account
      const securityReqs = await securityService.getSecurityRequirements('delete_account');
      
      // Show verification dialog based on requirements
      await securityService.showVerificationDialog('delete_account', securityReqs);
      
      // If we get here, verification was successful
      toast.success("Account deleted successfully");
      
      // Clear tokens and redirect to login
      localStorage.clear();
      window.location.href = "/login";
      
    } catch (error) {
      toast.error(error.message || "Failed to delete account");
    } finally {
      setIsDeleting(false);
      setShowDeleteDialog(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-4 sm:p-6 space-y-6 sm:space-y-8">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-white mb-2">Account Settings</h1>
        <p className="text-gray-400 text-sm sm:text-base">Manage your account settings and preferences</p>
      </div>

      {/* Profile Information */}
      <div className="bg-violet-900/20 rounded-lg border border-violet-500/30 p-4 sm:p-6">
        <div className="flex items-center gap-3 mb-4 sm:mb-6">
          <User className="w-5 h-5 text-violet-400" />
          <h2 className="text-lg font-semibold text-white">Profile Information</h2>
        </div>

        <form onSubmit={handleProfileUpdate} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="fullName" className="text-gray-300">Full Name</Label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <Input
                  id="fullName"
                  name="fullName"
                  type="text"
                  value={profileForm.fullName}
                  onChange={(e) => setProfileForm(prev => ({ ...prev, fullName: e.target.value }))}
                  className="pl-10 bg-violet-950/50 border-violet-500/30 text-white"
                  placeholder="John Doe"
                />
              </div>
            </div>

            <div>
              <Label htmlFor="company" className="text-gray-300">Company</Label>
              <div className="relative">
                <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <Input
                  id="company"
                  name="company"
                  type="text"
                  value={profileForm.company}
                  onChange={(e) => setProfileForm(prev => ({ ...prev, company: e.target.value }))}
                  className="pl-10 bg-violet-950/50 border-violet-500/30 text-white"
                  placeholder="Acme Inc."
                />
              </div>
            </div>
          </div>

          <div>
            <Label htmlFor="email" className="text-gray-300">Email Address</Label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <Input
                id="email"
                name="email"
                type="email"
                value={profileForm.email}
                disabled
                className="pl-10 bg-violet-950/50 border-violet-500/30 text-white opacity-50"
                placeholder="you@company.com"
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">Email cannot be changed. Contact support if needed.</p>
          </div>

          <Button
            type="submit"
            disabled={isLoading}
            className="bg-violet-600 hover:bg-violet-700 text-white"
          >
            {isLoading ? "Updating..." : "Update Profile"}
          </Button>
        </form>
      </div>

      {/* Password Change */}
      <div className="bg-violet-900/20 rounded-lg border border-violet-500/30 p-6">
        <div className="flex items-center gap-3 mb-6">
          <Lock className="w-5 h-5 text-violet-400" />
          <h2 className="text-lg font-semibold text-white">Change Password</h2>
        </div>

        <form onSubmit={handlePasswordChange} className="space-y-4">
          <div>
            <Label htmlFor="currentPassword" className="text-gray-300">Current Password</Label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <Input
                id="currentPassword"
                name="currentPassword"
                type={showCurrentPassword ? "text" : "password"}
                value={passwordForm.currentPassword}
                onChange={(e) => setPasswordForm(prev => ({ ...prev, currentPassword: e.target.value }))}
                className="pl-10 pr-10 bg-violet-950/50 border-violet-500/30 text-white"
                placeholder="••••••••"
                required
              />
              <button
                type="button"
                onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
              >
                {showCurrentPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="newPassword" className="text-gray-300">New Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <Input
                  id="newPassword"
                  name="newPassword"
                  type={showNewPassword ? "text" : "password"}
                  value={passwordForm.newPassword}
                  onChange={(e) => setPasswordForm(prev => ({ ...prev, newPassword: e.target.value }))}
                  className="pl-10 pr-10 bg-violet-950/50 border-violet-500/30 text-white"
                  placeholder="••••••••"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
                >
                  {showNewPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div>
              <Label htmlFor="confirmPassword" className="text-gray-300">Confirm New Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <Input
                  id="confirmPassword"
                  name="confirmPassword"
                  type={showConfirmPassword ? "text" : "password"}
                  value={passwordForm.confirmPassword}
                  onChange={(e) => setPasswordForm(prev => ({ ...prev, confirmPassword: e.target.value }))}
                  className="pl-10 pr-10 bg-violet-950/50 border-violet-500/30 text-white"
                  placeholder="••••••••"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
                >
                  {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
          </div>

          <Button
            type="submit"
            disabled={isLoading}
            className="bg-violet-600 hover:bg-violet-700 text-white"
          >
            {isLoading ? "Changing Password..." : "Change Password"}
          </Button>
        </form>
      </div>

      {/* MFA Settings */}
      <div className="bg-violet-900/20 rounded-lg border border-violet-500/30 p-6">
        <MFASettings embedded={true} />
      </div>

      {/* Account Status */}
      <div className="bg-violet-900/20 rounded-lg border border-violet-500/30 p-6">
        <div className="flex items-center gap-3 mb-6">
          <Shield className="w-5 h-5 text-violet-400" />
          <h2 className="text-lg font-semibold text-white">Account Status</h2>
        </div>

        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-gray-300">Account Status</span>
            <span className={`px-2 py-1 rounded text-xs font-medium ${
              user?.is_active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
            }`}>
              {user?.is_active ? 'Active' : 'Inactive'}
            </span>
          </div>
          
          <div className="flex justify-between items-center">
            <span className="text-gray-300">Email Verified</span>
            <span className={`px-2 py-1 rounded text-xs font-medium ${
              user?.email_verified ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'
            }`}>
              {user?.email_verified ? 'Verified' : 'Not Verified'}
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-gray-300">2FA Enabled</span>
            <span className={`px-2 py-1 rounded text-xs font-medium ${
              user?.mfa_enabled ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'
            }`}>
              {user?.mfa_enabled ? 'Enabled' : 'Disabled'}
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-gray-300">Member Since</span>
            <span className="text-gray-400">
              {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
            </span>
          </div>
        </div>
      </div>

      {/* Gmail Integration */}
      <div className="bg-violet-900/20 rounded-lg border border-violet-500/30 p-6">
        <div className="flex items-center gap-3 mb-6">
          <Mail className="w-5 h-5 text-violet-400" />
          <h2 className="text-lg font-semibold text-white">Gmail Integration</h2>
        </div>

        {gmailStatus?.connected ? (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-gray-300">Connected Account</p>
                <p className="text-sm text-gray-500">{gmailStatus.email}</p>
              </div>
              <span className="px-2 py-1 rounded text-xs font-medium bg-green-500/20 text-green-400">
                Connected
              </span>
            </div>

            <div className="flex justify-between items-center">
              <span className="text-gray-300">Auto-scan</span>
              <button
                onClick={() => handleToggleAutoScan(!gmailStatus.auto_scan)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  gmailStatus.auto_scan ? 'bg-violet-600' : 'bg-gray-600'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    gmailStatus.auto_scan ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            <div className="flex gap-3">
              <Button
                onClick={handleScanEmails}
                disabled={isScanning}
                className="flex items-center gap-2 bg-violet-600 hover:bg-violet-700"
              >
                <RefreshCw className={`w-4 h-4 ${isScanning ? 'animate-spin' : ''}`} />
                {isScanning ? 'Scanning...' : 'Scan Emails'}
              </Button>
              
              <Button
                onClick={handleDisconnectGmail}
                variant="outline"
                className="border-red-500/30 text-red-400 hover:bg-red-500/10"
              >
                Disconnect
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-gray-300">
              Connect your Gmail account to enable real-time email phishing detection and analysis.
            </p>
            
            <div className="bg-violet-950/50 rounded-lg p-4 border border-violet-500/30">
              <h3 className="text-white font-medium mb-2">Features:</h3>
              <ul className="text-sm text-gray-400 space-y-1">
                <li>• Real-time email scanning</li>
                <li>• Automatic phishing detection</li>
                <li>• Email threat reporting</li>
                <li>• Safe email marking</li>
              </ul>
            </div>
            
            <Button
              onClick={handleConnectGmail}
              className="bg-violet-600 hover:bg-violet-700 text-white"
            >
              <ExternalLink className="w-4 h-4 mr-2" />
              Connect Gmail Account
            </Button>
          </div>
        )}

        {/* Scan Results */}
        {scanResults && (
          <div className="mt-6 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-white font-medium">Recent Scan Results</h3>
              <span className="text-sm text-gray-400">
                {scanResults.scanned} scanned, {scanResults.threats_found} threats
              </span>
            </div>
            
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {scanResults.emails.map((email) => (
                <div
                  key={email.id}
                  className={`p-3 rounded-lg border ${
                    email.analysis?.is_phishing
                      ? 'bg-red-900/20 border-red-500/30'
                      : email.marked_safe
                      ? 'bg-green-900/20 border-green-500/30'
                      : 'bg-violet-950/50 border-violet-500/30'
                  }`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex-1">
                      <p className="text-white font-medium text-sm">{email.subject}</p>
                      <p className="text-gray-400 text-xs">{email.from}</p>
                    </div>
                    {email.analysis?.is_phishing ? (
                      <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
                    ) : email.marked_safe ? (
                      <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
                    ) : null}
                  </div>
                  
                  <p className="text-gray-400 text-xs mb-2 line-clamp-2">
                    {email.snippet}
                  </p>
                  
                  <div className="flex gap-2">
                    {!email.marked_safe && !email.reported_phishing && (
                      <>
                        <Button
                          size="sm"
                          onClick={() => handleMarkSafe(email.id)}
                          className="text-xs bg-green-600 hover:bg-green-700"
                        >
                          Mark Safe
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => handleReportPhishing(email.id)}
                          className="text-xs bg-red-600 hover:bg-red-700"
                        >
                          Report Phishing
                        </Button>
                      </>
                    )}
                    {email.marked_safe && (
                      <span className="text-xs text-green-400">✓ Marked as safe</span>
                    )}
                    {email.reported_phishing && (
                      <span className="text-xs text-red-400">✓ Reported as phishing</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Delete Account Section */}
      <div className="bg-red-900/20 rounded-lg border border-red-500/30 p-6">
        <div className="flex items-center gap-3 mb-6">
          <Shield className="w-5 h-5 text-red-400" />
          <h2 className="text-lg font-semibold text-white">Delete Account</h2>
        </div>

        <div className="space-y-4">
          <div className="bg-red-950/50 rounded-lg p-4 border border-red-500/30">
            <h3 className="text-white font-medium mb-2">⚠️ Danger Zone</h3>
            <p className="text-gray-300 text-sm mb-3">
              This action is permanent and cannot be undone. All your data will be permanently deleted.
            </p>
            <ul className="text-sm text-gray-400 space-y-1">
              <li>• Profile information and settings</li>
              <li>• Email analysis history and reports</li>
              <li>• Gmail integration and connections</li>
              <li>• All associated data and files</li>
            </ul>
          </div>

          <div className="flex justify-between items-center">
            <div>
              <p className="text-gray-300">Type your password to confirm deletion</p>
              <p className="text-xs text-gray-500">This action cannot be undone</p>
            </div>
            <Button
              onClick={() => setShowDeleteDialog(true)}
              variant="outline"
              className="border-red-500/30 text-red-400 hover:bg-red-500/10"
            >
              Delete Account
            </Button>
          </div>
        </div>
      </div>

      {/* Delete Account Confirmation Dialog */}
      {showDeleteDialog && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-violet-900 rounded-lg border border-violet-500/30 p-6 max-w-md w-full">
            <div className="flex items-center gap-3 mb-4">
              <AlertTriangle className="w-5 h-5 text-red-400" />
              <h3 className="text-lg font-semibold text-white">Delete Account</h3>
            </div>
            
            <p className="text-gray-300 mb-6">
              Are you sure you want to delete your account? This action cannot be undone.
              <br />
              <span className="text-amber-400">
                You will be asked to verify your identity before deletion.
              </span>
            </p>

            <div className="flex gap-3 justify-end">
              <Button
                onClick={() => {
                  setShowDeleteDialog(false);
                }}
                variant="outline"
                className="border-gray-500/30 text-gray-400 hover:bg-gray-500/10"
              >
                Cancel
              </Button>
              <Button
                onClick={handleDeleteAccount}
                disabled={isDeleting}
                className="bg-red-600 hover:bg-red-700 text-white"
              >
                {isDeleting ? "Deleting..." : "Delete Account"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
