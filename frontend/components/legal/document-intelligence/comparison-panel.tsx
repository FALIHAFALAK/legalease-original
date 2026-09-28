'use client';

import { ArrowRight, CircleCheck, CircleX, Sparkles } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { EmptyState } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import type { ComparisonItem, ComparisonResponse } from '@/lib/types';
import { LifecycleBadge, SeverityBadge } from './labels';

type ComparisonPanelProps = {
  comparison: ComparisonResponse | null;
  onSelectFinding: (findingId: number) => void;
};

const GROUPS: {
  key: keyof Pick<ComparisonResponse, 'fixed' | 'unresolved' | 'newly_introduced'>;
  title: string;
  blurb: string;
  icon: typeof CircleCheck;
  tone: string;
}[] = [
  {
    key: 'fixed',
    title: 'Addressed in this version',
    blurb:
      'The clause was rewritten and this review did not re-raise the concern. Check the evidence before you rely on it.',
    icon: CircleCheck,
    tone: 'text-emerald-600 dark:text-emerald-300',
  },
  {
    key: 'unresolved',
    title: 'Still outstanding',
    blurb: 'The concern survives in the revised document.',
    icon: CircleX,
    tone: 'text-amber-600 dark:text-amber-300',
  },
  {
    key: 'newly_introduced',
    title: 'Newly introduced',
    blurb: 'This version raised a concern the earlier review did not.',
    icon: Sparkles,
    tone: 'text-red-600 dark:text-red-300',
  },
];

function ComparisonRow({
  item,
  onSelectFinding,
}: {
  item: ComparisonItem;
  onSelectFinding: (findingId: number) => void;
}) {
  const clickable = item.finding_id !== null;
  const body = (
    <>
      <span className="flex flex-wrap items-center gap-2">
        <SeverityBadge severity={item.severity} />
        <LifecycleBadge outcome={item.outcome} />
        {item.clause_citation ? (
          <span className="text-xs text-muted">{item.clause_citation}</span>
        ) : null}
      </span>
      <span className="mt-2 block text-sm font-semibold leading-6 text-ink dark:text-white">
        {item.title}
      </span>
      {item.evidence ? (
        <span className="mt-2 block text-xs leading-5 text-muted">{item.evidence}</span>
      ) : null}
    </>
  );

  if (!clickable) {
    return (
      <li className="rounded-xl border border-border bg-card p-3">
        <span className="block text-[11px] text-muted">
          {item.summary} No current finding points at this concern, so it is kept here for the
          record.
        </span>
        <span className="mt-2 block">{body}</span>
      </li>
    );
  }

  return (
    <li>
      <button
        type="button"
        onClick={() => onSelectFinding(item.finding_id as number)}
        className="w-full rounded-xl border border-border bg-card p-3 text-left transition hover:border-forest/50 hover:bg-forest/5"
      >
        {body}
        <span className="mt-2 flex items-center gap-1 text-xs font-semibold text-forest">
          Open the finding
          <ArrowRight className="h-3.5 w-3.5" />
        </span>
      </button>
    </li>
  );
}

export function ComparisonPanel({ comparison, onSelectFinding }: ComparisonPanelProps) {
  if (!comparison || !comparison.previous_review_id) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Compared with an earlier version</CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            icon={ArrowRight}
            title="No earlier version to compare"
            description="Upload a revised copy of this document, or link it to a document you have already reviewed, to see what changed."
          />
        </CardContent>
      </Card>
    );
  }

  const hasAnything =
    comparison.fixed.length + comparison.unresolved.length + comparison.newly_introduced.length > 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Compared with {comparison.previous_filename}</CardTitle>
        <p className="flex flex-wrap gap-2 text-sm text-muted">
          <span className="font-semibold text-emerald-600 dark:text-emerald-300">
            {comparison.fixed_count} addressed
          </span>
          <span aria-hidden="true">&middot;</span>
          <span className="font-semibold text-amber-600 dark:text-amber-300">
            {comparison.unresolved_count} outstanding
          </span>
          <span aria-hidden="true">&middot;</span>
          <span className="font-semibold text-red-600 dark:text-red-300">
            {comparison.new_count} new
          </span>
        </p>
      </CardHeader>
      <CardContent className="space-y-5">
        <p className="rounded-xl bg-amber-50 p-3 text-xs leading-5 text-amber-900 dark:bg-amber-500/10 dark:text-amber-100">
          {comparison.disclaimer}
        </p>
        {!hasAnything ? (
          <EmptyState
            icon={ArrowRight}
            title="Nothing to report"
            description="This review raised no concerns to line up against the earlier version."
          />
        ) : null}
        {GROUPS.map((group) => {
          const items = comparison[group.key];
          if (!items.length) return null;
          const Icon = group.icon;
          return (
            <section key={group.key} className="space-y-2">
              <h3 className={cn('flex items-center gap-2 text-sm font-bold', group.tone)}>
                <Icon className="h-4 w-4" />
                {group.title}
                <span className="rounded-full bg-muted/10 px-2 py-0.5 text-xs text-muted">
                  {items.length}
                </span>
              </h3>
              <p className="text-xs leading-5 text-muted">{group.blurb}</p>
              <ul className="space-y-2">
                {items.map((item, index) => (
                  <ComparisonRow
                    key={`${group.key}-${item.finding_id ?? item.previous_finding_id ?? index}`}
                    item={item}
                    onSelectFinding={onSelectFinding}
                  />
                ))}
              </ul>
            </section>
          );
        })}
      </CardContent>
    </Card>
  );
}
