import * as SecureStore from 'expo-secure-store';
import {
  type ReactNode,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { Platform } from 'react-native';

export type ThemeMode = 'light' | 'dark';

export type ColorPalette = {
  background: string;
  surface: string;
  border: string;
  text: string;
  muted: string;
  primary: string;
  primaryPressed: string;
  onPrimary: string;
  primarySoft: string;
  danger: string;
  dangerSoft: string;
  success: string;
  successSoft: string;
  warning: string;
  warningSoft: string;
  disabled: string;
  disabledText: string;
};

export const lightColors: ColorPalette = {
  background: '#F4F5F8',
  surface: '#FFFFFF',
  border: '#DFE2EA',
  text: '#14161C',
  muted: '#646B7C',
  primary: '#4B3FE4',
  primaryPressed: '#3A30C2',
  onPrimary: '#FFFFFF',
  primarySoft: '#E9E7FD',
  danger: '#C4291C',
  dangerSoft: '#FCEBE9',
  success: '#1B7F4B',
  successSoft: '#E4F5EC',
  warning: '#8A5A00',
  warningSoft: '#FFF3D6',
  disabled: '#EDEFF3',
  disabledText: '#A3A9B8',
};

export const darkColors: ColorPalette = {
  background: '#0F1117',
  surface: '#181B24',
  border: '#2A2F3D',
  text: '#F3F4F8',
  muted: '#9CA3B5',
  primary: '#6E62FF',
  primaryPressed: '#584CE0',
  onPrimary: '#FFFFFF',
  primarySoft: '#25224C',
  danger: '#F05B4F',
  dangerSoft: '#3A1D1D',
  success: '#34B371',
  successSoft: '#163526',
  warning: '#E5A435',
  warningSoft: '#382B14',
  disabled: '#222632',
  disabledText: '#636A7E',
};

export const colors: ColorPalette = { ...lightColors };

export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24 };

export const radius = { sm: 8, md: 12, pill: 999 };

export function createFont(palette: ColorPalette) {
  return {
    title: { fontSize: 24, fontWeight: '700' as const, color: palette.text },
    heading: { fontSize: 17, fontWeight: '600' as const, color: palette.text },
    body: { fontSize: 16, color: palette.text },
    small: { fontSize: 14, color: palette.muted },
  };
}

export const font = createFont(colors);

const THEME_STORAGE_KEY = 'pcclub.theme';
const isWeb = Platform.OS === 'web';

async function readStoredTheme(): Promise<ThemeMode | null> {
  try {
    const raw = isWeb
      ? globalThis.localStorage?.getItem(THEME_STORAGE_KEY)
      : await SecureStore.getItemAsync(THEME_STORAGE_KEY);
    if (raw === 'light' || raw === 'dark') return raw;
    return null;
  } catch {
    return null;
  }
}

async function writeStoredTheme(mode: ThemeMode): Promise<void> {
  try {
    if (isWeb) globalThis.localStorage?.setItem(THEME_STORAGE_KEY, mode);
    else await SecureStore.setItemAsync(THEME_STORAGE_KEY, mode);
  } catch {
    // Ignore storage errors
  }
}

type ThemeContextValue = {
  mode: ThemeMode;
  isDark: boolean;
  colors: ColorPalette;
  font: ReturnType<typeof createFont>;
  setTheme: (mode: ThemeMode) => void;
  toggleTheme: () => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>('light');

  useEffect(() => {
    let active = true;
    void readStoredTheme().then((saved) => {
      if (active && saved) {
        setModeState(saved);
      }
    });
    return () => {
      active = false;
    };
  }, []);

  const setTheme = useCallback((next: ThemeMode) => {
    setModeState(next);
    void writeStoredTheme(next);
  }, []);

  const toggleTheme = useCallback(() => {
    setModeState((prev) => {
      const next = prev === 'light' ? 'dark' : 'light';
      void writeStoredTheme(next);
      return next;
    });
  }, []);

  const value = useMemo<ThemeContextValue>(() => {
    const activeColors = mode === 'dark' ? darkColors : lightColors;
    Object.assign(colors, activeColors);
    const activeFont = createFont(activeColors);
    Object.assign(font, activeFont);
    return {
      mode,
      isDark: mode === 'dark',
      colors: activeColors,
      font: activeFont,
      setTheme,
      toggleTheme,
    };
  }, [mode, setTheme, toggleTheme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) {
    return {
      mode: 'light',
      isDark: false,
      colors: lightColors,
      font: createFont(lightColors),
      setTheme: () => undefined,
      toggleTheme: () => undefined,
    };
  }
  return context;
}
