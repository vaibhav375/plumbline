import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The app uses no next/image, so the sharp-based optimizer never needs to run.
  images: { unoptimized: true },
};

export default nextConfig;
