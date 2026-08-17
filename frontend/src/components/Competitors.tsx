import type { Deal } from "../types";

// Mirrors sources/profiles/*.yaml — the seven acquirers the client named.
// Static, like CLAIM_FIELDS in types.ts: this is reference data, not
// something the frontend derives, so an acquirer with zero deals (Snowball,
// BSG) still shows up rather than silently vanishing from the list.
const ACQUIRERS = [
  { slug: "volaris", name: "Volaris Group" },
  { slug: "valsoft", name: "Valsoft" },
  { slug: "everfield", name: "Everfield" },
  { slug: "banyan", name: "Banyan Software" },
  { slug: "tss_topicus", name: "TSS / Topicus" },
  { slug: "snowball", name: "Snowball Software Group" },
  { slug: "bsg", name: "Business Software Group" },
];

function acquirerSlugOf(deal: Deal): string {
  return deal.deal_id.split("-")[0];
}

export function Competitors({
  deals,
  onSelect,
}: {
  deals: Deal[];
  onSelect: (slug: string) => void;
}) {
  const rows = ACQUIRERS.map((a) => {
    const theirDeals = deals.filter((d) => acquirerSlugOf(d) === a.slug);
    const lastDate = theirDeals
      .map((d) => d.date_announced.value)
      .filter((v): v is string => Boolean(v))
      .sort()
      .at(-1);
    return { ...a, count: theirDeals.length, lastDate };
  }).sort((a, b) => b.count - a.count);

  const maxCount = Math.max(1, ...rows.map((r) => r.count));

  return (
    <div className="max-w-[42rem]">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            {["Acquirer", "Activity", "Deals", "Last deal", "Status"].map((h) => (
              <th
                key={h}
                className="font-data text-[0.65rem] uppercase tracking-wider font-medium text-left px-3 py-2"
                style={{ color: "var(--ink-faint)", borderBottom: "1px solid var(--rule-strong)" }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.slug}>
              <td className="px-3 py-3" style={{ borderBottom: "1px solid var(--rule)" }}>
                {r.count > 0 ? (
                  <button
                    type="button"
                    onClick={() => onSelect(r.slug)}
                    className="underline text-left"
                    style={{ color: "var(--accent)" }}
                  >
                    {r.name}
                  </button>
                ) : (
                  r.name
                )}
              </td>
              <td className="px-3 py-3 w-32" style={{ borderBottom: "1px solid var(--rule)" }}>
                <div className="h-1.5 rounded-sm overflow-hidden" style={{ background: "var(--rule)" }}>
                  <div
                    className="h-full"
                    style={{ width: `${(r.count / maxCount) * 100}%`, background: "var(--accent)" }}
                  />
                </div>
              </td>
              <td className="px-3 py-3 font-data" style={{ borderBottom: "1px solid var(--rule)" }}>
                {r.count}
              </td>
              <td className="px-3 py-3 font-data text-[0.85rem]" style={{ borderBottom: "1px solid var(--rule)", color: "var(--ink-soft)" }}>
                {r.lastDate ?? "—"}
              </td>
              <td className="px-3 py-3" style={{ borderBottom: "1px solid var(--rule)" }}>
                <span
                  className="font-data text-[0.7rem]"
                  style={{ color: r.count > 0 ? "var(--verified)" : "var(--ink-faint)" }}
                >
                  {r.count > 0 ? "● Active" : "○ No deals found"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
