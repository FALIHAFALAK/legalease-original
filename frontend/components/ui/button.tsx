import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva('inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-semibold transition-all duration-200 disabled:pointer-events-none disabled:opacity-50 active:scale-[.98]', {
  variants: {
    variant: {
      primary: 'bg-forest text-white shadow-[0_8px_20px_rgba(30,58,50,.22)] hover:bg-[#2C5044] hover:shadow-[0_10px_26px_rgba(30,58,50,.3)]',
      secondary: 'border border-border bg-card text-ink hover:border-forest/40 hover:bg-forest/5 dark:text-white',
      ghost: 'text-muted hover:bg-forest/8 hover:text-forest',
      danger: 'bg-red-600 text-white hover:bg-red-700',
      outline: 'border border-forest/30 bg-transparent text-forest hover:bg-forest/5',
    },
    size: {
      sm: 'h-9 px-3.5 text-xs',
      md: 'h-11 px-5',
      lg: 'h-13 px-7 text-base',
      icon: 'h-10 w-10',
    },
  },
  defaultVariants: { variant: 'primary', size: 'md' },
});

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, type = 'button', ...props }, ref) => (
  <button ref={ref} type={type} className={cn(buttonVariants({ variant, size, className }))} {...props} />
));
Button.displayName = 'Button';

export { buttonVariants };
