import { VERTICALS, type Vertical } from "../lib/vertical";
import type { ClaimStatus } from "../types";

export interface FilterState {
  acquirer: string;
  vertical: Vertical | "all";
  minConfidence: number;
  priceStatus: ClaimStatus | "any";
  advisersOnly: boolean;
}

export const EMPTY_FILTERS: FilterState = {
  acquirer: "all",
  vertical: "all",
  minConfidence: 0,
  priceStatus: "any",
  advisersOnly: false,
};

const LABEL_CLASS = "block text-[11px] leading-[18px] font-semibold uppercase tracking-[0.88px] mb-2";
const CONTROL_CLASS = "w-full border-0 border-b border-black bg-transparent px-0 py-2 text-[14px] leading-6";

/** Stacked single-column — this renders inside a 260px fixed sidebar, not a
 * horizontal toolbar, so every control gets the full available width
 * rather than being squeezed into a multi-column grid that only works at
 * page width. */
export function Filters({
  acquirers,
  value,
  onChange,
}: {
  acquirers: { slug: string; label: string }[];
  value: FilterState;
  onChange: (next: FilterState) => void;
}) {
  return (
    <div className="flex flex-col gap-7">
      <p className={LABEL_CLASS} style={{ color: "var(--ink)" }}>
        Filters
      </p>

      <div>
        <label className={LABEL_CLASS} htmlFor="f-acq" style={{ color: "var(--ink-faint)" }}>
          Acquirer
        </label>
        <select
          id="f-acq"
          className={CONTROL_CLASS}
          value={value.acquirer}
          onChange={(e) => onChange({ ...value, acquirer: e.target.value })}
        >
          <option value="all">All</option>
          {acquirers.map((a) => (
            <option key={a.slug} value={a.slug}>
              {a.label}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className={LABEL_CLASS} htmlFor="f-vertical" style={{ color: "var(--ink-faint)" }}>
          Target vertical
        </label>
        <select
          id="f-vertical"
          className={CONTROL_CLASS}
          value={value.vertical}
          onChange={(e) => onChange({ ...value, vertical: e.target.value as FilterState["vertical"] })}
        >
          <option value="all">All</option>
          {VERTICALS.map((v) => (
            <option key={v} value={v}>
              {v}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className={LABEL_CLASS} htmlFor="f-price" style={{ color: "var(--ink-faint)" }}>
          Price
        </label>
        <select
          id="f-price"
          className={CONTROL_CLASS}
          value={value.priceStatus}
          onChange={(e) =>
            onChange({ ...value, priceStatus: e.target.value as FilterState["priceStatus"] })
          }
        >
          <option value="any">Any</option>
          <option value="verified">Disclosed</option>
          <option value="explicitly_undisclosed">Explicitly undisclosed</option>
          <option value="not_found">Not found</option>
        </select>
      </div>

      <div>
        <label className={LABEL_CLASS} htmlFor="f-conf" style={{ color: "var(--ink-faint)" }}>
          Min confidence
        </label>
        <select
          id="f-conf"
          className={CONTROL_CLASS}
          value={value.minConfidence}
          onChange={(e) => onChange({ ...value, minConfidence: Number(e.target.value) })}
        >
          <option value={0}>Any</option>
          <option value={0.5}>50% and above</option>
          <option value={0.7}>70% and above</option>
          <option value={0.9}>90% and above</option>
        </select>
      </div>

      <label className="flex items-center gap-3 text-[13px] leading-6 font-semibold uppercase tracking-[1px] cursor-pointer">
        <input
          type="checkbox"
          checked={value.advisersOnly}
          onChange={(e) => onChange({ ...value, advisersOnly: e.target.checked })}
          className="accent-[var(--accent)]"
        />
        Adviser identified
      </label>

      <button type="button" className="action-link" onClick={() => onChange(EMPTY_FILTERS)}>
        Reset filters
      </button>
    </div>
  );
}
