import type { Claim } from "../types";
import { StatusPill } from "./StatusPill";

/**
 * A field is never rendered as a bare value — the status pill and the
 * source quote travel with it, because that pairing is the whole point of
 * the system. Hovering (or focusing) a cell shows the verbatim quote the
 * Verifier matched, plus a link to the page it came from.
 */
export function ClaimCell({ claim }: { claim: Claim }) {
  const hasEvidence = Boolean(claim.verbatim_quote);

  return (
    <div className="claim-cell" tabIndex={hasEvidence ? 0 : -1}>
      <div className="flex flex-col gap-1 items-start">
        {claim.value ? (
          <span className="text-sm leading-snug">{claim.value}</span>
        ) : (
          <span className="text-sm" style={{ color: "var(--ink-faint)" }}>
            —
          </span>
        )}
        <StatusPill status={claim.status} />
      </div>

      {hasEvidence && (
        <div className="claim-tooltip" role="note">
          <p
            className="font-data text-[0.65rem] uppercase tracking-wider mb-1"
            style={{ color: "var(--ink-faint)" }}
          >
            Source quote{claim.source_language ? ` · ${claim.source_language}` : ""}
            {claim.verified ? " · re-checked" : " · unconfirmed"}
          </p>
          <p className="italic">"{claim.verbatim_quote}"</p>
          {claim.source_url && (
            <a
              href={claim.source_url}
              target="_blank"
              rel="noreferrer noopener"
              className="block mt-2 underline break-all text-[0.7rem]"
              style={{ color: "var(--accent)" }}
            >
              {claim.source_url}
            </a>
          )}
        </div>
      )}
    </div>
  );
}
