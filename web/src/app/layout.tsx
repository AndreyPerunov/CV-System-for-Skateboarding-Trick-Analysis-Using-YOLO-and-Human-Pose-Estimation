import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import { Topbar } from "@/components/Topbar";
import "./globals.css";

const plexSans = IBM_Plex_Sans({
  variable: "--font-plex-sans",
  weight: ["400", "500", "600", "700"],
  subsets: ["latin"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  weight: ["400", "500", "600"],
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "PoseSkateTrain",
  description: "Skateboard trick analysis from video — pose, board keypoints, classified tricks.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
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
  );
}
