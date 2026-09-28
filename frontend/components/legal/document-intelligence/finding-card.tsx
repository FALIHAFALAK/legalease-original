'use client';

import { useMemo } from 'react';
import { CircleCheck, CircleDot, FileWarning, TriangleAlert } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { FindingDetail } from '@/lib/types';
import { QuestionThread } from './question-thread';
import { StatusControl } from './status-control';
import { CategoryLabel, LifecycleBadge, SeverityBadge } from './labels';

type FindingCardProps = {
  finding: FindingDetail;
  onUpdated: (finding: FindingDetail) => void;
  expanded: boolean;
};

const SEVERITY_ICON = {
  high: TriangleAlert,
  medium: CircleDot,
  low: FileWarning,
} as const;

const SEVERITY_TONE = {
  high: 'border-red-200 bg-red-50/60 dark:border-red-500/20 dark:bg-red-500/5',
  medium: 'border-amber-200 bg-amber-50/50 dark:border-amber-500/20 dark:bg-amber-500/5',
  low: 'border-border bg-card',
} as const;

/**
 * Split the stored clause text around the finding's quote span so the flagged wording can be
 * highlighted in place. Offsets are relative to `clause_text`.
 */
function useHighlightedClause(finding: FindingDetail) {
  return useMemo(() => {
    const text = finding.clause_text || '';
    const start = finding.quote_start_offset;
    const end = finding.quote_end_offset;
    if (!text || end <= start || start < 0 || end > text.length) {
      return { before: text, quote: '', after: '' };
    }
    return {
      before: text.slice(0, start),
      quote: text.slice(start, end),
      after: text.slice(end),
    };
  }, [finding.clause_text, finding.quote_start_offset, finding.quote_end_offset]);
}

export function FindingCard({ finding, onUpdated, expanded }: FindingCardProps) {
  const { before, quote, after } = useHighlightedClause(finding);
  const Icon = SEVERITY_ICON[finding.severity] ?? CircleDot;

  return (
    <article
      id={`finding-${finding.id}`}
      className={cn(
        'space-y-4 rounded-2xl border p-5',
        SEVERITY_TONE[finding.severity],
        expanded && 'ring-4 ring-forest/10',
      )}
    >
      <header className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <SeverityBadge severity={finding.severity} />
          <CategoryLabel category={finding.category} />
          {finding.round_number > 1 ? <LifecycleBadge outcome={finding.lifecycle} /> : null}
        </div>
        <h3 className="flex items-start gap-2 text-base font-bold leading-6 text-ink dark:text-white">
          <Icon className="mt-0.5 h-4 w-4 shrink-0 text-forest" />
          {finding.title}
        </h3>
        <p className="text-xs text-muted">
          {finding.clause_citation}
          {finding.confidence !== null ? ` · ${Math.round(finding.confidence * 100)}% confidence` : ''}
        </p>
      </header>

      {finding.clause_text ? (
        <div className="rounded-xl border border-border bg-card p-3">
          <p className="text-[11px] font-bold uppercase tracking-wide text-muted">The clause</p>
          <p className="mt-1.5 whitespace-pre-wrap text-xs leading-6 text-muted">
            {before}
            {quote ? (
              <mark className="rounded bg-amber-200/70 px-0.5 text-ink dark:bg-amber-400/30 dark:text-white">
                {quote}
              </mark>
            ) : null}
            {after}
          </p>
        </div>
      ) : finding.excerpt ? (
        <blockquote className="border-l-2 border-forest/30 bg-forest/5 px-3 py-2 text-xs italic leading-5 text-muted">
          &ldquo;{finding.excerpt}&rdquo;
        </blockquote>
      ) : null}

      <div className="space-y-2 text-sm leading-6 text-ink dark:text-white">
        <p>{finding.explanation}</p>
        {finding.severity_explanation ? (
          <p className="text-xs text-muted">{finding.severity_explanation}</p>
        ) : null}
      </div>

      {finding.resolution_evidence ? (
        <p className="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-xs leading-5 text-emerald-800 dark:border-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-200">
          <CircleCheck className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          {finding.resolution_evidence}
        </p>
      ) : null}

      {finding.suggested_wording ? (
        <div className="rounded-xl border border-border bg-card p-3">
          <p className="text-[11px] font-bold uppercase tracking-wide text-muted">Suggested wording</p>
          <p className="mt-1.5 whitespace-pre-wrap text-xs leading-6 text-ink dark:text-white">
            {finding.suggested_wording}
          </p>
        </div>
      ) : null}

      <StatusControl finding={finding} onUpdated={onUpdated} />
      <QuestionThread finding={finding} questionCount={finding.question_count} />
    </article>
  );
}
