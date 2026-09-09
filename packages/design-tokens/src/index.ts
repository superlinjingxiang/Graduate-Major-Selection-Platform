export const designTokens = {
  color: {
    brand: {
      primary: "#0f766e",
      accent: "#22c55e",
      highlight: "#f59e0b",
      ink: "#163033",
      teal: "#0f766e",
    },
    surface: {
      canvas: "#f8fafc",
      elevated: "#e2e8f0",
      card: "#ffffff",
      warmWhite: "#fbfaf6",
      paleBlue: "#eaf3f7",
    },
    text: {
      primary: "#0f172a",
      secondary: "#475569",
      inverse: "#f8fafc",
    },
    border: {
      subtle: "#cbd5e1",
      strong: "#94a3b8",
    },
    chart: {
      primary: "#0f766e",
      secondary: "#4f7c8d",
      tertiary: "#c58b3a",
      quaternary: "#bd6654",
    },
  },
  spacing: {
    xxs: "0.25rem",
    xs: "0.5rem",
    sm: "0.75rem",
    md: "1rem",
    lg: "1.5rem",
    xl: "2rem",
    "2xl": "3rem",
  },
  radius: {
    sm: "0.375rem",
    md: "0.75rem",
    lg: "1rem",
    pill: "9999px",
  },
  shadow: {
    soft: "0 10px 30px rgba(15, 23, 42, 0.08)",
    medium: "0 18px 40px rgba(15, 23, 42, 0.12)",
  },
  typography: {
    family: {
      sans: '"IBM Plex Sans", "Segoe UI", sans-serif',
      mono: '"IBM Plex Mono", "SFMono-Regular", monospace',
    },
    size: {
      xs: "0.75rem",
      sm: "0.875rem",
      base: "1rem",
      lg: "1.125rem",
      xl: "1.5rem",
      "2xl": "2rem",
      "3xl": "3rem",
    },
    weight: {
      regular: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
    lineHeight: {
      tight: 1.2,
      normal: 1.5,
      relaxed: 1.7,
    },
  },
  motion: {
    duration: {
      instant: "80ms",
      fast: "160ms",
      normal: "240ms",
      slow: "360ms",
    },
    easing: {
      standard: "cubic-bezier(0.2, 0, 0, 1)",
      emphasized: "cubic-bezier(0.2, 0.8, 0.2, 1)",
    },
  },
} as const;

export type DesignTokens = typeof designTokens;
export type SemanticColors = DesignTokens["color"];
