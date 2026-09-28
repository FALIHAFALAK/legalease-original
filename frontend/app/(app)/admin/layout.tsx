'use client';

import { AuthGuard } from '@/components/legal/auth-guard';

export default function AdminLayout({ children }: { children: React.ReactNode }) { return <AuthGuard admin>{children}</AuthGuard>; }
