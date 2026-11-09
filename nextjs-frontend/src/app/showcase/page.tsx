'use client';

import { useTheme } from '@/components/providers/ThemeProvider';
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Globe, Palette, Monitor, Layers } from 'lucide-react';
import { isThemeId } from '@/lib/tokens';

export default function ShowcasePage() {
  const { tokens, theme, setTheme } = useTheme();
  const [themes, setThemes] = useState<{ id: string; name: string; primary: string }[]>([]);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000'}/api/themes`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` },
    })
      .then((r) => r.json())
      .then((data) => setThemes(data || []))
      .catch(() => {});
  }, []);

  const cardVariants = {
    hidden: { y: 50, opacity: 0 },
    visible: { y: 0, opacity: 1, transition: { duration: 0.5 } },
  };

  return (
    <div className="min-h-screen py-16 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-12">
          <div>
            <h1 className="text-3xl font-bold text-textPrimary mb-2">Theme Showcase</h1>
            <p className="text-textSecondary">Preview and switch between design system themes.</p>
          </div>
        </div>

        <div className="mb-12 p-8 rounded-2xl border border-border bg-surface shadow-sm">
          <h2 className="text-xl font-semibold text-textPrimary mb-6">Current theme: <span className="text-primary capitalize">{theme}</span></h2>
          <div className="flex flex-wrap gap-3">
            {['light', 'dark', 'neon'].map((t) => (
              <button
                key={t}
                onClick={() => setTheme(isThemeId(t) ? t : 'light')}
                className={`px-4 py-2 rounded-lg font-medium transition-all border ${
                  theme === t
                    ? 'bg-primary text-white border-primary shadow-lg'
                    : 'bg-background text-textSecondary border-border hover:border-primary hover:text-primary'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        <h2 className="text-2xl font-bold text-textPrimary mb-8">Available themes (from API)</h2>
        <AnimatePresence>
          <motion.div
            variants={{
              hidden: { opacity: 0 },
              visible: {
                opacity: 1,
                transition: { staggerChildren: 0.1 },
              },
            }}
            initial="hidden"
            animate="visible"
            className="showcase-grid grid grid-cols-1 md:grid-cols-3 gap-6"
          >
            {themes.length > 0 ? (
              themes.map((t) => (
                <motion.div
                  key={t.id}
                  variants={cardVariants}
                  initial="hidden"
                  animate="visible"
                  className="p-6 rounded-xl border border-border bg-surface"
                >
                  <div className="flex items-center justify-between mb-4">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: t.primary }} />
                    <span className="text-sm font-medium text-textMuted">{t.id}</span>
                  </div>
                  <h3 className="text-lg font-semibold text-textPrimary">{t.name}</h3>
                  <div className="mt-4 h-12 rounded-lg border border-border" style={{ backgroundColor: t.primary + '20' }} />
                </motion.div>
              ))
            ) : (
              <div className="col-span-3 text-center py-12 text-textMuted">Loading themes...</div>
            )}
          </motion.div>
        </AnimatePresence>

        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8">
          {[Globe, Palette, Monitor, Layers].slice(0, 3).map((Icon) => (
            <div key={Icon.displayName} className="p-6 rounded-xl border border-border bg-surface">
              <div className="w-12 h-12 rounded-lg bg-primary/10 text-primary flex items-center justify-center mb-4">
                <Icon className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-semibold text-textPrimary mb-2">Component preview</h3>
              <p className="text-sm text-textSecondary">Framer Motion animated UI elements integrated with the theme system.</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
