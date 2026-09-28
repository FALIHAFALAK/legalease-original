'use client';

import Link from 'next/link';
import { Download, Edit3, FileText, MoreHorizontal, Trash2, Copy } from 'lucide-react';
import { toast } from 'sonner';
import { apiFetch, API_URL } from '@/lib/api';
import type { DocumentSummary } from '@/lib/types';
import { formatRelative } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Skeleton, EmptyState } from '@/components/ui/skeleton';

export function StatusBadge({ status }: { status: string }) { return <Badge variant={status === 'draft' ? 'warning' : status === 'archived' ? 'muted' : 'success'}>{status === 'ready_for_review' ? 'Ready for review' : status.charAt(0).toUpperCase() + status.slice(1)}</Badge>; }

export function DocumentList({ documents, loading, onRefresh, compact = false }: { documents: DocumentSummary[]; loading: boolean; onRefresh: () => void; compact?: boolean }) {
  async function remove(document: DocumentSummary) { if (!window.confirm(`Delete “${document.title}”?`)) return; try { await apiFetch(`/api/documents/${document.id}`, { method: 'DELETE' }); toast.success('Document deleted.'); onRefresh(); } catch (error) { toast.error(error instanceof Error ? error.message : 'Could not delete document.'); } }
  async function duplicate(document: DocumentSummary) { try { await apiFetch(`/api/documents/${document.id}/duplicate`, { method: 'POST' }); toast.success('Document duplicated.'); onRefresh(); } catch (error) { toast.error(error instanceof Error ? error.message : 'Could not duplicate document.'); } }
  if (loading) return <div className="space-y-3">{Array.from({ length: compact ? 3 : 5 }).map((_, index) => <Skeleton key={index} className="h-[86px]" />)}</div>;
  if (!documents.length) return <EmptyState icon={FileText} title="No documents yet" description="Start with a template and create a draft you can shape in your workspace." action={<Link href="/documents/new"><Button>Create a document</Button></Link>} />;
  return <div className="space-y-3">{documents.map((document) => <Card key={document.id} className="group p-4 transition hover:border-forest/25 sm:p-5"><div className="flex flex-col gap-4 sm:flex-row sm:items-center"><div className="flex min-w-0 flex-1 items-center gap-3"><span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-forest/10 text-forest"><FileText className="h-5 w-5" /></span><div className="min-w-0"><Link href={`/documents/${document.id}/edit`} className="block truncate text-sm font-bold hover:text-forest sm:text-base">{document.title}</Link><div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted"><StatusBadge status={document.status} /><span>Updated {formatRelative(document.updated_at)}</span><span className="hidden sm:inline">• v{document.current_version}</span></div></div></div><div className="flex items-center gap-1 border-t border-border pt-3 sm:border-0 sm:pt-0"><Link href={`/documents/${document.id}/edit`}><Button variant="ghost" size="sm"><Edit3 className="h-3.5 w-3.5" /> <span className="hidden sm:inline">Edit</span></Button></Link><a href={`${API_URL}/api/documents/${document.id}/export/pdf`}><Button variant="ghost" size="icon" aria-label="Download PDF"><Download className="h-4 w-4" /></Button></a><Button variant="ghost" size="icon" onClick={() => duplicate(document)} aria-label="Duplicate"><Copy className="h-4 w-4" /></Button><Button variant="ghost" size="icon" onClick={() => remove(document)} aria-label="Delete" className="hover:text-red-600"><Trash2 className="h-4 w-4" /></Button></div></div></Card>)}</div>;
}
