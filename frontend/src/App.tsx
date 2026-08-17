import { useEffect, useMemo, useState } from "react";
import { Competitors } from "./components/Competitors";
import { DealDetail } from "./components/DealDetail";
import { DealsTable } from "./components/DealsTable";
import { EMPTY_FILTERS, Filters, type FilterState } from "./components/Filters";
import { OmissionsTable } from "./components/OmissionsTable";
import { dataMode, loadDeals, loadOmissions } from "./services/data";
import type { Deal, Omission } from "./types";

type Tab = "deals" | "competitors" | "omissions";

// High-confidence threshold for the KPI strip — matches the scoring rubric's
// own framing (source_tier + corroboration + verifier_pass_rate weigh most
// heavily), not an arbitrary round number picked for the UI.
const HIGH_CONFIDENCE = 0.7;

/**
 * Group by the deal_id's acquirer slug, not the extracted acquirer name:
 * the slug is canonical and always present, whereas acquirer.value is
 * absent whenever extraction failed — grouping on it would split one
 * acquirer into "Volaris Group" and "volaris".
 */
function acquirerSlugOf(deal: Deal): string {
  return deal.deal_id.split("-")[0];
}

/** Prettiest name available for a slug, preferring what Research verified. */
function acquirerLabel(slug: string, deals: Deal[]): string {
  const named = deals.find((d) => acquirerSlugOf(d) === slug && d.acquirer.value);
  return named?.acquirer.value ?? slug;
}

function Summary({ deals }: { deals: Deal[] }) {
  const stats = useMemo(() => {
    const advisers = deals.filter((d) => d.adviser.status === "verified").length;
    const highConfidence = deals.filter((d) => (d.confidence ?? 0) >= HIGH_CONFIDENCE).length;
    return [
      { label: "Deals found", value: String(deals.length) },
      { label: "Active acquirers", value: `${new Set(deals.map(acquirerSlugOf)).size} of 7` },
      { label: "Adviser identified", value: `${advisers} of ${deals.length}` },
      { label: "High confidence", value: `${highConfidence} of ${deals.length}` },
    ];
  }, [deals]);

  return (
    <div
      className="grid gap-px mb-8"
      style={{
        background: "var(--rule)",
        border: "1px solid var(--rule)",
        gridTemplateColumns: "repeat(auto-fit, minmax(9rem, 1fr))",
      }}
    >
      {stats.map((s) => (
        <div key={s.label} className="px-4 py-3" style={{ background: "var(--paper)" }}>
          <span
            className="font-data text-[0.6rem] uppercase tracking-wider block mb-1"
            style={{ color: "var(--ink-faint)" }}
          >
            {s.label}
          </span>
          <span className="font-data text-lg">{s.value}</span>
        </div>
      ))}
    </div>
  );
}

export default function App() {
  const [deals, setDeals] = useState<Deal[]>([]);
  const [omissions, setOmissions] = useState<Omission[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>("deals");
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS);
  const [selectedDeal, setSelectedDeal] = useState<Deal | null>(null);

  useEffect(() => {
    Promise.all([loadDeals(), loadOmissions()]).then(([d, o]) => {
      setDeals(d);
      setOmissions(o);
      setLoading(false);
    });
  }, []);

  const acquirers = useMemo(
    () =>
      [...new Set(deals.map(acquirerSlugOf))]
        .sort()
        .map((slug) => ({ slug, label: acquirerLabel(slug, deals) })),
    [deals],
  );

  const visible = useMemo(
    () =>
      deals.filter((d) => {
        if (filters.acquirer !== "all" && acquirerSlugOf(d) !== filters.acquirer) return false;
        if ((d.confidence ?? 0) < filters.minConfidence) return false;
        if (filters.priceStatus !== "any" && d.purchase_price.status !== filters.priceStatus)
          return false;
        if (filters.advisersOnly && d.adviser.status !== "verified") return false;
        return true;
      }),
    [deals, filters],
  );

  return (
    <div className="max-w-[1200px] mx-auto px-6 py-12">
      <header
        className="pb-5 mb-6 text-center"
        style={{
          borderTop: "3px double var(--ink)",
          borderBottom: "1px solid var(--ink)",
          paddingTop: "1.75rem",
        }}
      >
        <p
          className="font-data text-[0.65rem] uppercase tracking-[0.16em] mb-3"
          style={{ color: "var(--ink-faint)" }}
        >
          Competitor Acquisition Tracker · Private &amp; Confidential
        </p>
        <h1 className="font-display text-4xl mb-2">Tombstone</h1>
        <p className="font-display italic text-lg" style={{ color: "var(--ink-soft)" }}>
          Acquisitions announced by Abingdon Software Group's competitors
        </p>
      </header>

      <p className="font-data text-[0.65rem] mb-6" style={{ color: "var(--ink-faint)" }}>
        {dataMode === "static-snapshot"
          ? "Reading the committed reference snapshot — no live API, no cost."
          : "Reading the live API."}
      </p>

      {loading ? (
        <p className="py-16 text-center text-sm" style={{ color: "var(--ink-faint)" }}>
          Loading…
        </p>
      ) : (
        <>
          <Summary deals={deals} />

          <nav className="flex gap-6 mb-2" style={{ borderBottom: "1px solid var(--rule-strong)" }}>
            {(
              [
                ["deals", `Deals (${deals.length})`],
                ["competitors", "Competitors"],
                ["omissions", `Omissions (${omissions.length})`],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => setTab(key)}
                className="font-data text-[0.7rem] uppercase tracking-wider pb-2 -mb-px"
                style={{
                  color: tab === key ? "var(--accent)" : "var(--ink-faint)",
                  borderBottom:
                    tab === key ? "2px solid var(--accent)" : "2px solid transparent",
                }}
              >
                {label}
              </button>
            ))}
          </nav>

          {tab === "deals" && (
            <>
              <Filters acquirers={acquirers} value={filters} onChange={setFilters} />
              <DealsTable deals={visible} onSelect={setSelectedDeal} />
              <p className="font-data text-[0.65rem] mt-4" style={{ color: "var(--ink-faint)" }}>
                Hover any cell for the source quote inline, or open Evidence for the full picture.
                An empty cell means no source supported that field — never a guess.
              </p>
            </>
          )}

          {tab === "competitors" && (
            <Competitors
              deals={deals}
              onSelect={(slug) => {
                setFilters({ ...EMPTY_FILTERS, acquirer: slug });
                setTab("deals");
              }}
            />
          )}

          {tab === "omissions" && (
            <>
              <p className="text-sm py-4 max-w-[62ch]" style={{ color: "var(--ink-soft)" }}>
                Sources the pipeline deliberately excluded, and why. Blocked domains (LinkedIn,
                paywalled M&amp;A databases) are rejected at the network layer before any request
                is made; candidates outside the tracking window or outside the acquisition
                definition are dropped by the Normalizer.
              </p>
              <OmissionsTable omissions={omissions} />
            </>
          )}
        </>
      )}

      {selectedDeal && <DealDetail deal={selectedDeal} onClose={() => setSelectedDeal(null)} />}
    </div>
  );
}
