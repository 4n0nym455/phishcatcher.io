/**
 * LandingPage.jsx
 * Public marketing page. Full light/dark mode via CSS variables.
 * Logo: /phishcatcher.png  — no orb image needed, uses CSS blobs.
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Shield, Zap, BarChart3, Mail, Lock, CheckCircle,
  AlertTriangle, ArrowRight, ChevronRight, Eye, TrendingUp,
  Menu, X,
} from 'lucide-react';

/* ─── Background orb ─────────────────────────────────────────────────────── */
function CssOrb({ style = {} }) {
  return (
    <div
      className="absolute rounded-full pointer-events-none select-none"
      style={{ filter: 'blur(90px)', ...style }}
    />
  );
}

/* ─── Navbar ──────────────────────────────────────────────────────────────── */
function NavBar() {
  const [open, setOpen]       = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const h = () => setScrolled(window.scrollY > 24);
    window.addEventListener('scroll', h);
    return () => window.removeEventListener('scroll', h);
  }, []);

  const links = ['#features', '#how-it-works', '#security'];
  const labels = ['Features', 'How it works', 'Security'];

  return (
    <nav
      className="fixed top-0 left-0 right-0 z-50 transition-all duration-300"
      style={{
        background: scrolled ? 'var(--bg-overlay)' : 'transparent',
        backdropFilter: scrolled ? 'blur(16px)' : 'none',
        borderBottom: scrolled ? '1px solid var(--border)' : 'none',
      }}
    >
      <div className="max-w-6xl mx-auto px-5 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5">
          <img src="/phishcatcher.png" alt="PhishCatcher" className="w-8 h-8 object-contain" />
          <span className="font-heading font-700 text-[15px]" style={{ color: 'var(--text-primary)' }}>
            PhishCatcher
          </span>
        </Link>

        <div className="hidden md:flex items-center gap-8">
          {links.map((href, i) => (
            <a
              key={href}
              href={href}
              className="text-sm font-500 transition-opacity hover:opacity-70"
              style={{ color: 'var(--text-muted)' }}
            >
              {labels[i]}
            </a>
          ))}
        </div>

        <div className="hidden md:flex items-center gap-3">
          <Link to="/login" className="text-sm font-500 px-4 py-2 rounded-lg transition-opacity hover:opacity-70"
            style={{ color: 'var(--text-secondary)' }}>
            Sign in
          </Link>
          <Link to="/register" className="btn-primary text-sm h-9 px-5">
            Get started <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <button
          className="md:hidden p-2 rounded-lg"
          style={{ color: 'var(--text-muted)' }}
          onClick={() => setOpen(v => !v)}
        >
          {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {open && (
        <div
          className="md:hidden px-5 pb-5 space-y-1"
          style={{ background: 'var(--bg-surface)', borderBottom: '1px solid var(--border)' }}
        >
          {links.map((href, i) => (
            <a
              key={href}
              href={href}
              onClick={() => setOpen(false)}
              className="block py-2.5 text-sm font-500"
              style={{ color: 'var(--text-secondary)', borderBottom: '1px solid var(--border)' }}
            >
              {labels[i]}
            </a>
          ))}
          <div className="pt-3 flex flex-col gap-2">
            <Link to="/login" onClick={() => setOpen(false)} className="btn-ghost h-10 justify-center text-sm">
              Sign in
            </Link>
            <Link to="/register" onClick={() => setOpen(false)} className="btn-primary h-10 justify-center text-sm">
              Get started
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}

/* ─── Data ────────────────────────────────────────────────────────────────── */
const FEATURES = [
  {
    icon: Shield, title: 'AI Threat Detection', color: 'var(--brand)', bg: 'var(--brand-dim)',
    desc: 'ML model trained on millions of phishing samples. Detects spoofed domains, malicious URLs, and social engineering with 97.4% accuracy.',
  },
  {
    icon: Zap, title: 'Real-Time Analysis', color: 'var(--threat)', bg: 'var(--threat-dim)',
    desc: 'Upload any .eml file and receive a full threat report in under 3 seconds — with risk score, category, and per-indicator breakdown.',
  },
  {
    icon: BarChart3, title: 'Weekly Reports', color: 'var(--success)', bg: 'var(--success-dim)',
    desc: 'Automated weekly threat intelligence summaries showing attack trends, patterns, and your organisation\'s evolving risk posture.',
  },
  {
    icon: Mail, title: 'Gmail Integration', color: 'var(--brand)', bg: 'var(--brand-dim)',
    desc: 'Connect your Gmail inbox via OAuth 2.0. PhishCatcher continuously monitors incoming mail and flags threats in real time.',
  },
  {
    icon: Lock, title: 'Enterprise Security', color: 'var(--danger)', bg: 'var(--danger-dim)',
    desc: 'MFA, OTP email login, Redis-backed sessions, encrypted secrets, and a full immutable audit log on every action.',
  },
  {
    icon: Eye, title: 'Deep Threat Intel', color: 'var(--threat)', bg: 'var(--threat-dim)',
    desc: 'Per-email breakdown of sender spoofing, header anomalies, link redirection chains, urgency language, and impersonation signals.',
  },
];

const STATS = [
  { value: '97.4%', label: 'Detection accuracy' },
  { value: '<3s',   label: 'Analysis time'      },
  { value: '50K+',  label: 'Emails analyzed'    },
  { value: '12+',   label: 'Threat categories'  },
];

const HOW_STEPS = [
  { n: '01', title: 'Upload your email', desc: 'Drag and drop an .eml file, or connect Gmail for automatic continuous monitoring.' },
  { n: '02', title: 'AI analysis',       desc: 'Headers, links, sender reputation, language patterns, and known attack signatures — all checked in parallel.' },
  { n: '03', title: 'Get your report',   desc: 'A threat score, category, and full indicator breakdown ready in under 3 seconds.' },
];

const SECURITY_ITEMS = [
  { icon: Lock,         title: 'End-to-end encryption',   desc: 'All data is TLS 1.3 in transit. Email body content is never permanently stored.' },
  { icon: Shield,       title: 'Multi-factor auth',        desc: 'TOTP 2FA with backup codes, plus OTP email verification on every login attempt.' },
  { icon: TrendingUp,   title: 'Audit logging',            desc: 'Every action timestamped with IP and user agent for compliance and forensics.' },
  { icon: CheckCircle,  title: 'Redis sessions',           desc: 'Short-lived JWTs with server-side invalidation — logout is immediate across all devices.' },
];

/* ─── Main ────────────────────────────────────────────────────────────────── */
export default function LandingPage() {
  return (
    <div style={{ background: 'var(--bg-base)', color: 'var(--text-primary)', minHeight: '100dvh' }}>
      <NavBar />

      {/* ═══ HERO ════════════════════════════════════════════════════════════ */}
      <section className="relative pt-36 pb-28 px-5 overflow-hidden">
        <CssOrb style={{ width: 700, height: 700, top: -200, left: -200, background: 'var(--brand)', opacity: 0.12 }} />
        <CssOrb style={{ width: 500, height: 500, top: -50, right: -100, background: 'var(--threat)', opacity: 0.09 }} />

        <div className="max-w-5xl mx-auto text-center relative z-10">
          {/* Badge */}
          <div
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-600 mb-8 animate-fade-in"
            style={{ background: 'var(--brand-dim)', color: 'var(--brand)', border: '1px solid var(--brand)' }}
          >
            <Zap className="w-3 h-3" />
            AI-powered phishing detection · 97.4% accuracy
          </div>

          <h1
            className="font-heading font-800 mb-6 animate-slide-up"
            style={{ fontSize: 'clamp(2.4rem, 6vw, 4.2rem)', lineHeight: 1.08, color: 'var(--text-primary)' }}
          >
            Stop phishing attacks<br />
            <span style={{ color: 'var(--brand)' }}>before they land</span>
          </h1>

          <p
            className="text-lg max-w-2xl mx-auto mb-10 animate-slide-up animate-stagger-1"
            style={{ color: 'var(--text-muted)', lineHeight: 1.75 }}
          >
            PhishCatcher analyzes emails in real time using advanced ML —
            catching sophisticated attacks that bypass traditional filters in under 3 seconds.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-slide-up animate-stagger-2">
            <Link to="/register" className="btn-primary h-12 px-9 text-[15px]">
              Start for free <ArrowRight className="w-5 h-5" />
            </Link>
            <Link to="/login" className="btn-ghost h-12 px-9 text-[15px]">
              Sign in <ChevronRight className="w-4 h-4" />
            </Link>
          </div>

          <div
            className="flex flex-wrap items-center justify-center gap-6 mt-10 text-sm animate-fade-in animate-stagger-3"
            style={{ color: 'var(--text-muted)' }}
          >
            {['No credit card required', 'Free tier available', 'SOC 2 aligned'].map(t => (
              <span key={t} className="flex items-center gap-1.5">
                <CheckCircle className="w-4 h-4" style={{ color: 'var(--success)' }} /> {t}
              </span>
            ))}
          </div>
        </div>

        {/* Demo card */}
        <div className="max-w-3xl mx-auto mt-16 relative z-10 animate-slide-up animate-stagger-4">
          <div
            className="rounded-2xl overflow-hidden"
            style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', boxShadow: 'var(--shadow-lg)' }}
          >
            {/* window chrome */}
            <div
              className="flex items-center gap-2 px-4 py-3"
              style={{ background: 'var(--bg-elevated)', borderBottom: '1px solid var(--border)' }}
            >
              <span className="w-3 h-3 rounded-full" style={{ background: '#f87171' }} />
              <span className="w-3 h-3 rounded-full" style={{ background: '#fbbf24' }} />
              <span className="w-3 h-3 rounded-full" style={{ background: '#34d399' }} />
              <span className="mx-auto text-xs font-500" style={{ color: 'var(--text-muted)' }}>
                PhishCatcher — Threat Analysis
              </span>
            </div>
            <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-5">
              {/* Email preview */}
              <div className="space-y-3">
                <p className="text-xs font-700 uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
                  Analyzed Email
                </p>
                {[
                  { label: 'From',     value: 'security@paypa1.com',            warn: true  },
                  { label: 'Subject',  value: 'Your account needs verification', warn: false },
                  { label: 'Reply-To', value: 'collect@attacker.xyz',            warn: true  },
                  { label: 'Link',     value: 'http://paypa1-login.tk/verify',   warn: true  },
                ].map(r => (
                  <div key={r.label} className="flex gap-2">
                    <span className="text-xs font-600 w-16 shrink-0 pt-0.5" style={{ color: 'var(--text-muted)' }}>
                      {r.label}
                    </span>
                    <span className="text-xs leading-relaxed" style={{ color: r.warn ? 'var(--danger)' : 'var(--text-secondary)' }}>
                      {r.warn && <AlertTriangle className="w-3 h-3 inline mr-1 mb-0.5" />}
                      {r.value}
                    </span>
                  </div>
                ))}
              </div>
              {/* Threat score */}
              <div
                className="rounded-xl p-4"
                style={{ background: 'var(--danger-dim)', border: '1px solid var(--danger)' }}
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-700 uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
                    Threat Score
                  </span>
                  <span className="badge badge-danger">HIGH RISK</span>
                </div>
                <div
                  className="font-heading font-800 mb-0.5"
                  style={{ fontSize: '3.5rem', lineHeight: 1, color: 'var(--danger)' }}
                >
                  94
                </div>
                <p className="text-xs mb-4" style={{ color: 'var(--text-muted)' }}>out of 100</p>
                <div className="space-y-2">
                  {['Spoofed sender domain', 'Malicious redirect URL', 'Urgency manipulation', 'Lookalike domain'].map(f => (
                    <div key={f} className="flex items-center gap-2 text-xs" style={{ color: 'var(--danger)' }}>
                      <AlertTriangle className="w-3 h-3 shrink-0" /> {f}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ STATS ═══════════════════════════════════════════════════════════ */}
      <section style={{ borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)' }}>
        <div className="max-w-4xl mx-auto px-5 py-12 grid grid-cols-2 md:grid-cols-4 gap-8">
          {STATS.map(s => (
            <div key={s.label} className="text-center">
              <div className="font-heading font-800 text-3xl mb-1" style={{ color: 'var(--brand)' }}>{s.value}</div>
              <div className="text-sm" style={{ color: 'var(--text-muted)' }}>{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ═══ FEATURES ════════════════════════════════════════════════════════ */}
      <section id="features" className="py-24 px-5">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="font-heading font-700 text-3xl md:text-4xl mb-4">Everything you need to stay safe</h2>
            <p className="text-lg max-w-xl mx-auto" style={{ color: 'var(--text-muted)' }}>
              Professional-grade threat detection without the enterprise price tag.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {FEATURES.map((f, i) => (
              <div
                key={f.title}
                className="card p-6 theme-transition animate-fade-in"
                style={{ animationDelay: `${i * 0.07}s` }}
              >
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center mb-4"
                  style={{ background: f.bg, color: f.color }}
                >
                  <f.icon className="w-5 h-5" />
                </div>
                <h3 className="font-heading font-700 text-[15px] mb-2" style={{ color: 'var(--text-primary)' }}>
                  {f.title}
                </h3>
                <p className="text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ HOW IT WORKS ════════════════════════════════════════════════════ */}
      <section id="how-it-works" className="py-24 px-5" style={{ background: 'var(--bg-surface)' }}>
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="font-heading font-700 text-3xl md:text-4xl mb-4">How it works</h2>
            <p className="text-lg" style={{ color: 'var(--text-muted)' }}>From upload to report in under 10 seconds.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
            {HOW_STEPS.map((step, i) => (
              <div key={step.n} className="text-center animate-slide-up" style={{ animationDelay: `${i * 0.1}s` }}>
                <div
                  className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4 font-heading font-800 text-xl"
                  style={{ background: 'var(--brand-dim)', color: 'var(--brand)' }}
                >
                  {step.n}
                </div>
                <h3 className="font-heading font-700 text-lg mb-2" style={{ color: 'var(--text-primary)' }}>{step.title}</h3>
                <p className="text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ SECURITY ════════════════════════════════════════════════════════ */}
      <section id="security" className="py-24 px-5">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="font-heading font-700 text-3xl md:text-4xl mb-4">Built with security first</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {SECURITY_ITEMS.map(item => (
              <div
                key={item.title}
                className="flex gap-4 p-5 rounded-2xl theme-transition"
                style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
              >
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                  style={{ background: 'var(--brand-dim)', color: 'var(--brand)' }}
                >
                  <item.icon className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="font-heading font-700 text-sm mb-1" style={{ color: 'var(--text-primary)' }}>{item.title}</h4>
                  <p className="text-sm" style={{ color: 'var(--text-muted)' }}>{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ CTA ═════════════════════════════════════════════════════════════ */}
      <section className="py-24 px-5 relative overflow-hidden">
        <CssOrb style={{ width: 600, height: 600, bottom: -150, right: -100, background: 'var(--brand)', opacity: 0.1 }} />
        <div
          className="max-w-2xl mx-auto text-center rounded-3xl p-12 relative z-10"
          style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', boxShadow: 'var(--shadow-lg)' }}
        >
          <img src="/phishcatcher.png" alt="PhishCatcher" className="w-14 h-14 object-contain mx-auto mb-6" />
          <h2 className="font-heading font-800 text-3xl mb-4" style={{ color: 'var(--text-primary)' }}>
            Protect your inbox today
          </h2>
          <p className="mb-8 text-lg" style={{ color: 'var(--text-muted)' }}>
            Join thousands of users who trust PhishCatcher to guard against email-based attacks.
          </p>
          <Link to="/register" className="btn-primary h-12 px-10 text-[15px] inline-flex">
            Create free account <ArrowRight className="w-5 h-5" />
          </Link>
          <p className="mt-4 text-xs" style={{ color: 'var(--text-muted)' }}>
            No credit card required · Cancel anytime
          </p>
        </div>
      </section>

      {/* ═══ FOOTER ══════════════════════════════════════════════════════════ */}
      <footer className="px-5 py-8" style={{ borderTop: '1px solid var(--border)' }}>
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <img src="/phishcatcher.png" alt="PhishCatcher" className="w-5 h-5 object-contain" />
            <span className="text-sm font-600" style={{ color: 'var(--text-secondary)' }}>PhishCatcher</span>
          </div>
          <div className="flex gap-6 text-sm">
            {[{ label: 'Terms', to: '/terms' }, { label: 'Privacy', to: '/privacy' }, { label: 'Sign in', to: '/login' }].map(l => (
              <Link key={l.label} to={l.to} className="hover:underline" style={{ color: 'var(--text-muted)' }}>
                {l.label}
              </Link>
            ))}
          </div>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            © {new Date().getFullYear()} PhishCatcher. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}