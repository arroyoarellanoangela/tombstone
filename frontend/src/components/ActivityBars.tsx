import { useMemo } from "react";
import { colorForAcquirer } from "../lib/vertical";
import type { Deal } from "../types";

function acquirerSlugOf(deal: Deal): string {
  return deal.deal_id.split("-")[0];
}

/** Deal count per acquirer — the counterpart to the vertical donut, placed
 * beside it so the two answer adjacent questions at a glance: who is
 * active, and what are they buying. Two comparatives side by side, not
 * stacked, is the F-pattern reading order for a dashboard's second layer
 * (KPIs first, then the main comparatives). */
export function ActivityBars({ deals }: { deals: Deal[] }) {
  const rows = useMemo(() => {
    const counts = new Map<string, { slug: string; name: string; count: number }>();
    for (const d of deals) {
      const slug = acquirerSlugOf(d);
      const existing = counts.get(slug);
      const name = d.acquirer.value ?? existing?.name ?? slug;
      counts.set(slug, { slug, name, count: (existing?.count ?? 0) + 1 });
    }
    return [...counts.values()].sort((a, b) => b.count - a.count);
  }, [deals]);

  const slugs = useMemo(() => rows.map((r) => r.slug), [rows]);

  if (rows.length === 0) return null;

  const maxCount = Math.max(...rows.map((r) => r.count));

  return (
    <div className="space-y-8">
      {rows.map((r) => (
        <div key={r.slug}>
          <div className="mb-2 flex items-baseline justify-between gap-6">
            <span className="text-[20px] leading-8 truncate" title={r.name}>
              {r.name}
            </span>
            <span className="font-display text-[32px] leading-[48px]">{r.count}</span>
          </div>
          <div className="h-[10px]" style={{ background: "var(--rule)" }}>
            <div
              className="h-full"
              style={{
                width: `${(r.count / maxCount) * 100}%`,
                background: colorForAcquirer(r.slug, slugs),
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
