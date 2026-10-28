import { NextResponse, type NextRequest } from "next/server";

const AUTH_COOKIE = "jes_access_token";

const PROTECTED_PREFIXES = [
  "/dashboard",
  "/projects",
  "/inventory",
  "/purchases",
  "/alerts",
  "/users",
  "/settings",
  "/audit",
  "/change-password",
];

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasSession = request.cookies.has(AUTH_COOKIE);

  if (pathname === "/") {
    return NextResponse.redirect(
      new URL(hasSession ? "/dashboard" : "/login", request.url),
    );
  }

  if (PROTECTED_PREFIXES.some((prefix) => pathname.startsWith(prefix))) {
    if (!hasSession) {
      const loginUrl = new URL("/login", request.url);
      if (pathname !== "/login" && pathname !== "/change-password") {
        loginUrl.searchParams.set("next", pathname);
      }
      return NextResponse.redirect(loginUrl);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!api|_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)",
  ],
};
