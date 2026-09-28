'use client';

import { Download, FileText, GitCompareArrows, RefreshCw, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { deleteReview, reviewErrorMessage, reviewReportUrl } from '@/lib/review-api';
import type { ReviewDetailResponse } from '@/lib/types';

type ReviewSummaryProps = {
  review: ReviewDetailResponse;
  reanalyzing: boolean;
  onReanalyze: () => void;
  onDelete: () => void;
};

function Stat({ label, value, tone }: { label: string; value: number; tone?: string }) {
  return (
    <div className="rounded-xl border border-border p-3">
      <p className="text-xs text-muted">{label}</p>
      <p className={`mt-1 text-xl font-extrabold ${tone ?? 'text-ink dark:text-white'}`}>{value}</p>
    </div>
  );
}

export function ReviewSummary({
  review,
  reanalyzing,
  onReanalyze,
  onDelete,
}: ReviewSummaryProps) {
  const { counts, comparison } = review;

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <CardTitle className="flex min-w-0 items-center gap-2">
              <FileText className="h-4 w-4 shrink-0 text-forest" />
              {/* Filenames contain underscores, which are not line-break opportunities, so the
                  name sets this card's min-content width and overflows narrow viewports.
                  `break-all` (not `break-words`) is required: only a `word-break` change
                  reduces the min-content contribution the grid track is sized from. */}
              <span className="min-w-0 break-all">{review.filename}</span>
            </CardTitle>
            <p className="mt-1.5 text-xs text-muted">
              {review.clause_count} clause{review.clause_count === 1 ? '' : 's'}
              {review.page_count ? ` · ${review.page_count} pages` : ''}
              {review.word_count ? ` · ${review.word_count.toLocaleString()} words` : ''}
              {review.round_number > 1 ? ` · round ${review.round_number}` : ''}
              {` · analysed by ${review.provider}${review.model ? ` (${review.model})` : ''}`}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              size="sm"
              variant="secondary"
              disabled={reanalyzing}
              onClick={onReanalyze}
            >
              <RefreshCw className={`h-4 w-4 ${reanalyzing ? 'animate-spin' : ''}`} />
              Re-analyse
            </Button>
            <a
              href={reviewReportUrl(review.review_id)}
              className="inline-flex h-9 items-center gap-2 rounded-xl border border-border bg-card px-3.5 text-xs font-semibold text-ink transition hover:border-forest/40 hover:bg-forest/5 dark:text-white"
            >
              <Download className="h-4 w-4" />
              PDF report
            </a>
            <Button type="button" size="sm" variant="ghost" onClick={onDelete}>
              <Trash2 className="h-4 w-4" />
              Delete
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {review.summary ? (
          <p className="text-sm leading-6 text-ink dark:text-white">{review.summary}</p>
        ) : null}

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Open" value={counts.open} tone="text-amber-600 dark:text-amber-300" />
          <Stat label="Resolved" value={counts.resolved} tone="text-emerald-600 dark:text-emerald-300" />
          <Stat label="Dismissed" value={counts.dismissed} />
          <Stat label="Needs a lawyer" value={counts.needs_professional_review} tone="text-forest" />
        </div>

        {comparison?.previous_review_id ? (
          <p className="flex flex-wrap items-center gap-2 rounded-xl border border-border p-3 text-xs text-muted">
            <GitCompareArrows className="h-4 w-4 text-forest" />
            Compared with {comparison.previous_filename}:{' '}
            <Badge variant="success">{comparison.fixed_count} addressed</Badge>
            <Badge variant="warning">{comparison.unresolved_count} outstanding</Badge>
            <Badge variant="danger">{comparison.new_count} new</Badge>
          </p>
        ) : null}

        <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-900 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-100">
          <p className="font-bold">{review.professional_review_notice}</p>
          <p className="mt-1">{review.disclaimer}</p>
        </div>
      </CardContent>
    </Card>
  );
}

export async function confirmDeleteReview(
  review: ReviewDetailResponse,
  onDeleted: () => void,
): Promise<void> {
  if (
    typeof window !== 'undefined' &&
    !window.confirm(`Delete the review of ${review.filename}? This cannot be undone.`)
  ) {
    return;
  }
  try {
    await deleteReview(review.review_id);
    toast.success('Review deleted.');
    onDeleted();
  } catch (error) {
    toast.error(reviewErrorMessage(error));
  }
}
