'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, FileText, Search, Sparkles } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import type { TemplateDetail, TemplateSummary } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { Input, Select } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { EmptyState, Skeleton } from '@/components/ui/skeleton';
import { PublicShell } from '@/components/legal/public-shell';
import { SectionHeading } from '@/components/legal/marketing';

export function TemplateCard({ template }: { template: TemplateSummary }) {
  return <Link href={`/templates/${template.slug}`} className="group block"><Card className="h-full p-6 transition duration-300 hover:-translate-y-1 hover:border-forest/30 hover:shadow-lift"><div className="flex items-start justify-between gap-3"><span className="flex h-11 w-11 items-center justify-center rounded-xl bg-forest/10 text-forest"><FileText className="h-5 w-5" /></span><ArrowRight className="h-4 w-4 text-muted transition group-hover:translate-x-1 group-hover:text-forest" /></div><Badge variant="muted" className="mt-5 w-fit">{template.category}</Badge><h3 className="mt-3 text-lg font-bold leading-6">{template.name}</h3><p className="mt-2 line-clamp-3 text-sm leading-6 text-muted">{template.description}</p><p className="mt-5 text-xs font-semibold text-muted">{template.estimated_time}</p></Card></Link>;
}

export function TemplateLibrary({ compact = false }: { compact?: boolean }) {
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => {
    const params = new URLSearchParams();
    if (query) params.set('q', query);
    if (category) params.set('category', category);
    const timer = window.setTimeout(() => {
      setLoading(true);
      apiFetch<{ items: TemplateSummary[]; categories: string[] }>(`/api/templates?${params.toString()}`).then((data) => { setTemplates(data.items); setCategories(data.categories); setError(''); }).catch(() => setError('The template library is temporarily unavailable.')).finally(() => setLoading(false));
    }, query ? 220 : 0);
    return () => window.clearTimeout(timer);
  }, [query, category]);
  const visible = useMemo(() => templates, [templates]);
  return <><div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between"><SectionHeading eyebrow="Template library" title="A focused place to begin." description="Search by the situation you are facing. Each template includes a guided form and a structure you can make your own." /><div className="flex w-full flex-col gap-2 sm:flex-row lg:max-w-[500px]"><div className="relative flex-1"><Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" /><Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search templates" className="pl-10" /></div><Select value={category} onChange={(event) => setCategory(event.target.value)} className="sm:w-44"><option value="">All categories</option>{categories.map((item) => <option key={item} value={item}>{item}</option>)}</Select></div></div><div className="mt-10 flex items-center justify-between"><p className="text-sm text-muted"><span className="font-bold text-ink dark:text-white">{visible.length}</span> templates available</p><div className="hidden items-center gap-2 text-xs font-semibold text-muted sm:flex"><Sparkles className="h-3.5 w-3.5 text-forest" /> Built for real decisions</div></div>{error ? <div className="mt-6"><EmptyState icon={FileText} title="Could not load templates" description={error} action={<Button variant="secondary" onClick={() => setQuery((value) => `${value} `)}>Try again</Button>} /></div> : loading ? <div className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{Array.from({ length: compact ? 3 : 6 }).map((_, index) => <Skeleton key={index} className="h-64" />)}</div> : visible.length ? <div className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{visible.map((template) => <TemplateCard key={template.slug} template={template} />)}</div> : <div className="mt-6"><EmptyState icon={Search} title="No templates found" description="Try a broader search or choose another category." /></div>}</>;
}

export function TemplatesPage() {
  return <PublicShell><div className="container-shell py-16 sm:py-24"><TemplateLibrary /></div></PublicShell>;
}
