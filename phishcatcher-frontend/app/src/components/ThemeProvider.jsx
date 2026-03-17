import { createContext, useContext, useEffect, useState } from "react";

const ThemeContext = createContext({
  theme: "system",
  setTheme: () => null,
  resolvedTheme: "dark",
});

export function ThemeProvider({
  children,
  defaultTheme = "system",
  storageKey = "phishcatcher-theme",
}) {
  const [theme, setTheme] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem(storageKey) || defaultTheme;
    }
    return defaultTheme;
  });

  const [resolvedTheme, setResolvedTheme] = useState("dark");

  useEffect(() => {
    const root = window.document.documentElement;

    const getResolvedTheme = (t) => {
      if (t === "system") {
        return window.matchMedia("(prefers-color-scheme: dark)").matches
          ? "dark"
          : "light";
      }
      return t;
    };

    const resolved = getResolvedTheme(theme);
    setResolvedTheme(resolved);

    root.classList.remove("light", "dark");
    root.classList.add(resolved);

    localStorage.setItem(storageKey, theme);
  }, [theme, storageKey]);

  // Listen for system theme changes
  useEffect(() => {
    if (theme === "system") {
      const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
      const handleChange = () => {
        const resolved = mediaQuery.matches ? "dark" : "light";
        setResolvedTheme(resolved);
        const root = window.document.documentElement;
        root.classList.remove("light", "dark");
        root.classList.add(resolved);
      };

      mediaQuery.addEventListener("change", handleChange);
      return () => mediaQuery.removeEventListener("change", handleChange);
    }
  }, [theme]);

  const value = {
    theme,
    setTheme: (newTheme) => setTheme(newTheme),
    resolvedTheme,
  };

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
};
