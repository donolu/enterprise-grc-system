import type { Metadata } from "next";
import "./globals.css";
import AppLayout from "@/components/AppLayout";
import AuthWrapper from "@/components/AuthWrapper";
import { AppTheme } from "@/theme";
import ThemeScript from "@/components/ThemeScript";

export const metadata: Metadata = {
  title: "GRC SaaS",
  description: "GRC SaaS Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <ThemeScript />
        <AppTheme>
          <AuthWrapper>
            <AppLayout>{children}</AppLayout>
          </AuthWrapper>
        </AppTheme>
      </body>
    </html>
  );
}
