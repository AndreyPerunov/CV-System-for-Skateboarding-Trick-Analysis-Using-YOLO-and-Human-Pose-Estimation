"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { getStats } from "@/lib/api";

export function Topbar() {
  const pathname = usePathname();
  const [calls, setCalls] = useState<number | null>(null);

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const s = await getStats();
        if (alive) setCalls(s.total_requests);
      } catch {
        if (alive) setCalls(null);
      }
    };
    tick();
    const iv = setInterval(tick, 5000);
    return () => { alive = false; clearInterval(iv); };
  }, [pathname]);

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
      <div className="stats-badge" title="Backend API calls">
        <span className="dot" />
        <span className="num">{calls == null ? "—" : calls.toLocaleString()}</span>
        <span className="muted">API calls</span>
      </div>
    </header>
  );
}
