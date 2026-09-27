import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Optimistic route protection (RF-1). Real authorization still lives in
// the backend (DRF permissions) — this only pre-filters navigation so an
// unauthenticated or wrong-role user never even sees a protected page.
// See specs/001-autenticacion-usuarios/plan.md, decision 7.

const BACKEND_API_URL = process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000";

const PUBLIC_ADMIN_PATHS = ["/admin/login"];
const PUBLIC_MESERO_PATHS = ["/mesero/login"];

type SessionInfo = { role?: string };

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const isPublicAdminPath = PUBLIC_ADMIN_PATHS.some((path) =>
    pathname.startsWith(path)
  );
  const isPublicMeseroPath = PUBLIC_MESERO_PATHS.some((path) =>
    pathname.startsWith(path)
  );

  const isAdminRoute = pathname.startsWith("/admin") && !isPublicAdminPath;
  const isMeseroRoute = pathname.startsWith("/mesero") && !isPublicMeseroPath;

  if (!isAdminRoute && !isMeseroRoute) {
    return NextResponse.next();
  }

  const expectedRole = isAdminRoute ? "ADMIN" : "MESERO";
  const loginUrl = new URL(isAdminRoute ? "/admin/login" : "/mesero/login", request.url);

  const sessionCookie = request.cookies.get("sessionid");
  if (!sessionCookie) {
    return NextResponse.redirect(loginUrl);
  }

  const sessionResponse = await fetch(`${BACKEND_API_URL}/api/auth/session`, {
    headers: { cookie: `sessionid=${sessionCookie.value}` },
  });

  if (!sessionResponse.ok) {
    return NextResponse.redirect(loginUrl);
  }

  const session: SessionInfo = await sessionResponse.json();
  if (session.role !== expectedRole) {
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/admin/:path*", "/mesero/:path*"],
};
