/**
 * TermsOfService.jsx
 * Full Terms of Service page — opens in new tab from RegisterPage/ActivateAccountPage.
 */

import { Link } from 'react-router-dom';
import { Shield, ArrowLeft } from 'lucide-react';

const TERMS_SECTIONS = [
  {
    title: '1. Acceptance of Terms',
    body: `By creating a PhishCatcher account or using any of our services, you confirm that you are at least 16 years old (or the minimum age of digital consent in your jurisdiction), that you have the legal capacity to enter into a binding agreement, and that you have read, understood, and agree to be bound by these Terms of Service.

If you are using PhishCatcher on behalf of an organisation, you represent and warrant that you are authorised to bind that organisation to these Terms.`,
  },
  {
    title: '2. Description of Service',
    body: `PhishCatcher is an AI-powered email threat detection platform that allows users to upload email files (.eml format) and receive threat analysis reports. The service includes Gmail inbox integration, weekly threat intelligence summaries, and account management features.

The service is provided "as is" and is intended for cybersecurity awareness and threat analysis purposes only. PhishCatcher is not a substitute for professional security services or enterprise-grade email security gateways.`,
  },
  {
    title: '3. Account Registration and Security',
    body: `You must provide accurate and complete information when creating your account. You are responsible for maintaining the confidentiality of your login credentials and for all activity that occurs under your account.

You agree to: (a) immediately notify us of any unauthorised use of your account; (b) enable multi-factor authentication when handling sensitive analysis data; (c) not share your account credentials with any third party; (d) use a strong, unique password for your PhishCatcher account.

PhishCatcher employs OTP-based login verification, Redis-backed sessions, and MFA options to help protect your account. You agree to use these security features responsibly.`,
  },
  {
    title: '4. Acceptable Use',
    body: `You agree to use PhishCatcher only for lawful purposes and in a manner consistent with these Terms. You must not:

• Upload email files that you do not have a right to analyse or that belong to individuals without their consent
• Attempt to reverse-engineer, decompile, or extract the underlying machine learning models
• Use the platform to facilitate any form of harassment, abuse, or illegal activity
• Attempt to gain unauthorised access to any portion of our systems
• Interfere with or disrupt the integrity or performance of the service
• Use automated tools to scrape or extract data from our platform beyond what the API permits
• Resell, sublicense, or otherwise commercially exploit the service without written permission`,
  },
  {
    title: '5. Email Data and Privacy',
    body: `When you upload an email file for analysis, you affirm that you have the right to share its contents with our service. PhishCatcher processes the email content solely for the purpose of threat detection.

We do not permanently store the full body content of analysed emails. Metadata required for generating analysis reports (sender, subject, threat score, indicators) may be stored for up to 90 days to support your analysis history. You can delete your analysis history at any time.

For details on how we collect, use, and protect your data, please review our Privacy Policy.`,
  },
  {
    title: '6. Intellectual Property',
    body: `All content, features, and functionality of PhishCatcher — including but not limited to the machine learning models, threat detection algorithms, user interface, and documentation — are owned by PhishCatcher and its licensors and are protected by applicable intellectual property laws.

You are granted a limited, non-exclusive, non-transferable licence to access and use the service for its intended purpose. You retain ownership of any email data you upload and any reports generated from your data.`,
  },
  {
    title: '7. Disclaimers and Limitation of Liability',
    body: `PhishCatcher provides threat analysis on a best-effort basis. The service does not guarantee detection of every phishing attempt, and analysis results should be used as one input among several when making security decisions.

TO THE MAXIMUM EXTENT PERMITTED BY LAW, PHISHCATCHER SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, INCLUDING LOSS OF DATA, LOSS OF PROFITS, OR SECURITY INCIDENTS ARISING FROM YOUR USE OF THE SERVICE.

Our total liability to you for any claim arising from these Terms shall not exceed the amount you paid for the service in the three months preceding the claim, or £50 (or local equivalent), whichever is greater.`,
  },
  {
    title: '8. Service Modifications and Termination',
    body: `We reserve the right to modify, suspend, or discontinue any part of the service at any time. We will provide reasonable notice of material changes where practicable.

We may terminate or suspend your account immediately if you violate these Terms, engage in fraudulent activity, or for any other reason at our sole discretion. Upon termination, your right to use the service ceases immediately.

You may close your account at any time by using the account deletion feature in Settings.`,
  },
  {
    title: '9. Governing Law',
    body: `These Terms shall be governed by and construed in accordance with applicable law, without regard to conflict of law principles. Any disputes arising from these Terms or your use of the service shall be subject to the exclusive jurisdiction of the relevant courts.`,
  },
  {
    title: '10. Changes to These Terms',
    body: `We may update these Terms from time to time. When we make material changes, we will notify you by email or by displaying a prominent notice in the application. Your continued use of the service after the effective date of the updated Terms constitutes your acceptance of those changes.

If you do not agree to the updated Terms, you must stop using the service and may close your account.

Last updated: March 2026`,
  },
];

export function TermsOfService() {
  return (
    <div style={{ background: 'var(--bg-base)', color: 'var(--text-primary)', minHeight: '100dvh' }}>
      {/* Nav */}
      <nav className="sticky top-0 z-10 flex items-center justify-between px-6 h-14"
        style={{ background: 'var(--bg-overlay)', backdropFilter: 'blur(12px)', borderBottom: '1px solid var(--border)' }}>
        <Link to="/" className="flex items-center gap-2">
          <img src="/phishcatcher.png" alt="PhishCatcher" className="w-6 h-6 object-contain" />
          <span className="font-heading font-700 text-sm" style={{ color: 'var(--text-primary)' }}>PhishCatcher</span>
        </Link>
        <button
          onClick={() => {
            if (window.opener) {
              window.close();
            } else {
              window.history.back();
            }
          }}
          className="btn-ghost h-8 px-3 text-xs"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Close
        </button>
      </nav>

      <div className="max-w-3xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="flex items-center gap-3 mb-8 p-4 rounded-2xl"
          style={{ background: 'var(--brand-dim)', border: '1px solid var(--brand)' }}>
          <Shield className="w-6 h-6 shrink-0" style={{ color: 'var(--brand)' }} />
          <div>
            <h1 className="font-heading font-700 text-xl" style={{ color: 'var(--text-primary)' }}>
              Terms of Service
            </h1>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
              Please read these terms carefully before creating an account
            </p>
          </div>
        </div>

        <p className="text-sm leading-relaxed mb-8" style={{ color: 'var(--text-secondary)' }}>
          These Terms of Service ("Terms") govern your access to and use of PhishCatcher's email threat detection
          platform and related services. By using PhishCatcher, you agree to these Terms.
        </p>

        <div className="space-y-8">
          {TERMS_SECTIONS.map(section => (
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
            By creating an account, you confirm you have read and agree to these Terms.
          </p>
          <div className="flex items-center justify-center gap-4">
            <button onClick={() => {
              if (window.opener) {
                window.close();
              } else {
                window.history.back();
              }
            }} className="btn-primary h-10 px-6">
              I understand — close
            </button>
            <Link to="/privacy" className="btn-ghost h-10 px-5 text-sm">
              View Privacy Policy
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

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
        <button onClick={() => {
          if (window.opener) {
            window.close();
          } else {
            window.history.back();
          }
        }} className="btn-ghost h-8 px-3 text-xs">
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
            <button onClick={() => {
              if (window.opener) {
                window.close();
              } else {
                window.history.back();
              }
            }} className="btn-primary h-10 px-6">
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