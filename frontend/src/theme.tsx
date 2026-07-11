"use client";
import { ConfigProvider, theme } from "antd";
import { createContext, useContext, useState, useEffect } from "react";

type ThemeMode = 'light' | 'dark';

interface ThemeContextType {
  mode: ThemeMode;
  toggleMode: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within AppTheme');
  }
  return context;
};

// Professional color palette
const colors = {
  primary: "#2F6FED",
  success: "#0EB57D",
  warning: "#FFB020",
  error: "#E5484D",
  info: "#3B82F6",
  light: {
    bg: "#FFFFFF",
    bgLayout: "#F7F8FA",
    bgContainer: "#FFFFFF",
    border: "#E7EBF0",
    text: "#0F172A",
    textSecondary: "#64748B",
    textTertiary: "#94A3B8",
    sider: "#0F1219",
    header: "#FFFFFF",
  },
  dark: {
    bg: "#0F1419",
    bgLayout: "#151B23",
    bgContainer: "#1E2532",
    border: "#2A3441",
    text: "#F8FAFC",
    textSecondary: "#CBD5E1",
    textTertiary: "#94A3B8",
    sider: "#0F1419",
    header: "#1E2532",
  }
};

export const AppTheme = ({ children }: { children: React.ReactNode }) => {
  const [mode, setMode] = useState<ThemeMode>('light');
  const [mounted, setMounted] = useState(false);

  // Handle client-side mounting and theme loading
  useEffect(() => {
    setMounted(true);
    const savedMode = localStorage.getItem('theme-mode') as ThemeMode;
    if (savedMode) {
      setMode(savedMode);
    }

    // Apply theme class to html element
    const html = document.documentElement;
    html.classList.remove('light-mode', 'dark-mode');
    html.classList.add(savedMode === 'dark' ? 'dark-mode' : 'light-mode');

    // Add hydrated class to enable transitions
    setTimeout(() => {
      document.body.classList.add('hydrated');
    }, 100);
  }, []);

  // Save theme preference to localStorage
  const toggleMode = () => {
    const newMode = mode === 'light' ? 'dark' : 'light';
    setMode(newMode);
    if (typeof window !== 'undefined') {
      localStorage.setItem('theme-mode', newMode);
      // Update HTML class immediately for instant theme change
      const html = document.documentElement;
      html.classList.remove('light-mode', 'dark-mode');
      html.classList.add(newMode === 'dark' ? 'dark-mode' : 'light-mode');
    }
  };

  const isDark = mode === 'dark';
  const colorScheme = isDark ? colors.dark : colors.light;

  return (
    <ThemeContext.Provider value={{ mode, toggleMode }}>
      <ConfigProvider
        theme={{
          algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
          token: {
            fontFamily: 'Inter, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif',
            colorPrimary: colors.primary,
            colorSuccess: colors.success,
            colorWarning: colors.warning,
            colorError: colors.error,
            colorInfo: colors.info,
            borderRadius: 10,
            borderRadiusLG: 12,
            borderRadiusSM: 6,
            colorBorder: colorScheme.border,
            colorBgLayout: colorScheme.bgLayout,
            colorBgContainer: colorScheme.bgContainer,
            colorText: colorScheme.text,
            colorTextSecondary: colorScheme.textSecondary,
            colorTextTertiary: colorScheme.textTertiary,
            controlHeight: 40,
            controlHeightLG: 48,
            controlHeightSM: 32,
            fontSize: 14,
            fontSizeLG: 16,
            fontSizeSM: 12,
            fontWeightStrong: 600,
            lineHeight: 1.5,
            boxShadow: isDark
              ? "0 6px 24px rgba(0,0,0,0.15)"
              : "0 6px 24px rgba(15,18,25,0.06)",
            boxShadowSecondary: isDark
              ? "0 3px 12px rgba(0,0,0,0.1)"
              : "0 3px 12px rgba(15,18,25,0.04)",
          },
          components: {
            Layout: {
              headerBg: colorScheme.header,
              siderBg: colorScheme.sider,
              bodyBg: colorScheme.bgLayout,
              triggerBg: colorScheme.sider,
              triggerColor: colorScheme.text,
            },
            Card: {
              borderRadiusLG: 12,
              boxShadow: isDark
                ? "0 6px 24px rgba(0,0,0,0.15)"
                : "0 6px 24px rgba(15,18,25,0.06)",
              headerBg: "transparent",
            },
            Button: {
              borderRadius: 8,
              controlHeight: 40,
              fontWeight: 600,
            },
            Tag: {
              borderRadiusSM: 20,
            },
            Table: {
              borderColor: colorScheme.border,
              headerBg: isDark ? colorScheme.bgContainer : "#FAFBFC",
              rowHoverBg: isDark ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.02)",
            },
            Input: {
              borderRadius: 8,
            },
            Select: {
              borderRadius: 8,
            },
            Modal: {
              borderRadiusLG: 16,
            },
            Tooltip: {
              colorBgSpotlight: colorScheme.sider,
            },
            Menu: {
              itemBg: "transparent",
              subMenuItemBg: "transparent",
              itemSelectedBg: isDark ? "rgba(47,111,237,0.15)" : "rgba(47,111,237,0.1)",
              itemHoverBg: isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.04)",
              itemActiveBg: isDark ? "rgba(47,111,237,0.2)" : "rgba(47,111,237,0.15)",
              iconSize: 16,
            },
            Dropdown: {
              borderRadiusLG: 12,
            },
            Avatar: {
              borderRadius: 10,
            },
            Badge: {
              borderRadiusSM: 10,
            },
            Alert: {
              borderRadiusLG: 12,
            },
            Progress: {
              borderRadius: 20,
            },
            Statistic: {
              titleFontSize: 14,
              contentFontSize: 24,
              fontFamily: 'Inter, system-ui, sans-serif',
            },
            Divider: {
              colorSplit: colorScheme.border,
            },
            Typography: {
              titleMarginBottom: 16,
              titleMarginTop: 0,
            }
          },
        }}
      >
        <div
          style={{
            backgroundColor: colorScheme.bgLayout,
            color: colorScheme.text,
            minHeight: '100vh',
            transition: mounted ? 'background-color 0.3s ease, color 0.3s ease' : 'none'
          }}
        >
          {children}
        </div>
      </ConfigProvider>
    </ThemeContext.Provider>
  );
};
