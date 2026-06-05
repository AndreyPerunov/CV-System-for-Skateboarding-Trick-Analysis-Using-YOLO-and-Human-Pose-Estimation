"use client";

import { useRef } from "react";

interface Props {
  time:        number;
  duration:    number;
  trickBands?: [number, number][];
  onSeek:      (t: number) => void;
}

export function Scrubber({ time, duration, trickBands = [], onSeek }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const drag = useRef(false);

  function seekFromEvent(e: React.PointerEvent) {
    if (!ref.current) return;
    const r = ref.current.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width;
    onSeek(Math.max(0, Math.min(1, x)) * duration);
  }

  const pct = duration ? (time / duration) * 100 : 0;

  return (
    <div
      ref={ref}
      className="scrub"
      onPointerDown={(e) => { drag.current = true; e.currentTarget.setPointerCapture(e.pointerId); seekFromEvent(e); }}
      onPointerMove={(e) => { if (drag.current) seekFromEvent(e); }}
      onPointerUp={() => { drag.current = false; }}
      style={{ marginTop: 10 }}
    >
      <div className="scrub-track">
        <div className="scrub-buffered" style={{ left: 0, width: "100%" }} />
        {trickBands.map(([a, b], i) => {
          const tA = duration ? (a / duration) * 100 : 0;
          const tB = duration ? (b / duration) * 100 : 0;
          return <div key={i} className="scrub-trick" style={{ left: `${tA}%`, width: `${Math.max(0, tB - tA)}%` }} />;
        })}
        <div className="scrub-fill" style={{ left: 0, width: `${pct}%` }} />
      </div>
      <div className="scrub-thumb" style={{ left: `${pct}%` }} />
    </div>
  );
}
