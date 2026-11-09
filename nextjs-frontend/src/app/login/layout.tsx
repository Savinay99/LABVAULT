import Link from 'next/link';

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col">
      <nav className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link href="/" className="font-bold text-lg tracking-tight">
              GSAP<span className="text-primary">Theme</span>
            </Link>
            <div className="flex items-center gap-4">
              <Link href="/login" className="px-4 py-2 rounded-md bg-primary text-white text-sm font-medium hover:bg-primaryHover transition-colors shadow-sm">
                Sign in
              </Link>
            </div>
          </div>
        </div>
      </nav>
      <main className="flex-1">{children}</main>
    </div>
  );
}
