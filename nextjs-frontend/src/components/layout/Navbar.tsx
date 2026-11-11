'use client';

import Link from 'next/link';
import { useTheme } from '@/components/providers/ThemeProvider';
import { Menu, LogOut, User, Sun, Moon, Palette, Layout } from 'lucide-react';

export default function Navbar() {
  const { theme, tokens, setTheme } = useTheme();

  const themeIcons: Record<string, React.ElementType> = {
    light: Sun,
    dark: Moon,
    neon: Palette,
  };

  const ThemeIcon = themeIcons[theme] || Sun;

  return (
    <nav className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-white font-bold">
              G
            </div>
            <Link href="/" className="font-bold text-lg tracking-tight">
              GSAP<span className="text-primary">Theme</span>
            </Link>
          </div>

          <div className="hidden md:flex items-center gap-6">
            <Link
              href="/"
              className="px-3 py-2 rounded-md text-sm font-medium text-textSecondary hover:text-primary hover:bg-surfaceHover transition-colors"
            >
              Home
            </Link>
            <Link
              href="/showcase"
              className="px-3 py-2 rounded-md text-sm font-medium text-textSecondary hover:text-primary hover:bg-surfaceHover transition-colors"
            >
              Showcase
            </Link>
            <div className="relative inline-block">
              <button
                onClick={() => {
                  const next = theme === 'light' ? 'dark' : 'neon';
                  setTheme(next);
                }}
                className="flex items-center gap-2 px-3 py-2 rounded-md text-textSecondary hover:text-primary hover:bg-surfaceHover transition-colors"
                aria-label="Change theme"
              >
                <ThemeIcon className="w-5 h-5" />
                <span className="text-sm font-medium capitalize">{theme}</span>
              </button>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <Link href="/login" className="hidden sm:inline px-4 py-2 rounded-md bg-primary text-white text-sm font-medium hover:bg-primaryHover transition-colors shadow-sm">
              Sign in
            </Link>
            <button className="md:hidden inline p-2 text-textSecondary hover:text-primary">
              <Menu className="w-6 h-6" />
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
