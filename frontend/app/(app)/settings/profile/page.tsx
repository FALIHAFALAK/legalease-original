'use client';

import { SettingsNav, ProfileSettings } from '@/components/legal/settings-pages';

export default function ProfileSettingsPage() { return <div className="mx-auto max-w-4xl space-y-7"><div><p className="eyebrow">Account</p><h1 className="mt-2 text-3xl font-extrabold tracking-tight">Profile</h1><p className="mt-2 text-sm text-muted">Keep your workspace identity up to date.</p></div><SettingsNav /><ProfileSettings /></div>; }
