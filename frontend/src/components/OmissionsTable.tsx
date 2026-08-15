import type { Omission } from "../types";

/**
 * The brief says "if in doubt, leave it out and say so". This tab is the
 * "say so" — every source the pipeline deliberately excluded, with the
 * reason, rendered as data rather than buried in a README.
 */
export function OmissionsTable({ omissions }: { omissions: Omission[] }) {
  if (omissions.length === 0) {
    return (
      <p className="py-12 text-center text-sm" style={{ color: "var(--ink-faint)" }}>
        Nothing was excluded in this run.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            {["Source", "Stage", "Reason"].map((label) => (
              <th
                key={label}
                className="font-data text-[0.65rem] uppercase tracking-wider font-medium text-left px-3 py-2"
                style={{
                  color: "var(--ink-faint)",
                  borderBottom: "1px solid var(--rule-strong)",
                }}
              >
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {omissions.map((o, i) => (
            <tr key={`${o.url}-${i}`}>
              <td className="px-3 py-2.5 align-top" style={{ borderBottom: "1px solid var(--rule)" }}>
                <a
                  href={o.url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="underline break-all text-xs"
                  style={{ color: "var(--accent)" }}
                >
                  {o.url}
                </a>
              </td>
              <td className="px-3 py-2.5 align-top" style={{ borderBottom: "1px solid var(--rule)" }}>
                <span className="font-data text-xs">{o.stage}</span>
              </td>
              <td
                className="px-3 py-2.5 align-top"
                style={{ borderBottom: "1px solid var(--rule)", color: "var(--ink-soft)" }}
              >
                {o.reason}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
