'use client';

import { SettingsNav, SecuritySettings } from '@/components/legal/settings-pages';

export default function SecuritySettingsPage() { return <div className="mx-auto max-w-4xl space-y-7"><div><p className="eyebrow">Account</p><h1 className="mt-2 text-3xl font-extrabold tracking-tight">Security</h1><p className="mt-2 text-sm text-muted">Protect your account and control your data.</p></div><SettingsNav /><SecuritySettings /></div>; }
