'use client';

import Link from 'next/link';
import { Menu, Moon, Sun, X } from 'lucide-react';
import { useState } from 'react';
import { usePathname } from 'next/navigation';
import { Logo } from '@/components/legal/logo';
import { Button } from '@/components/ui/button';
import { useTheme } from '@/components/theme-provider';
import { cn } from '@/lib/utils';

const links = [
  { href: '/templates', label: 'Templates' },
  { href: '/how-it-works', label: 'How it works' },
  { href: '/pricing', label: 'Pricing' },
  { href: '/faq', label: 'FAQ' },
];

export function SiteHeader() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const { theme, toggle } = useTheme();
  return <header className="sticky top-0 z-40 border-b border-border/70 bg-[var(--background)]/85 backdrop-blur-xl"><div className="container-shell flex h-[72px] items-center justify-between"><Logo /><nav className="hidden items-center gap-7 md:flex">{links.map((link) => <Link key={link.href} href={link.href} className={cn('text-sm font-semibold transition hover:text-forest', pathname === link.href ? 'text-forest' : 'text-muted')}>{link.label}</Link>)}</nav><div className="hidden items-center gap-2 md:flex"><Button variant="ghost" size="icon" onClick={toggle} aria-label="Toggle color theme">{theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}</Button><Link href="/login"><Button variant="ghost" size="sm">Sign in</Button></Link><Link href="/register"><Button size="sm">Start drafting <span aria-hidden>→</span></Button></Link></div><button onClick={() => setOpen((value) => !value)} className="rounded-lg p-2 text-muted hover:bg-card md:hidden" aria-label="Toggle navigation">{open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}</button></div>{open ? <div className="border-t border-border bg-card px-4 py-4 md:hidden"><nav className="container-shell flex flex-col gap-1">{links.map((link) => <Link key={link.href} href={link.href} onClick={() => setOpen(false)} className="rounded-lg px-3 py-3 text-sm font-semibold text-muted hover:bg-forest/5 hover:text-forest">{link.label}</Link>)}<div className="mt-3 flex gap-2 border-t border-border pt-4"><Link href="/login" className="flex-1"><Button variant="secondary" className="w-full" onClick={() => setOpen(false)}>Sign in</Button></Link><Link href="/register" className="flex-1"><Button className="w-full" onClick={() => setOpen(false)}>Get started</Button></Link></div></nav></div> : null}</header>;
}
