import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Lets the dev server (HMR/Fast Refresh) trust requests coming from
  // the PC's LAN IP, so phones on the restaurant's WiFi can load the app
  // without Next.js silently forcing full page reloads on every client
  // interaction (its default cross-origin protection for the dev
  // server). See https://nextjs.org/docs/app/api-reference/config/next-config-js/allowedDevOrigins
  allowedDevOrigins: ["192.168.18.32"],
};

export default nextConfig;
