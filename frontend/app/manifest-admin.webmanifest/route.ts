// Separate installable app for the admin PWA (006: HTTPS/PWA
// installability) — app/manifest.ts only supports one manifest per
// project, so each app gets its own plain Route Handler instead.
export function GET() {
  return Response.json(
    {
      name: "Los Arrayanes – Admin",
      short_name: "Admin",
      start_url: "/admin",
      scope: "/admin/",
      display: "standalone",
      background_color: "#ffffff",
      theme_color: "#171717",
      icons: [
        { src: "/icon-admin-192", sizes: "192x192", type: "image/png" },
        { src: "/icon-admin-512", sizes: "512x512", type: "image/png" },
      ],
    },
    { headers: { "Content-Type": "application/manifest+json" } }
  );
}
