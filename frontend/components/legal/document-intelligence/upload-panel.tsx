'use client';

import { useState } from 'react';
import { FileText, Loader2, Upload, X } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  MAX_REVIEW_UPLOAD_MB,
  REVIEW_ACCEPT_ATTRIBUTE,
  checkReviewUpload,
  formatFileSize,
} from '@/lib/validation';
import type { DocumentSummary } from '@/lib/types';

type UploadPanelProps = {
  file: File | null;
  documentId: string;
  documents: DocumentSummary[];
  loadingDocuments: boolean;
  submitting: boolean;
  baselineReviewId: number | null;
  onFileChange: (file: File | null) => void;
  onDocumentChange: (documentId: string) => void;
  onSubmit: () => void;
};

export function UploadPanel({
  file,
  documentId,
  documents,
  loadingDocuments,
  submitting,
  baselineReviewId,
  onFileChange,
  onDocumentChange,
  onSubmit,
}: UploadPanelProps) {
  const [dragging, setDragging] = useState(false);
  const [checking, setChecking] = useState(false);

  async function accept(next: File | undefined) {
    if (!next) return;
    setChecking(true);
    try {
      const result = await checkReviewUpload(next);
      if (!result.ok) {
        toast.error(result.message);
        return;
      }
      onFileChange(next);
    } finally {
      setChecking(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>1. Choose a file</CardTitle>
        <p className="text-sm text-muted">
          PDF, DOCX, or TXT up to {MAX_REVIEW_UPLOAD_MB} MB.
          {baselineReviewId ? ' This will be compared with the version you just reviewed.' : ''}
        </p>
      </CardHeader>
      <CardContent className="space-y-5">
        <label
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            void accept(event.dataTransfer.files?.[0]);
          }}
          className={
            dragging
              ? 'flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-forest bg-forest/5 px-6 py-10 text-center'
              : 'flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-border px-6 py-10 text-center transition hover:border-forest/40 hover:bg-forest/5'
          }
        >
          <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-forest/10 text-forest">
            {checking ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Upload className="h-5 w-5" />
            )}
          </span>
          <span className="mt-4 text-sm font-bold text-ink dark:text-white">
            Drop a document here, or choose a file
          </span>
          <span className="mt-1.5 text-xs text-muted">
            Clause-level page references are exact for PDFs and estimated for DOCX and TXT.
          </span>
          <input
            type="file"
            accept={REVIEW_ACCEPT_ATTRIBUTE}
            className="sr-only"
            onChange={(event) => void accept(event.target.files?.[0])}
          />
        </label>

        {file ? (
          <div className="flex min-w-0 items-center gap-3 rounded-xl border border-border p-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-muted/10 text-muted">
              <FileText className="h-4 w-4" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-semibold text-ink dark:text-white">
                {file.name}
              </span>
              <span className="block text-xs text-muted">{formatFileSize(file.size)}</span>
            </span>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => onFileChange(null)}
              aria-label={`Remove ${file.name}`}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        ) : null}

        <div className="border-t border-border pt-5">
          <Label htmlFor="review-document">Link to a saved document (optional)</Label>
          <Select
            id="review-document"
            className="mt-1.5 min-w-0"
            value={documentId}
            onChange={(event) => onDocumentChange(event.target.value)}
            disabled={loadingDocuments || submitting}
          >
            <option value="">{loadingDocuments ? 'Loading documents...' : 'No linked document'}</option>
            {documents.map((item) => (
              <option key={item.id} value={item.id}>
                {item.title}
              </option>
            ))}
          </Select>
          <p className="mt-1.5 text-xs leading-5 text-muted">
            Linking stores each upload as a version, so you can compare a revision against the one
            you already reviewed.
          </p>
        </div>

        <Button
          type="button"
          className="w-full"
          size="lg"
          disabled={!file || submitting || checking}
          onClick={onSubmit}
        >
          {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          {submitting ? 'Reviewing clauses...' : 'Review clauses'}
        </Button>
      </CardContent>
    </Card>
  );
}
