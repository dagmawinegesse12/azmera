import Link from "next/link";

// ── 404 page ───────────────────────────────────────────────────────
export default function NotFound() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-6">
      <div className="text-center max-w-md">
        <p className="text-text-faint text-6xl font-bold mb-4">404</p>
        <h1 className="text-text-primary text-xl font-semibold mb-2">Page not found</h1>
        <p className="text-text-muted text-sm mb-8">
          The page you&apos;re looking for doesn&apos;t exist or has moved.
        </p>
        <div className="flex gap-3 justify-center">
          <Link
            href="/forecast"
            className="bg-accent-green text-white rounded-lg px-5 py-2 text-sm font-medium hover:opacity-90 transition-opacity"
          >
            Go to Forecast
          </Link>
          <Link
            href="/"
            className="border border-background-border text-text-secondary rounded-lg px-5 py-2 text-sm font-medium hover:bg-background-elevated transition-colors"
          >
            Home
          </Link>
        </div>
      </div>
    </div>
  );
}
