/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  basePath: "/legalease-original",
  assetPrefix: "/legalease-original/",
  trailingSlash: true,
  reactStrictMode: true,
  poweredByHeader: false,
  images: {
    unoptimized: true,
  },
};

module.exports = nextConfig;
