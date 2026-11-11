'use client';

import Link from 'next/link';
import { useTheme } from '@/components/providers/ThemeProvider';
import { ArrowRight, Zap, Palette, Layers, Code2 } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';

const features = [
  {
    title: 'Fluid Motion',
    desc: 'GSAP-powered scroll and entrance animations with precise timing controls.',
    icon: Zap,
  },
  {
    title: 'Design Tokens',
    desc: 'Themeable color system with light, dark, and neon modes driven by CSS variables.',
    icon: Palette,
  },
  {
    title: 'Responsive Layout',
    desc: 'Mobile-first grid system that adapts seamlessly across all screen sizes.',
    icon: Layers,
  },
  {
    title: 'TypeScript Safe',
    desc: 'Full type safety across components, theme tokens, and API integration.',
    icon: Code2,
  },
];

export default function HomePage() {
  const { theme, setTheme } = useTheme();

  const itemVariants = {
    hidden: { y: 40, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: { type: 'spring', stiffness: 100, damping: 12 },
    },
  };

  return (
    <section className="min-h-screen flex flex-col items-center justify-center px-4 py-16 text-center relative overflow-hidden">
      <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/stardust.png')] opacity-10 pointer-events-none" />
      <div className="relative z-10 max-w-5xl">
        <motion.h1
          variants={itemVariants}
          initial="hidden"
          animate="visible"
          className="text-4xl md:text-6xl font-extrabold tracking-tight text-textPrimary mb-6"
        >
          Design in motion.<br />
          <span className="text-primary">Built with Framer Motion.</span>
        </motion.h1>
        <motion.p
          variants={itemVariants}
          initial="hidden"
          animate="visible"
          className="text-lg md:text-xl text-textSecondary max-w-2xl mx-auto mb-10"
        >
          A professional design system featuring Next.js, Express.js, MongoDB, and Framer Motion animations.
          Light, dark, and neon themes with a fully functional UI/UX layer.
        </motion.p>
        <motion.div
          variants={itemVariants}
          initial="hidden"
          animate="visible"
          className="hero-cta flex flex-col sm:flex-row gap-4 justify-center items-center"
        >
          <Link href="/showcase" className="px-8 py-4 bg-primary text-white rounded-xl font-semibold text-lg hover:bg-primaryHover transition-colors shadow-lg hover:shadow-xl transform hover:-translate-y-1">
            Explore Showcase <ArrowRight className="ml-2 w-5 h-5" />
          </Link>
          <button onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')} className="px-8 py-4 rounded-xl font-semibold text-lg border border-border text-textPrimary hover:bg-surfaceHover transition-colors">
            Switch Theme
          </button>
        </motion.div>
      </div>

      <motion.div
        variants={{
          hidden: { opacity: 0 },
          visible: {
            opacity: 1,
            transition: { staggerChildren: 0.15 },
          },
        }}
        initial="hidden"
        animate="visible"
        className="mt-20 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-7xl mx-auto px-4"
      >
        {features.map((f) => (
          <motion.div
            key={f.title}
            variants={itemVariants}
            initial="hidden"
            animate="visible"
            className="p-6 rounded-xl border border-border bg-surface hover:shadow-lg hover:-translate-y-2 transition-all duration-300 group"
          >
            <div className="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center mb-4 group-hover:bg-primary group-hover:text-white transition-colors">
              <f.icon className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-semibold text-textPrimary mb-2">{f.title}</h3>
            <p className="text-sm text-textSecondary leading-relaxed">{f.desc}</p>
          </motion.div>
        ))}
      </motion.div>
    </section>
  );
}
