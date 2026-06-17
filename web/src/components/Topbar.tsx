"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function Topbar() {
  const pathname = usePathname();
  const onViewer = pathname?.startsWith("/viewer");

  return (
    <header className="topbar">
      <Link href="/" className="brand">
        <span className="brand-mark" aria-hidden="true" />
        <span className="brand-name">PoseSkateTrain</span>
      </Link>
      <nav className="crumbs">
        <span className="sep">/</span>
        {!onViewer && <span className="crumb-current">Dashboard</span>}
        {onViewer && (
          <>
            <Link href="/" style={{ cursor: "pointer" }}>Analyses</Link>
            <span className="sep">/</span>
            <span className="crumb-current mono" style={{ fontSize: 12 }}>analysis</span>
          </>
        )}
      </nav>
      <div className="topbar-spacer" />
      <div className="stats-badge is-off" title="Backend API is disabled in the demo build">
        <span className="dot" />
        <span className="num">off</span>
        <span className="muted">API calls</span>
      </div>
    </header>
  );
}
