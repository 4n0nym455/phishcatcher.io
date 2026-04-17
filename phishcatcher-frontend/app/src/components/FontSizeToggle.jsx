/**
 * FontSizeToggle
 *
 * Floating accessibility button - bottom-right corner.
 * Click to toggle panel with font size options (14-28px).
 */

import { useState, useEffect, useRef } from 'react';
import { useFontSize } from '@/context/FontSizeContext';
import { Glasses } from 'lucide-react';

export function FontSizeToggle({ className = '' }) {
  const { fontSize, setFontSize, fontSizes } = useFontSize();
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div 
      className={`fixed bottom-6 right-6 z-50 ${className}`} 
      ref={dropdownRef}
    >
{/* Floating Button */}
      <button
        onClick={() => setOpen(v => !v)}
        aria-label={`Font size: ${fontSize}px, click to change`}
        aria-expanded={open}
        className={`
          w-14 h-14 rounded-full
          flex items-center justify-center
          transition-all duration-200
          hover:scale-110 active:scale-95
          shadow-lg
          ${open 
            ? 'bg-[var(--brand)] text-white' 
            : 'bg-[var(--brand)] text-white hover:bg-[var(--brand-hover)]'
          }
        `}
        style={{
          boxShadow: 'var(--shadow-md), 0 4px 14px rgba(14, 165, 199, 0.35)',
        }}
      >
        <Glasses className="w-6 h-6" />
      </button>

      {/* Dropdown Panel */}
      {open && (
        <div
          className="absolute bottom-[calc(100%+12px)] right-0 w-40 rounded-2xl py-2 animate-fade-in"
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            boxShadow: 'var(--shadow-lg)',
          }}
        >
          <div
            className="px-4 py-2 text-xs font-semibold uppercase tracking-wider"
            style={{ color: 'var(--text-muted)', borderBottom: '1px solid var(--border)' }}
          >
            Font Size
          </div>
          {fontSizes.map((size) => (
            <button
              key={size}
              onClick={() => {
                setFontSize(size);
                setOpen(false);
              }}
              className={`
                w-full px-4 py-2.5 text-sm text-left flex items-center justify-between
                transition-colors
                ${fontSize === size ? 'font-semibold' : 'font-normal'}
              `}
              style={{
                color: fontSize === size ? 'var(--brand)' : 'var(--text-secondary)',
                background: fontSize === size ? 'var(--brand-dim)' : 'transparent',
              }}
              onMouseEnter={e => {
                if (fontSize !== size) e.currentTarget.style.background = 'var(--bg-elevated)';
              }}
              onMouseLeave={e => {
                if (fontSize !== size) e.currentTarget.style.background = 'transparent';
              }}
            >
              <span>{size}px</span>
              {fontSize === size && (
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}