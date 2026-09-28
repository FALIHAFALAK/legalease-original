import * as React from 'react';
import { cn } from '@/lib/utils';

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(({ className, ...props }, ref) => (
  <input ref={ref} className={cn('flex h-11 w-full rounded-xl border border-border bg-card px-3.5 text-sm text-ink shadow-sm outline-none transition placeholder:text-muted/70 focus:border-forest focus:ring-4 focus:ring-forest/10 disabled:cursor-not-allowed disabled:opacity-50 dark:text-white', className)} {...props} />
));
Input.displayName = 'Input';

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(({ className, ...props }, ref) => (
  <textarea ref={ref} className={cn('flex min-h-28 w-full resize-y rounded-xl border border-border bg-card px-3.5 py-3 text-sm text-ink shadow-sm outline-none transition placeholder:text-muted/70 focus:border-forest focus:ring-4 focus:ring-forest/10 disabled:cursor-not-allowed disabled:opacity-50 dark:text-white', className)} {...props} />
));
Textarea.displayName = 'Textarea';

export const Select = React.forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(({ className, ...props }, ref) => (
  <select ref={ref} className={cn('flex h-11 w-full rounded-xl border border-border bg-card px-3.5 text-sm text-ink shadow-sm outline-none transition focus:border-forest focus:ring-4 focus:ring-forest/10 dark:text-white', className)} {...props} />
));
Select.displayName = 'Select';
