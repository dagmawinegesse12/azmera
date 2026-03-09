"use client";

// ── Global error boundary ──────────────────────────────────────────
import { useEffect } from "react";

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function GlobalError({ error, reset }: ErrorProps) {
  useEffect(() => {
    // Log to console in development; swap for Sentry or similar in production
    console.error("[Azmera] Unhandled error:", error);
  }, [error]);

  return (
    <html lang="en">
      <body className="bg-[#05080f] text-[#e0e8f0] min-h-screen flex items-center justify-center">
        <div className="text-center max-w-md px-6">
          <div className="text-[#e74c3c] text-5xl mb-4">⚠</div>
          <h1 className="text-xl font-semibold mb-2">Something went wrong</h1>
          <p className="text-[#7a90a8] text-sm mb-6">
            {error.message || "An unexpected error occurred. Please try again."}
          </p>
          <button
            onClick={reset}
            className="bg-[#27ae60] text-white rounded-lg px-6 py-2 text-sm font-medium hover:opacity-90 transition-opacity"
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
