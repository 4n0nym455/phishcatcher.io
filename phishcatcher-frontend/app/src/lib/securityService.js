/**
 * Security Service for Risk-Based Authentication
 * 
 * This service handles enterprise-grade security with risk-based authentication,
 * following patterns used by Google, Microsoft, and GitHub.
 */

class SecurityService {
    constructor() {
        this.verificationMethods = {
            NONE: 'none',
            SESSION: 'session',
            EMAIL_CODE: 'email_code',
            OAUTH_REAUTH: 'oauth_reauth',
            PASSWORD: 'password',
            MFA: 'mfa'
        };
        
        this.riskLevels = {
            LOW: 'low',
            MEDIUM: 'medium',
            HIGH: 'high',
            CRITICAL: 'critical'
        };
    }

    /**
     * Get security requirements for an action
     */
    async getSecurityRequirements(action) {
        try {
            const response = await fetch('/api/v1/me/security/requirements', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAccessToken()}`
                },
                body: JSON.stringify({ action })
            });
            
            if (!response.ok) {
                throw new Error('Failed to get security requirements');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Security requirements error:', error);
            throw error;
        }
    }

    /**
     * Send email verification code
     */
    async sendEmailVerification(action) {
        try {
            const response = await fetch('/api/v1/me/security/verify/email', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAccessToken()}`
                },
                body: JSON.stringify({ action })
            });
            
            if (!response.ok) {
                throw new Error('Failed to send verification code');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Email verification error:', error);
            throw error;
        }
    }

    /**
     * Initiate OAuth re-authentication
     */
    async initiateOAuthReauth() {
        try {
            const response = await fetch('/api/v1/auth/google/url', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${this.getAccessToken()}`
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to initiate OAuth re-authentication');
            }
            
            const data = await response.json();
            
            // Store re-auth state
            sessionStorage.setItem('oauth_reauth_state', data.state);
            sessionStorage.setItem('oauth_reauth_action', 'reauth');
            
            return data.auth_url;
        } catch (error) {
            console.error('OAuth re-auth error:', error);
            throw error;
        }
    }

    /**
     * Verify action with appropriate method
     */
    async verifyAction(action, verificationData) {
        try {
            const securityReqs = await this.getSecurityRequirements(action);
            const method = securityReqs.method;
            
            switch (method) {
                case this.verificationMethods.PASSWORD:
                    return await this.verifyWithPassword(action, verificationData.password);
                
                case this.verificationMethods.EMAIL_CODE:
                    return await this.verifyWithEmailCode(action, verificationData.code);
                
                case this.verificationMethods.OAUTH_REAUTH:
                    return await this.verifyWithOAuth(action, verificationData.token);
                
                case this.verificationMethods.MFA:
                    return await this.verifyWithMFA(action, verificationData.mfa_code);
                
                case this.verificationMethods.SESSION:
                case this.verificationMethods.NONE:
                    return { success: true };
                
                default:
                    throw new Error(`Unsupported verification method: ${method}`);
            }
        } catch (error) {
            console.error('Action verification error:', error);
            throw error;
        }
    }

    /**
     * Verify with password
     */
    async verifyWithPassword(action, password) {
        const endpoints = {
            'delete_account': '/api/v1/me/delete/secure',
            'setup_mfa': '/api/v1/mfa/setup',
            'change_email': '/api/v1/me/email'
        };
        
        const endpoint = endpoints[action] || `/api/v1/me/${action}`;
        
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.getAccessToken()}`
            },
            body: JSON.stringify({ password })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Verification failed');
        }
        
        return await response.json();
    }

    /**
     * Verify with email code
     */
    async verifyWithEmailCode(action, code) {
        const response = await fetch('/api/v1/me/delete/secure', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.getAccessToken()}`
            },
            body: JSON.stringify({ 
                action,
                email_code: code 
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Invalid verification code');
        }
        
        return await response.json();
    }

    /**
     * Verify with OAuth re-authentication
     */
    async verifyWithOAuth(action, token) {
        const response = await fetch('/api/v1/me/delete/secure', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.getAccessToken()}`
            },
            body: JSON.stringify({ 
                action,
                reauth_token: token 
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Re-authentication failed');
        }
        
        return await response.json();
    }

    /**
     * Verify with MFA
     */
    async verifyWithMFA(action, mfaCode) {
        const response = await fetch('/api/v1/me/delete/secure', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.getAccessToken()}`
            },
            body: JSON.stringify({ 
                action,
                mfa_code: mfaCode 
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Invalid MFA code');
        }
        
        return await response.json();
    }

    /**
     * Handle OAuth re-authentication callback
     */
    handleOAuthReauthCallback(code, state) {
        const storedState = sessionStorage.getItem('oauth_reauth_state');
        const action = sessionStorage.getItem('oauth_reauth_action');
        
        if (state !== storedState || action !== 'reauth') {
            throw new Error('Invalid OAuth re-authentication state');
        }
        
        // Clear re-auth state
        sessionStorage.removeItem('oauth_reauth_state');
        sessionStorage.removeItem('oauth_reauth_action');
        
        // Exchange code for re-auth token and complete verification
        return this.exchangeCodeForReauthToken(code).then(() => {
            // Notify parent window of successful re-authentication
            if (window.opener && !window.opener.closed) {
                window.opener.postMessage({
                    type: 'OAUTH_REAUTH_SUCCESS',
                    token: 'reauth_completed'
                }, window.location.origin);
            }
            
            // Close the re-auth popup
            window.close();
        });
    }

    /**
     * Exchange OAuth code for re-auth token
     */
    async exchangeCodeForReauthToken(code) {
        try {
            const response = await fetch('/api/v1/auth/google/callback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAccessToken()}`
                },
                body: JSON.stringify({ code, state: 'reauth' })
            });
            
            if (!response.ok) {
                throw new Error('Failed to exchange code for re-auth token');
            }
            
            const data = await response.json();
            return data.reauth_token;
        } catch (error) {
            console.error('Re-auth token exchange error:', error);
            throw error;
        }
    }

    /**
     * Get access token from localStorage
     */
    getAccessToken() {
        return localStorage.getItem('access_token');
    }

    /**
     * Show verification dialog based on requirements
     */
    async showVerificationDialog(action, securityReqs) {
        return new Promise((resolve, reject) => {
            const method = securityReqs.method;
            const message = securityReqs.message;
            
            // Create modal dialog
            const modal = document.createElement('div');
            modal.className = 'fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4';
            modal.innerHTML = `
                <div class="bg-violet-900 rounded-lg border border-violet-500/30 p-6 max-w-md w-full">
                    <h3 class="text-lg font-semibold text-white mb-4">Security Verification</h3>
                    <p class="text-gray-300 mb-6">${message}</p>
                    <div id="verification-form"></div>
                    <div class="flex gap-3 justify-end mt-6">
                        <button id="cancel-btn" class="px-4 py-2 border border-gray-500/30 text-gray-400 rounded hover:bg-gray-500/10">
                            Cancel
                        </button>
                        <button id="verify-btn" class="px-4 py-2 bg-violet-500 text-white rounded hover:bg-violet-600">
                            Verify
                        </button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            // Handle different verification methods
            this.setupVerificationForm(method, securityReqs, resolve, reject);
            
            // Handle cancel
            document.getElementById('cancel-btn').onclick = () => {
                document.body.removeChild(modal);
                reject(new Error('Verification cancelled'));
            };
        });
    }

    /**
     * Setup verification form based on method
     */
    setupVerificationForm(method, securityReqs, resolve, reject) {
        const formContainer = document.getElementById('verification-form');
        const verifyBtn = document.getElementById('verify-btn');
        
        switch (method) {
            case this.verificationMethods.PASSWORD:
                formContainer.innerHTML = `
                    <div class="space-y-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-300 mb-2">Password</label>
                            <input type="password" id="password-input" class="w-full px-3 py-2 bg-violet-950/50 border border-violet-500/30 rounded text-white placeholder-gray-400" placeholder="Enter your password">
                        </div>
                    </div>
                `;
                
                verifyBtn.onclick = async () => {
                    const password = document.getElementById('password-input').value;
                    try {
                        const result = await this.verifyWithPassword('delete_account', password);
                        document.body.removeChild(document.querySelector('.fixed'));
                        resolve(result);
                    } catch (error) {
                        reject(error);
                    }
                };
                break;
                
            case this.verificationMethods.EMAIL_CODE:
                formContainer.innerHTML = `
                    <div class="space-y-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-300 mb-2">Verification Code</label>
                            <input type="text" id="code-input" class="w-full px-3 py-2 bg-violet-950/50 border border-violet-500/30 rounded text-white placeholder-gray-400" placeholder="Enter 6-digit code">
                        </div>
                        <button type="button" id="send-code-btn" class="text-sm text-violet-400 hover:text-violet-300">
                            Send new code
                        </button>
                    </div>
                `;
                
                // Send code on load
                this.sendEmailVerification('delete_account');
                
                verifyBtn.onclick = async () => {
                    const code = document.getElementById('code-input').value;
                    try {
                        const result = await this.verifyWithEmailCode('delete_account', code);
                        document.body.removeChild(document.querySelector('.fixed'));
                        resolve(result);
                    } catch (error) {
                        reject(error);
                    }
                };
                
                document.getElementById('send-code-btn').onclick = () => {
                    this.sendEmailVerification('delete_account');
                };
                break;
                
            case this.verificationMethods.OAUTH_REAUTH:
                formContainer.innerHTML = `
                    <div class="space-y-4">
                        <p class="text-sm text-gray-300">Click the button below to re-authenticate with Google</p>
                    </div>
                `;
                
                verifyBtn.onclick = async () => {
                    try {
                        const authUrl = await this.initiateOAuthReauth();
                        window.open(authUrl, 'oauth-reauth', 'width=500,height=600,scrollbars=yes,resizable=yes');
                        
                        // Listen for re-auth completion
                        const messageHandler = (event) => {
                            if (event.data.type === 'OAUTH_REAUTH_SUCCESS') {
                                window.removeEventListener('message', messageHandler);
                                document.body.removeChild(document.querySelector('.fixed'));
                                resolve({ success: true });
                            } else if (event.data.type === 'OAUTH_REAUTH_ERROR') {
                                window.removeEventListener('message', messageHandler);
                                reject(new Error('Re-authentication failed'));
                            }
                        };
                        
                        window.addEventListener('message', messageHandler);
                    } catch (error) {
                        reject(error);
                    }
                };
                break;
                
            default:
                reject(new Error(`Unsupported verification method: ${method}`));
        }
    }
}

// Export singleton instance
export const securityService = new SecurityService();
