import { useMemo } from "react";
import { dealVertical, type Vertical } from "../lib/vertical";
import type { Deal } from "../types";

// A real categorical palette, not a greyscale-plus-one-accent set — with 11
// verticals in the data, six mostly-grey tones repeating made adjacent
// slices indistinguishable. Coral leads (it's the brand accent, and the
// most active vertical should read as the "headline" colour), the rest are
// genuinely different hues so every slice is legible at a glance.
const SLICE_COLORS = [
  "#ff5e5e",
  "#2c2c2c",
  "#4a90d9",
  "#e8a33d",
  "#5fa36a",
  "#9b6bce",
  "#d94f8c",
  "#3ab0a2",
  "#c9962c",
  "#7a8ca8",
  "#b85c3e",
  "#8a8a8a",
];

function arcPath(cx: number, cy: number, r: number, startAngle: number, endAngle: number): string {
  const start = { x: cx + r * Math.cos(startAngle), y: cy + r * Math.sin(startAngle) };
  const end = { x: cx + r * Math.cos(endAngle), y: cy + r * Math.sin(endAngle) };
  const largeArc = endAngle - startAngle > Math.PI ? 1 : 0;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y}`;
}

export function VerticalDonut({
  deals,
  selected,
  onSelect,
}: {
  deals: Deal[];
  selected: Vertical | null;
  onSelect: (vertical: Vertical | null) => void;
}) {
  const counts = useMemo(() => {
    const m = new Map<Vertical, number>();
    for (const d of deals) {
      const v = dealVertical(d);
      m.set(v, (m.get(v) ?? 0) + 1);
    }
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  }, [deals]);

  if (deals.length === 0) return null;

  const total = deals.length;
  const size = 220;
  const cx = size / 2;
  const cy = size / 2;
  const rOuter = 105;
  const rInner = 62;

  let angle = -Math.PI / 2;
  const slices = counts.map(([vertical, count], i) => {
    const sweep = (count / total) * Math.PI * 2;
    const start = angle;
    const end = angle + sweep;
    angle = end;
    const outer = arcPath(cx, cy, rOuter, start, end);
    const innerStart = { x: cx + rInner * Math.cos(end), y: cy + rInner * Math.sin(end) };
    const innerEnd = { x: cx + rInner * Math.cos(start), y: cy + rInner * Math.sin(start) };
    const largeArc = end - start > Math.PI ? 1 : 0;
    const d = `${outer} L ${innerStart.x} ${innerStart.y} A ${rInner} ${rInner} 0 ${largeArc} 0 ${innerEnd.x} ${innerEnd.y} Z`;
    return { vertical, count, d, color: SLICE_COLORS[i % SLICE_COLORS.length] };
  });

  return (
    <div>
      <p className="text-[14px] leading-6 font-semibold uppercase tracking-[1.12px] mb-6" style={{ color: "var(--ink-faint)" }}>
        Derived, not verified
      </p>
      <div className="flex items-center gap-12 flex-wrap">
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="shrink-0" role="img" aria-label="Target vertical mix">
          {slices.map((s) => (
            <path
              key={s.vertical}
              d={s.d}
              fill={s.color}
              opacity={selected && selected !== s.vertical ? 0.2 : 1}
              style={{ cursor: "pointer", transition: "opacity 120ms ease" }}
              onClick={() => onSelect(selected === s.vertical ? null : s.vertical)}
            >
              <title>
                {s.vertical}: {s.count} deal{s.count === 1 ? "" : "s"}
              </title>
            </path>
          ))}
          <text
            x={cx}
            y={cy - 4}
            textAnchor="middle"
            style={{ fill: "var(--ink)", fontSize: "56px", fontFamily: "var(--font-display)" }}
          >
            {total}
          </text>
          <text
            x={cx}
            y={cy + 26}
            textAnchor="middle"
            style={{
              fill: "var(--ink-faint)",
              fontSize: "11px",
              fontFamily: "var(--font-sans)",
              fontWeight: 600,
              letterSpacing: "1.12px",
            }}
          >
            DEALS
          </text>
        </svg>

        <ul className="text-[16px] leading-6 flex-1 min-w-[15rem]">
          {slices.map((s) => (
            <li key={s.vertical} style={{ borderBottom: "1px solid var(--rule)" }}>
              <button
                type="button"
                onClick={() => onSelect(selected === s.vertical ? null : s.vertical)}
                className="flex items-center gap-3 text-left w-full py-3"
                style={{ opacity: selected && selected !== s.vertical ? 0.35 : 1 }}
              >
                <span
                  className="inline-block shrink-0"
                  style={{ width: "0.75rem", height: "0.75rem", background: s.color }}
                />
                <span className="flex-1">{s.vertical}</span>
                <span className="tabular-nums" style={{ color: "var(--ink-soft)" }}>
                  {s.count}
                </span>
                <span className="tabular-nums w-10 text-right" style={{ color: "var(--ink-faint)" }}>
                  {Math.round((s.count / total) * 100)}%
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
