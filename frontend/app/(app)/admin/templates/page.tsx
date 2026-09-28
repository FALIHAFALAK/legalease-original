'use client';

import { useEffect, useState } from 'react';
import { FileText, Search } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import type { TemplateSummary } from '@/lib/types';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';

export default function AdminTemplatesPage() { const [templates, setTemplates] = useState<TemplateSummary[]>([]); const [query, setQuery] = useState(''); const [loading, setLoading] = useState(true); useEffect(() => { apiFetch<TemplateSummary[]>('/api/admin/templates').then(setTemplates).finally(() => setLoading(false)); }, []); const visible = templates.filter((item) => `${item.name} ${item.category} ${item.description}`.toLowerCase().includes(query.toLowerCase())); return <div className="space-y-7"><div><p className="eyebrow">Administration</p><h1 className="mt-2 text-3xl font-extrabold tracking-tight">Templates</h1><p className="mt-2 text-sm text-muted">Monitor the structured library used for document generation.</p></div><Card className="p-4"><div className="relative max-w-md"><Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" /><Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search templates" className="pl-10" /></div></Card>{loading ? <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{Array.from({ length: 6 }).map((_, index) => <Skeleton key={index} className="h-36" />)}</div> : <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{visible.map((template) => <Card key={template.id} className="p-5"><div className="flex items-start justify-between gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-forest/10 text-forest"><FileText className="h-4 w-4" /></span><Badge variant="success">Active</Badge></div><h2 className="mt-4 text-sm font-bold">{template.name}</h2><p className="mt-1 text-xs text-muted">{template.category} · {template.estimated_time}</p><p className="mt-3 line-clamp-2 text-xs leading-5 text-muted">{template.description}</p></Card>)}</div>}</div>; }
