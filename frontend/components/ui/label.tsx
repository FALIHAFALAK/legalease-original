import * as React from 'react';
import { cn } from '@/lib/utils';

export function Label({ className, ...props }: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return <label className={cn('text-sm font-semibold text-ink dark:text-white', className)} {...props} />;
}

export function FieldHint({ children }: { children: React.ReactNode }) {
  return <p className="mt-1.5 text-xs leading-5 text-muted">{children}</p>;
}

export function FieldError({ children }: { children?: React.ReactNode }) {
  return children ? <p className="mt-1.5 text-xs font-medium text-red-600">{children}</p> : null;
}
