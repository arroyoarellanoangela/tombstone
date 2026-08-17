// Mirrors src/domain/models.py — the backend's Pydantic models are the
// source of truth; keep these in sync with them, not the other way around.

export type ClaimStatus = "verified" | "explicitly_undisclosed" | "not_found";

export interface Claim {
  field: string;
  status: ClaimStatus;
  value: string | null;
  source_url: string | null;
  verbatim_quote: string | null;
  source_language: string | null;
  extracted_at: string;
  verified: boolean;
}

export interface ValuationEstimate {
  value: string;
  kind: "deal_value_range" | "estimated_revenue" | "implied_valuation_range" | string;
  method: string;
  source_url: string;
  verbatim_quote: string | null;
  confidence: "low" | "medium" | "high" | string;
}

export const CLAIM_FIELDS = [
  "acquirer",
  "target",
  "date_announced",
  "target_description",
  "geography",
  "adviser",
  "purchase_price",
] as const;

export type ClaimField = (typeof CLAIM_FIELDS)[number];

export type Deal = {
  deal_id: string;
  confidence: number | null;
  source_urls: string[];
  valuation_estimate: ValuationEstimate | null;
  // Claims the Verifier rejected, and why. Surfaced in the UI rather than
  // hidden: a field that reads empty because a quote failed re-checking is
  // a different story from one no source ever mentioned.
  conflicts: string[];
} & Record<ClaimField, Claim>;

export interface Omission {
  url: string;
  reason: string;
  stage: string;
}
