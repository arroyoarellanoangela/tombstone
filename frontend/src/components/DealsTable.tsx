import { Fragment } from "react";
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

export function DealsTable({
  deals,
  onSelect,
}: {
  deals: Deal[];
  onSelect: (deal: Deal) => void;
}) {
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
            <th
              className="font-data text-[0.65rem] uppercase tracking-wider font-medium text-left px-3 py-2 align-bottom"
              style={{
                color: "var(--ink-faint)",
                borderBottom: "1px solid var(--rule-strong)",
              }}
            >
              <span className="sr-only">Evidence</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {deals.map((deal) => (
            <Fragment key={deal.deal_id}>
              <tr>
                {COLUMNS.map((col) => (
                  <td
                    key={col.key}
                    className="px-3 py-3 align-top"
                    style={{
                      borderBottom: deal.conflicts.length
                        ? "none"
                        : "1px solid var(--rule)",
                    }}
                  >
                    <ClaimCell claim={deal[col.key]} />
                  </td>
                ))}
                <td
                  className="px-3 py-3 align-top"
                  style={{
                    borderBottom: deal.conflicts.length
                      ? "none"
                      : "1px solid var(--rule)",
                  }}
                >
                  <ConfidenceBar value={deal.confidence} />
                </td>
                <td
                  className="px-3 py-3 align-top"
                  style={{
                    borderBottom: deal.conflicts.length
                      ? "none"
                      : "1px solid var(--rule)",
                  }}
                >
                  <button
                    type="button"
                    onClick={() => onSelect(deal)}
                    className="font-data text-[0.7rem] underline whitespace-nowrap"
                    style={{ color: "var(--accent)" }}
                  >
                    Evidence →
                  </button>
                </td>
              </tr>
              {deal.conflicts.length > 0 && (
                <tr>
                  {/* An empty cell above reads as "no source said this". A
                      rejected claim is a different story, and the one worth
                      telling — so it's stated, not left to be inferred. */}
                  <td
                    colSpan={COLUMNS.length + 2}
                    className="px-3 pb-3 align-top"
                    style={{ borderBottom: "1px solid var(--rule)" }}
                  >
                    <details className="text-xs">
                      <summary
                        className="cursor-pointer font-data text-[0.65rem] uppercase tracking-wider"
                        style={{ color: "var(--notfound)" }}
                      >
                        {deal.conflicts.length} claim
                        {deal.conflicts.length === 1 ? "" : "s"} rejected by the
                        Verifier
                      </summary>
                      <ul
                        className="mt-2 space-y-1 pl-4 list-disc"
                        style={{ color: "var(--ink-faint)" }}
                      >
                        {deal.conflicts.map((conflict, i) => (
                          <li key={i}>{conflict}</li>
                        ))}
                      </ul>
                    </details>
                  </td>
                </tr>
              )}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}
