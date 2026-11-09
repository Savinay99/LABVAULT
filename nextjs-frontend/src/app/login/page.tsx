'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import { Mail, Lock, User as UserIcon, AlertCircle } from 'lucide-react';

type Mode = 'login' | 'register';

export default function AuthPage() {
  const [mode, setMode] = useState<Mode>('login');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    const formData = new FormData(e.currentTarget as HTMLFormElement);
    const name = formData.get('name') as string;
    const email = formData.get('email') as string;
    const password = formData.get('password') as string;

    try {
      const endpoint = mode === 'login' ? '/login' : '/register';
      const body: Record<string, string> = mode === 'login' ? { email, password } : { name, email, password };
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000'}/api/auth${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.msg || 'Request failed');
      localStorage.setItem('token', data.token);
      router.push('/');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-160px)] flex items-center justify-center px-4 py-12">
      <Card className="w-full max-w-md p-8 shadow-lg" hover={false}>
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-textPrimary">{mode === 'login' ? 'Welcome back' : 'Create account'}</h1>
          <p className="mt-2 text-textSecondary">
            {mode === 'login'
              ? 'Please enter your details to sign in.'
              : 'Join us today and start exploring the design system.'}
          </p>
        </div>

        {error && (
          <div className="mb-6 p-3 rounded-md bg-red-50 border border-red-100 text-red-700 text-sm flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === 'register' && (
            <div className="space-y-2">
              <label className="block text-sm font-medium text-textSecondary">Full name</label>
              <div className="relative">
                <UserIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-textMuted" />
                <input
                  name="name"
                  type="text"
                  required
                  className="w-full pl-9 pr-3 py-2.5 rounded-lg border border-border bg-background text-textPrimary focus:outline-none focus:ring-2 focus:ring-primary transition-colors"
                  placeholder="John Doe"
                />
              </div>
            </div>
          )}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-textSecondary">Email address</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-textMuted" />
              <input
                name="email"
                type="email"
                required
                className="w-full pl-9 pr-3 py-2.5 rounded-lg border border-border bg-background text-textPrimary focus:outline-none focus:ring-2 focus:ring-primary transition-colors"
                placeholder="you@example.com"
              />
            </div>
          </div>
          <div className="space-y-2">
            <label className="block text-sm font-medium text-textSecondary">Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-textMuted" />
              <input
                name="password"
                type="password"
                required
                minLength={6}
                className="w-full pl-9 pr-3 py-2.5 rounded-lg border border-border bg-background text-textPrimary focus:outline-none focus:ring-2 focus:ring-primary transition-colors"
                placeholder="••••••••"
              />
            </div>
          </div>
          <Button type="submit" variant="primary" className="w-full py-3" disabled={loading}>
            {loading ? 'Please wait...' : mode === 'login' ? 'Sign in' : 'Create account'}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-textSecondary">
          {mode === 'login'
            ? "Don't have an account? "
            : 'Already have an account? '}
          <button
            onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
            className="font-medium text-primary hover:underline"
          >
            {mode === 'login' ? 'Sign up' : 'Sign in'}
          </button>
        </p>
      </Card>
    </div>
  );
}
