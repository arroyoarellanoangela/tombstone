import type { ClaimField, Deal } from "../types";
import { ClaimCell } from "./ClaimCell";

const COLUMNS: { key: ClaimField; label: string }[] = [
  { key: "acquirer", label: "Acquirer" },
  { key: "target", label: "Target" },
  { key: "date_announced", label: "Announced" },
  { key: "target_description", label: "What the target does" },
  { key: "geography", label: "Geography" },
  { key: "adviser", label: "M&A adviser" },
  { key: "purchase_price", label: "Price" },
];

function ConfidenceBar({ value }: { value: number | null }) {
  const pct = Math.round((value ?? 0) * 100);
  return (
    <div className="flex items-center gap-2 min-w-[5.5rem]">
      <div
        className="h-1.5 w-12 rounded-sm overflow-hidden"
        style={{ background: "var(--rule)" }}
        aria-hidden="true"
      >
        <div
          className="h-full"
          style={{ width: `${pct}%`, background: "var(--accent)" }}
        />
      </div>
      <span className="font-data text-xs">{pct}%</span>
    </div>
  );
}

export function DealsTable({ deals }: { deals: Deal[] }) {
  if (deals.length === 0) {
    return (
      <p className="py-12 text-center text-sm" style={{ color: "var(--ink-faint)" }}>
        No deals match these filters.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                className="font-data text-[0.65rem] uppercase tracking-wider font-medium text-left px-3 py-2 align-bottom"
                style={{
                  color: "var(--ink-faint)",
                  borderBottom: "1px solid var(--rule-strong)",
                }}
              >
                {col.label}
              </th>
            ))}
            <th
              className="font-data text-[0.65rem] uppercase tracking-wider font-medium text-left px-3 py-2 align-bottom"
              style={{
                color: "var(--ink-faint)",
                borderBottom: "1px solid var(--rule-strong)",
              }}
            >
              Confidence
            </th>
          </tr>
        </thead>
        <tbody>
          {deals.map((deal) => (
            <tr key={deal.deal_id}>
              {COLUMNS.map((col) => (
                <td
                  key={col.key}
                  className="px-3 py-3 align-top"
                  style={{ borderBottom: "1px solid var(--rule)" }}
                >
                  <ClaimCell claim={deal[col.key]} />
                </td>
              ))}
              <td
                className="px-3 py-3 align-top"
                style={{ borderBottom: "1px solid var(--rule)" }}
              >
                <ConfidenceBar value={deal.confidence} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
