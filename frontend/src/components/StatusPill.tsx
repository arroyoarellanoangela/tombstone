import type { ClaimStatus } from "../types";

const LABELS: Record<ClaimStatus, string> = {
  verified: "verified",
  explicitly_undisclosed: "undisclosed",
  not_found: "not found",
};

const CLASSES: Record<ClaimStatus, string> = {
  verified: "pill pill-verified",
  explicitly_undisclosed: "pill pill-undisclosed",
  not_found: "pill pill-notfound",
};

export function StatusPill({ status }: { status: ClaimStatus }) {
  return <span className={CLASSES[status]}>{LABELS[status]}</span>;
}
