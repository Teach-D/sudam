import { type NextRequest, NextResponse } from 'next/server'

const PROTECTED = ['/dashboard', '/games']

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const isProtected = PROTECTED.some((p) => pathname.startsWith(p))
  if (!isProtected) return NextResponse.next()

  const authPresent = request.cookies.get('auth_present')?.value
  if (!authPresent) {
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    return NextResponse.redirect(url)
  }
  return NextResponse.next()
}

export const config = {
  matcher: ['/dashboard/:path*', '/games/:path*'],
}
