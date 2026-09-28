import { ApiError, apiFetch, API_URL } from '@/lib/api';
import type {
  ComparisonResponse,
  FindingDetail,
  FindingQuestionResponse,
  FindingStatus,
  ReanalyzeResponse,
  ReviewDetailResponse,
  ReviewListResponse,
  ReviewMessage,
  ReviewResponse,
} from '@/lib/types';

export type ReviewUpload = {
  file: File;
  documentId?: number | null;
  previousReviewId?: number | null;
};

export function reviewListUrl(documentId?: number | null): string {
  return documentId ? `/api/review?document_id=${documentId}` : '/api/review';
}

/** Direct URL for the PDF report, which is binary and should not go through `apiFetch`. */
export function reviewReportUrl(reviewId: number, options: { resolved?: boolean; questions?: boolean } = {}): string {
  const params = new URLSearchParams({
    include_resolved: options.resolved === false ? 'false' : 'true',
    include_questions: options.questions === false ? 'false' : 'true',
  });
  return `${API_URL}/api/review/${reviewId}/report?${params.toString()}`;
}

export async function analyzeDocument(upload: ReviewUpload): Promise<ReviewResponse> {
  const form = new FormData();
  form.append('file', upload.file);
  if (upload.documentId) form.append('document_id', String(upload.documentId));
  if (upload.previousReviewId) form.append('previous_review_id', String(upload.previousReviewId));
  return apiFetch<ReviewResponse>('/api/review', { method: 'POST', body: form });
}

export function listReviews(documentId?: number | null): Promise<ReviewListResponse> {
  return apiFetch<ReviewListResponse>(reviewListUrl(documentId));
}

export function getReview(reviewId: number): Promise<ReviewDetailResponse> {
  return apiFetch<ReviewDetailResponse>(`/api/review/${reviewId}`);
}

export function deleteReview(reviewId: number): Promise<string> {
  return apiFetch<string>(`/api/review/${reviewId}`, { method: 'DELETE' });
}

export function getComparison(reviewId: number): Promise<ComparisonResponse> {
  return apiFetch<ComparisonResponse>(`/api/review/${reviewId}/comparison`);
}

export function reanalyzeReview(reviewId: number): Promise<ReanalyzeResponse> {
  return apiFetch<ReanalyzeResponse>(`/api/review/${reviewId}/reanalyze`, { method: 'POST' });
}

export function getFinding(findingId: number): Promise<FindingDetail> {
  return apiFetch<FindingDetail>(`/api/review/findings/${findingId}`);
}

export function updateFindingStatus(
  findingId: number,
  update: { status: FindingStatus; note?: string; evidence?: string },
): Promise<FindingDetail> {
  return apiFetch<FindingDetail>(`/api/review/findings/${findingId}`, {
    method: 'PATCH',
    body: JSON.stringify({ note: '', evidence: '', ...update }),
  });
}

export function listFindingQuestions(findingId: number): Promise<ReviewMessage[]> {
  return apiFetch<ReviewMessage[]>(`/api/review/findings/${findingId}/questions`);
}

export function askFindingQuestion(
  findingId: number,
  payload: { question: string; request_revision?: boolean },
): Promise<FindingQuestionResponse> {
  return apiFetch<FindingQuestionResponse>(`/api/review/findings/${findingId}/questions`, {
    method: 'POST',
    body: JSON.stringify({ request_revision: false, ...payload }),
  });
}

export function reviewDisclaimer(): Promise<{ disclaimer: string }> {
  return apiFetch<{ disclaimer: string }>('/api/review/disclaimer');
}

/** Turn a failed review call into something a user can act on. */
export function reviewErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === 'invalid_upload') return error.message;
    if (error.code === 'ai_not_configured')
      return 'Clause-level review is not configured on this deployment yet. Set AI_PROVIDER on the API.';
    if (error.code === 'ai_timeout') return 'The review took too long to respond. Try a shorter document.';
    if (error.code === 'ai_unavailable' || error.code === 'ai_quota_exceeded')
      return 'The AI provider is unavailable right now. Try again shortly.';
    if (error.code === 'invalid_ai_response')
      return 'The AI provider returned an unusable response. Try again, or split the document.';
    if (error.code === 'evidence_required')
      return 'Marking a finding resolved needs a note or evidence describing what changed.';
    if (error.code === 'review_rounds_exceeded')
      return 'This document has reached the comparison round limit. Start a new review instead.';
    return error.message;
  }
  if (error instanceof TypeError)
    return 'Could not reach the review service. Check the API connection and try again.';
  return error instanceof Error ? error.message : 'The review could not be completed.';
}
