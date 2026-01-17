/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // API proxy for development
  async rewrites() {
    return [
      // Removed API rewrites to force direct connection to backend
      // This prevents Netlify 10s timeout on proxy
    ];
  },
};

module.exports = nextConfig;
