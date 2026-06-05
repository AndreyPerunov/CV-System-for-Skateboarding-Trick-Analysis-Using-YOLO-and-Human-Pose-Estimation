import type { TrickReport } from "@/lib/types";
import { fmtClock } from "@/lib/format";

interface Props {
  trick:    TrickReport;
  stance:   string;
  index?:   number;
  total?:   number;
  active?:  boolean;
  onClick?: () => void;
}

function Metric({ label, value, unit }: { label: string; value: React.ReactNode; unit?: string }) {
  return (
    <div className="metric">
      <span className="lbl">{label}</span>
      <span className="val">{value}{unit && <span className="u">{unit}</span>}</span>
    </div>
  );
}

export function TrickSummaryCard({ trick, stance, index, total, active, onClick }: Props) {
  const rotation = trick.board_yaw_deg == null ? "—" : Math.round(Math.abs(trick.board_yaw_deg));
  const jump     = Math.max(0, Math.round(trick.peak_height_cm));
  const airMs    = Math.round(trick.duration_s * 1000);
  const showIndex = index != null && total != null && total > 1;
  const range    = `${fmtClock(trick.start_time_s)}–${fmtClock(trick.end_time_s)}`;

  const className = [
    "trick-card",
    onClick ? "clickable" : "",
    active ? "active" : "",
  ].filter(Boolean).join(" ");

  return (
    <div
      className={className}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onClick(); } } : undefined}
    >
      <div className="label-row">
        <span>{showIndex ? `Trick ${index} / ${total}` : "Detected trick"}</span>
        <span className="range mono">{range}</span>
      </div>
      <div className="name">{trick.trick_name} <span className="light">· {stance}</span></div>
      <div className="metrics">
        <Metric label="Stance"   value={stance} />
        <Metric label="Rotation" value={rotation} unit="°" />
        <Metric label="Jump"     value={jump} unit="cm" />
        <Metric label="Air time" value={airMs} unit="ms" />
      </div>
    </div>
  );
}
