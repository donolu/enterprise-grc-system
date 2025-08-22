"use client";
import { ConfigProvider } from "antd";

export const AppTheme = ({ children }: { children: React.ReactNode }) => {
  return (
    <ConfigProvider
      theme={{
        token: {
          fontFamily: 'Inter, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif',
          colorPrimary: "#2F6FED",
          colorSuccess: "#0EB57D",
          colorWarning: "#FFB020",
          colorError:   "#E5484D",
          borderRadius: 10,
          colorBorder:  "#E7EBF0",
          colorBgLayout: "#F7F8FA",
          colorText: "#0F172A",
          controlHeight: 40,
        },
        components: {
          Layout: { headerBg: "#FFFFFF", siderBg: "#0F1219", bodyBg: "#F7F8FA" },
          Card: { borderRadiusLG: 12, boxShadow: "0 6px 24px rgba(15,18,25,0.06)" },
          Button: { borderRadius: 8, controlHeight: 40, fontWeight: 600 },
          Tag: { borderRadiusSM: 999 },
          Table: { borderColor: "#E7EBF0", headerBg: "#FAFBFC" },
          Input: { borderRadius: 8 },
          Select: { borderRadius: 8 },
          Modal: { borderRadiusLG: 16 },
          Tooltip: { colorBgSpotlight: "#0F1219" },
        },
      }}
    >
      {children}
    </ConfigProvider>
  );
};
