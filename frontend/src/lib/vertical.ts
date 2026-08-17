import type { Deal } from "../types";

/**
 * A closed taxonomy, keyword-matched against the already-Verified
 * target_description — never asked of an LLM, for the same reason the
 * acquisition-scope check (src/domain/deal_definition.py) is keyword-based
 * code and not a prompt: a category with one correct, checkable answer
 * doesn't belong to a model's judgment. This is derived intelligence
 * layered on top of verified facts, not a Claim — it never gets a
 * VERIFIED pill, only a DERIVED one, and there is no "vertical" field on
 * the backend DealRecord at all.
 */
export const VERTICALS = [
  "Government / Public Sector",
  "Healthcare",
  "Media & Broadcast",
  "Industrial / Manufacturing",
  "Logistics",
  "Retail",
  "Cybersecurity",
  "Hospitality / Leisure",
  "Education",
  "Sports / Associations",
  "Financial Services",
  "Other",
] as const;

export type Vertical = (typeof VERTICALS)[number];

const RULES: [Vertical, RegExp][] = [
  ["Government / Public Sector", /public (sector|administration)|local authorit|local government|urban planning|municipalit/i],
  ["Healthcare", /health|medical|ehealth|patient|clinic/i],
  ["Cybersecurity", /cybersecurity|cyber[- ]?security|security awareness|security monitoring/i],
  ["Media & Broadcast", /broadcast|newsroom|playout|tv audience|advertising analytics|media (production|technology)/i],
  ["Sports / Associations", /sports? (club|federation|management)|membership.management/i],
  ["Education", /k-12|school district|assessment management|curriculum/i],
  ["Hospitality / Leisure", /venue management|entertainment center|karting|trampoline|escape room|hospitality/i],
  ["Logistics", /logistics|fleet management|freight|supply chain|transport/i],
  ["Retail", /retail (execution|management)|point.of.sale|specialty retailer/i],
  ["Financial Services", /financial services|banking|insurance|wealth management|asset management/i],
  ["Industrial / Manufacturing", /manufactur|field service|compliance software|oee|shop.floor|estimat(ion|ors)|takeoff/i],
];

/** Returns null rather than guessing when the description doesn't clearly
 * match — "Other" is a visible, honest bucket, not a forced fit. */
export function classifyVertical(description: string | null): Vertical {
  if (!description) return "Other";
  for (const [vertical, pattern] of RULES) {
    if (pattern.test(description)) return vertical;
  }
  return "Other";
}

export function dealVertical(deal: Deal): Vertical {
  return classifyVertical(deal.target_description.value);
}

// Stable colour per acquirer slug, reused across the timeline and the
// competitor activity bars so a colour always means the same acquirer.
const PALETTE = [
  "#ff5e5e",
  "#2c2c2c",
  "#4a90d9",
  "#e8a33d",
  "#5fa36a",
  "#9b6bce",
  "#3ab0a2",
];

export function colorForAcquirer(slug: string, allSlugs: string[]): string {
  const idx = allSlugs.indexOf(slug);
  return PALETTE[idx % PALETTE.length];
}
