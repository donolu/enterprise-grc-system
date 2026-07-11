"use client";
import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { getAccessToken } from '@/lib/auth';
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
    const token = getAccessToken();

    if (!token && !isPublicPage) {
      // No token and not on a public page - redirect to login
      router.push('/login');
      return;
    }

    if (token && isPublicPage) {
      // Has token but on login page - redirect to dashboard
      router.push('/');
      return;
    }

    setIsAuthenticated(!!token);
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