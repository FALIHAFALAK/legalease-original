'use client';

import { Suspense } from 'react';
import { PublicShell } from '@/components/legal/public-shell';
import { RegisterForm } from '@/components/legal/auth-forms';

export default function RegisterPage() { return <PublicShell><div className="container-shell flex min-h-[calc(100vh-160px)] items-center justify-center py-16"><Suspense fallback={null}><RegisterForm /></Suspense></div></PublicShell>; }
