import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import AppLayout from "@/components/AppLayout";
import AuthWrapper from "@/components/AuthWrapper";
import { AppTheme } from "@/theme";
import ThemeScript from "@/components/ThemeScript";

const inter = localFont({
  src: [
    { path: "../../public/fonts/Inter-Regular.ttf", weight: "400", style: "normal" },
    { path: "../../public/fonts/Inter-Medium.ttf", weight: "500", style: "normal" },
    { path: "../../public/fonts/Inter-SemiBold.ttf", weight: "600", style: "normal" },
    { path: "../../public/fonts/Inter-Bold.ttf", weight: "700", style: "normal" },
  ],
  display: "swap",
  variable: "--font-inter",
});

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
