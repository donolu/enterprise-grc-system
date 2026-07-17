"use client";
import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { getAccessToken, refresh, setAccessToken } from '@/lib/auth';
import { Spin } from 'antd';

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
    const token = getAccessToken();

    if (!token && !isPublicPage) {
      refresh()
        .then((newToken) => {
          if (cancelled) return;
          setAccessToken(newToken);
          setIsAuthenticated(true);
        })
        .catch(() => {
          if (cancelled) return;
          router.push('/login');
        });
      return () => {
        cancelled = true;
      };
    }

    if (token && isPublicPage) {
      // Has token but on login page - redirect to dashboard
      router.push('/');
      return () => {
        cancelled = true;
      };
    }

    setIsAuthenticated(!!token);
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

  return <>{children}</>;
}
