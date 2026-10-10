// Separate installable app for the mesero PWA (006: HTTPS/PWA
// installability) — app/manifest.ts only supports one manifest per
// project, so each app gets its own plain Route Handler instead.
export function GET() {
  return Response.json(
    {
      name: "Los Arrayanes – Mesero",
      short_name: "Mesero",
      start_url: "/mesero",
      scope: "/mesero/",
      display: "standalone",
      background_color: "#ffffff",
      theme_color: "#c2541f",
      icons: [
        { src: "/icon-mesero-192", sizes: "192x192", type: "image/png" },
        { src: "/icon-mesero-512", sizes: "512x512", type: "image/png" },
      ],
    },
    { headers: { "Content-Type": "application/manifest+json" } }
  );
}
