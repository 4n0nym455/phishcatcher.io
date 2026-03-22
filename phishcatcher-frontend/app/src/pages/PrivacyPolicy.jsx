/* ══════════════════════════════════════════════════════════════════════════
   PrivacyPolicy.jsx
══════════════════════════════════════════════════════════════════════════ */
 
import { Lock } from 'lucide-react';
 
const PRIVACY_SECTIONS = [
  {
    title: '1. Introduction',
    body: `PhishCatcher ("we", "our", "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard information when you use our email threat detection service.
 
By using PhishCatcher, you consent to the data practices described in this policy. If you do not agree with any part of this policy, please do not use our service.`,
  },
  {
    title: '2. Information We Collect',
    body: `Account Information: When you register, we collect your name, email address, and optionally your company name.
 
Authentication Data: We store a hashed version of your password (never plain-text), MFA secrets in encrypted form, and session tokens in Redis with short TTLs.
 
Email Analysis Data: When you upload an email for analysis, we process the content to generate a threat report. We store analysis metadata (sender, subject, threat score, indicators, timestamp) for up to 90 days. Full body content is not permanently stored.
 
Usage Data: Standard server logs including IP addresses, browser/client type, and pages visited for security and debugging purposes.
 
Gmail Integration Data: If you connect Gmail, we use OAuth 2.0 to obtain limited read access. We store OAuth access and refresh tokens in encrypted form. You can revoke access at any time.`,
  },
  {
    title: '3. How We Use Your Information',
    body: `We use collected information to:
 
• Provide, operate, and maintain the PhishCatcher service
• Process email threat analysis requests and generate reports
• Send transactional emails (OTP codes, account activation, password resets)
• Send weekly threat summary reports if opted in
• Improve our ML models using anonymised, aggregated threat patterns
• Detect and prevent fraud, abuse, and security incidents
• Comply with legal obligations
 
We do not sell your personal information to third parties. We do not use your email content for advertising purposes.`,
  },
  {
    title: '4. Data Retention',
    body: `Account data is retained for as long as your account is active. You can delete your account at any time from Settings, which anonymises your personal data immediately.
 
Analysis history is retained for up to 90 days by default. You can delete individual records or your entire history from the Analysis History page.
 
Server logs are retained for up to 30 days for security monitoring. Backup data may be retained for up to 7 additional days after deletion.`,
  },
  {
    title: '5. Data Security',
    body: `We implement industry-standard security measures:
 
• All data is encrypted in transit using TLS 1.3
• Passwords are hashed using bcrypt with appropriate cost factors
• MFA secrets are encrypted at rest using AES-256
• Redis sessions use short-lived tokens (default 2 hours) with server-side invalidation
• All authentication events are logged in an immutable audit log
• Rate limiting and account lockout protect against brute-force attacks
 
Despite these measures, no method of electronic storage is 100% secure. We cannot guarantee absolute security.`,
  },
  {
    title: '6. Your Rights',
    body: `Depending on your location, you may have the right to:
 
• Access the personal data we hold about you
• Request correction of inaccurate or incomplete data
• Request deletion of your account and associated data
• Request your data in a machine-readable format
• Withdraw consent for Gmail integration at any time
• Object to processing of your data in certain circumstances
 
To exercise these rights, use the account management features in Settings. We will respond to requests within 30 days.`,
  },
  {
    title: '7. Cookies and Tracking',
    body: `PhishCatcher uses minimal, functional browser storage:
 
• Authentication tokens stored in localStorage (access and refresh tokens only)
• Session preferences (theme, etc.) stored in localStorage
• No advertising cookies or third-party tracking pixels
• No Google Analytics or analytics services that share data with third parties
 
You can clear your browser's localStorage at any time, which will log you out of the service.`,
  },
  {
    title: '8. Children\'s Privacy',
    body: `PhishCatcher is not intended for children under the age of 16. We do not knowingly collect personal information from children under 16. If we become aware that we have inadvertently collected such information, we will promptly delete it.`,
  },
  {
    title: '9. Changes to This Policy',
    body: `We may update this Privacy Policy from time to time. We will notify you of significant changes by email or by displaying a prominent notice in the application at least 30 days before changes take effect.
 
Your continued use of the service after the effective date constitutes acceptance of the updated policy.
 
Last updated: March 2026`,
  },
];
 
export function PrivacyPolicy() {
  return (
    <div style={{ background: 'var(--bg-base)', color: 'var(--text-primary)', minHeight: '100dvh' }}>
      {/* Nav */}
      <nav className="sticky top-0 z-10 flex items-center justify-between px-6 h-14"
        style={{ background: 'var(--bg-overlay)', backdropFilter: 'blur(12px)', borderBottom: '1px solid var(--border)' }}>
        <Link to="/" className="flex items-center gap-2">
          <img src="/phishcatcher.png" alt="PhishCatcher" className="w-6 h-6 object-contain" />
          <span className="font-heading font-700 text-sm" style={{ color: 'var(--text-primary)' }}>PhishCatcher</span>
        </Link>
        <button onClick={() => window.close()} className="btn-ghost h-8 px-3 text-xs">
          <ArrowLeft className="w-3.5 h-3.5" /> Close
        </button>
      </nav>
 
      <div className="max-w-3xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="flex items-center gap-3 mb-8 p-4 rounded-2xl"
          style={{ background: 'var(--brand-dim)', border: '1px solid var(--brand)' }}>
          <Lock className="w-6 h-6 shrink-0" style={{ color: 'var(--brand)' }} />
          <div>
            <h1 className="font-heading font-700 text-xl" style={{ color: 'var(--text-primary)' }}>
              Privacy Policy
            </h1>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
              How we collect, use, and protect your data
            </p>
          </div>
        </div>
 
        <p className="text-sm leading-relaxed mb-8" style={{ color: 'var(--text-secondary)' }}>
          Your privacy matters to us. This policy explains our data practices in plain language.
        </p>
 
        <div className="space-y-8">
          {PRIVACY_SECTIONS.map(section => (
            <div key={section.title}>
              <h2 className="font-heading font-700 text-base mb-3" style={{ color: 'var(--text-primary)' }}>
                {section.title}
              </h2>
              <div className="space-y-3">
                {section.body.split('\n\n').map((para, i) => (
                  <p key={i} className="text-sm leading-relaxed whitespace-pre-wrap"
                    style={{ color: 'var(--text-secondary)' }}>
                    {para}
                  </p>
                ))}
              </div>
              <div className="mt-6 h-px" style={{ background: 'var(--border)' }} />
            </div>
          ))}
        </div>
 
        <div className="mt-12 text-center">
          <p className="text-sm mb-5" style={{ color: 'var(--text-muted)' }}>
            By creating an account, you confirm you have read and agree to this Privacy Policy.
          </p>
          <div className="flex items-center justify-center gap-4">
            <button onClick={() => window.close()} className="btn-primary h-10 px-6">
              I understand — close
            </button>
            <Link to="/terms" className="btn-ghost h-10 px-5 text-sm">
              View Terms of Service
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}