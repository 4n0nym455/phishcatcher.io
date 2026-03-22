import { useEffect, useState, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { authApi, setTokens } from "@/lib/api";
import { oauthService } from "@/lib/oauthService";

export default function GoogleCallbackPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Get URL parameters safely - handle special characters in authorization code
  const code = searchParams.get("code");
  const state = searchParams.get("state");
  const error = searchParams.get("error");

  // State to store the OAuth state from parent window
  const [oauthState, setOauthState] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processedCode, setProcessedCode] = useState(null);

  // Immediate synchronous guard to prevent double processing
  const processedRef = useRef(false);

  // Listen for OAuth state from parent window
  useEffect(() => {
    const messageHandler = (event) => {
      // Verify origin for security
      if (event.origin !== window.location.origin) return;

      if (event.data.type === "OAUTH_STATE") {
        setOauthState(event.data.state);
      }
    };

    window.addEventListener("message", messageHandler);

    // Request OAuth state from parent window
    if (window.opener && !window.opener.closed) {
      window.opener.postMessage(
        { type: "REQUEST_OAUTH_STATE" },
        window.location.origin,
      );
    }

    return () => {
      window.removeEventListener("message", messageHandler);
    };
  }, []);

  useEffect(() => {
    // Process OAuth callback IMMEDIATELY - no delays, no waiting
    // Add multiple layers of protection against duplicate processing
    if (code && !processedRef.current && code !== processedCode) {
      console.log("🚀 Processing OAuth callback IMMEDIATELY...");
      console.log("🔍 Code exists:", !!code);
      console.log("🔍 processedRef.current:", processedRef.current);
      console.log("🔍 code !== processedCode:", code !== processedCode);

      // Set all protection flags immediately
      processedRef.current = true;
      setIsProcessing(true);
      setProcessedCode(code);

      // Process RIGHT NOW - no async delays
      (async () => {
        try {
          console.log(
            "⏰ Immediate processing start:",
            new Date().toISOString(),
          );

          // Use URL state directly - no waiting for parent window
          const response = await oauthService.handleOAuthCallback(code, state);

          console.log("✅ OAuth callback response:", response);

          if (response.mfa_required) {
            localStorage.setItem(
              "mfa_session_token",
              response.mfa_session_token,
            );
            localStorage.setItem("mfa_user", JSON.stringify(response.user));
            oauthService.closePopup("google-auth-mfa-required");
            return;
          }

          if (response.activation_required) {
            // New user - activation required
            // Store activation info for the activation pending page
            const activationInfo = {
              email: response.email,
              full_name: response.full_name,
              message:
                response.message ||
                "Please check your email for activation instructions",
            };

            // Store activation info temporarily
            localStorage.setItem(
              "pending_activation",
              JSON.stringify(activationInfo),
            );

            // Close popup and notify parent to redirect to activation pending
            oauthService.closePopup("google-auth-activation-required");
            return;
          }

          if (response.access_token) {
            // Existing active user - direct login
            setTokens(response);
            if (response.user) {
              localStorage.setItem("phishcatcher_email", response.user.email);
              localStorage.setItem(
                "phishcatcher_role",
                response.user.role || "user",
              );
              localStorage.setItem(
                "phishcatcher_name",
                response.user.full_name || "",
              );
              // Store login method for MFA detection
              localStorage.setItem("login_method", "oauth");
            }
            oauthService.closePopup("google-auth-success");
            return;
          }

          throw new Error(
            "Failed to authenticate with Google - no valid response received",
          );
        } catch (error) {
          console.error("❌ OAuth callback error:", error);

          // Show error in popup and notify parent
          document.body.innerHTML = `
            <div style="padding: 20px; font-family: Arial, sans-serif; text-align: center; max-width: 400px;">
              <h2>❌ Authentication Error</h2>
              <p><strong>Error:</strong> ${error.message}</p>
              <p>This window will close in 5 seconds...</p>
            </div>
          `;

          oauthService.closePopup("google-auth-error", 5000);
        }
      })();
    } else {
      console.log("🔄 Skipping OAuth processing:");
      console.log("🔍 Code exists:", !!code);
      console.log("🔍 processedRef.current:", processedRef.current);
      console.log("🔍 code !== processedCode:", code !== processedCode);
    }
  }, [code, state, oauthState, navigate]);

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-slate-800/50 backdrop-blur-xl border border-violet-500/20 rounded-2xl p-8 text-center">
        <div className="w-12 h-12 bg-violet-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
          <div className="w-6 h-6 bg-violet-500 rounded-full animate-pulse"></div>
        </div>

        <h1 className="text-2xl font-bold text-white mb-4">
          {error ? "Authentication Error" : "Processing Authentication"}
        </h1>

        <p className="text-gray-300 mb-6">
          {isProcessing
            ? "Processing your authentication..."
            : "Please wait..."}
        </p>

        {error && (
          <div className="bg-red-500/20 border border-red-500/30 rounded-lg p-4 mb-6">
            <p className="text-red-300 text-sm">Error: {error}</p>
          </div>
        )}
      </div>
    </div>
  );
}
