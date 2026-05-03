/**
 * RegisterPage.jsx
 * Registration with:
 *  - Full name, email, company (optional)
 *  - Password + confirm password with live match feedback
 *  - 4-bar password strength indicator
 *  - Mandatory Terms + Privacy checkboxes — submit blocked until both checked
 */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Eye, EyeOff, ArrowRight, Loader2, CheckCircle2, XCircle } from 'lucide-react';
import { toast } from 'sonner';
import { authApi } from '@/lib/api';

/* ─── Password strength ─────────────────────────────────────────────────── */
const PWD_RULES = [
  { id: 'len',   label: '8+ chars',  test: p => p.length >= 8 },
  { id: 'upper', label: 'Uppercase', test: p => /[A-Z]/.test(p) },
  { id: 'num',   label: 'Number',    test: p => /\d/.test(p) },
  { id: 'sym',   label: 'Symbol',    test: p => /[!@#$%^&*(),.?":{}|<>_\-]/.test(p) },
];
const STRENGTH_COLORS = ['', 'var(--danger)', 'var(--threat)', 'var(--threat)', 'var(--success)'];
const STRENGTH_LABELS = ['', 'Weak', 'Fair', 'Good', 'Strong'];

function PasswordStrength({ password }) {
  if (!password) return null;
  const score = PWD_RULES.filter(r => r.test(password)).length;
  return (
    <div className="mt-2 space-y-2">
      <div className="flex gap-1">
        {[1, 2, 3, 4].map(i => (
          <div
            key={i}
            className="h-1 flex-1 rounded-full transition-all duration-300"
            style={{ background: i <= score ? STRENGTH_COLORS[score] : 'var(--border)' }}
          />
        ))}
      </div>
      <div className="flex items-center justify-between flex-wrap gap-y-1">
        {PWD_RULES.map(r => {
          const ok = r.test(password);
          return (
            <span
              key={r.id}
              className="text-[11px] font-500 flex items-center gap-1"
              style={{ color: ok ? 'var(--success)' : 'var(--text-muted)' }}
            >
              {ok ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
              {r.label}
            </span>
          );
        })}
        {score > 0 && (
          <span className="text-[11px] font-700" style={{ color: STRENGTH_COLORS[score] }}>
            {STRENGTH_LABELS[score]}
          </span>
        )}
      </div>
    </div>
  );
}

/* ─── Custom checkbox ───────────────────────────────────────────────────── */
function Checkbox({ id, checked, onChange, children }) {
  return (
    <label htmlFor={id} className="flex items-start gap-3 cursor-pointer">
      <div
        id={id}
        role="checkbox"
        aria-checked={checked}
        tabIndex={0}
        onClick={() => onChange(!checked)}
        onKeyDown={e => (e.key === ' ' || e.key === 'Enter') && onChange(!checked)}
        className="w-5 h-5 rounded-md border-2 flex items-center justify-center shrink-0 mt-0.5 transition-all cursor-pointer"
        style={{
          borderColor: checked ? 'var(--brand)' : 'var(--border-strong)',
          background:  checked ? 'var(--brand)' : 'transparent',
        }}
      >
        {checked && (
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="white" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        )}
      </div>
      <span className="text-sm leading-snug" style={{ color: 'var(--text-secondary)' }}>
        {children}
      </span>
    </label>
  );
}

/* ─── Main component ───────────────────────────────────────────────────── */
export default function RegisterPage() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    fullName:        '',
    email:           '',
    company:         '',
    phone:           '',
    password:        '',
    confirmPassword: '',
  });
  const [showPwd,     setShowPwd]     = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [termsOk,     setTermsOk]     = useState(false);
  const [privacyOk,   setPrivacyOk]   = useState(false);
  const [loading,     setLoading]     = useState(false);
  const [error,       setError]       = useState('');

  const set = key => e => setForm(prev => ({ ...prev, [key]: e.target.value }));

  const passwordsMatch = form.password === form.confirmPassword;
  const confirmDirty   = form.confirmPassword.length > 0;
  const allAgreed      = termsOk && privacyOk;
  const canSubmit      = allAgreed && !loading && (!confirmDirty || passwordsMatch);

  const phoneDigits = form.phone.replace(/[^+\d]/g, '');
  const phoneValid = phoneDigits === '' || /^\+\d{7,15}$/.test(phoneDigits);

  const handleSubmit = async e => {
    e.preventDefault();
    setError('');

    if (!passwordsMatch)
      return setError('Passwords do not match.');
    if (!allAgreed)
      return setError('You must accept both the Terms of Service and Privacy Policy to create an account.');
    if (form.phone && !phoneValid)
      return setError('Phone number must be in E.164 format (e.g., +254876543210).');

    setLoading(true);
    try {
      await authApi.register({
        email:                 form.email,
        password:              form.password,
        fullName:              form.fullName,
        company:               form.company || undefined,
        phone:                 form.phone || undefined,
        acceptTermsAndPrivacy: true,
      });
      toast.success('Account created! Check your email to activate it.');
      navigate('/activation-pending', { state: { email: form.email } });
    } catch (err) {
      setError(err.message ?? 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-bg flex items-center justify-center p-4 py-10">
      <div className="w-full max-w-[460px] animate-slide-up">

        {/* Logo */}
        <div className="flex justify-center mb-8">
          <Link to="/" className="flex items-center gap-2.5">
            <img src="/phishcatcher.png" alt="PhishCatcher" className="w-9 h-9 object-contain" />
            <span className="font-heading font-700 text-xl" style={{ color: 'var(--text-primary)' }}>
              PhishCatcher
            </span>
          </Link>
        </div>

        <div className="auth-card">
          <div className="mb-6">
            <h1 className="font-heading text-2xl font-700 mb-1" style={{ color: 'var(--text-primary)' }}>
              Create your account
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              Start catching phishing attacks in minutes.
            </p>
          </div>

          {error && <div className="alert-error mb-5">{error}</div>}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Hidden dummy password field to satisfy browser password manager */}
            <input
              type="password"
              name="hidden-password"
              autoComplete="current-password"
              tabIndex={-1}
              aria-hidden="true"
              style={{ position: 'absolute', left: '-9999px', width: '1px', height: '1px', opacity: 0 }}
            />

            {/* Full name */}
            <div>
              <label className="form-label">Full name</label>
              <input
                type="text"
                value={form.fullName}
                onChange={set('fullName')}
                placeholder="Jane Smith"
                required
                autoComplete="off"
                className="input-base"
              />
            </div>

            {/* Email */}
            <div>
              <label className="form-label">Email address</label>
              <input
                type="email"
                value={form.email}
                onChange={set('email')}
                placeholder="you@company.com"
                required
                autoComplete="off"
                spellCheck="false"
                className="input-base"
              />
            </div>

            {/* Company */}
            <div>
              <label className="form-label">
                Company
                <span
                  className="ml-1.5 normal-case tracking-normal text-xs font-400"
                  style={{ color: 'var(--text-muted)' }}
                >(optional)</span>
              </label>
              <input
                type="text"
                value={form.company}
                onChange={set('company')}
                placeholder="Acme Corp"
                autoComplete="off"
                className="input-base"
              />
            </div>

            {/* Phone (optional) */}
            <div>
              <label className="form-label">
                Phone number
                <span
                  className="ml-1.5 normal-case tracking-normal text-xs font-400"
                  style={{ color: 'var(--text-muted)' }}
                >(optional)</span>
              </label>
              <input
                type="tel"
                value={form.phone}
                onChange={e => {
                  const raw = e.target.value;
                  const digits = raw.replace(/[^+\d]/g, '');
                  set('phone')({ target: { value: digits } });
                }}
                placeholder="+254876543210"
                autoComplete="tel"
                className="input-base"
                style={!phoneValid && form.phone ? {
                  borderColor: 'var(--danger)',
                  boxShadow: '0 0 0 3px rgba(239,68,68,0.12)',
                } : {}}
              />
              {form.phone && !phoneValid && (
                <p className="text-xs mt-1.5 font-500 flex items-center gap-1" style={{ color: 'var(--danger)' }}>
                  <XCircle className="w-3.5 h-3.5" /> E.164 format required (e.g., +254876543210)
                </p>
              )}
              {form.phone && phoneValid && (
                <p className="text-xs mt-1.5 font-500 flex items-center gap-1" style={{ color: 'var(--success)' }}>
                  <CheckCircle2 className="w-3.5 h-3.5" /> Valid format
                </p>
              )}
              <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                Used for SMS OTP during login. We'll send a verification code.
              </p>
            </div>

            {/* Password */}
            <div>
              <label className="form-label">Password</label>
              <div className="relative">
                <input
                  type={showPwd ? 'text' : 'password'}
                  value={form.password}
                  onChange={set('password')}
                  placeholder="••••••••"
                  required
                  autoComplete="new-password"
                  className="input-base pr-10"
                />
                <button
                  type="button"
                  tabIndex={-1}
                  onClick={() => setShowPwd(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2"
                  style={{ color: 'var(--text-muted)' }}
                >
                  {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <PasswordStrength password={form.password} />
            </div>

            {/* Confirm password */}
            <div>
              <label className="form-label">Confirm password</label>
              <div className="relative">
                <input
                  type={showConfirm ? 'text' : 'password'}
                  value={form.confirmPassword}
                  onChange={set('confirmPassword')}
                  placeholder="••••••••"
                  required
                  autoComplete="new-password"
                  className="input-base pr-10"
                  style={confirmDirty ? {
                    borderColor: passwordsMatch ? 'var(--success)' : 'var(--danger)',
                    boxShadow: passwordsMatch
                      ? '0 0 0 3px rgba(16,185,129,0.12)'
                      : '0 0 0 3px rgba(239,68,68,0.12)',
                  } : {}}
                />
                <button
                  type="button"
                  tabIndex={-1}
                  onClick={() => setShowConfirm(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2"
                  style={{ color: 'var(--text-muted)' }}
                >
                  {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {confirmDirty && !passwordsMatch && (
                <p className="text-xs mt-1.5 font-500 flex items-center gap-1" style={{ color: 'var(--danger)' }}>
                  <XCircle className="w-3.5 h-3.5" /> Passwords do not match
                </p>
              )}
              {confirmDirty && passwordsMatch && (
                <p className="text-xs mt-1.5 font-500 flex items-center gap-1" style={{ color: 'var(--success)' }}>
                  <CheckCircle2 className="w-3.5 h-3.5" /> Passwords match
                </p>
              )}
            </div>

            {/* ── Legal agreements — both REQUIRED ── */}
            <div
              className="rounded-xl p-4 space-y-3"
              style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}
            >
              <p className="text-xs font-700 uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
                Required agreements
              </p>

              <Checkbox id="cb-terms" checked={termsOk} onChange={setTermsOk}>
                I have read and agree to the{' '}
                <Link
                  to="/terms"
                  target="_blank"
                  rel="noreferrer"
                  className="font-600 underline decoration-dotted hover:opacity-80"
                  style={{ color: 'var(--brand)' }}
                  onClick={e => e.stopPropagation()}
                >
                  Terms of Service
                </Link>
              </Checkbox>

              <Checkbox id="cb-privacy" checked={privacyOk} onChange={setPrivacyOk}>
                I have read and agree to the{' '}
                <Link
                  to="/privacy"
                  target="_blank"
                  rel="noreferrer"
                  className="font-600 underline decoration-dotted hover:opacity-80"
                  style={{ color: 'var(--brand)' }}
                  onClick={e => e.stopPropagation()}
                >
                  Privacy Policy
                </Link>
              </Checkbox>

              {!allAgreed && (
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  Both agreements are required to create an account.
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={!canSubmit}
              className="btn-primary w-full h-11 justify-center"
            >
              {loading
                ? <Loader2 className="w-4 h-4 animate-spin" />
                : <>Create account <ArrowRight className="w-4 h-4" /></>
              }
            </button>
          </form>

          <p className="text-center text-sm mt-5" style={{ color: 'var(--text-muted)' }}>
            Already have an account?{' '}
            <Link to="/login" className="font-600 hover:underline" style={{ color: 'var(--brand)' }}>
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}