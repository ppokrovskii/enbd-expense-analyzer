/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    missingSuspenseWithCSRBailout: false,
  },
  async rewrites() {
    // Use backend service name in Docker, localhost for local development
    const apiUrl = process.env.API_URL || 'http://backend:8000';
    
    return [
      {
        source: '/api/:path*/',
        destination: `${apiUrl}/api/:path*/`,
      },
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*/`, // Add trailing slash
      },
    ];
  },
};

module.exports = nextConfig;

