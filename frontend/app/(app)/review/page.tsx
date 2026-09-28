'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { BookOpen, Loader2, ShieldAlert } from 'lucide-react';
import { toast } from 'sonner';
import { apiFetch } from '@/lib/api';
import {
  analyzeDocument,
  getReview,
  reanalyzeReview,
  reviewErrorMessage,
} from '@/lib/review-api';
import type {
  DocumentListResponse,
  DocumentSummary,
  FindingDetail,
  ReviewDetailResponse,
} from '@/lib/types';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { EmptyState, Skeleton } from '@/components/ui/skeleton';
import { ClauseViewer } from '@/components/legal/document-intelligence/clause-viewer';
import { ComparisonPanel } from '@/components/legal/document-intelligence/comparison-panel';
import { FindingCard } from '@/components/legal/document-intelligence/finding-card';
import { ReviewSummary, confirmDeleteReview } from '@/components/legal/document-intelligence/review-summary';
import { UploadPanel } from '@/components/legal/document-intelligence/upload-panel';

type StatusFilter = 'all' | 'open' | 'resolved' | 'dismissed' | 'needs_professional_review';

const FILTERS: { value: StatusFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'open', label: 'Open' },
  { value: 'needs_professional_review', label: 'Needs a lawyer' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'dismissed', label: 'Dismissed' },
];

export default function ReviewPage() {
  const [file, setFile] = useState<File | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [documentId, setDocumentId] = useState('');
  const [review, setReview] = useState<ReviewDetailResponse | null>(null);
  const [baselineReviewId, setBaselineReviewId] = useState<number | null>(null);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [reanalyzing, setReanalyzing] = useState(false);
  const [loadingReview, setLoadingReview] = useState(false);
  const [activeFindingId, setActiveFindingId] = useState<number | null>(null);
  const [filter, setFilter] = useState<StatusFilter>('all');
  const [error, setError] = useState('');

  useEffect(() => {
    apiFetch<DocumentListResponse>('/api/documents')
      .then((data) => setDocuments(data.items))
      .catch(() => setDocuments([]))
      .finally(() => setLoadingDocs(false));
  }, []);

  const applyReview = useCallback((next: ReviewDetailResponse) => {
    setReview(next);
    setError('');
    setFilter('all');
  }, []);

  const findings = useMemo(() => review?.detailed_findings ?? [], [review]);

  const visibleFindings = useMemo(() => {
    if (filter === 'all') return findings;
    return findings.filter((item) => item.status === filter);
  }, [findings, filter]);

  function replaceFinding(updated: FindingDetail) {
    setReview((current) =>
      current
        ? {
            ...current,
            detailed_findings: current.detailed_findings.map((item) =>
              item.id === updated.id ? { ...item, ...updated } : item,
            ),
          }
        : current,
    );
  }

  async function submit() {
    if (!file) {
      toast.error('Choose a document first.');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      const linkedDocumentId = documentId ? Number(documentId) : null;
      // Comparing against a linked document means picking up where its last review left off.
      let baseline = baselineReviewId;
      if (linkedDocumentId && baseline === null) {
        const existing = await apiFetch<{ items: { id: number }[] }>(
          `/api/review?document_id=${linkedDocumentId}`,
        );
        baseline = existing.items[0]?.id ?? null;
      }
      const response = await analyzeDocument({
        file,
        documentId: linkedDocumentId,
        previousReviewId: baseline,
      });
      const detail = await getReview(response.review_id);
      applyReview(detail);
      setBaselineReviewId(null);
      setFile(null);
      toast.success(
        detail.comparison?.previous_review_id
          ? 'Review complete and compared with the earlier version.'
          : 'Review complete.',
      );
    } catch (caught) {
      const message = reviewErrorMessage(caught);
      setError(message);
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  }

  async function reanalyze() {
    if (!review) return;
    setReanalyzing(true);
    setError('');
    try {
      const response = await reanalyzeReview(review.review_id);
      applyReview(await getReview(response.review.review_id));
      toast.success('Re-analysed the latest version.');
    } catch (caught) {
      const message = reviewErrorMessage(caught);
      setError(message);
      toast.error(message);
    } finally {
      setReanalyzing(false);
    }
  }

  function focusFinding(findingId: number) {
    setFilter('all');
    setActiveFindingId(findingId);
    if (typeof document === 'undefined') return;
    window.requestAnimationFrame(() => {
      document
        .getElementById(`finding-${findingId}`)
        ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  function reset() {
    setReview(null);
    setBaselineReviewId(null);
    setActiveFindingId(null);
    setError('');
  }

  return (
    <div className="space-y-8">
      <div>
        <p className="eyebrow">Document intelligence</p>
        <h1 className="mt-2 font-display text-3xl tracking-tight sm:text-4xl">
          Review a document clause by clause
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Every concern is tied to the wording that raised it and the page it appears on. Track what
          you have resolved, compare a revision against the version you already reviewed, and ask
          questions about any single clause.
        </p>
      </div>

      {error ? (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-200"
        >
          {error}
        </div>
      ) : null}

      {/* `minmax(0, …)` on both axes and `min-w-0` on the columns stop the grid tracks from
          being sized by the upload panel's min-content, which otherwise overflows narrow
          viewports. */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,.8fr)_minmax(0,1.2fr)]">
        <div className="min-w-0 space-y-4">
          <UploadPanel
            file={file}
            documentId={documentId}
            documents={documents}
            loadingDocuments={loadingDocs}
            submitting={submitting}
            baselineReviewId={baselineReviewId}
            onFileChange={setFile}
            onDocumentChange={setDocumentId}
            onSubmit={() => void submit()}
          />
          {review ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="w-full"
              onClick={() => {
                reset();
                setBaselineReviewId(review.review_id);
                toast.info('Upload the revised copy to compare it with this review.');
              }}
            >
              Compare a revised copy against this
            </Button>
          ) : null}
        </div>

        <div className="min-w-0 space-y-6">
          {loadingReview ? (
            <Skeleton className="h-64" />
          ) : !review ? (
            <Card className="flex min-h-[520px] flex-col items-center justify-center p-8 text-center">
              <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-forest/10 text-forest">
                <BookOpen className="h-5 w-5" />
              </span>
              <h2 className="mt-5 text-xl font-bold">No review yet</h2>
              <p className="mt-2 max-w-md text-sm leading-6 text-muted">
                Choose a document to see its clauses, the concerns raised against each one, and what
                you decide about them.
              </p>
              <p className="mt-6 flex items-start gap-2 rounded-xl bg-amber-50 p-3 text-left text-xs leading-5 text-amber-900 dark:bg-amber-500/10 dark:text-amber-100">
                <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                This is automated drafting support, not legal advice. A qualified lawyer should
                confirm anything you rely on.
              </p>
            </Card>
          ) : (
            <>
              <ReviewSummary
                review={review}
                reanalyzing={reanalyzing}
                onReanalyze={() => void reanalyze()}
                onDelete={() => void confirmDeleteReview(review, reset)}
              />

              <ComparisonPanel
                comparison={review.comparison}
                onSelectFinding={focusFinding}
              />

              <Card>
                <CardContent className="space-y-4 pt-6">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <h2 className="text-lg font-bold tracking-tight">
                      Findings ({visibleFindings.length} of {findings.length})
                    </h2>
                    <div className="flex flex-wrap gap-1.5">
                      {FILTERS.map((option) => (
                        <button
                          key={option.value}
                          type="button"
                          aria-pressed={filter === option.value}
                          onClick={() => setFilter(option.value)}
                          className={
                            filter === option.value
                              ? 'rounded-full bg-forest px-3 py-1 text-xs font-semibold text-white'
                              : 'rounded-full border border-border px-3 py-1 text-xs font-semibold text-muted transition hover:border-forest/40 hover:text-forest'
                          }
                        >
                          {option.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {reanalyzing ? (
                    <p className="flex items-center gap-2 text-xs text-muted">
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      Re-analysing the latest version...
                    </p>
                  ) : null}

                  {visibleFindings.length ? (
                    <div className="space-y-4">
                      {visibleFindings.map((finding) => (
                        <FindingCard
                          key={finding.id}
                          finding={finding}
                          onUpdated={replaceFinding}
                          expanded={finding.id === activeFindingId}
                        />
                      ))}
                    </div>
                  ) : (
                    <EmptyState
                      icon={BookOpen}
                      title="Nothing in this filter"
                      description="Change the filter to see the rest of the findings for this document."
                    />
                  )}
                </CardContent>
              </Card>

              <ClauseViewer
                clauses={review.clauses}
                findings={findings}
                activeFindingId={activeFindingId}
                onSelectFinding={focusFinding}
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
