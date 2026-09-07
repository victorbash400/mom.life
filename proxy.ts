import { NextRequest, NextResponse } from "next/server";

export function proxy(request: NextRequest) {
  if (request.nextUrl.pathname.startsWith("/api/") && !["GET", "HEAD", "OPTIONS"].includes(request.method) && request.headers.get("origin") !== request.nextUrl.origin) {
    return NextResponse.json({ error: "Invalid request origin." }, { status: 403 });
  }
  if (!request.cookies.get("mom-life-session") && !request.nextUrl.pathname.startsWith("/api/auth/")) {
    if (request.nextUrl.pathname.startsWith("/api/")) return NextResponse.json({ error: "Sign in to continue." }, { status: 401 });
    return NextResponse.redirect(new URL("/sign-in", request.url));
  }
  return NextResponse.next();
}
export const config = { matcher: ["/", "/api/:path*"] };
