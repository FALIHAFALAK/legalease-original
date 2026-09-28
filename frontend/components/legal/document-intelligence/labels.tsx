'use client';

import type { ComponentProps } from 'react';
import { Badge } from '@/components/ui/badge';
import type {
  FindingCategory,
  FindingLifecycle,
  FindingStatus,
  ReviewSeverity,
} from '@/lib/types';

type BadgeVariant = ComponentProps<typeof Badge>['variant'];

export const CATEGORY_LABELS: Record<FindingCategory, string> = {
  unclear_clause: 'Unclear clause',
  missing_information: 'Missing information',
  inconsistent_detail: 'Inconsistent detail',
  ambiguous_wording: 'Ambiguous wording',
  unusual_obligation: 'Unusual obligation',
  professional_review: 'Professional review',
};

export const STATUS_LABELS: Record<FindingStatus, string> = {
  open: 'Open',
  resolved: 'Resolved',
  dismissed: 'Dismissed',
  needs_professional_review: 'Needs a lawyer',
};

export const LIFECYCLE_LABELS: Record<FindingLifecycle, string> = {
  new: 'New',
  fixed: 'Fixed in this version',
  unresolved: 'Still unresolved',
  carried_over: 'Carried over',
};

const SEVERITY_VARIANTS: Record<ReviewSeverity, BadgeVariant> = {
  high: 'danger',
  medium: 'warning',
  low: 'muted',
};

const STATUS_VARIANTS: Record<FindingStatus, BadgeVariant> = {
  open: 'default',
  resolved: 'success',
  dismissed: 'muted',
  needs_professional_review: 'warning',
};

const LIFECYCLE_VARIANTS: Record<FindingLifecycle, BadgeVariant> = {
  new: 'danger',
  fixed: 'success',
  unresolved: 'warning',
  carried_over: 'default',
};

export function SeverityBadge({ severity }: { severity: ReviewSeverity }) {
  return (
    <Badge variant={SEVERITY_VARIANTS[severity] ?? 'muted'}>
      {severity === 'high' ? 'High' : severity === 'medium' ? 'Medium' : 'Low'} priority
    </Badge>
  );
}

export function FindingStatusBadge({ status }: { status: FindingStatus }) {
  return <Badge variant={STATUS_VARIANTS[status] ?? 'muted'}>{STATUS_LABELS[status] ?? status}</Badge>;
}

export function LifecycleBadge({ outcome }: { outcome: FindingLifecycle }) {
  return (
    <Badge variant={LIFECYCLE_VARIANTS[outcome] ?? 'muted'}>
      {LIFECYCLE_LABELS[outcome] ?? outcome}
    </Badge>
  );
}

export function CategoryLabel({ category }: { category: FindingCategory | string }) {
  return (
    <span className="text-xs font-bold text-ink dark:text-white">
      {CATEGORY_LABELS[category as FindingCategory] ?? category}
    </span>
  );
}
