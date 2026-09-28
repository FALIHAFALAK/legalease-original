'use client';

import { Suspense } from 'react';
import { PublicShell } from '@/components/legal/public-shell';
import { LoginForm } from '@/components/legal/auth-forms';

export default function LoginPage() { return <PublicShell><div className="container-shell flex min-h-[calc(100vh-160px)] items-center justify-center py-16"><Suspense fallback={null}><LoginForm /></Suspense></div></PublicShell>; }
