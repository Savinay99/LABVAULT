export default function Footer() {
  return (
    <footer className="border-t border-border bg-surface py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-textMuted">
        <p>GSAP Theme System. Built with Next.js, GSAP, Express & MongoDB.</p>
        <p>&copy; {new Date().getFullYear()} Design System. All rights reserved.</p>
      </div>
    </footer>
  );
}
