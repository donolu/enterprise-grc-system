export const designTokens = {
  color: {
    primary: "#0B8F84",
    success: "#0EB57D",
    warning: "#FFB020",
    error: "#E5484D",
    info: "#256D8A",
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
    },
  },
  radius: {
    small: 6,
    default: 8,
    pill: 20,
  },
  size: {
    controlSmall: 32,
    control: 40,
    controlLarge: 48,
  },
} as const;

export type ThemeMode = "light" | "dark";
