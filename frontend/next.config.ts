import type { NextConfig } from 'next';

// The browser always calls /api/* on the same origin. In development (and in the
// standalone Docker image without a reverse proxy) Next.js forwards those calls to the
// FastAPI backend at BACKEND_URL. In production Caddy routes /api to the backend directly.
const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

const nextConfig: NextConfig = {
  output: 'standalone',
  poweredByHeader: false,
  async rewrites() {
    return [{ source: '/api/:path*', destination: `${BACKEND_URL}/api/:path*` }];
  },
  images: { unoptimized: true },
};

export default nextConfig;
