import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: '수담',
  description: 'AI 사범과 함께하는 지도대국',
  icons: { icon: '/icon.svg' },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="bg-gray-50 min-h-screen">{children}</body>
    </html>
  )
}
