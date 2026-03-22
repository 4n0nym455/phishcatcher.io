/**
 * PhishCatcher Theme System
 * 
 * Comprehensive color palette and design tokens for consistent UI design
 */

export const theme = {
  // Color Palette
  colors: {
    // Primary Colors
    primary: {
      50: '#f0f0ff',
      100: '#e0e7ff', 
      200: '#c7d2fe',
      300: '#a5b4fc',
      400: '#8b5cf6',
      500: '#7c3aed',
      600: '#6d28d9',
      700: '#5b21b6',
      800: '#4c1bf5',
      900: '#3730a3',
      950: '#2e1065',
    },
    
    // Status Colors
    status: {
      safe: {
        bg: '#0d9488',
        fg: '#6ee7b7',
        border: '#10b981',
        light: '#059669',
      },
      warning: {
        bg: '#f59e0b',
        fg: '#fbbf24',
        border: '#f97316',
        light: '#eab308',
      },
      danger: {
        bg: '#e11d48',
        fg: '#f87171',
        border: '#ef4444',
        light: '#dc2626',
      },
    },
    
    // Neutral Colors
    neutral: {
      50: '#f8fafc',
      100: '#f1f5f9',
      200: '#e2e8f0',
      300: '#cbd5e1',
      400: '#94a3b8',
      500: '#64748b',
      600: '#475569',
      700: '#334155',
      800: '#1e293b',
      900: '#0f172a',
      950: '#020617',
    },
    
    // Glass Effects
    glass: {
      bg: 'rgba(255, 255, 255, 0.05)',
      border: 'rgba(139, 92, 246, 0.2)',
      backdrop: 'blur(10px)',
      hover: 'rgba(139, 92, 246, 0.3)',
    },
    
    // Text Colors
    text: {
      primary: '#ffffff',
      secondary: '#a1a1aa',
      muted: '#6b7280',
      accent: '#e2e8f0',
    },
  },

  // Typography
  typography: {
    fontFamily: {
      sans: ['Inter', 'system-ui', 'sans-serif'],
      mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      heading: ['Inter', 'system-ui', 'sans-serif'],
    },
    fontSize: {
      xs: '0.75rem',
      sm: '0.875rem', 
      base: '1rem',
      lg: '1.125rem',
      xl: '1.25rem',
      '2xl': '1.5rem',
      '3xl': '1.875rem',
      '4xl': '2.25rem',
    },
    fontWeight: {
      light: '300',
      normal: '400',
      medium: '500',
      semibold: '600',
      bold: '700',
    },
    lineHeight: {
      tight: '1.25',
      normal: '1.5',
      relaxed: '1.75',
    },
  },

  // Spacing
  spacing: {
    0: '0px',
    1: '0.25rem',
    2: '0.5rem',
    3: '0.75rem',
    4: '1rem',
    5: '1.25rem',
    6: '1.5rem',
    8: '2rem',
    10: '2.5rem',
    12: '3rem',
    16: '4rem',
    20: '5rem',
    24: '6rem',
  },

  // Border Radius
  borderRadius: {
    none: '0px',
    sm: '0.25rem',
    base: '0.375rem',
    md: '0.5rem',
    lg: '0.75rem',
    xl: '1rem',
    '2xl': '1.5rem',
    '3xl': '2rem',
    full: '9999px',
  },

  // Shadows
  shadows: {
    sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    base: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
    md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.06)',
    lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.05)',
    xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.04)',
    glass: '0 8px 32px 0 rgba(139, 92, 246, 0.15)',
  },

  // Animations
  animation: {
    duration: {
      fast: '150ms',
      normal: '250ms',
      slow: '350ms',
    },
    easing: {
      ease: 'cubic-bezier(0.4, 0, 0.2, 1)',
      easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
      easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
      easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    },
  },

  // Breakpoints
  breakpoints: {
    sm: '640px',
    md: '768px',
    lg: '1024px',
    xl: '1280px',
    '2xl': '1536px',
  },

  // Z-Index
  zIndex: {
    hide: -1,
    auto: 'auto',
    base: 0,
    docked: 10,
    sticky: 20,
    banner: 30,
    overlay: 40,
    modal: 50,
    popover: 60,
    tooltip: 70,
    toast: 80,
  },
};

// CSS Custom Properties for theme usage
export const cssVars = {
  '--color-primary-50': theme.colors.primary[50],
  '--color-primary-100': theme.colors.primary[100],
  '--color-primary-200': theme.colors.primary[200],
  '--color-primary-300': theme.colors.primary[300],
  '--color-primary-400': theme.colors.primary[400],
  '--color-primary-500': theme.colors.primary[500],
  '--color-primary-600': theme.colors.primary[600],
  '--color-primary-700': theme.colors.primary[700],
  '--color-primary-800': theme.colors.primary[800],
  '--color-primary-900': theme.colors.primary[900],
  '--color-primary-950': theme.colors.primary[950],
  
  '--color-safe-bg': theme.colors.status.safe.bg,
  '--color-safe-fg': theme.colors.status.safe.fg,
  '--color-safe-border': theme.colors.status.safe.border,
  '--color-safe-light': theme.colors.status.safe.light,
  
  '--color-warning-bg': theme.colors.status.warning.bg,
  '--color-warning-fg': theme.colors.status.warning.fg,
  '--color-warning-border': theme.colors.status.warning.border,
  '--color-warning-light': theme.colors.status.warning.light,
  
  '--color-danger-bg': theme.colors.status.danger.bg,
  '--color-danger-fg': theme.colors.status.danger.fg,
  '--color-danger-border': theme.colors.status.danger.border,
  '--color-danger-light': theme.colors.status.danger.light,
  
  '--color-glass-bg': theme.colors.glass.bg,
  '--color-glass-border': theme.colors.glass.border,
  '--color-glass-hover': theme.colors.glass.hover,
  
  '--color-text-primary': theme.colors.text.primary,
  '--color-text-secondary': theme.colors.text.secondary,
  '--color-text-muted': theme.colors.text.muted,
  '--color-text-accent': theme.colors.text.accent,
  
  '--font-sans': theme.typography.fontFamily.sans.join(', '),
  '--font-mono': theme.typography.fontFamily.mono.join(', '),
  '--font-heading': theme.typography.fontFamily.heading.join(', '),
  
  '--spacing-1': theme.spacing[1],
  '--spacing-2': theme.spacing[2],
  '--spacing-3': theme.spacing[3],
  '--spacing-4': theme.spacing[4],
  '--spacing-6': theme.spacing[6],
  '--spacing-8': theme.spacing[8],
  '--spacing-12': theme.spacing[12],
  '--spacing-16': theme.spacing[16],
  '--spacing-20': theme.spacing[20],
  
  '--radius-sm': theme.borderRadius.sm,
  '--radius-base': theme.borderRadius.base,
  '--radius-md': theme.borderRadius.md,
  '--radius-lg': theme.borderRadius.lg,
  '--radius-xl': theme.borderRadius.xl,
  '--radius-2xl': theme.borderRadius['2xl'],
  '--radius-3xl': theme.borderRadius['3xl'],
  
  '--shadow-sm': theme.shadows.sm,
  '--shadow-base': theme.shadows.base,
  '--shadow-md': theme.shadows.md,
  '--shadow-lg': theme.shadows.lg,
  '--shadow-glass': theme.shadows.glass,
  
  '--animation-fast': theme.animation.duration.fast,
  '--animation-normal': theme.animation.duration.normal,
  '--animation-slow': theme.animation.duration.slow,
  '--animation-ease': theme.animation.easing.ease,
  '--animation-ease-in': theme.animation.easing.easeIn,
  '--animation-ease-out': theme.animation.easing.easeOut,
  '--animation-ease-in-out': theme.animation.easing.easeInOut,
};

export default theme;
