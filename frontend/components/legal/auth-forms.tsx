'use client';

import Link from 'next/link';
import { useSearchParams, useRouter } from 'next/navigation';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { ArrowRight, CheckCircle2, Eye, EyeOff, ShieldCheck } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import { useAuth } from '@/components/auth-provider';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label, FieldError, FieldHint } from '@/components/ui/label';
import { Card, CardContent } from '@/components/ui/card';
import { Logo } from '@/components/legal/logo';
import { toast } from 'sonner';

const loginSchema = z.object({ email: z.string().email('Enter a valid email address.'), password: z.string().min(1, 'Enter your password.') });
type LoginValues = z.infer<typeof loginSchema>;

function internalPath(value: string | null): string | null {
  if (!value || !value.startsWith('/') || value.startsWith('//')) return null;
  try {
    const url = new URL(value, window.location.origin);
    return url.origin === window.location.origin ? `${url.pathname}${url.search}${url.hash}` : null;
  } catch {
    return null;
  }
}
export function LoginForm() {
  const router = useRouter(); const search = useSearchParams(); const { refresh } = useAuth(); const [show, setShow] = useState(false);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginValues>({ resolver: zodResolver(loginSchema), defaultValues: { email: '', password: '' } });
  async function submit(values: LoginValues) { try { await apiFetch('/api/auth/login', { method: 'POST', body: JSON.stringify(values) }); await refresh(); toast.success('Welcome back.'); router.push(internalPath(search.get('next')) || '/dashboard'); } catch (error) { toast.error(error instanceof Error ? error.message : 'Could not sign in.'); } }
  return <Card className="w-full max-w-md"><CardContent className="p-7 sm:p-9"><div className="mb-8 lg:hidden"><Logo /></div><p className="eyebrow">Welcome back</p><h1 className="mt-3 text-3xl font-extrabold tracking-tight">Sign in to LegalEase</h1><p className="mt-2 text-sm leading-6 text-muted">Continue where you left off with your private workspace.</p><form onSubmit={handleSubmit(submit)} className="mt-8 space-y-5"><div className="space-y-2"><Label htmlFor="email">Work email</Label><Input id="email" type="email" autoComplete="email" placeholder="you@company.com" {...register('email')} /><FieldError>{errors.email?.message}</FieldError></div><div className="space-y-2"><div className="flex items-center justify-between"><Label htmlFor="password">Password</Label><Link href="/forgot-password" className="text-xs font-semibold text-forest hover:underline">Forgot password?</Link></div><div className="relative"><Input id="password" type={show ? 'text' : 'password'} autoComplete="current-password" {...register('password')} className="pr-11" /><button type="button" onClick={() => setShow((value) => !value)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-forest" aria-label={show ? 'Hide password' : 'Show password'}>{show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button></div><FieldError>{errors.password?.message}</FieldError></div><Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>{isSubmitting ? 'Signing in…' : <>Sign in <ArrowRight className="h-4 w-4" /></>}</Button></form><div className="my-7 flex items-center gap-3 text-xs text-muted"><span className="h-px flex-1 bg-border" />New to LegalEase?<span className="h-px flex-1 bg-border" /></div><Link href="/register"><Button variant="secondary" size="lg" className="w-full">Create an account</Button></Link><p className="mt-6 flex items-start gap-2 text-[11px] leading-5 text-muted"><ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-500" /> Your session uses secure, HttpOnly cookies. Never share your password.</p></CardContent></Card>;
}

const registerSchema = z.object({ full_name: z.string().min(2, 'Enter your name.'), email: z.string().email('Enter a valid email address.'), password: z.string().min(10, 'Use at least 10 characters.').regex(/[A-Za-z]/, 'Include a letter.').regex(/[0-9]/, 'Include a number.') });
type RegisterValues = z.infer<typeof registerSchema>;
export function RegisterForm() {
  const router = useRouter(); const search = useSearchParams(); const { refresh } = useAuth(); const [show, setShow] = useState(false);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<RegisterValues>({ resolver: zodResolver(registerSchema), defaultValues: { full_name: '', email: '', password: '' } });
  async function submit(values: RegisterValues) { try { await apiFetch('/api/auth/register', { method: 'POST', body: JSON.stringify(values) }); await refresh(); toast.success('Your workspace is ready.'); router.push(internalPath(search.get('next')) || (search.get('template') ? `/documents/new?template=${encodeURIComponent(search.get('template') || '')}` : '/dashboard')); } catch (error) { toast.error(error instanceof Error ? error.message : 'Could not create your account.'); } }
  return <Card className="w-full max-w-md"><CardContent className="p-7 sm:p-9"><div className="mb-8 lg:hidden"><Logo /></div><p className="eyebrow">Start with clarity</p><h1 className="mt-3 text-3xl font-extrabold tracking-tight">Create your workspace</h1><p className="mt-2 text-sm leading-6 text-muted">A private place to prepare, edit, and review legal documents.</p><form onSubmit={handleSubmit(submit)} className="mt-8 space-y-5"><div className="space-y-2"><Label htmlFor="full_name">Full name</Label><Input id="full_name" autoComplete="name" placeholder="Alex Morgan" {...register('full_name')} /><FieldError>{errors.full_name?.message}</FieldError></div><div className="space-y-2"><Label htmlFor="email">Work email</Label><Input id="email" type="email" autoComplete="email" placeholder="you@company.com" {...register('email')} /><FieldError>{errors.email?.message}</FieldError></div><div className="space-y-2"><Label htmlFor="password">Password</Label><div className="relative"><Input id="password" type={show ? 'text' : 'password'} autoComplete="new-password" {...register('password')} className="pr-11" /><button type="button" onClick={() => setShow((value) => !value)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-forest" aria-label={show ? 'Hide password' : 'Show password'}>{show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button></div><FieldError>{errors.password?.message}</FieldError><FieldHint>At least 10 characters with a letter and number.</FieldHint></div><Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>{isSubmitting ? 'Creating workspace…' : <>Create workspace <ArrowRight className="h-4 w-4" /></>}</Button></form><p className="mt-6 text-center text-sm text-muted">Already have an account? <Link href="/login" className="font-bold text-forest hover:underline">Sign in</Link></p><p className="mt-5 flex items-start gap-2 text-[11px] leading-5 text-muted"><CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-500" /> By creating an account, you agree to the <Link href="/terms" className="underline">Terms</Link> and acknowledge the <Link href="/disclaimer" className="underline">Legal Disclaimer</Link>.</p></CardContent></Card>;
}

export function ForgotPasswordForm() { const [sent, setSent] = useState(false); const [email, setEmail] = useState(''); const [loading, setLoading] = useState(false); async function submit(event: React.FormEvent) { event.preventDefault(); setLoading(true); try { await apiFetch('/api/auth/forgot-password', { method: 'POST', body: JSON.stringify({ email }) }); } catch { } finally { setLoading(false); setSent(true); } } if (sent) return <Card className="w-full max-w-md p-8 text-center"><CheckCircle2 className="mx-auto h-10 w-10 text-emerald-500" /><h1 className="mt-5 text-2xl font-bold">Check your inbox</h1><p className="mt-3 text-sm leading-6 text-muted">If an account exists for {email || 'that address'}, we&apos;ll send reset instructions when email delivery is configured.</p><Link href="/login" className="mt-6 inline-block"><Button variant="secondary">Back to sign in</Button></Link></Card>; return <Card className="w-full max-w-md p-7 sm:p-9"><p className="eyebrow">Account recovery</p><h1 className="mt-3 text-3xl font-extrabold tracking-tight">Reset your password</h1><p className="mt-2 text-sm leading-6 text-muted">Enter your email and we&apos;ll send instructions if the account can be recovered.</p><form onSubmit={submit} className="mt-8 space-y-5"><div className="space-y-2"><Label htmlFor="email">Email</Label><Input id="email" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@company.com" /></div><Button size="lg" className="w-full" disabled={loading}>{loading ? 'Checking…' : 'Send reset instructions'}</Button></form><Link href="/login" className="mt-6 block text-center text-sm font-semibold text-forest">Back to sign in</Link></Card>; }
