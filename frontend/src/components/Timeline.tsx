import { useMemo, useState } from "react";
import type { Deal } from "../types";

/** One dot per dated deal, positioned on a real day-scale axis (not bucketed
 * into months) so a burst of activity in a two-week window — the thing
 * worth noticing — is visible as a cluster, not smoothed away. Undated
 * deals (date_announced not_found) are omitted: plotting them at a guessed
 * position would be exactly the kind of invented certainty this system
 * exists to avoid. */
export function Timeline({
  deals,
  onSelect,
}: {
  deals: Deal[];
  onSelect: (deal: Deal) => void;
}) {
  const [hovered, setHovered] = useState<string | null>(null);

  const dated = useMemo(
    () =>
      deals
        .filter((d) => d.date_announced.value)
        .map((d) => ({ deal: d, date: new Date(d.date_announced.value as string) }))
        .filter((d) => !Number.isNaN(d.date.getTime()))
        .sort((a, b) => a.date.getTime() - b.date.getTime()),
    [deals],
  );

  if (dated.length === 0) {
    return null;
  }

  const minTime = dated[0].date.getTime();
  const maxTime = dated[dated.length - 1].date.getTime();
  const span = Math.max(1, maxTime - minTime);

  // Stack same-day deals vertically so they don't overlap into one dot.
  const dayCounts = new Map<string, number>();
  const positioned = dated.map(({ deal, date }) => {
    const key = date.toISOString().slice(0, 10);
    const row = dayCounts.get(key) ?? 0;
    dayCounts.set(key, row + 1);
    return { deal, date, xPct: ((date.getTime() - minTime) / span) * 100, row };
  });

  const months = useMemo(() => {
    const set = new Set<string>();
    dated.forEach(({ date }) => set.add(`${date.getFullYear()}-${date.getMonth()}`));
    return [...set].map((key) => {
      const [y, m] = key.split("-").map(Number);
      const d = new Date(y, m, 1);
      const xPct = ((d.getTime() - minTime) / span) * 100;
      return { label: d.toLocaleDateString("en-US", { month: "short" }), xPct: Math.max(0, xPct) };
    });
  }, [dated, minTime, span]);

  return (
    <div>
      <div className="relative" style={{ height: "5.5rem" }}>
        <div className="absolute left-0 right-0" style={{ top: "2.75rem", height: "1px", background: "var(--rule-strong)" }} />

        {months.map((m) => (
          <div key={m.label + m.xPct} className="absolute" style={{ left: `${m.xPct}%`, top: 0 }}>
            <div style={{ width: "1px", height: "3rem", background: "var(--rule)" }} />
            <span className="font-data text-[0.6rem]" style={{ color: "var(--ink-faint)" }}>
              {m.label}
            </span>
          </div>
        ))}

        {positioned.map(({ deal, date, xPct, row }) => {
          const color = "var(--accent)";
          const isHovered = hovered === deal.deal_id;
          return (
            <button
              key={deal.deal_id}
              type="button"
              onClick={() => onSelect(deal)}
              onMouseEnter={() => setHovered(deal.deal_id)}
              onMouseLeave={() => setHovered(null)}
              className="absolute"
              style={{
                left: `${xPct}%`,
                top: `${2.75 - row * 0.55}rem`,
                width: isHovered ? "0.6rem" : "0.5rem",
                height: isHovered ? "0.6rem" : "0.5rem",
                background: color,
                transform: "translate(-50%, -50%)",
                border: isHovered ? "2px solid var(--black)" : "0",
                zIndex: isHovered ? 10 : 1,
              }}
              aria-label={`${deal.acquirer.value ?? "Unknown acquirer"} acquires ${deal.target.value ?? deal.deal_id}, ${date.toDateString()}`}
            >
              {isHovered && (
                <div
                  className="absolute px-2.5 py-2 text-[0.75rem] whitespace-nowrap"
                  style={{
                    bottom: "1rem",
                    left: "50%",
                    transform: "translateX(-50%)",
                    background: "var(--paper-raised)",
                    border: "1px solid var(--rule-strong)",
                    color: "var(--ink)",
                  }}
                >
                  <strong>{deal.acquirer.value ?? "—"}</strong> → {deal.target.value ?? "—"}
                  <br />
                  <span className="font-data text-[0.65rem]" style={{ color: "var(--ink-faint)" }}>
                    {date.toDateString()}
                  </span>
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
