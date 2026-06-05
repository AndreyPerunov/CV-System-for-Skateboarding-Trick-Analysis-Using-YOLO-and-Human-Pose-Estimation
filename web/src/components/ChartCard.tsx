interface Legend {
  name: string
  color: string
}

interface Props {
  title: string
  yLabel: string
  legend: Legend[]
  readout?: [string, string][]
  children: React.ReactNode
}

export function ChartCard({ title, yLabel, legend, readout, children }: Props) {
  return (
    <div className="chart-card">
      <div className="flex w-full justify-between items-center gap-2">
        <div className="ch-head flex-1">
          <span className="ch-title">{title}</span>
          <span className="ch-y">{yLabel}</span>
          <span className="ch-legend">
            {legend.map((l, i) => (
              <span key={i} className="lg" style={{ "--c": l.color } as React.CSSProperties}>
                {l.name}
              </span>
            ))}
          </span>
        </div>
        {readout && readout.length > 0 && (
          <div className="ch-readout">
            {readout.map(([k, v], i) => (
              <span key={i}>
                <span style={{ color: "var(--muted-2)" }}>{k}</span>&nbsp;{v}
              </span>
            ))}
          </div>
        )}
      </div>
      {children}
    </div>
  )
}
