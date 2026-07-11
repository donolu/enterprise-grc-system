import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import AppLayout from "@/components/AppLayout";
import AuthWrapper from "@/components/AuthWrapper";
import { AppTheme } from "@/theme";
import ThemeScript from "@/components/ThemeScript";

const inter = Inter({ subsets: ["latin"] });

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
      <body className={inter.className}>
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
