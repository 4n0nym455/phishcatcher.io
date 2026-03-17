import { useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { usePageVisitTracker } from "@/hooks/usePageVisitTracker";
import { toast } from "sonner";
import { setTokens } from "@/lib/api";

export default function TermsOfService() {
  const { markPageVisited } = usePageVisitTracker();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  // Check if coming from Google signup
  const fromGoogle = searchParams.get("from") === "google";
  const fromGoogleOAuth = searchParams.get("fromGoogle") === "true";
  const userEmail = searchParams.get("email");

  useEffect(() => {
    markPageVisited('terms');
    
    // Handle Google OAuth users
    if (fromGoogleOAuth) {
      // Get user info from temporary storage
      const tempUserInfo = localStorage.getItem('temp_user_info');
      const userInfo = tempUserInfo ? JSON.parse(tempUserInfo) : null;
      
      if (userInfo) {
        // Mark terms as consented
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
        
        toast.success("Terms and Privacy accepted successfully!");
        navigate('/dashboard');
        return;
      }
    }
    
    // Handle legacy Google signup (from URL parameters)
    if (fromGoogle && userEmail) {
      const timer = setTimeout(() => {
        // Mark terms as consented
        localStorage.setItem('terms_consent', 'true');
        
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
            <Link to="/" className="flex items-center gap-2">
              <div className="w-15 h-15 rounded-xl bg-primary-60 flex items-center justify-center shadow-glow">
                <img
                  src="/phishcatcher.png"
                  alt="PhishCatcher Logo"
                  className="w-12 h-12 object-contain" // Adjusted size to fit comfortably like the icon
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
                console.log('Terms: Button clicked');
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
            Terms of Service
          </h1>
          <p className="text-muted-foreground mb-8">
            Last updated: January 2026
          </p>

          <div className="prose prose-invert max-w-none">
            <section className="mb-8">
              <h2 className="text-xl font-heading font-semibold text-white mb-4">
                1. Acceptance of Terms
              </h2>
              <p className="text-muted-foreground mb-4">
                By accessing or using PhishCatcher (&quot;the Service&quot;),
                you agree to be bound by these Terms of Service. If you do not
                agree to these terms, please do not use the Service. These terms
                apply to all visitors, users, and others who access or use the
                Service.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-heading font-semibold text-white mb-4">
                2. Description of Service
              </h2>
              <p className="text-muted-foreground mb-4">
                PhishCatcher is a machine learning-based email analysis platform
                that helps users identify potential phishing attempts, malicious
                attachments, and other email-borne threats. The Service
                provides:
              </p>
              <ul className="list-disc list-inside text-muted-foreground space-y-2 ml-4">
                <li>Email file upload and analysis capabilities</li>
                <li>Threat detection and risk scoring</li>
                <li>Comprehensive analysis reports</li>
                <li>Weekly threat intelligence summaries</li>
                <li>API access for enterprise users</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-heading font-semibold text-white mb-4">
                3. User Accounts
              </h2>
              <p className="text-muted-foreground mb-4">
                To access certain features of the Service, you must register for
                an account. You agree to:
              </p>
              <ul className="list-disc list-inside text-muted-foreground space-y-2 ml-4">
                <li>
                  Provide accurate, current, and complete information during
                  registration
                </li>
                <li>
                  Maintain the security of your password and account credentials
                </li>
                <li>
                  Promptly notify us of any unauthorized access or security
                  breaches
                </li>
                <li>
                  Accept responsibility for all activities that occur under your
                  account
                </li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-heading font-semibold text-white mb-4">
                4. Acceptable Use
              </h2>
              <p className="text-muted-foreground mb-4">
                You agree not to use the Service to:
              </p>
              <ul className="list-disc list-inside text-muted-foreground space-y-2 ml-4">
                <li>
                  Upload, analyze, or distribute malware, viruses, or malicious
                  content
                </li>
                <li>
                  Violate any applicable laws, including data protection
                  regulations
                </li>
                <li>Infringe upon intellectual property rights of others</li>
                <li>
                  Attempt to gain unauthorized access to the Service or its
                  systems
                </li>
                <li>
                  Interfere with or disrupt the integrity or performance of the
                  Service
                </li>
                <li>
                  Harvest or collect email addresses or other personal data
                  without consent
                </li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-heading font-semibold text-white mb-4">
                5. Data Processing and Privacy
              </h2>
              <p className="text-muted-foreground mb-4">
                Your use of the Service is also governed by our Privacy Policy.
                By using the Service, you consent to the collection, processing,
                and storage of your data as described in the Privacy Policy. We
                comply with:
              </p>
              <ul className="list-disc list-inside text-muted-foreground space-y-2 ml-4">
                <li>General Data Protection Regulation (GDPR) - EU users</li>
                <li>Kenya Data Protection Act, 2019 - Kenyan users</li>
                <li>Applicable data protection laws in your jurisdiction</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-heading font-semibold text-white mb-4">
                6. Email Analysis and Data Retention
              </h2>
              <p className="text-muted-foreground mb-4">
                When you upload email files for analysis:
              </p>
              <ul className="list-disc list-inside text-muted-foreground space-y-2 ml-4">
                <li>
                  Email content is processed solely for threat detection
                  purposes
                </li>
                <li>
                  We do not read, store, or analyze email content for any other
                  purpose
                </li>
                <li>
                  Uploaded files are retained for 30 days for quality assurance
                  and model improvement
                </li>
                <li>You may request deletion of your data at any time</li>
                <li>
                  Analysis results are stored for the duration of your account
                </li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-heading font-semibold text-white mb-4">
                7. Disclaimer of Warranties
              </h2>
              <p className="text-muted-foreground mb-4">
                THE SERVICE IS PROVIDED &quot;AS IS&quot; AND &quot;AS
                AVAILABLE&quot; WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS
                OR IMPLIED. PhishCatcher:
              </p>
              <ul className="list-disc list-inside text-muted-foreground space-y-2 ml-4">
                <li>Does not guarantee 100% detection of all threats</li>
                <li>May produce false positives or false negatives</li>
                <li>Is not a substitute for comprehensive security measures</li>
                <li>Does not block or prevent email delivery</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-heading font-semibold text-white mb-4">
                8. Limitation of Liability
              </h2>
              <p className="text-muted-foreground mb-4">
                TO THE MAXIMUM EXTENT PERMITTED BY LAW, PhishCatcher SHALL NOT
                BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL,
                OR PUNITIVE DAMAGES ARISING FROM YOUR USE OF THE SERVICE,
                INCLUDING BUT NOT LIMITED TO:
              </p>
              <ul className="list-disc list-inside text-muted-foreground space-y-2 ml-4">
                <li>Loss of data or profits</li>
                <li>Security breaches that occur despite our analysis</li>
                <li>Reliance on analysis results</li>
                <li>Service interruptions or downtime</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-heading font-semibold text-white mb-4">
                9. Termination
              </h2>
              <p className="text-muted-foreground mb-4">
                We may terminate or suspend your account immediately, without
                prior notice or liability, for any reason, including breach of
                these Terms. Upon termination, your right to use the Service
                will immediately cease. You may also delete your account at any
                time.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-heading font-semibold text-white mb-4">
                10. Governing Law
              </h2>
              <p className="text-muted-foreground mb-4">
                These Terms shall be governed by and construed in accordance
                with the laws of Kenya, without regard to its conflict of law
                provisions. For EU users, mandatory provisions of EU consumer
                protection law shall apply.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-heading font-semibold text-white mb-4">
                11. Changes to Terms
              </h2>
              <p className="text-muted-foreground mb-4">
                We reserve the right to modify these Terms at any time. We will
                notify users of significant changes via email or through the
                Service. Continued use of the Service after changes constitutes
                acceptance of the modified Terms.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-heading font-semibold text-white mb-4">
                12. Contact Information
              </h2>
              <p className="text-muted-foreground">
                For questions about these Terms, please contact us at:{" "}
                <a
                  href="mailto:legal@phishcatcher.io"
                  className="text-violet-400 hover:text-violet-300"
                >
                  legal@phishcatcher.io
                </a>
              </p>
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
