import type { StatusPresentation } from "./status";

type StatusPanelProps = Readonly<{
  presentation: StatusPresentation;
}>;

export function StatusPanel({ presentation }: StatusPanelProps) {
  const metadata = presentation.kind === "error" ? null : presentation.metadata;

  return (
    <section aria-live="polite" className={`status-panel status-${presentation.kind}`}>
      <div className="status-indicator" aria-hidden="true" />
      <div>
        <p className="eyebrow">平台状态</p>
        <h2>{presentation.title}</h2>
        <p className="status-message">{presentation.message}</p>
        {metadata ? (
          <p className="status-metadata">
            {metadata.name} · {metadata.environment} · v{metadata.version}
          </p>
        ) : null}
      </div>
    </section>
  );
}
