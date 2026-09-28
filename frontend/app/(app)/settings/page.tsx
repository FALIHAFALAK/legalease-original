'use client';

import { SettingsNav, SettingsOverview } from '@/components/legal/settings-pages';

export default function SettingsPage() { return <div className="mx-auto max-w-4xl space-y-7"><div><p className="eyebrow">Account</p><h1 className="mt-2 text-3xl font-extrabold tracking-tight">Settings</h1><p className="mt-2 text-sm text-muted">Manage your LegalEase workspace and account.</p></div><SettingsNav /><SettingsOverview /></div>; }
