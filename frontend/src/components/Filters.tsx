import type { ClaimStatus } from "../types";

export interface FilterState {
  acquirer: string;
  minConfidence: number;
  priceStatus: ClaimStatus | "any";
  advisersOnly: boolean;
}

export const EMPTY_FILTERS: FilterState = {
  acquirer: "all",
  minConfidence: 0,
  priceStatus: "any",
  advisersOnly: false,
};

const LABEL_CLASS = "font-data text-[0.65rem] uppercase tracking-wider block mb-1";
const CONTROL_STYLE = {
  background: "var(--paper-raised)",
  borderColor: "var(--rule-strong)",
  color: "var(--ink)",
};

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
    <div className="flex flex-wrap items-end gap-5 py-4">
      <div>
        <label className={LABEL_CLASS} style={{ color: "var(--ink-faint)" }} htmlFor="f-acq">
          Acquirer
        </label>
        <select
          id="f-acq"
          className="border px-2 py-1 text-sm rounded-sm"
          style={CONTROL_STYLE}
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
        <label className={LABEL_CLASS} style={{ color: "var(--ink-faint)" }} htmlFor="f-conf">
          Min confidence · {Math.round(value.minConfidence * 100)}%
        </label>
        <input
          id="f-conf"
          type="range"
          min={0}
          max={100}
          step={5}
          value={value.minConfidence * 100}
          onChange={(e) => onChange({ ...value, minConfidence: Number(e.target.value) / 100 })}
          className="w-36 align-middle"
        />
      </div>

      <div>
        <label className={LABEL_CLASS} style={{ color: "var(--ink-faint)" }} htmlFor="f-price">
          Price
        </label>
        <select
          id="f-price"
          className="border px-2 py-1 text-sm rounded-sm"
          style={CONTROL_STYLE}
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

      <label className="flex items-center gap-2 text-sm pb-1 cursor-pointer">
        <input
          type="checkbox"
          checked={value.advisersOnly}
          onChange={(e) => onChange({ ...value, advisersOnly: e.target.checked })}
        />
        Adviser identified
      </label>

      <button
        type="button"
        className="text-sm underline pb-1"
        style={{ color: "var(--accent)" }}
        onClick={() => onChange(EMPTY_FILTERS)}
      >
        Reset
      </button>
    </div>
  );
}
