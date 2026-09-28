'use client';

import Link from 'next/link';
import { FilePlus2, Filter, Search } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { apiFetch } from '@/lib/api';
import type { DocumentListResponse } from '@/lib/types';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input, Select } from '@/components/ui/input';
import { DocumentList } from '@/components/legal/document-list';

export default function DocumentsPage() {
  const [data, setData] = useState<DocumentListResponse | null>(null); const [query, setQuery] = useState(''); const [status, setStatus] = useState(''); const [loading, setLoading] = useState(true);
  const load = useCallback(() => { const params = new URLSearchParams(); if (query) params.set('q', query); if (status) params.set('status', status); setLoading(true); apiFetch<DocumentListResponse>(`/api/documents?${params}`).then(setData).catch(() => undefined).finally(() => setLoading(false)); }, [query, status]);
  useEffect(() => { const timer = window.setTimeout(load, query ? 200 : 0); return () => window.clearTimeout(timer); }, [load, query]);
  return <div className="space-y-8"><div className="flex flex-col justify-between gap-5 md:flex-row md:items-end"><div><p className="eyebrow">Workspace</p><h1 className="mt-2 text-3xl font-extrabold tracking-tight sm:text-4xl">Documents</h1><p className="mt-2 text-sm leading-6 text-muted">Every draft, version, and export in one place.</p></div><Link href="/documents/new"><Button><FilePlus2 className="h-4 w-4" /> New document</Button></Link></div><div className="grid gap-4 sm:grid-cols-3"><Card className="p-4"><p className="text-xs font-semibold text-muted">All documents</p><p className="mt-2 text-2xl font-extrabold">{data?.total ?? '—'}</p></Card><Card className="p-4"><p className="text-xs font-semibold text-muted">Drafts</p><p className="mt-2 text-2xl font-extrabold text-amber-600">{data?.draft_count ?? '—'}</p></Card><Card className="p-4"><p className="text-xs font-semibold text-muted">Ready for review</p><p className="mt-2 text-2xl font-extrabold text-emerald-600">{data?.completed_count ?? '—'}</p></Card></div><Card className="p-4 sm:p-5"><div className="flex flex-col gap-3 lg:flex-row"><div className="relative flex-1"><Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" /><Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by title or jurisdiction" className="pl-10" /></div><div className="relative lg:w-52"><Filter className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" /><Select value={status} onChange={(event) => setStatus(event.target.value)} className="pl-10"><option value="">All statuses</option><option value="draft">Draft</option><option value="ready_for_review">Ready for review</option><option value="archived">Archived</option></Select></div></div></Card><DocumentList documents={data?.items || []} loading={loading} onRefresh={load} /></div>;
}
