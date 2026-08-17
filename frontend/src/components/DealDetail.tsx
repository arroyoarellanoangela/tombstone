import { useEffect } from "react";
import { CLAIM_FIELDS, type Claim, type Deal } from "../types";
import { StatusPill } from "./StatusPill";

const FIELD_LABELS: Record<(typeof CLAIM_FIELDS)[number], string> = {
  acquirer: "Acquirer",
  target: "Target",
  date_announced: "Date announced",
  target_description: "What it does",
  geography: "Geography",
  adviser: "M&A adviser",
  purchase_price: "Purchase price",
};

/** One field's full provenance — the same information ClaimCell shows on
 * hover, laid out permanently rather than requiring the viewer to find and
 * hover each cell. This panel is the whole thesis of the system made
 * visible: not "the target is X" but "the target is X, here is the exact
 * sentence that says so, and here is where it came from." */
function FieldEvidence({ label, claim }: { label: string; claim: Claim }) {
  return (
    <div className="py-4" style={{ borderBottom: "1px solid var(--rule)" }}>
      <div className="flex items-baseline justify-between gap-3 mb-1.5">
        <span className="font-data text-[0.65rem] uppercase tracking-wider" style={{ color: "var(--ink-faint)" }}>
          {label}
        </span>
        <StatusPill status={claim.status} />
      </div>

      <p className="text-[0.95rem] leading-snug mb-1.5">
        {claim.value ?? <span style={{ color: "var(--ink-faint)" }}>No public value located.</span>}
      </p>

      {claim.verbatim_quote && (
        <div className="mt-2 pl-3" style={{ borderLeft: "2px solid var(--rule-strong)" }}>
          <p className="italic text-[0.8rem] leading-relaxed" style={{ color: "var(--ink-soft)" }}>
            "{claim.verbatim_quote}"
          </p>
          <div className="flex items-center gap-2 mt-1.5 flex-wrap">
            <span className="font-data text-[0.6rem] uppercase tracking-wider" style={{ color: "var(--ink-faint)" }}>
              {claim.source_language ? `${claim.source_language} · ` : ""}
              {claim.verified ? "re-checked by Verifier" : "unconfirmed"}
            </span>
            {claim.source_url && (
              <a
                href={claim.source_url}
                target="_blank"
                rel="noreferrer noopener"
                className="font-data text-[0.7rem] underline"
                style={{ color: "var(--accent)" }}
              >
                Open source ↗
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function DealDetail({ deal, onClose }: { deal: Deal; onClose: () => void }) {
  // Escape closes the panel — a modal that traps focus without an obvious
  // keyboard exit is a small but real accessibility miss.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const sourceCount = new Set(deal.source_urls).size;

  return (
    <div className="fixed inset-0 z-30 flex justify-end" role="dialog" aria-modal="true">
      <button
        type="button"
        aria-label="Close"
        onClick={onClose}
        className="absolute inset-0"
        style={{ background: "rgb(0 0 0 / 0.35)" }}
      />
      <div
        className="relative h-full w-full max-w-[30rem] overflow-y-auto px-7 py-8"
        style={{ background: "var(--paper-raised)", borderLeft: "1px solid var(--rule-strong)" }}
      >
        <button
          type="button"
          onClick={onClose}
          className="font-data text-[0.7rem] uppercase tracking-wider mb-6"
          style={{ color: "var(--ink-faint)" }}
        >
          ← Close
        </button>

        <p className="font-data text-[0.65rem] uppercase tracking-wider mb-1" style={{ color: "var(--ink-faint)" }}>
          Acquired by {deal.acquirer.value ?? "—"}
        </p>
        <h2 className="font-display text-2xl mb-4">{deal.target.value ?? deal.deal_id}</h2>

        <div className="flex items-center gap-5 mb-6 pb-5" style={{ borderBottom: "1px solid var(--rule-strong)" }}>
          <div>
            <span className="font-data text-[0.6rem] uppercase tracking-wider block" style={{ color: "var(--ink-faint)" }}>
              Confidence
            </span>
            <span className="font-data text-lg">
              {deal.confidence === null ? "Unscored" : `${Math.round(deal.confidence * 100)}%`}
            </span>
          </div>
          <div>
            <span className="font-data text-[0.6rem] uppercase tracking-wider block" style={{ color: "var(--ink-faint)" }}>
              Sources
            </span>
            <span className="font-data text-lg">{sourceCount}</span>
          </div>
          <div>
            <span className="font-data text-[0.6rem] uppercase tracking-wider block" style={{ color: "var(--ink-faint)" }}>
              Verifier
            </span>
            <span className="font-data text-lg" style={{ color: deal.conflicts.length ? "var(--notfound)" : "var(--verified)" }}>
              {deal.conflicts.length ? `${deal.conflicts.length} rejected` : "clean"}
            </span>
          </div>
        </div>

        {deal.conflicts.length > 0 && (
          <div
            className="mb-6 px-3 py-2.5 text-[0.8rem]"
            style={{ background: "var(--notfound-bg)", color: "var(--notfound)", border: "1px solid currentColor" }}
          >
            {deal.conflicts.map((c, i) => (
              <p key={i} className={i > 0 ? "mt-1.5" : ""}>
                {c}
              </p>
            ))}
          </div>
        )}

        {CLAIM_FIELDS.map((field) => (
          <FieldEvidence key={field} label={FIELD_LABELS[field]} claim={deal[field]} />
        ))}
      </div>
    </div>
  );
}
