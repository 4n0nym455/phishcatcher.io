/**
 * ThemeContext
 *
 * Manages dark / light mode:
 *  - Persists in localStorage as 'pc_theme'
 *  - Falls back to system preference on first visit
 *  - Applies `.dark` class to <html> element
 *  - Provides useTheme() hook
 */

import { createContext, useContext, useEffect, useState, useCallback } from 'react';

const ThemeContext = createContext(null);

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => {
    if (typeof window === 'undefined') return 'dark';
    const saved = localStorage.getItem('pc_theme');
    if (saved === 'light' || saved === 'dark') return saved;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  // Apply class to <html> on mount and change
  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    localStorage.setItem('pc_theme', theme);
  }, [theme]);

  const toggle = useCallback(() => {
    const root = document.documentElement;
    root.setAttribute('data-theme-changing', 'true');
    requestAnimationFrame(() => {
      setThemeState(t => (t === 'dark' ? 'light' : 'dark'));
      setTimeout(() => {
        root.removeAttribute('data-theme-changing');
      }, 800);
    });
  }, []);

  const setTheme = useCallback((value) => {
    if (value === 'light' || value === 'dark') setThemeState(value);
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, toggle, setTheme, isDark: theme === 'dark' }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used inside <ThemeProvider>');
  return ctx;
}