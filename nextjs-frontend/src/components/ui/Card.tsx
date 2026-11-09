import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

export type CardProps = {
  children: ReactNode;
  className?: string;
  hover?: boolean;
};

export default function Card({ children, className, hover = true }: CardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border border-border bg-surface p-6 text-textPrimary transition-all duration-300',
        hover ? 'hover:shadow-md hover:-translate-y-1' : '',
        className
      )}
    >
      {children}
    </div>
  );
}
