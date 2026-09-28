'use client';

import { PublicShell } from '@/components/legal/public-shell';
import { ForgotPasswordForm } from '@/components/legal/auth-forms';

export default function ForgotPasswordPage() { return <PublicShell><div className="container-shell flex min-h-[calc(100vh-160px)] items-center justify-center py-16"><ForgotPasswordForm /></div></PublicShell>; }
