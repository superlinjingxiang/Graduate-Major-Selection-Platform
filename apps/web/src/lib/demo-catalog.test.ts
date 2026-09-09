import { describe, expect, it } from "vitest";
import {
  demoPrograms,
  examRegistrationTrend,
  getDemoProgramBySlug,
  searchDemoPrograms,
} from "./demo-catalog";

describe("demo catalog", () => {
  it("covers multiple disciplines and labels every record as demo data", () => {
    expect(new Set(demoPrograms.map(({ discipline }) => discipline)).size).toBeGreaterThanOrEqual(
      4,
    );
    expect(demoPrograms.every(({ evidenceState }) => evidenceState === "demo")).toBe(true);
  });

  it.each(["北京师范大学", "应用心理", "045400"])("searches by %s", (query) => {
    expect(searchDemoPrograms(query, {}).map(({ slug }) => slug)).toContain(
      "bnu-applied-psychology-045400",
    );
  });

  it("filters degree type and region without inventing results", () => {
    const result = searchDemoPrograms("", { degreeType: "academic", region: "上海" });
    expect(result.every((item) => item.degreeType === "academic" && item.region === "上海")).toBe(
      true,
    );
  });

  it("returns undefined for an unknown slug", () => {
    expect(getDemoProgramBySlug("missing")).toBeUndefined();
  });

  it("keeps official registration trend source metadata", () => {
    expect(examRegistrationTrend.find(({ year }) => year === 2026)).toMatchObject({ value: 343 });
    expect(
      examRegistrationTrend.every(({ sourceUrl }) =>
        sourceUrl.startsWith("https://www.moe.gov.cn/"),
      ),
    ).toBe(true);
  });
});
