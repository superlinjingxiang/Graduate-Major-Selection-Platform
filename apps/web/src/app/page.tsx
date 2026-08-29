import { designTokens } from "@gradmatch/design-tokens";

const stack = {
  next: "Next.js App Router",
  packages: "Strict TypeScript workspaces",
  python: "uv-managed Python service",
  mobile: "Expo deferred",
} as const;

export default function HomePage() {
  return (
    <main
      className="min-h-screen px-6 py-12"
      style={{
        background: `linear-gradient(160deg, ${designTokens.color.surface.canvas} 0%, ${designTokens.color.surface.elevated} 100%)`,
        color: designTokens.color.text.primary,
        fontFamily: designTokens.typography.family.sans,
      }}
    >
      <div
        className="mx-auto max-w-5xl"
        style={{
          display: "grid",
          gap: designTokens.spacing.xl,
        }}
      >
        <section
          style={{
            border: `1px solid ${designTokens.color.border.subtle}`,
            borderRadius: designTokens.radius.lg,
            backgroundColor: designTokens.color.surface.card,
            boxShadow: designTokens.shadow.soft,
            padding: designTokens.spacing.xl,
          }}
        >
          <p
            className="text-sm uppercase tracking-[0.2em]"
            style={{ color: designTokens.color.text.secondary }}
          >
            Task 1 placeholder
          </p>
          <h1
            className="mt-4 text-4xl font-semibold sm:text-5xl"
            style={{
              lineHeight: designTokens.typography.lineHeight.tight,
              marginBottom: designTokens.spacing.md,
            }}
          >
            GradMatch monorepo foundation is ready for the next vertical slices.
          </h1>
          <p
            className="max-w-3xl text-lg"
            style={{
              color: designTokens.color.text.secondary,
              lineHeight: designTokens.typography.lineHeight.relaxed,
            }}
          >
            This page intentionally stays minimal while the repository establishes shared TypeScript
            boundaries, semantic design tokens, and the Python API service scaffold.
          </p>
        </section>

        <section className="grid gap-4 md:grid-cols-2">
          {Object.entries(stack).map(([key, value]) => (
            <article
              key={key}
              style={{
                border: `1px solid ${designTokens.color.border.subtle}`,
                borderRadius: designTokens.radius.md,
                backgroundColor: designTokens.color.surface.card,
                padding: designTokens.spacing.lg,
                boxShadow: designTokens.shadow.medium,
              }}
            >
              <p
                className="text-sm uppercase tracking-[0.14em]"
                style={{ color: designTokens.color.brand.accent }}
              >
                {key}
              </p>
              <p className="mt-3 text-xl font-medium">{value}</p>
            </article>
          ))}
        </section>
      </div>
    </main>
  );
}
