'use client';

import { useMemo } from 'react';
import { ChevronDown, FileText, Scale } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { EmptyState } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import type { ClauseReference, FindingDetail } from '@/lib/types';
import { CategoryLabel, FindingStatusBadge, SeverityBadge } from './labels';

type ClauseViewerProps = {
  clauses: ClauseReference[];
  findings: FindingDetail[];
  activeFindingId: number | null;
  onSelectFinding: (findingId: number) => void;
};

function severityWeight(severity: string): number {
  if (severity === 'high') return 0;
  if (severity === 'medium') return 1;
  return 2;
}

function pageNote(kind: string): string {
  return kind === 'source_page'
    ? 'Page numbers are taken from the source file.'
    : 'Page numbers are estimated from the text, as this format has no fixed pages.';
}

export function ClauseViewer({
  clauses,
  findings,
  activeFindingId,
  onSelectFinding,
}: ClauseViewerProps) {
  const byClause = useMemo(() => {
    const grouped = new Map<number, FindingDetail[]>();
    for (const finding of findings) {
      const list = grouped.get(finding.clause_index) ?? [];
      list.push(finding);
      grouped.set(finding.clause_index, list);
    }
    for (const list of grouped.values()) {
      list.sort(
        (a, b) =>
          severityWeight(a.severity) - severityWeight(b.severity) || a.id - b.id,
      );
    }
    return grouped;
  }, [findings]);

  const pageKind = clauses[0]?.page_reference_kind ?? 'estimated_page';

  if (!clauses.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Document clauses</CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            icon={FileText}
            title="No clauses were extracted"
            description="This document could not be split into clause-level units. The extracted text is still available below."
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Scale className="h-4 w-4 text-forest" />
          Document clauses
        </CardTitle>
        <p className="text-sm text-muted">
          {clauses.length} clause{clauses.length === 1 ? '' : 's'} extracted. Findings sit under the
          wording they came from.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="flex items-start gap-2 rounded-xl bg-muted/8 p-3 text-xs leading-5 text-muted">
          <Scale className="mt-0.5 h-3.5 w-3.5 shrink-0 text-forest" />
          {pageNote(pageKind)}
        </p>
        {clauses.map((clause) => {
          const clauseFindings = byClause.get(clause.index) ?? [];
          const hasActive = clauseFindings.some((item) => item.id === activeFindingId);
          return (
            <details
              key={clause.index}
              open={hasActive || clauseFindings.length > 0}
              className={cn(
                'group rounded-xl border border-border bg-card transition',
                hasActive && 'border-forest/50 ring-4 ring-forest/10',
              )}
            >
              <summary className="flex cursor-pointer list-none items-start gap-3 p-4">
                <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-forest/10 text-xs font-bold text-forest">
                  {clause.index}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-bold text-ink dark:text-white">
                    {clause.heading || `Clause ${clause.index}`}
                  </span>
                  <span className="mt-1 block text-xs text-muted">{clause.citation}</span>
                </span>
                {clauseFindings.length ? (
                  <span className="flex shrink-0 items-center gap-1.5">
                    {clause.open_finding_count > 0 ? (
                      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-bold text-amber-700 dark:bg-amber-500/15 dark:text-amber-300">
                        {clause.open_finding_count} open
                      </span>
                    ) : null}
                    <ChevronDown className="h-4 w-4 text-muted transition group-open:rotate-180" />
                  </span>
                ) : null}
              </summary>
              <div className="border-t border-border px-4 pb-4 pt-3">
                {clause.summary ? (
                  <p className="text-xs leading-5 text-muted">{clause.summary}</p>
                ) : null}
                <pre className="mt-3 max-h-72 overflow-y-auto whitespace-pre-wrap rounded-xl bg-[var(--background)] p-3 text-xs leading-6 text-muted">
                  {clause.text}
                </pre>
                {clauseFindings.length ? (
                  <ul className="mt-3 space-y-2">
                    {clauseFindings.map((finding) => (
                      <li key={finding.id}>
                        <button
                          type="button"
                          onClick={() => onSelectFinding(finding.id)}
                          className={cn(
                            'w-full rounded-xl border p-3 text-left transition hover:border-forest/50 hover:bg-forest/5',
                            finding.id === activeFindingId
                              ? 'border-forest bg-forest/8'
                              : 'border-border',
                          )}
                        >
                          <span className="flex flex-wrap items-center gap-2">
                            <SeverityBadge severity={finding.severity} />
                            <CategoryLabel category={finding.category} />
                            <FindingStatusBadge status={finding.status} />
                          </span>
                          <span className="mt-2 block text-sm font-semibold leading-6 text-ink dark:text-white">
                            {finding.title}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-3 text-xs text-muted">
                    No concerns were raised about this clause.
                  </p>
                )}
              </div>
            </details>
          );
        })}
      </CardContent>
    </Card>
  );
}
