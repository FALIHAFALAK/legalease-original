'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import { BarChart3, BookOpen, ChevronDown, FilePlus2, Files, LayoutDashboard, LogOut, Menu, MessageCircle, Moon, PanelLeftClose, PanelLeftOpen, Search, Settings, Shield, Sparkles, Sun, Users, X } from 'lucide-react';
import { useAuth } from '@/components/auth-provider';
import { useTheme } from '@/components/theme-provider';
import { Logo } from '@/components/legal/logo';
import { Button } from '@/components/ui/button';
import { cn, initials } from '@/lib/utils';

const mainLinks = [
  { href: '/dashboard', label: 'Overview', icon: LayoutDashboard },
  { href: '/documents', label: 'Documents', icon: Files },
  { href: '/assistant', label: 'AI assistant', icon: MessageCircle },
  { href: '/review', label: 'Document review', icon: BookOpen },
];
const adminLinks = [
  { href: '/admin', label: 'Admin overview', icon: BarChart3 },
  { href: '/admin/users', label: 'Users', icon: Users },
  { href: '/admin/templates', label: 'Templates', icon: Shield },
];

function NavLink({ href, label, icon: Icon, onNavigate }: { href: string; label: string; icon: React.ElementType; onNavigate: () => void }) {
  const pathname = usePathname();
  const active = pathname === href || (href !== '/dashboard' && pathname.startsWith(`${href}/`));
  return <Link href={href} onClick={onNavigate} className={cn('flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition', active ? 'bg-forest text-white shadow-[0_8px_18px_rgba(30,58,50,.2)]' : 'text-muted hover:bg-forest/7 hover:text-forest')}><Icon className="h-[17px] w-[17px]" />{label}</Link>;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const close = () => setMobileOpen(false);
  const sidebar = <aside className={cn('flex h-full flex-col border-r border-border bg-card transition-all', collapsed ? 'w-[76px]' : 'w-[260px]')}><div className="flex h-[76px] items-center px-5"><Logo compact={collapsed} /></div><div className="flex-1 overflow-y-auto px-3 py-3"><Link href="/documents/new" onClick={close} className={cn('mb-6 flex items-center justify-center gap-2 rounded-xl bg-forest px-3 py-3 text-sm font-bold text-white shadow-[0_8px_18px_rgba(30,58,50,.2)] transition hover:bg-[#2C5044]', collapsed ? 'px-2' : '')}><FilePlus2 className="h-4 w-4" />{!collapsed ? <span>New document</span> : null}</Link><p className={cn('mb-2 px-3 text-[10px] font-bold uppercase tracking-[.16em] text-muted/70', collapsed ? 'text-center' : '')}>{!collapsed ? 'Workspace' : '—'}</p><nav className="flex flex-col gap-1">{mainLinks.map((link) => <NavLink key={link.href} {...link} onNavigate={close} />)}</nav>{user?.role === 'admin' ? <><p className={cn('mb-2 mt-7 px-3 text-[10px] font-bold uppercase tracking-[.16em] text-muted/70', collapsed ? 'text-center' : '')}>{!collapsed ? 'Administration' : '—'}</p><nav className="flex flex-col gap-1">{adminLinks.map((link) => <NavLink key={link.href} {...link} onNavigate={close} />)}</nav></> : null}</div><div className="border-t border-border p-3"><div className={cn('flex items-center gap-2 rounded-xl p-2', collapsed ? 'justify-center' : '')}><span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-forestDeep text-xs font-bold text-white">{initials(user?.full_name || 'User')}</span>{!collapsed ? <div className="min-w-0 flex-1"><p className="truncate text-xs font-bold">{user?.full_name}</p><p className="truncate text-[11px] text-muted">{user?.email}</p></div> : null}{!collapsed ? <button onClick={async () => { await logout(); window.location.href = '/'; }} className="rounded-lg p-1.5 text-muted hover:bg-red-50 hover:text-red-600" aria-label="Sign out"><LogOut className="h-4 w-4" /></button> : null}</div></div></aside>;
  return <div className="min-h-screen bg-[var(--background)]"><div className={cn('fixed inset-y-0 left-0 z-50 hidden lg:block', collapsed ? 'w-[76px]' : 'w-[260px]')}>{sidebar}</div>{mobileOpen ? <div className="fixed inset-0 z-50 flex lg:hidden"><button className="absolute inset-0 bg-forestDeep/40" onClick={close} aria-label="Close menu" /><div className="relative h-full">{sidebar}<button onClick={close} className="absolute right-3 top-5 rounded-lg p-2 text-muted hover:bg-forest/10" aria-label="Close menu"><X className="h-5 w-5" /></button></div></div> : null}<div className={cn('min-h-screen transition-[padding] duration-300', collapsed ? 'lg:pl-[76px]' : 'lg:pl-[260px]')}><header className="sticky top-0 z-30 flex h-[76px] items-center justify-between border-b border-border/70 bg-[var(--background)]/85 px-4 backdrop-blur-xl sm:px-6"><div className="flex items-center gap-3"><button onClick={() => setMobileOpen(true)} className="rounded-xl p-2 text-muted hover:bg-card lg:hidden" aria-label="Open menu"><Menu className="h-5 w-5" /></button><button onClick={() => setCollapsed((value) => !value)} className="hidden rounded-xl p-2 text-muted hover:bg-card lg:block" aria-label="Collapse sidebar">{collapsed ? <PanelLeftOpen className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}</button><div className="hidden items-center gap-2 text-sm text-muted md:flex"><span className="h-2 w-2 rounded-full bg-emerald-500" /> Workspace secure</div></div><div className="flex items-center gap-2"><Link href="/documents" className="hidden items-center gap-2 rounded-xl border border-border bg-card px-3 py-2 text-sm text-muted hover:border-forest/30 sm:flex"><Search className="h-4 w-4" /> Search documents <span className="rounded bg-muted/10 px-1.5 py-0.5 text-[10px]">⌘ K</span></Link><Button variant="ghost" size="icon" onClick={toggle} aria-label="Toggle color theme">{theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}</Button><Link href="/settings" className="rounded-xl p-2 text-muted hover:bg-card" aria-label="Settings"><Settings className="h-5 w-5" /></Link><span className="hidden h-8 w-px bg-border sm:block" /><Link href="/settings/profile" className="flex items-center gap-2"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-forestDeep text-xs font-bold text-white">{initials(user?.full_name || 'User')}</span><ChevronDown className="hidden h-4 w-4 text-muted sm:block" /></Link></div></header><main className="mx-auto w-full max-w-[1440px] p-4 sm:p-6 lg:p-8">{children}</main></div></div>;
}
