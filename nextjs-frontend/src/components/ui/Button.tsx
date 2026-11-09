import type { ButtonHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'outline' | 'ghost';
};

export default function Button({ className, variant = 'primary', ...props }: ButtonProps) {
  const base =
    'inline-flex items-center justify-center rounded-md font-medium transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none';
  const variants = {
    primary: 'bg-primary text-white hover:bg-primaryHover focus:ring-primary shadow-sm',
    outline:
      'border border-border bg-background hover:bg-surfaceHover focus:ring-primary text-textPrimary',
    ghost: 'hover:bg-surfaceHover focus:ring-primary text-textPrimary',
  };
  return (
    <button className={cn(base, variants[variant], className)} {...props} />
  );
}
