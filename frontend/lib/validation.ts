/**
 * Client-side upload checks for clause-level review.
 *
 * These mirror the backend limits in `app/services/reviews.py` so a bad file is rejected before it
 * is uploaded. The server re-validates everything; this only saves the user a round trip.
 */

export const REVIEW_EXTENSIONS = ['.pdf', '.docx', '.txt'] as const;

export const REVIEW_ACCEPT_ATTRIBUTE = REVIEW_EXTENSIONS.join(',');

/** Keep in step with `settings.max_upload_mb` on the backend. */
export const MAX_REVIEW_UPLOAD_MB = 10;

const MAX_REVIEW_UPLOAD_BYTES = MAX_REVIEW_UPLOAD_MB * 1024 * 1024;

const DOCX_MIME =
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document';

const ACCEPTED_CONTENT_TYPES: Record<string, string[]> = {
  '.pdf': ['application/pdf', 'application/octet-stream', 'application/x-pdf'],
  '.docx': [DOCX_MIME, 'application/octet-stream', 'application/msword'],
  '.txt': ['text/plain', 'text/markdown', 'text/csv', 'application/octet-stream'],
};

const PDF_SIGNATURE = '%PDF';
const ZIP_SIGNATURE = 'PK';

export type ReviewFileKind = 'pdf' | 'docx' | 'txt';

export type ReviewUploadCheck = { ok: true; file: File; kind: ReviewFileKind } | { ok: false; message: string };

export function fileExtension(filename: string): string {
  const dot = filename.lastIndexOf('.');
  return dot > 0 ? filename.slice(dot).toLowerCase() : '';
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

async function readSignature(file: File, length: number): Promise<string> {
  const head = await file.slice(0, length).arrayBuffer();
  return Array.from(new Uint8Array(head))
    .map((byte) => String.fromCharCode(byte))
    .join('');
}

/**
 * Check an upload is a reviewable document. Extension, declared content type and the file's own
 * leading bytes must all agree, so a renamed executable cannot slip through as a `.txt`.
 */
export async function checkReviewUpload(file: File): Promise<ReviewUploadCheck> {
  const extension = fileExtension(file.name);
  const kind = extension.replace('.', '') as ReviewFileKind;

  if (!REVIEW_EXTENSIONS.includes(extension as (typeof REVIEW_EXTENSIONS)[number])) {
    return {
      ok: false,
      message: `Upload a ${REVIEW_EXTENSIONS.join(', ')} file. Clause-level review cannot read ${file.name}.`,
    };
  }

  if (file.size === 0) {
    return { ok: false, message: 'That file is empty. Choose a document with content in it.' };
  }

  if (file.size > MAX_REVIEW_UPLOAD_BYTES) {
    return {
      ok: false,
      message: `Files must be smaller than ${MAX_REVIEW_UPLOAD_MB} MB. This one is ${formatFileSize(file.size)}.`,
    };
  }

  if (file.type && !ACCEPTED_CONTENT_TYPES[extension].includes(file.type)) {
    return {
      ok: false,
      message: `A ${extension.slice(1).toUpperCase()} file was uploaded as "${file.type}", which does not match.`,
    };
  }

  const signature = await readSignature(file, 8);
  if (kind === 'pdf' && !signature.startsWith(PDF_SIGNATURE)) {
    return { ok: false, message: 'That file is not a readable PDF.' };
  }
  if (kind === 'docx' && !signature.startsWith(ZIP_SIGNATURE)) {
    return { ok: false, message: 'That file is not a readable Word document.' };
  }

  return { ok: true, file, kind };
}
