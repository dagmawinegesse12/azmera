import Link from "next/link";

// ── Feature card data ─────────────────────────────────────────────────────────

const FEATURES = [
  {
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
        className="w-6 h-6"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M9 6.75V15m6-6v8.25m.503 3.498 4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 0 0-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0Z"
        />
      </svg>
    ),
    title: "13 Regions",
    body: "Independent logistic regression models for all 13 Ethiopian administrative regions, each trained on region-specific CHIRPS precipitation and SST predictors.",
  },
  {
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
        className="w-6 h-6"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z"
        />
      </svg>
    ),
    title: "Validated Skill",
    body: "Rolling-origin Heidke Skill Score evaluation using 27 years of prospective data. Only models that beat climatology earn a full release — no false confidence.",
  },
  {
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
        className="w-6 h-6"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M9 12.75 11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 0 1-1.043 3.296 3.745 3.745 0 0 1-3.296 1.043A3.745 3.745 0 0 1 12 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 0 1-3.296-1.043 3.745 3.745 0 0 1-1.043-3.296A3.745 3.745 0 0 1 3 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 0 1 1.043-3.296 3.746 3.746 0 0 1 3.296-1.043A3.746 3.746 0 0 1 12 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 0 1 3.296 1.043 3.746 3.746 0 0 1 1.043 3.296A3.745 3.745 0 0 1 21 12Z"
        />
      </svg>
    ),
    title: "Transparent Tiers",
    body: "Full, Experimental, and Suppressed release tiers based on out-of-sample skill. Forecasters always know how much to trust each regional outlook before acting.",
  },
];

// ── Stat bar items ────────────────────────────────────────────────────────────

const STATS = [
  { value: "13", label: "regions" },
  { value: "2", label: "seasons" },
  { value: "27 yr", label: "validation window" },
  { value: "HSS", label: "skill metric" },
];

// ── Page ──────────────────────────────────────────────────────────────────────

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col overflow-x-hidden" style={{ background: "var(--background)" }}>

      {/* ── Subtle grid overlay ──────────────────────────────────────────── */}
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 z-0"
        style={{
          backgroundImage:
            "linear-gradient(rgba(30,42,61,0.35) 1px, transparent 1px), linear-gradient(90deg, rgba(30,42,61,0.35) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />

      {/* ── Glow blobs ───────────────────────────────────────────────────── */}
      <div
        aria-hidden="true"
        className="pointer-events-none fixed z-0"
        style={{
          top: "-20%",
          left: "50%",
          transform: "translateX(-50%)",
          width: "900px",
          height: "600px",
          background:
            "radial-gradient(ellipse at center, rgba(39,174,96,0.07) 0%, rgba(39,174,96,0.02) 45%, transparent 70%)",
          filter: "blur(40px)",
        }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none fixed z-0"
        style={{
          bottom: "0",
          right: "-10%",
          width: "600px",
          height: "500px",
          background:
            "radial-gradient(ellipse at center, rgba(30,90,180,0.06) 0%, transparent 70%)",
          filter: "blur(60px)",
        }}
      />

      {/* ── Nav ──────────────────────────────────────────────────────────── */}
      <header className="relative z-10 flex items-center justify-between px-8 py-5 border-b" style={{ borderColor: "var(--background-border)" }}>
        <div className="flex items-center gap-3">
          {/* Rain-drop / water mark icon */}
          <svg
            viewBox="0 0 32 32"
            fill="none"
            className="w-7 h-7 shrink-0"
            aria-hidden="true"
          >
            <path
              d="M16 3 C16 3, 6 16, 6 21 a10 10 0 0 0 20 0 C26 16, 16 3, 16 3Z"
              fill="var(--accent-green)"
              opacity="0.9"
            />
            <path
              d="M11 22 a6 6 0 0 0 6 5"
              stroke="white"
              strokeWidth="1.5"
              strokeLinecap="round"
              opacity="0.5"
            />
          </svg>
          <span className="text-lg font-semibold tracking-tight" style={{ color: "var(--text-primary)" }}>
            Azmera
          </span>
        </div>

        <nav className="flex items-center gap-6 text-sm" style={{ color: "var(--text-muted)" }}>
          <Link href="/forecast" className="hover:text-text-primary transition-colors duration-150" style={{ color: "inherit" }}>
            Forecast
          </Link>
          <Link href="/validation" className="hover:text-text-primary transition-colors duration-150" style={{ color: "inherit" }}>
            Validation
          </Link>
          <Link href="/map" className="hover:text-text-primary transition-colors duration-150" style={{ color: "inherit" }}>
            Map
          </Link>
        </nav>
      </header>

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <main className="relative z-10 flex flex-col items-center justify-center flex-1 px-6 pt-24 pb-16 text-center">

        {/* Season badge */}
        <div
          className="inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-medium mb-8 border"
          style={{
            background: "rgba(39,174,96,0.08)",
            borderColor: "rgba(39,174,96,0.25)",
            color: "var(--accent-green)",
          }}
        >
          <span
            className="w-1.5 h-1.5 rounded-full inline-block animate-pulse"
            style={{ background: "var(--accent-green)" }}
          />
          Kiremt 2026 · March outlook available
        </div>

        {/* Name block */}
        <h1
          className="text-7xl font-bold tracking-tight leading-none mb-2"
          style={{ color: "var(--text-primary)" }}
        >
          Azmera
        </h1>
        <p
          className="text-2xl font-light tracking-widest mb-6"
          style={{ color: "var(--text-muted)", fontFamily: "var(--font-geist-sans, sans-serif)" }}
        >
          አዝመራ
        </p>

        {/* Subtitle */}
        <p
          className="text-xl font-medium mb-5 max-w-xl"
          style={{ color: "var(--text-secondary)" }}
        >
          Probabilistic seasonal rainfall forecasts for Ethiopia
        </p>

        {/* Description */}
        <p
          className="text-base leading-relaxed max-w-2xl mb-10"
          style={{ color: "var(--text-muted)" }}
        >
          Azmera issues above-/near-/below-normal tercile outlooks for Ethiopia&apos;s 13
          administrative regions using SST-based logistic regression trained on CHIRPS
          satellite data and validated over 27 years of rolling-origin hindcasts.
          Every forecast carries an explicit skill tier so meteorologists always know
          how much confidence the model warrants.
        </p>

        {/* CTA buttons */}
        <div className="flex flex-wrap items-center justify-center gap-4 mb-20">
          <Link
            href="/forecast"
            className="inline-flex items-center gap-2 rounded-xl px-7 py-3 text-sm font-semibold text-white transition-all duration-200 hover:brightness-110 active:scale-95 shadow-lg"
            style={{
              background: "var(--accent-green)",
              boxShadow: "0 0 24px rgba(39,174,96,0.3)",
            }}
          >
            View Forecasts
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 8h10M9 4l4 4-4 4" />
            </svg>
          </Link>
          <Link
            href="/validation"
            className="inline-flex items-center gap-2 rounded-xl px-7 py-3 text-sm font-semibold transition-all duration-200 hover:brightness-125 active:scale-95 border"
            style={{
              color: "var(--text-secondary)",
              borderColor: "var(--background-border)",
              background: "rgba(15,22,35,0.6)",
            }}
          >
            Explore Validation
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 8h10M9 4l4 4-4 4" />
            </svg>
          </Link>
        </div>

        {/* ── Stat bar ───────────────────────────────────────────────────── */}
        <div
          className="flex flex-wrap justify-center gap-px rounded-2xl overflow-hidden border mb-24 w-full max-w-2xl"
          style={{ borderColor: "var(--background-border)", background: "var(--background-border)" }}
        >
          {STATS.map(({ value, label }) => (
            <div
              key={label}
              className="flex flex-col items-center justify-center flex-1 min-w-[120px] px-6 py-4"
              style={{ background: "var(--background-elevated)" }}
            >
              <span className="text-2xl font-bold tabular-nums" style={{ color: "var(--accent-green)" }}>
                {value}
              </span>
              <span className="text-xs mt-0.5 uppercase tracking-widest" style={{ color: "var(--text-faint)" }}>
                {label}
              </span>
            </div>
          ))}
        </div>

        {/* ── Feature cards ──────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 w-full max-w-4xl mb-8">
          {FEATURES.map(({ icon, title, body }) => (
            <div
              key={title}
              className="flex flex-col items-start gap-4 rounded-2xl p-6 border text-left transition-all duration-200 hover:border-opacity-60"
              style={{
                background: "var(--background-elevated)",
                borderColor: "var(--background-border)",
              }}
            >
              {/* Icon circle */}
              <div
                className="flex items-center justify-center w-10 h-10 rounded-xl shrink-0"
                style={{
                  background: "rgba(39,174,96,0.1)",
                  color: "var(--accent-green)",
                }}
              >
                {icon}
              </div>
              <div>
                <h3 className="text-base font-semibold mb-2" style={{ color: "var(--text-primary)" }}>
                  {title}
                </h3>
                <p className="text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
                  {body}
                </p>
              </div>
            </div>
          ))}
        </div>
      </main>

      {/* ── Footer ───────────────────────────────────────────────────────── */}
      <footer
        className="relative z-10 text-center py-6 text-xs border-t"
        style={{
          color: "var(--text-faint)",
          borderColor: "var(--background-border)",
        }}
      >
        © 2026 Azmera · Created by Dagmawi Negesse · Built for Ethiopia&apos;s meteorological community
      </footer>
    </div>
  );
}
