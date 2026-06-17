import type { Metadata } from "next"
import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google"
import { Topbar } from "@/components/Topbar"
import "./globals.css"

const plexSans = IBM_Plex_Sans({
  variable: "--font-plex-sans",
  weight: ["400", "500", "600", "700"],
  subsets: ["latin"]
})

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  weight: ["400", "500", "600"],
  subsets: ["latin"]
})

const SITE_URL = "https://cv-sk8.andreyperunov.com"
const SITE_TITLE = "PoseSkateTrain"
const SITE_DESCRIPTION = "Skateboard trick analysis from video — pose, board keypoints, classified tricks."

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: SITE_TITLE,
  description: SITE_DESCRIPTION,
  openGraph: {
    type: "website",
    url: SITE_URL,
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
    siteName: SITE_TITLE,
    images: [
      {
        url: "/image-for-opengraph.png",
        width: 1200,
        height: 630,
        alt: "PoseSkateTrain — skateboard trick analysis"
      }
    ]
  },
  twitter: {
    card: "summary_large_image",
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
    images: ["/image-for-opengraph.png"]
  }
}

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" data-theme="light" className={`${plexSans.variable} ${plexMono.variable}`}>
      <body>
        <div className="app">
          <Topbar />
          <main style={{ minHeight: 0, overflow: "hidden" }}>{children}</main>
        </div>
      </body>
    </html>
  )
}
