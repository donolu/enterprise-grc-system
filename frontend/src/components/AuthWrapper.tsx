"use client";
import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { checkSession } from '@/lib/auth';
import { Spin } from 'antd';
import AppLayout from './AppLayout';

interface AuthWrapperProps {
  children: React.ReactNode;
}

export default function AuthWrapper({ children }: AuthWrapperProps) {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const router = useRouter();
  const pathname = usePathname();

  // Pages that don't require authentication
  const publicPages = ['/login', '/register', '/forgot-password'];
  const isPublicPage = publicPages.some(page => pathname.startsWith(page));

  useEffect(() => {
    let cancelled = false;
    if (!isPublicPage) {
      checkSession()
        .then(() => {
          if (cancelled) return;
          setIsAuthenticated(true);
        })
        .catch(() => {
          if (cancelled) return;
          const next = `${pathname}${window.location.search}`;
          router.push(`/login?next=${encodeURIComponent(next)}`);
        });
      return () => {
        cancelled = true;
      };
    }

    setIsAuthenticated(true);
    return () => {
      cancelled = true;
    };
  }, [pathname, isPublicPage, router]);

  // Show loading spinner while checking authentication
  if (isAuthenticated === null && !isPublicPage) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh'
      }}>
        <Spin size="large" />
      </div>
    );
  }

  return isPublicPage ? <>{children}</> : <AppLayout>{children}</AppLayout>;
}
