'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { ArrowLeft, CalendarDays, FileClock, GitBranch } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import type { Version } from '@/lib/types';
import { formatDate } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';

export default function DocumentHistoryPage() { const params = useParams<{ id: string }>(); const [versions, setVersions] = useState<Version[]>([]); const [error, setError] = useState(''); useEffect(() => { apiFetch<Version[]>(`/api/documents/${params.id}/versions`).then(setVersions).catch(() => setError('Version history could not be loaded.')); }, [params.id]); return <div className="mx-auto max-w-4xl space-y-7"><div><Link href={`/documents/${params.id}/edit`} className="inline-flex items-center gap-2 text-sm font-semibold text-muted hover:text-forest"><ArrowLeft className="h-4 w-4" /> Back to editor</Link><p className="eyebrow mt-8">Document history</p><h1 className="mt-2 font-display text-3xl tracking-tight">Every saved version</h1><p className="mt-2 text-sm leading-6 text-muted">A transparent record of the changes saved to this workspace.</p></div>{error ? <Card className="p-8 text-center text-sm font-semibold text-red-600">{error}</Card> : !versions.length ? <Skeleton className="h-64" /> : <div className="space-y-3">{versions.map((version, index) => <Card key={version.id} className="p-5 sm:p-6"><div className="flex gap-4"><div className="relative flex w-9 shrink-0 justify-center"><span className={`z-10 flex h-9 w-9 items-center justify-center rounded-xl ${index === 0 ? 'bg-forest text-white' : 'bg-muted/10 text-muted'}`}><GitBranch className="h-4 w-4" /></span>{index < versions.length - 1 ? <span className="absolute top-9 h-full w-px bg-border" /> : null}</div><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h2 className="text-sm font-bold">Version {version.version_number}</h2>{index === 0 ? <Badge>Current</Badge> : null}</div><p className="mt-1 text-sm text-muted">{version.change_note || 'Saved edit'}</p><div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-muted"><span className="inline-flex items-center gap-1.5"><CalendarDays className="h-3.5 w-3.5" /> {formatDate(version.created_at)}</span><span className="inline-flex items-center gap-1.5"><FileClock className="h-3.5 w-3.5" /> {version.title}</span></div></div><Link href={`/documents/${params.id}/preview`} className="self-center text-xs font-bold text-forest">Preview</Link></div></Card>)}</div>}</div>; }
