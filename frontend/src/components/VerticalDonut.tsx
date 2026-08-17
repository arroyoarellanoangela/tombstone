import { useMemo } from "react";
import { dealVertical, type Vertical } from "../lib/vertical";
import type { Deal } from "../types";

const SLICE_COLORS = [
  "#1e3a5f",
  "#8a6d1f",
  "#1f6f54",
  "#8a3b3b",
  "#5c4a8a",
  "#2f6b8a",
  "#8a5c2f",
  "#3f6b3f",
  "#6b3f6b",
  "#3f3f6b",
  "#6b6b3f",
  "#7c807e",
];

function arcPath(cx: number, cy: number, r: number, startAngle: number, endAngle: number): string {
  const start = { x: cx + r * Math.cos(startAngle), y: cy + r * Math.sin(startAngle) };
  const end = { x: cx + r * Math.cos(endAngle), y: cy + r * Math.sin(endAngle) };
  const largeArc = endAngle - startAngle > Math.PI ? 1 : 0;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y}`;
}

/** What kind of software the competition is buying — derived from
 * target_description, never asked of the model (see lib/vertical.ts). A
 * label reading "Other" is the honest outcome for a description too vague
 * to place in the closed taxonomy, not a bug to hide. */
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
  const cx = 60;
  const cy = 60;
  const rOuter = 56;
  const rInner = 32;

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
      <p className="font-data text-[0.65rem] uppercase tracking-wider mb-3" style={{ color: "var(--ink-faint)" }}>
        Target vertical mix
        <span className="normal-case" style={{ color: "var(--ink-faint)" }}> · ◇ derived, not verified</span>
      </p>
      <div className="flex items-start gap-5">
        <svg width="120" height="120" viewBox="0 0 120 120" aria-hidden="true">
          {slices.map((s) => (
            <path
              key={s.vertical}
              d={s.d}
              fill={s.color}
              opacity={selected && selected !== s.vertical ? 0.25 : 1}
              style={{ cursor: "pointer", transition: "opacity 120ms ease" }}
              onClick={() => onSelect(selected === s.vertical ? null : s.vertical)}
            />
          ))}
        </svg>
        <ul className="text-[0.8rem] space-y-1">
          {slices.map((s) => (
            <li key={s.vertical}>
              <button
                type="button"
                onClick={() => onSelect(selected === s.vertical ? null : s.vertical)}
                className="flex items-center gap-2 text-left"
                style={{ opacity: selected && selected !== s.vertical ? 0.4 : 1 }}
              >
                <span
                  className="inline-block rounded-full shrink-0"
                  style={{ width: "0.6rem", height: "0.6rem", background: s.color }}
                />
                <span>{s.vertical}</span>
                <span className="font-data" style={{ color: "var(--ink-faint)" }}>
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
