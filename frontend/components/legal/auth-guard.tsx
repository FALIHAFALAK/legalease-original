'use client';

import { useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/components/auth-provider';
import { Logo } from '@/components/legal/logo';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';

export function AuthGuard({ children, admin = false }: { children: React.ReactNode; admin?: boolean }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  useEffect(() => {
    if (!loading && !user) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    if (!loading && user && admin && user.role !== 'admin') router.replace('/dashboard');
  }, [admin, loading, pathname, router, user]);
  if (loading || !user || (admin && user.role !== 'admin')) return <div className="flex min-h-screen items-center justify-center bg-[var(--background)]"><div className="w-full max-w-sm space-y-4"><Logo /><Skeleton className="h-12 w-full" /><Skeleton className="h-40 w-full" /></div></div>;
  return <>{children}</>;
}

export function SignOutButton() {
  const { logout } = useAuth();
  const router = useRouter();
  return <Button variant="ghost" size="sm" onClick={async () => { await logout(); router.push('/'); }}>Sign out</Button>;
}
