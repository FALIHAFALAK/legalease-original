import * as React from 'react';
import { cn } from '@/lib/utils';

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('animate-pulse rounded-xl bg-muted/15', className)} {...props} />;
}

export function EmptyState({ icon: Icon, title, description, action }: { icon?: React.ElementType; title: string; description: string; action?: React.ReactNode }) {
  return <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-card px-6 py-16 text-center"><div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-forest/10 text-forest">{Icon ? <Icon className="h-5 w-5" /> : null}</div><h3 className="text-lg font-bold">{title}</h3><p className="mt-2 max-w-md text-sm leading-6 text-muted">{description}</p>{action ? <div className="mt-6">{action}</div> : null}</div>;
}
