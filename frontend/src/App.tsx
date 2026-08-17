import { useEffect, useMemo, useState } from "react";
import { ActivityBars } from "./components/ActivityBars";
import { Competitors } from "./components/Competitors";
import { DealDetail } from "./components/DealDetail";
import { DealsTable } from "./components/DealsTable";
import { EMPTY_FILTERS, Filters, type FilterState } from "./components/Filters";
import { OmissionsTable } from "./components/OmissionsTable";
import { Panel } from "./components/Panel";
import { Timeline } from "./components/Timeline";
import { VerticalDonut } from "./components/VerticalDonut";
import { dealVertical } from "./lib/vertical";
import { dataMode, loadDeals, loadOmissions } from "./services/data";
import type { Deal, Omission } from "./types";

type Tab = "overview" | "deals" | "competitors" | "omissions";

const FILTERED_TABS: readonly Tab[] = ["overview", "deals"];

const HIGH_CONFIDENCE = 0.7;

function acquirerSlugOf(deal: Deal): string {
  return deal.deal_id.split("-")[0];
}

function acquirerLabel(slug: string, deals: Deal[]): string {
  const named = deals.find((d) => acquirerSlugOf(d) === slug && d.acquirer.value);
  return named?.acquirer.value ?? slug;
}

function Summary({ deals }: { deals: Deal[] }) {
  const stats = useMemo(() => {
    const advisers = deals.filter((d) => d.adviser.status === "verified").length;
    const valuationSignals = deals.filter((d) => d.valuation_estimate).length;
    const highConfidence = deals.filter((d) => (d.confidence ?? 0) >= HIGH_CONFIDENCE).length;
    const dates = deals
      .map((d) => d.date_announced.value)
      .filter((v): v is string => Boolean(v))
      .sort();
    const dateSpan =
      dates.length > 0
        ? dates[0] === dates[dates.length - 1]
          ? dates[0]
          : `${dates[0]} to ${dates[dates.length - 1]}`
        : "current snapshot";

    return [
      { label: "Deals identified", value: String(deals.length), caption: dateSpan },
      { label: "Competitors active", value: `${new Set(deals.map(acquirerSlugOf)).size} of 7`, caption: "named in the brief" },
      { label: "Advisers found", value: `${advisers} of ${deals.length}`, caption: "financial adviser only" },
      { label: "Valuation signals", value: `${valuationSignals} of ${deals.length}`, caption: "separate from deal price" },
      { label: "High confidence", value: `${highConfidence} of ${deals.length}`, caption: `${Math.round(HIGH_CONFIDENCE * 100)}% and above` },
    ];
  }, [deals]);

  return (
    <div className="grid gap-x-12 gap-y-8 border-y border-black py-8" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))" }}>
      {stats.map((s) => (
        <div key={s.label}>
          <p className="font-display text-[56px] leading-[62px] font-normal">{s.value}</p>
          <p className="mt-2 text-[14px] leading-6 font-semibold uppercase tracking-[1.12px]">{s.label}</p>
          <p className="mt-1 text-[14px] leading-6" style={{ color: "var(--ink-faint)" }}>
            {s.caption}
          </p>
        </div>
      ))}
    </div>
  );
}

export default function App() {
  const [deals, setDeals] = useState<Deal[]>([]);
  const [omissions, setOmissions] = useState<Omission[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>("overview");
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

  const filteredExceptVertical = useMemo(
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

  const visible = useMemo(
    () =>
      filteredExceptVertical.filter(
        (d) => filters.vertical === "all" || dealVertical(d) === filters.vertical,
      ),
    [filteredExceptVertical, filters.vertical],
  );

  const showSidebar = FILTERED_TABS.includes(tab);

  return (
    <>
      <header className="site-header">
        <div className="page-inner flex h-full items-center justify-between gap-10">
          <button
            type="button"
            onClick={() => setTab("overview")}
            className="text-[20px] leading-8 font-medium"
          >
            Tombstone
          </button>
          <nav className="flex items-center gap-8 text-[20px] leading-6 font-medium uppercase tracking-[0.2px]">
            {(
              [
                ["overview", "Overview"],
                ["deals", "Deals"],
                ["competitors", "Competitors"],
                ["omissions", "Omissions"],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => setTab(key)}
                style={{ color: tab === key ? "var(--accent)" : "var(--ink)" }}
              >
                {label}
              </button>
            ))}
          </nav>
          <p className="text-[14px] leading-6 font-semibold uppercase tracking-[1.12px] shrink-0" style={{ color: "var(--accent)" }}>
            {dataMode === "static-snapshot" ? "Committed snapshot / no live API" : "Reading the live API"}
          </p>
        </div>
      </header>

      <div className={showSidebar ? "page-main page-main--with-sidebar" : "page-main"}>
        {showSidebar && (
          <aside className="app-sidebar">
            <Filters acquirers={acquirers} value={filters} onChange={setFilters} />
          </aside>
        )}

        <main className="flex-1 min-w-0">
          <section className="page-shell dashboard-section">
            <div className="page-inner">
              <div className="content-column">
                <h1 className="font-display text-[32px] leading-[38px] font-normal">
                  Competitor Acquisition Intelligence
                </h1>
                <p className="mt-4 text-[18px] leading-7 font-medium tracking-[0.2px]" style={{ color: "var(--ink-soft)" }}>
                  A source-grounded view of acquisitions announced by Abingdon Software Group's competitors.
                </p>
              </div>
            </div>
          </section>

          {loading ? (
            <section className="page-shell dashboard-section">
              <div className="page-inner">
                <p className="section-copy">Loading...</p>
              </div>
            </section>
          ) : (
            <>
              {tab === "overview" && (
                <>
                  <section className="page-shell dashboard-section pt-0">
                    <div className="page-inner">
                      <Summary deals={deals} />
                    </div>
                  </section>

                  <section className="page-shell dashboard-section">
                    <div className="page-inner">
                      <Panel
                        title="Acquisition timeline"
                        description="Every dated deal in the current filter, plotted on a real day scale."
                      >
                        <Timeline deals={visible} onSelect={setSelectedDeal} />
                      </Panel>
                    </div>
                  </section>

                  <section className="page-shell dashboard-section">
                    <div className="page-inner grid gap-20 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
                      <Panel title="Acquisition activity" description="Deals per acquirer, most active first.">
                        <ActivityBars deals={filteredExceptVertical} />
                      </Panel>
                      <Panel
                        title="What competitors are buying"
                        description="Target vertical mix, derived from verified descriptions."
                      >
                        <VerticalDonut
                          deals={filteredExceptVertical}
                          selected={filters.vertical === "all" ? null : filters.vertical}
                          onSelect={(v) => setFilters({ ...filters, vertical: v ?? "all" })}
                        />
                      </Panel>
                    </div>
                  </section>
                </>
              )}

              {tab === "deals" && (
                <section className="page-shell dashboard-section">
                  <div className="page-inner">
                    <div className="content-column mb-12">
                      <h2 className="section-title">Deals</h2>
                      <p className="section-copy mt-4">
                        Hover any cell for the source quote, or open Evidence for the full provenance.
                      </p>
                    </div>
                    <DealsTable deals={visible} onSelect={setSelectedDeal} />
                  </div>
                </section>
              )}

              {tab === "competitors" && (
                <section className="page-shell dashboard-section">
                  <div className="page-inner">
                    <div className="content-column mb-12">
                      <h2 className="section-title">Competitors</h2>
                      <p className="section-copy mt-4">
                        Seven acquirers from the brief, including those with no current-window deal found.
                      </p>
                    </div>
                    <Competitors
                      deals={deals}
                      onSelect={(slug) => {
                        setFilters({ ...EMPTY_FILTERS, acquirer: slug });
                        setTab("deals");
                      }}
                    />
                  </div>
                </section>
              )}

              {tab === "omissions" && (
                <section className="page-shell dashboard-section">
                  <div className="page-inner">
                    <div className="content-column mb-12">
                      <h2 className="section-title">Omissions</h2>
                      <p className="section-copy mt-4">
                        Sources and candidates deliberately excluded, with the reason shown rather than hidden.
                      </p>
                    </div>
                    <OmissionsTable omissions={omissions} />
                  </div>
                </section>
              )}
            </>
          )}
        </main>
      </div>

      {selectedDeal && <DealDetail deal={selectedDeal} onClose={() => setSelectedDeal(null)} />}
    </>
  );
}
