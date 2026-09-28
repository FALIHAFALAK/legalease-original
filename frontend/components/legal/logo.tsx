import Link from 'next/link';
import { Scale } from 'lucide-react';

export function Logo({ compact = false }: { compact?: boolean }) {
  return <Link href="/" className="group inline-flex items-center gap-2.5" aria-label="LegalEase home"><span className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-forestDeep text-white shadow-[0_7px_16px_rgba(19,39,34,.2)] transition group-hover:-rotate-3"><Scale className="h-[18px] w-[18px]" strokeWidth={2.2} /><span className="absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full bg-gold" /></span>{!compact ? <span className="text-lg font-extrabold tracking-[-0.04em] text-forestDeep dark:text-white">Legal<span className="text-forest">Ease</span></span> : null}</Link>;
}
