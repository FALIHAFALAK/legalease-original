'use client';

import { AuthGuard } from '@/components/legal/auth-guard';
import { AppShell } from '@/components/legal/app-shell';

export default function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  return <AuthGuard><AppShell>{children}</AppShell></AuthGuard>;
}
