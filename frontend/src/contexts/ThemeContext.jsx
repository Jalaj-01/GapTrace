import React, { createContext, useContext, useEffect, useState } from 'react';

const ThemeContext = createContext({
  theme: 'dark',
  effectiveTheme: 'dark',
  setTheme: () => {},
  cycleTheme: () => {},
});

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => {
    try {
      const saved = localStorage.getItem('gaptrace_theme');
      if (saved && ['dark', 'light', 'system'].includes(saved)) {
        return saved;
      }
    } catch {
      // Fallback
    }
    return 'dark'; // Genuine dark mode default
  });

  const [effectiveTheme, setEffectiveTheme] = useState('dark');

  useEffect(() => {
    const updateEffectiveTheme = () => {
      let resolved = theme;
      if (theme === 'system') {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        resolved = prefersDark ? 'dark' : 'light';
      }
      setEffectiveTheme(resolved);
      document.documentElement.setAttribute('data-theme', resolved);
    };

    updateEffectiveTheme();

    if (theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const listener = () => updateEffectiveTheme();
      mediaQuery.addEventListener('change', listener);
      return () => mediaQuery.removeEventListener('change', listener);
    }
  }, [theme]);

  const setTheme = (newTheme) => {
    setThemeState(newTheme);
    try {
      localStorage.setItem('gaptrace_theme', newTheme);
    } catch {
      // Ignore
    }
  };

  const cycleTheme = () => {
    if (theme === 'dark') setTheme('light');
    else if (theme === 'light') setTheme('system');
    else setTheme('dark');
  };

  return (
    <ThemeContext.Provider value={{ theme, effectiveTheme, setTheme, cycleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
