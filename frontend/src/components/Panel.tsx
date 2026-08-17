import type { ReactNode } from "react";

export function Panel({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <section>
      <div className="content-column mb-10">
        <h2 className="section-title">{title}</h2>
        {description && <p className="section-copy mt-4">{description}</p>}
      </div>
      <div className="border-t border-black pt-8">{children}</div>
    </section>
  );
}
