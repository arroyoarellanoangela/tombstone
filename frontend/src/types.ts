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
} & Record<ClaimField, Claim>;

export interface Omission {
  url: string;
  reason: string;
  stage: string;
}
