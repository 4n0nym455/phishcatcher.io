import { useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Shield, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { usePageVisitTracker } from "@/hooks/usePageVisitTracker";
import { toast } from "sonner";
import { setTokens } from "@/lib/api";

export default function PrivacyPolicy() {
  const { markPageVisited } = usePageVisitTracker();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  // Check if coming from Google signup
  const fromGoogle = searchParams.get("from") === "google";
  const fromGoogleOAuth = searchParams.get("fromGoogle") === "true";
  const userEmail = searchParams.get("email");

  useEffect(() => {
    markPageVisited('privacy');
    
    // Handle Google OAuth users
    if (fromGoogleOAuth) {
      // Get user info from temporary storage
      const tempUserInfo = localStorage.getItem('temp_user_info');
      const userInfo = tempUserInfo ? JSON.parse(tempUserInfo) : null;
      
      if (userInfo) {
        // Mark privacy as consented
        localStorage.setItem('terms_consent', 'true');
        localStorage.setItem('privacy_consent', 'true');
        
        // Store tokens permanently
        const accessToken = searchParams.get('access_token');
        const refreshToken = searchParams.get('refresh_token');
        
        if (accessToken && refreshToken) {
          localStorage.setItem('access_token', accessToken);
          localStorage.setItem('refresh_token', refreshToken);
          localStorage.setItem('phishcatcher_email', userInfo.email);
          localStorage.setItem('phishcatcher_role', userInfo.role || 'user');
        }
        
        toast.success("Privacy Policy accepted successfully!");
        navigate('/dashboard');
        return;
      }
    }
    
    // Auto-proceed for Google signup users after 3 seconds
    if (fromGoogle && userEmail) {
      const timer = setTimeout(() => {
        // Mark privacy as consented
        localStorage.setItem('privacy_consent', 'true');
        
        // Get tokens from URL (if they were passed)
        const accessToken = searchParams.get("access_token");
        const refreshToken = searchParams.get("refresh_token");
        
        if (accessToken && refreshToken) {
          // Set tokens and redirect to dashboard
          setTokens({ access_token: accessToken, refresh_token: refreshToken });
          toast.success(`Welcome! Your Google account ${userEmail} has been connected.`);
          navigate("/dashboard");
        }
      }, 3000);
      
      return () => clearTimeout(timer);
    }
  }, [fromGoogle, fromGoogleOAuth, navigate, searchParams]);
  return (
    <div className="min-h-screen bg-primary-60">
      {/* Header */}
      <header className="border-b border-violet-500/15">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link to="/" className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-xl bg-white/90 flex items-center justify-center shadow-glow">
                <img
                  src="/phishcatcher.png"
                  alt="PhishCatcher Logo"
                  className="w-8 h-8 object-contain" // Adjusted size to fit comfortably like the icon
                />{" "}
              </div>
              <span className="text-xl font-heading font-bold text-white">
                PhishCatcher
              </span>
            </Link>
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                if (fromGoogle) {
                  // Google users already handled by auto-proceed
                  return;
                }
                navigate("/register");
              }}
              className="inline-flex items-center justify-center rounded-lg text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-violet-500/25 bg-transparent hover:bg-violet-500/10 px-4 py-2 text-white"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              {fromGoogle ? "Processing..." : "Done"}
            </button>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="glass-card-strong rounded-2xl p-8 sm:p-12">
          <h1 className="text-3xl sm:text-4xl font-heading font-bold text-white mb-4">
            Privacy Policy
          </h1>
          <p className="text-muted-foreground mb-8">
            Last updated: January 2026
          </p>

          <div className="prose prose-invert max-w-none">
            <section className="mb-8">
              <h2 className="text-xl font-heading font-semibold text-white mb-4">
                1. Introduction
              </h2>
              <p className="text-muted-foreground mb-4">
                PhishCatcher (&quot;we,&quot; &quot;our,&quot; or
                &quot;us&quot;) is committed to protecting your privacy. This
                Privacy Policy explains how we collect, use, store, and protect
                your personal information when you use our email analysis
                service.
              </p>
              <p className="text-muted-foreground">
                This policy complies with the General Data Protection Regulation
                (GDPR) for users in the European Union and the Kenya Data
                Protection Act, 2019 for users in Kenya.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-heading font-semibold text-white mb-4">
                2. Data Controller
              </h2>
              <p className="text-muted-foreground mb-4">
                For the purposes of applicable data protection laws:
              </p>
              <div className="bg-secondary-30/50 rounded-lg p-4 text-muted-foreground">
                <p>
                  <strong>Data Controller:</strong> PhishCatcher Ltd
                </p>
                <p>
                  <strong>Address:</strong> Nairobi, Kenya
                </p>
                <p>
                  <strong>Email:</strong> privacy@phishcatcher.io
                </p>
                <p>
                  <strong>DPO Email:</strong> dpo@phishcatcher.io
                </p>
              </div>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-heading font-semibold text-white mb-4">
                3. Information We Collect
              </h2>

              <h3 className="text-lg font-medium text-white mb-3">
                3.1 Account Information
              </h3>
              <ul className="list-disc list-inside text-muted-foreground space-y-2 ml-4 mb-4">
                <li>Name and email address</li>
                <li>Company/organization (optional)</li>
                <li>Account credentials (encrypted)</li>
                <li>Profile preferences</li>
              </ul>

              <h3 className="text-lg font-medium text-white mb-3">
                3.2 Email Analysis Data
              </h3>
              <ul className="list-disc list-inside text-muted-foreground space-y-2 ml-4 mb-4">
                <li>Email headers (From, To, Subject, Date, etc.)</li>
                <li>Email body content (for threat analysis only)</li>
                <li>Attachment metadata (filename, size, type)</li>
                <li>URLs and links within emails</li>
              </ul>
              <p className="text-muted-foreground mb-4">
                <strong>Important:</strong> We do not read, store, or process
                email content for any purpose other than threat detection. Email
                content is analyzed in real-time and not retained beyond the
                analysis period.
              </p>

              <h3 className="text-lg font-medium text-white mb-3">
                3.3 Usage Data
              </h3>
              <ul className="list-disc list-inside text-muted-foreground space-y-2 ml-4">
                <li>IP address and browser information</li>
                <li>Device type and operating system</li>
                <li>Pages visited and features used</li>
                <li>Analysis history and timestamps</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-heading font-semibold text-white mb-4">
                4. Legal Basis for Processing (GDPR)
              </h2>
              <p className="text-muted-foreground mb-4">
                We process your personal data based on the following legal
                grounds:
              </p>
              <ul className="list-disc list-inside text-muted-foreground space-y-2 ml-4">
                <li>
                  <strong>Contract:</strong> Processing necessary to provide the
                  Service you requested
                </li>
                <li>
                  <strong>Consent:</strong> Where you have given explicit
                  consent (e.g., marketing communications)
                </li>
                <li>
                  <strong>Legitimate Interests:</strong> Improving our services
                  and ensuring security
                </li>
                <li>
                  <strong>Legal Obligation:</strong> Compliance with applicable
                  laws and regulations
                </li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-heading font-semibold text-white mb-4">
                5. How We Use Your Information
              </h2>
              <ul className="list-disc list-inside text-muted-foreground space-y-2 ml-4">
                <li>To provide and maintain the email analysis service</li>
                <li>To detect and analyze potential email threats</li>
                <li>To generate analysis reports and threat intelligence</li>
                <li>
                  To improve our machine learning models and detection accuracy
                </li>
                <li>
                  To communicate with you about your account and the Service
                </li>
                <li>To respond to your inquiries and support requests</li>
                <li>To ensure the security and integrity of our systems</li>
                <li>To comply with legal obligations</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-heading font-semibold text-white mb-4">
                6. Data Retention
              </h2>
              <table className="w-full text-sm text-muted-foreground mb-4">
                <thead>
                  <tr className="border-b border-violet-500/20">
                    <th className="text-left py-2">Data Type</th>
                    <th className="text-left py-2">Retention Period</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-violet-500/10">
                    <td className="py-2">Account information</td>
                    <td className="py-2">Until account deletion</td>
                  </tr>
                  <tr className="border-b border-violet-500/10">
                    <td className="py-2">Uploaded email files</td>
                    <td className="py-2">30 days after analysis</td>
                  </tr>
                  <tr className="border-b border-violet-500/10">
                    <td className="py-2">Analysis results</td>
                    <td className="py-2">Duration of account + 90 days</td>
                  </tr>
                  <tr className="border-b border-violet-500/10">
                    <td className="py-2">Usage logs</td>
                    <td className="py-2">12 months</td>
                  </tr>
                  <tr>
                    <td className="py-2">Support communications</td>
                    <td className="py-2">3 years</td>
                  </tr>
                </tbody>
              </table>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-heading font-semibold text-white mb-4">
                7. Data Sharing and Transfers
              </h2>
              <p className="text-muted-foreground mb-4">
                We do not sell your personal data. We may share data with:
              </p>
              <ul className="list-disc list-inside text-muted-foreground space-y-2 ml-4 mb-4">
                <li>
                  <strong>Service Providers:</strong> Cloud hosting, analytics,
                  and security vendors (under strict data processing agreements)
                </li>
                <li>
                  <strong>Legal Authorities:</strong> When required by law or to
                  protect our rights
                </li>
                <li>
                  <strong>Threat Intelligence Partners:</strong> Anonymized
                  threat indicators only
                </li>
              </ul>
              <p className="text-muted-foreground">
                International transfers outside the EEA are protected by
                Standard Contractual Clauses approved by the European
                Commission.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-heading font-semibold text-white mb-4">
                8. Your Rights
              </h2>
              <p className="text-muted-foreground mb-4">
                Under GDPR and the Kenya Data Protection Act, you have the
                following rights:
              </p>
              <ul className="list-disc list-inside text-muted-foreground space-y-2 ml-4">
                <li>
                  <strong>Right to Access:</strong> Request a copy of your
                  personal data
                </li>
                <li>
                  <strong>Right to Rectification:</strong> Correct inaccurate or
                  incomplete data
                </li>
                <li>
                  <strong>Right to Erasure:</strong> Request deletion of your
                  data (&quot;Right to be Forgotten&quot;)
                </li>
                <li>
                  <strong>Right to Restrict Processing:</strong> Limit how we
                  use your data
                </li>
                <li>
                  <strong>Right to Data Portability:</strong> Receive your data
                  in a structured format
                </li>
                <li>
                  <strong>Right to Object:</strong> Object to certain types of
                  processing
                </li>
                <li>
                  <strong>Right to Withdraw Consent:</strong> Withdraw consent
                  at any time
                </li>
              </ul>
              <p className="text-muted-foreground mt-4">
                To exercise these rights, contact us at{" "}
                <a
                  href="mailto:privacy@phishcatcher.io"
                  className="text-violet-400 hover:text-violet-300"
                >
                  privacy@phishcatcher.io
                </a>
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-heading font-semibold text-white mb-4">
                9. Data Security
              </h2>
              <p className="text-muted-foreground mb-4">
                We implement appropriate technical and organizational measures
                to protect your data:
              </p>
              <ul className="list-disc list-inside text-muted-foreground space-y-2 ml-4">
                <li>Encryption at rest (AES-256) and in transit (TLS 1.3)</li>
                <li>Regular security audits and penetration testing</li>
                <li>Access controls and authentication mechanisms</li>
                <li>Employee training on data protection</li>
                <li>Incident response procedures</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-heading font-semibold text-white mb-4">
                10. Cookies and Tracking
              </h2>
              <p className="text-muted-foreground mb-4">
                We use cookies and similar technologies to:
              </p>
              <ul className="list-disc list-inside text-muted-foreground space-y-2 ml-4">
                <li>Authenticate users and maintain sessions</li>
                <li>Remember user preferences (including theme settings)</li>
                <li>Analyze usage patterns to improve the Service</li>
              </ul>
              <p className="text-muted-foreground mt-4">
                You can manage cookie preferences through your browser settings.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-heading font-semibold text-white mb-4">
                11. Children&apos;s Privacy
              </h2>
              <p className="text-muted-foreground">
                The Service is not intended for users under 16 years of age. We
                do not knowingly collect personal information from children. If
                you believe we have collected data from a child, please contact
                us immediately.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-heading font-semibold text-white mb-4">
                12. Data Breach Notification
              </h2>
              <p className="text-muted-foreground">
                In the event of a personal data breach, we will notify affected
                users and relevant supervisory authorities within 72 hours of
                becoming aware of the breach, as required by applicable law.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-heading font-semibold text-white mb-4">
                13. Changes to This Policy
              </h2>
              <p className="text-muted-foreground">
                We may update this Privacy Policy from time to time. We will
                notify you of significant changes via email or through the
                Service. The updated policy will indicate the effective date.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-heading font-semibold text-white mb-4">
                14. Contact Us
              </h2>
              <p className="text-muted-foreground mb-4">
                If you have questions or concerns about this Privacy Policy or
                our data practices, please contact us:
              </p>
              <div className="bg-secondary-30/50 rounded-lg p-4 text-muted-foreground">
                <p>
                  <strong>Email:</strong>{" "}
                  <a
                    href="mailto:privacy@phishcatcher.io"
                    className="text-violet-400 hover:text-violet-300"
                  >
                    privacy@phishcatcher.io
                  </a>
                </p>
                <p>
                  <strong>Data Protection Officer:</strong>{" "}
                  <a
                    href="mailto:dpo@phishcatcher.io"
                    className="text-violet-400 hover:text-violet-300"
                  >
                    dpo@phishcatcher.io
                  </a>
                </p>
              </div>
            </section>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-violet-500/15 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p className="text-sm text-muted-foreground">
            © 2026 PhishCatcher. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
