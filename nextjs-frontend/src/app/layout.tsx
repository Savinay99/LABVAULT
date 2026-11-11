import React from 'react';
import { ThemeProvider } from '@/components/providers/ThemeProvider';

export const metadata = {
  title: 'GSAP Theme System',
  description: 'Professional Next.js + GSAP + Express + MongoDB UI/UX design system',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" data-theme="light">
      <body className="antialiased min-h-screen bg-surface text-textPrimary transition-colors duration-300">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
