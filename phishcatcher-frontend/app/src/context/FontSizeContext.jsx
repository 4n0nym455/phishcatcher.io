/**
 * FontSizeContext
 *
 * Manages font size scaling:
 *  - Options: 14, 16, 18, 20, 22, 24, 26, 28px
 *  - Persists in localStorage as 'pc_fontSize'
 *  - Applies --font-scale to <html> element
 *  - Provides useFontSize() hook
 */

import { createContext, useContext, useEffect, useState, useCallback } from 'react';

const FONT_SIZES = [14, 16, 18, 20, 22, 24, 26, 28];
const DEFAULT_SIZE = 16;
const STORAGE_KEY = 'pc_fontSize';

const FontSizeContext = createContext(null);

export function FontSizeProvider({ children }) {
  const [fontSize, setFontSizeState] = useState(() => {
    if (typeof window === 'undefined') return DEFAULT_SIZE;
    const saved = localStorage.getItem(STORAGE_KEY);
    const parsed = parseInt(saved, 10);
    if (FONT_SIZES.includes(parsed)) return parsed;
    return DEFAULT_SIZE;
  });

  useEffect(() => {
    const scale = fontSize / 16;
    document.documentElement.style.setProperty('--font-scale', scale.toString());
    localStorage.setItem(STORAGE_KEY, fontSize.toString());
  }, [fontSize]);

  const setFontSize = useCallback((value) => {
    if (FONT_SIZES.includes(value)) {
      setFontSizeState(value);
    }
  }, []);

  return (
    <FontSizeContext.Provider value={{ fontSize, setFontSize, fontSizes: FONT_SIZES }}>
      {children}
    </FontSizeContext.Provider>
  );
}

export function useFontSize() {
  const ctx = useContext(FontSizeContext);
  if (!ctx) throw new Error('useFontSize must be used inside <FontSizeProvider>');
  return ctx;
}