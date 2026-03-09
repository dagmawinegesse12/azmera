// @ts-check

const PYTHON_API_BASE = process.env.PYTHON_API_BASE ?? "http://127.0.0.1:8000";
/** @type {import('next').NextConfig} */
const nextConfig = {
  // All /api/* calls are proxied to the Python FastAPI backend.
  // The Next.js API routes in src/app/api/ act as a thin translation layer,
  // so the frontend never talks directly to Python — only to Next.js routes.
  async rewrites() {
    return [];
  },
  // Pass the Python API base URL into server components and API routes.
  env: {
    PYTHON_API_BASE,
  },
  // Allow images from CHIRPS / external sources if needed
  images: {
    remotePatterns: [],
  },
  // Strict: warn on unused imports, enforce proper typing
  eslint: {
    dirs: ["src"],
  },
};

module.exports = nextConfig;
