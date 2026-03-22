/**
 * ThemeToggle
 *
 * Animated sun ↔ moon toggle button.
 * Renders in the header next to the user menu.
 */

import { Sun, Moon } from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';

export function ThemeToggle({ className = '' }) {
  const { isDark, toggle } = useTheme();

  return (
    <button
      onClick={toggle}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      className={`
        relative w-9 h-9 rounded-lg
        flex items-center justify-center
        transition-all duration-200
        hover:scale-105 active:scale-95
        ${isDark
          ? 'bg-[var(--bg-elevated)] text-[var(--brand)] hover:bg-[var(--brand-dim)]'
          : 'bg-[var(--bg-elevated)] text-[var(--threat)] hover:bg-[var(--threat-dim)]'
        }
        ${className}
      `}
    >
      <span
        className="absolute inset-0 flex items-center justify-center transition-all duration-300"
        style={{ opacity: isDark ? 1 : 0, transform: isDark ? 'rotate(0deg) scale(1)' : 'rotate(90deg) scale(0.5)' }}
      >
        <Moon className="w-4 h-4" />
      </span>
      <span
        className="absolute inset-0 flex items-center justify-center transition-all duration-300"
        style={{ opacity: isDark ? 0 : 1, transform: isDark ? 'rotate(-90deg) scale(0.5)' : 'rotate(0deg) scale(1)' }}
      >
        <Sun className="w-4 h-4" />
      </span>
    </button>
  );
}