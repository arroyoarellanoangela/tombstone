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

function ValuationCell({ deal }: { deal: Deal }) {
  const estimate = deal.valuation_estimate;
  if (!estimate) {
    return (
      <span className="text-sm" style={{ color: "var(--ink-faint)" }}>
        —
      </span>
    );
  }

  return (
    <div className="claim-cell" tabIndex={0}>
      <div className="flex flex-col gap-1 items-start">
        <span className="text-sm leading-snug">{estimate.value}</span>
        <span className="pill pill-derived">estimate</span>
      </div>
      <div className="claim-tooltip" role="note">
        <p
          className="font-data text-[0.65rem] uppercase tracking-wider mb-1"
          style={{ color: "var(--ink-faint)" }}
        >
          {estimate.kind.replaceAll("_", " ")} · {estimate.confidence} confidence
        </p>
        <p>{estimate.method}</p>
        {estimate.verbatim_quote && <p className="italic mt-2">"{estimate.verbatim_quote}"</p>}
        <a
          href={estimate.source_url}
          target="_blank"
          rel="noreferrer noopener"
          className="block mt-2 underline break-all text-[0.7rem]"
          style={{ color: "var(--accent)" }}
        >
          {estimate.source_url}
        </a>
      </div>
    </div>
  );
}

// null means the Scorer never ran on this record, not "zero confidence" —
// those are different claims, and rendering one as the other would be a
// small, silent instance of exactly the fabrication this system exists to
// avoid. In practice the Scorer always runs, so this is a defensive
// display rule more than an expected state.
function ConfidenceBar({ value }: { value: number | null }) {
  if (value === null) {
    return (
      <span className="font-data text-xs" style={{ color: "var(--ink-faint)" }}>
        — Unscored
      </span>
    );
  }
  const pct = Math.round(value * 100);
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
              Valuation signal
            </th>
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
                  <ValuationCell deal={deal} />
                </td>
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
                    className="action-link whitespace-nowrap"
                  >
                    Evidence
                  </button>
                </td>
              </tr>
              {deal.conflicts.length > 0 && (
                <tr>
                  {/* An empty cell above reads as "no source said this". A
                      rejected claim is a different story, and the one worth
                      telling — so it's stated, not left to be inferred. */}
                  <td
                    colSpan={COLUMNS.length + 3}
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
