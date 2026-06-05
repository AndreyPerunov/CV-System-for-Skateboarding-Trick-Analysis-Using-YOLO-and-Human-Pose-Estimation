import type { ThumbColor } from "@/lib/library";

const ACCENT_MAP: Record<ThumbColor, string> = {
  lime:    "oklch(0.86 0.22 128)",
  magenta: "oklch(0.78 0.22 320)",
  cyan:    "oklch(0.84 0.18 220)",
  amber:   "oklch(0.84 0.20 75)",
  red:     "oklch(0.72 0.20 25)",
  violet:  "oklch(0.72 0.18 290)",
};

const ANGLES = [-25, 0, -45, 18, -10, 30];

interface Props {
  color?:   ThumbColor;
  variant?: number;
}

export function ThumbFig({ color = "lime", variant = 0 }: Props) {
  const c = ACCENT_MAP[color] ?? ACCENT_MAP.lime;
  const a = ANGLES[variant % ANGLES.length];
  const patternId = `p${variant}`;
  return (
    <div className="thumb-fig">
      <svg viewBox="0 0 200 112" preserveAspectRatio="xMidYMid slice">
        <defs>
          <pattern id={patternId} width={6} height={6} patternUnits="userSpaceOnUse" patternTransform="rotate(35)">
            <line x1={0} y1={0} x2={0} y2={6} stroke="oklch(1 0 0 / 0.04)" strokeWidth={1} />
          </pattern>
        </defs>
        <rect width={200} height={112} fill={`url(#${patternId})`} />
        <path d={`M10 88 Q 100 ${variant % 2 ? 10 : 24} 190 88`} fill="none" stroke={c} strokeWidth={1.4} strokeDasharray="2 3" opacity={0.7} />
        <g transform={`translate(100 60) rotate(${a})`}>
          <rect x={-38} y={-5} width={76} height={10} rx={5} fill={c} opacity={0.85} />
          <circle cx={-26} cy={8} r={3} fill="oklch(0.2 0 0)" />
          <circle cx={26}  cy={8} r={3} fill="oklch(0.2 0 0)" />
        </g>
        <g fill={c}>
          <circle cx={60}  cy={68} r={2} />
          <circle cx={140} cy={68} r={2} />
          <circle cx={100} cy={40} r={1.6} />
        </g>
      </svg>
    </div>
  );
}
