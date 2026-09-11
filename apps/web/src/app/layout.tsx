import { designTokens } from "@gradmatch/design-tokens";
import type { Metadata } from "next";
import type { CSSProperties, ReactNode } from "react";

import { QueryProvider } from "../components/providers/query-provider";
import { CompareProvider } from "../features/compare/compare-provider";
import { CompareTray } from "../features/compare/compare-tray";
import "./globals.css";

export const metadata: Metadata = {
  title: "GradMatch｜研究生匹配平台",
  description: "为研究生申请者与未来机会建立可靠的决策基础。",
};

const tokenVariables = {
  "--gm-accent": designTokens.color.brand.accent,
  "--gm-brand": designTokens.color.brand.primary,
  "--gm-border": designTokens.color.border.subtle,
  "--gm-border-strong": designTokens.color.border.strong,
  "--gm-canvas": designTokens.color.surface.canvas,
  "--gm-card": designTokens.color.surface.card,
  "--gm-elevated": designTokens.color.surface.elevated,
  "--gm-highlight": designTokens.color.brand.highlight,
  "--gm-ink": designTokens.color.brand.ink,
  "--gm-teal": designTokens.color.brand.teal,
  "--gm-warm-white": designTokens.color.surface.warmWhite,
  "--gm-pale-blue": designTokens.color.surface.paleBlue,
  "--gm-chart-primary": designTokens.color.chart.primary,
  "--gm-chart-secondary": designTokens.color.chart.secondary,
  "--gm-chart-tertiary": designTokens.color.chart.tertiary,
  "--gm-chart-quaternary": designTokens.color.chart.quaternary,
  "--gm-shadow-medium": designTokens.shadow.medium,
  "--gm-shadow-soft": designTokens.shadow.soft,
  "--gm-text": designTokens.color.text.primary,
  "--gm-text-muted": designTokens.color.text.secondary,
  "--gm-transition": designTokens.motion.duration.normal,
} as CSSProperties;

type RootLayoutProps = Readonly<{
  children: ReactNode;
}>;

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="zh-CN">
      <body style={tokenVariables}>
        <QueryProvider>
          <CompareProvider>
            {children}
            <CompareTray />
          </CompareProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
