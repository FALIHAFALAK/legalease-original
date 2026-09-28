'use client';

import { useState } from 'react';
import { CheckCircle2, Loader2, ShieldQuestion } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/input';
import { reviewErrorMessage, updateFindingStatus } from '@/lib/review-api';
import type { FindingDetail, FindingStatus } from '@/lib/types';
import { FindingStatusBadge } from './labels';

const OPTIONS: { value: FindingStatus; label: string; hint: string }[] = [
  { value: 'open', label: 'Open', hint: 'Still outstanding.' },
  { value: 'resolved', label: 'Resolved', hint: 'Needs a note or evidence.' },
  { value: 'dismissed', label: 'Dismissed', hint: 'Not a real issue here.' },
  {
    value: 'needs_professional_review',
    label: 'Needs a lawyer',
    hint: 'Refer this to a qualified lawyer.',
  },
];

type StatusControlProps = {
  finding: FindingDetail;
  onUpdated: (finding: FindingDetail) => void;
};

/**
 * Persist a decision about one finding. Resolving a finding requires a note or evidence, which the
 * form asks for up front rather than letting the server reject the request.
 */
export function StatusControl({ finding, onUpdated }: StatusControlProps) {
  const [note, setNote] = useState('');
  const [evidence, setEvidence] = useState('');
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const needsReason = open && note.trim().length === 0 && evidence.trim().length === 0;

  async function save(status: FindingStatus) {
    if (status === 'resolved' && needsReason) {
      setError('Add a note or evidence describing what changed before marking this resolved.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      const updated = await updateFindingStatus(finding.id, {
        status,
        note: note.trim(),
        evidence: evidence.trim(),
      });
      onUpdated(updated);
      setNote('');
      setEvidence('');
      setOpen(false);
      toast.success(`Marked ${status.replace(/_/g, ' ')}.`);
    } catch (caught) {
      setError(reviewErrorMessage(caught));
      toast.error(reviewErrorMessage(caught));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-bold text-ink dark:text-white">Your decision</p>
        <FindingStatusBadge status={finding.status} />
      </div>

      {finding.status_note || finding.status_evidence ? (
        <div className="mt-3 space-y-1 rounded-xl bg-muted/8 p-3 text-xs leading-5 text-muted">
          {finding.status_note ? <p>Note: {finding.status_note}</p> : null}
          {finding.status_evidence ? <p>Evidence: {finding.status_evidence}</p> : null}
        </div>
      ) : null}

      {!open ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {OPTIONS.map((option) => (
            <Button
              key={option.value}
              type="button"
              size="sm"
              variant={finding.status === option.value ? 'primary' : 'secondary'}
              disabled={saving || finding.status === option.value}
              onClick={() => {
                setError('');
                if (option.value === 'resolved' || option.value === 'dismissed') {
                  setOpen(true);
                  return;
                }
                void save(option.value);
              }}
            >
              {option.value === 'resolved' ? <CheckCircle2 className="h-4 w-4" /> : null}
              {option.value === 'needs_professional_review' ? (
                <ShieldQuestion className="h-4 w-4" />
              ) : null}
              {option.label}
            </Button>
          ))}
        </div>
      ) : (
        <div className="mt-3 space-y-3">
          <div>
            <label
              htmlFor={`note-${finding.id}`}
              className="text-xs font-semibold text-ink dark:text-white"
            >
              What changed?
            </label>
            <Textarea
              id={`note-${finding.id}`}
              rows={2}
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="Agreed 45 day payment terms by email on 12 March."
              className="mt-1.5 min-h-20"
            />
          </div>
          <div>
            <label
              htmlFor={`evidence-${finding.id}`}
              className="text-xs font-semibold text-ink dark:text-white"
            >
              Evidence (optional)
            </label>
            <Textarea
              id={`evidence-${finding.id}`}
              rows={2}
              value={evidence}
              onChange={(event) => setEvidence(event.target.value)}
              placeholder="Signed side letter, clause reference, or a link to the thread."
              className="mt-1.5 min-h-20"
            />
          </div>
          {error ? (
            <p role="alert" className="text-xs font-semibold text-red-600">
              {error}
            </p>
          ) : null}
          <div className="flex flex-wrap gap-2">
            {OPTIONS.map((option) => (
              <Button
                key={option.value}
                type="button"
                size="sm"
                variant={option.value === finding.status ? 'primary' : 'secondary'}
                disabled={saving}
                onClick={() => void save(option.value)}
              >
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                {option.label}
              </Button>
            ))}
            <Button
              type="button"
              size="sm"
              variant="ghost"
              disabled={saving}
              onClick={() => {
                setOpen(false);
                setError('');
              }}
            >
              Cancel
            </Button>
          </div>
          <p className="text-[11px] leading-4 text-muted">
            Marking something resolved records your note against this clause, so the report shows why
            you closed it.
          </p>
        </div>
      )}
    </div>
  );
}
