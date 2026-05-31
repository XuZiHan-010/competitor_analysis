interface PositioningCardProps {
  xAxis: string;
  yAxis: string;
  points: { id: string; x: number; y: number; label: string }[];
}

export function PositioningCard({ xAxis, yAxis, points }: PositioningCardProps) {
  return (
    <aside aria-label="竞品定位图" className="rounded-md border border-border/60 bg-card/60 p-4">
      <p
        className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground mb-3"
        style={{ fontFamily: "var(--font-mono)" }}
      >
        定位图
      </p>
      <div className="relative w-full aspect-square border border-border/60 bg-background/50">
        <span aria-hidden="true" className="absolute left-0 right-0 top-1/2 h-px bg-border/60" />
        <span aria-hidden="true" className="absolute top-0 bottom-0 left-1/2 w-px bg-border/60" />
        {points.map((p) => (
          <span
            key={p.id}
            className="absolute -translate-x-1/2 -translate-y-1/2 flex flex-col items-center"
            style={{ left: `${p.x}%`, top: `${100 - p.y}%` }}
          >
            <span className="block h-2 w-2 rounded-full bg-[var(--color-accent-warm)]" />
            <span className="text-[10.5px] mt-1 text-foreground/90 whitespace-nowrap">
              {p.label}
            </span>
          </span>
        ))}
      </div>
      <p className="text-[10.5px] text-muted-foreground mt-2 leading-snug">
        x · {xAxis}
        <br />
        y · {yAxis}
      </p>
    </aside>
  );
}
