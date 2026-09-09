# GradMatch 全专业 Web Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一条可本机演示的高保真 Web 链路，让用户从数据型首页搜索任意专业或院校，查看项目详情、建立临时对比，并在保存时进入已确认的登录体验。

**Architecture:** 本轮只改造 `apps/web`，使用类型化本地演示目录承载少量跨学科样本，保留现有 Django 纵向链路但不让 Demo 依赖后端启动。页面和数据叙事区保持 Server Components，搜索、筛选、对比与演示登录使用小型 Client Components；临时对比保存到 `localStorage`，不接真实短信、OAuth、支付或外部采集。

**Tech Stack:** Next.js 16 App Router、React 19、TypeScript strict、Tailwind CSS 4/原生 CSS、Vitest、React Testing Library、Playwright

**Spec:** `docs/gradmatch-demo-product-design-v0.md`

## Global Constraints

- 所有研究生专业使用一致的基础选择能力，不把计算机或其他单一专业设为产品主线。
- 基础字段包含专业名称与代码、学位类型、招生单位、培养单位、地区、学习方式、考试科目、招生年度、公开计划口径、来源与数据状态。
- Demo 样本必须明确显示“演示样本，不可作为报考依据”；官方宏观数据必须显示来源、年度和口径。
- 首页、详情页和静态内容默认使用 Server Components；只有浏览器状态与事件处理使用 Client Components。
- 游客可搜索、查看详情和临时对比；保存操作进入登录页。
- 本轮不调用真实微信、QQ、短信、支付、外部采集或推荐模型。
- 公开页面不得出现平台状态、环境、版本、数据库、缓存或内部诊断信息。
- 页面需兼容桌面和手机、键盘操作、文字状态提示及 `prefers-reduced-motion`。
- 不删除现有 `/match`、真实邮箱注册登录或后端接口；Demo 新链路与旧纵向链路并存。

---

## File Structure

### New files

- `apps/web/src/lib/demo-catalog.ts`：Demo 数据类型、官方宏观数据、跨学科样本和纯搜索函数。
- `apps/web/src/lib/demo-catalog.test.ts`：目录搜索、筛选和 slug 查询测试。
- `apps/web/src/components/site/site-header.tsx`：统一品牌导航。
- `apps/web/src/components/site/site-footer.tsx`：来源、纠错与政策入口。
- `apps/web/src/components/site/evidence-chip.tsx`：数据状态文字标签。
- `apps/web/src/components/site/evidence-chip.test.tsx`：数据状态的文字与无障碍测试。
- `apps/web/src/features/discovery/catalog-search.tsx`：首页统一搜索与分组建议。
- `apps/web/src/features/discovery/catalog-search.test.tsx`：键盘、建议和提交测试。
- `apps/web/src/features/discovery/search-explorer.tsx`：结果筛选与项目选择。
- `apps/web/src/features/discovery/search-explorer.test.tsx`：多字段搜索和筛选测试。
- `apps/web/src/features/compare/compare-provider.tsx`：临时对比状态和本地持久化。
- `apps/web/src/features/compare/compare-provider.test.tsx`：添加、移除、上限和恢复测试。
- `apps/web/src/features/compare/compare-action.tsx`：详情/结果页加入对比按钮。
- `apps/web/src/features/compare/compare-tray.tsx`：全局对比浮层。
- `apps/web/src/features/auth/demo-login.tsx`：微信、手机号、QQ 和邮箱入口编排。
- `apps/web/src/features/auth/demo-login.test.tsx`：登录方式、演示手机号流程和返回地址测试。
- `apps/web/src/app/search/page.tsx`：搜索结果路由。
- `apps/web/src/app/programs/[slug]/page.tsx`：项目详情动态路由。
- `apps/web/src/app/compare/page.tsx`：临时对比页。
- `apps/web/e2e/demo-journey.spec.ts`：完整 Demo 链路测试。
- `apps/web/playwright.demo.config.ts`：无需 Docker 的桌面/手机 E2E 配置。

### Modified files

- `apps/web/src/app/page.tsx`：替换旧试点首页为数据型首页。
- `apps/web/src/app/layout.tsx`：更新元数据并挂载临时对比 Provider/Tray。
- `apps/web/src/app/globals.css`：建立新页面布局、图表、卡片、响应式和动效样式。
- `packages/design-tokens/src/index.ts`：扩展数据产品所需的语义颜色。
- `apps/web/src/app/account/login/page.tsx`：改为主登录体验并支持安全返回地址。
- `apps/web/src/features/auth/auth-forms.tsx`：密码登录增加显示/隐藏按钮。
- `apps/web/src/features/auth/auth-forms.test.tsx`：覆盖登录密码眼睛按钮。
- `apps/web/src/features/match/home-page.test.tsx`：改为新首页价值和无内部状态测试。
- `apps/web/package.json`：增加 `e2e:demo` 命令。
- `README.md`：增加本机 Demo 启动与验收入口。

---

### Task 1: 建立类型化跨学科 Demo 目录

**Files:**
- Create: `apps/web/src/lib/demo-catalog.ts`
- Create: `apps/web/src/lib/demo-catalog.test.ts`

**Interfaces:**
- Produces: `DemoProgram`, `DemoSearchFilters`, `examRegistrationTrend`, `degreeStructure`, `demoPrograms`, `searchDemoPrograms(query, filters)`, `getDemoProgramBySlug(slug)`。
- Consumes: 无；该模块必须是无 DOM、无 Next.js 依赖的纯 TypeScript。

- [ ] **Step 1: 写失败的搜索与数据边界测试**

```ts
import { describe, expect, it } from "vitest";
import {
  demoPrograms,
  examRegistrationTrend,
  getDemoProgramBySlug,
  searchDemoPrograms,
} from "./demo-catalog";

describe("demo catalog", () => {
  it("covers multiple disciplines and labels every record as demo data", () => {
    expect(new Set(demoPrograms.map(({ discipline }) => discipline)).size).toBeGreaterThanOrEqual(4);
    expect(demoPrograms.every(({ evidenceState }) => evidenceState === "demo")).toBe(true);
  });

  it.each(["北京师范大学", "应用心理", "045400"])("searches by %s", (query) => {
    expect(searchDemoPrograms(query, {}).map(({ slug }) => slug)).toContain(
      "bnu-applied-psychology-045400",
    );
  });

  it("filters degree type and region without inventing results", () => {
    const result = searchDemoPrograms("", { degreeType: "academic", region: "上海" });
    expect(result.every((item) => item.degreeType === "academic" && item.region === "上海")).toBe(true);
  });

  it("returns undefined for an unknown slug", () => {
    expect(getDemoProgramBySlug("missing")).toBeUndefined();
  });

  it("keeps official registration trend source metadata", () => {
    expect(examRegistrationTrend.find(({ year }) => year === 2026)).toMatchObject({ value: 343 });
    expect(examRegistrationTrend.every(({ sourceUrl }) => sourceUrl.startsWith("https://www.moe.gov.cn/"))).toBe(true);
  });
});
```

- [ ] **Step 2: 运行测试并确认因模块不存在而失败**

Run: `pnpm --filter @gradmatch/web test -- src/lib/demo-catalog.test.ts`

Expected: FAIL，提示无法解析 `./demo-catalog`。

- [ ] **Step 3: 实现纯数据契约与搜索函数**

```ts
export type EvidenceState = "confirmed" | "pending" | "conflict" | "stale" | "demo";
export type DegreeType = "academic" | "professional";

export interface DemoProgram {
  readonly slug: string;
  readonly institution: string;
  readonly school: string;
  readonly programCode: string;
  readonly title: string;
  readonly discipline: string;
  readonly degreeType: DegreeType;
  readonly region: string;
  readonly studyMode: "全日制" | "非全日制";
  readonly examSubjects: readonly string[];
  readonly targetYear: number;
  readonly planLabel: string;
  readonly tuitionLabel: string;
  readonly evidenceState: EvidenceState;
  readonly sourceLabel: string;
  readonly sourceUrl?: string;
  readonly updatedAt: string;
}

export interface DemoSearchFilters {
  readonly degreeType?: DegreeType;
  readonly region?: string;
  readonly studyMode?: DemoProgram["studyMode"];
}

export function searchDemoPrograms(query: string, filters: DemoSearchFilters): DemoProgram[] {
  const keyword = query.trim().toLocaleLowerCase("zh-CN");
  return demoPrograms.filter((program) => {
    const searchable = [program.institution, program.school, program.title, program.programCode]
      .join(" ")
      .toLocaleLowerCase("zh-CN");
    return (
      (!keyword || searchable.includes(keyword)) &&
      (!filters.degreeType || program.degreeType === filters.degreeType) &&
      (!filters.region || program.region === filters.region) &&
      (!filters.studyMode || program.studyMode === filters.studyMode)
    );
  });
}

export function getDemoProgramBySlug(slug: string) {
  return demoPrograms.find((program) => program.slug === slug);
}
```

`demoPrograms` 至少包含经济学、法学、教育学、工学、文学五类样本；所有项目的 `sourceLabel` 固定为“演示样本，不可作为报考依据”。`examRegistrationTrend` 写入 2025 年 388 万和 2026 年 343 万，并使用需求文档中的两个教育部链接。`degreeStructure` 使用“演示结构数据”标签，不把未完成口径复核的比例写成官方事实。

- [ ] **Step 4: 运行目录测试**

Run: `pnpm --filter @gradmatch/web test -- src/lib/demo-catalog.test.ts`

Expected: PASS，5 组断言全部通过。

- [ ] **Step 5: 提交任务**

```bash
git add apps/web/src/lib/demo-catalog.ts apps/web/src/lib/demo-catalog.test.ts
git commit -m "feat(web): add cross-discipline demo catalog"
```

### Task 2: 建立统一站点外壳与视觉基础

**Files:**
- Create: `apps/web/src/components/site/site-header.tsx`
- Create: `apps/web/src/components/site/site-footer.tsx`
- Create: `apps/web/src/components/site/evidence-chip.tsx`
- Create: `apps/web/src/components/site/evidence-chip.test.tsx`
- Modify: `apps/web/src/app/layout.tsx`
- Modify: `apps/web/src/app/globals.css`
- Modify: `packages/design-tokens/src/index.ts`

**Interfaces:**
- Produces: `SiteHeader`, `SiteFooter`, `EvidenceChip({ state })`，以及 `--gm-*` 语义变量。
- Consumes: `EvidenceState` 和现有 `designTokens`。

- [ ] **Step 1: 写组件状态测试**

在 `apps/web/src/components/site/evidence-chip.test.tsx` 中断言 `demo` 显示“演示数据”、`pending` 显示“待发布”、`conflict` 显示“来源冲突”，并且每个状态都有可见文字而不是只靠颜色。

```tsx
render(<EvidenceChip state="conflict" />);
expect(screen.getByText("来源冲突")).toBeVisible();
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `pnpm --filter @gradmatch/web test -- src/components/site/evidence-chip.test.tsx`

Expected: FAIL，提示组件不存在。

- [ ] **Step 3: 实现站点组件与设计令牌**

`SiteHeader` 使用 `next/link`，导航固定为“数据、院校、专业、择校工具、资讯”，账户入口为“登录”。移动端保留品牌、搜索和登录，其他导航可横向滚动，不能使用不可操作的汉堡菜单占位。

```tsx
const labels = ["数据", "院校", "专业", "择校工具", "资讯"] as const;

export function SiteHeader() {
  return (
    <header className="global-header">
      <Link className="brand" href="/" aria-label="GradMatch 首页">
        <span className="brand-mark" aria-hidden="true">G</span>
        <span>GradMatch</span>
      </Link>
      <nav aria-label="主导航">{labels.map((label) => <Link href="/search" key={label}>{label}</Link>)}</nav>
      <Link className="header-login" href="/account/login">登录</Link>
    </header>
  );
}
```

`EvidenceChip` 使用映射表输出中文文字；`SiteFooter` 包含“数据来源、纠错反馈、隐私政策、用户协议”，未实现页面使用非跳转文字，不写空 `href`。

扩展 `designTokens` 的深色墨水、青绿色、暖白、浅蓝和图表色，并在 `layout.tsx` 暴露 CSS 变量。保留现有变量，避免旧页面失效。

- [ ] **Step 4: 添加响应式基础 CSS**

在 `globals.css` 添加 `.global-header`、`.content-shell`、`.section-shell`、`.data-card`、`.evidence-chip`、`.demo-banner` 和移动断点；所有 hover 动效在 `prefers-reduced-motion: reduce` 下关闭。正文最小字号 14px，交互控件最小高度 44px。

- [ ] **Step 5: 运行组件测试、类型检查和旧页面冒烟测试**

Run: `pnpm --filter @gradmatch/web test -- src/components/site/evidence-chip.test.tsx src/features/match/home-page.test.tsx`

Expected: 新组件测试 PASS；旧首页测试此时仍 PASS，证明外壳改造没有提前改变首页行为。

- [ ] **Step 6: 提交任务**

```bash
git add packages/design-tokens/src/index.ts apps/web/src/app/layout.tsx apps/web/src/app/globals.css apps/web/src/components/site
git commit -m "feat(web): add data product visual foundation"
```

### Task 3: 构建数据型首页与统一搜索

**Files:**
- Create: `apps/web/src/features/discovery/catalog-search.tsx`
- Create: `apps/web/src/features/discovery/catalog-search.test.tsx`
- Modify: `apps/web/src/app/page.tsx`
- Modify: `apps/web/src/features/match/home-page.test.tsx`
- Modify: `apps/web/src/app/globals.css`

**Interfaces:**
- Consumes: `examRegistrationTrend`, `degreeStructure`, `demoPrograms`, `SiteHeader`, `SiteFooter`。
- Produces: 首页搜索建议和 `/search?q=keyword` 导航入口。

- [ ] **Step 1: 把首页测试改为新价值主张**

```tsx
render(<HomePage />);
expect(screen.getByRole("heading", { name: "把分散的招生信息，变成清晰的选择。" })).toBeVisible();
expect(screen.getByRole("searchbox", { name: "搜索院校、专业或专业代码" })).toBeVisible();
expect(screen.getByText("343 万")).toBeVisible();
expect(screen.getByText("演示结构数据")).toBeVisible();
expect(screen.queryByText(/平台状态|development|2027 北京全日制计算机统考/u)).not.toBeInTheDocument();
```

- [ ] **Step 2: 写搜索建议失败测试**

```tsx
render(<CatalogSearch programs={demoPrograms} />);
await user.type(screen.getByRole("searchbox"), "045400");
expect(screen.getByRole("link", { name: /北京师范大学.*应用心理/u })).toHaveAttribute(
  "href",
  "/programs/bnu-applied-psychology-045400",
);
```

- [ ] **Step 3: 运行测试确认旧首页和缺失组件导致失败**

Run: `pnpm --filter @gradmatch/web test -- src/features/match/home-page.test.tsx src/features/discovery/catalog-search.test.tsx`

Expected: FAIL，旧首页标题不匹配且 `CatalogSearch` 不存在。

- [ ] **Step 4: 实现搜索岛与 Server Component 首页**

`CatalogSearch` 使用原生 GET 表单提交到 `/search`，输入名为 `q`；有输入时最多显示 6 条按“院校/专业”描述的建议，Escape 关闭建议，点击外部不作为首轮必需行为。

首页依次渲染：首屏搜索、报名人数趋势、学硕/专硕演示结构、专业分类入口、免费工具、最新变化、会员预览和页脚。趋势图使用语义 HTML 和 CSS 条形/折线表达，并为每个数值保留可读文本，不引入图表依赖。

- [ ] **Step 5: 运行首页和搜索测试**

Run: `pnpm --filter @gradmatch/web test -- src/features/match/home-page.test.tsx src/features/discovery/catalog-search.test.tsx`

Expected: PASS。

- [ ] **Step 6: 提交任务**

```bash
git add apps/web/src/app/page.tsx apps/web/src/app/globals.css apps/web/src/features/match/home-page.test.tsx apps/web/src/features/discovery
git commit -m "feat(web): build data-first product homepage"
```

### Task 4: 实现搜索结果与跨专业筛选

**Files:**
- Create: `apps/web/src/app/search/page.tsx`
- Create: `apps/web/src/features/discovery/search-explorer.tsx`
- Create: `apps/web/src/features/discovery/search-explorer.test.tsx`
- Modify: `apps/web/src/app/globals.css`

**Interfaces:**
- Consumes: `DemoProgram`, `DemoSearchFilters`, `demoPrograms`, `searchDemoPrograms`。
- Produces: `SearchExplorer({ initialQuery, programs })` 与详情链接 `/programs/[slug]`。

- [ ] **Step 1: 写搜索结果行为测试**

```tsx
render(<SearchExplorer initialQuery="" programs={demoPrograms} />);
await user.type(screen.getByRole("searchbox"), "法律");
expect(screen.getByText("法律（非法学）")).toBeVisible();
expect(screen.queryByText("应用心理")).not.toBeInTheDocument();
await user.clear(screen.getByRole("searchbox"));
await user.selectOptions(screen.getByLabelText("地区"), "上海");
expect(screen.getAllByTestId("program-card").every((card) => card.textContent?.includes("上海"))).toBe(true);
```

另加无结果断言：显示“暂未找到匹配项目”和“清除筛选”，不产生虚构近似项目。

- [ ] **Step 2: 运行测试确认失败**

Run: `pnpm --filter @gradmatch/web test -- src/features/discovery/search-explorer.test.tsx`

Expected: FAIL，提示组件不存在。

- [ ] **Step 3: 实现筛选组件和页面**

`app/search/page.tsx` 按 Next.js 16 的 Promise 约定读取查询参数：

```tsx
export default async function SearchPage({ searchParams }: PageProps<"/search">) {
  const { q } = await searchParams;
  return <SearchExplorer initialQuery={typeof q === "string" ? q : ""} programs={demoPrograms} />;
}
```

`SearchExplorer` 提供关键词、地区、学位类型、学习方式四类控件。结果卡显示院校、培养单位、代码与专业、学位类型、地区、学习方式、年度、证据标签和“查看详情”。顶部固定展示“当前为跨学科演示样本，不代表全国完整数据”。

- [ ] **Step 4: 运行测试与类型检查**

Run: `pnpm --filter @gradmatch/web test -- src/features/discovery/search-explorer.test.tsx`

Run: `pnpm --filter @gradmatch/web typecheck`

Expected: 两条命令均退出码 0。

- [ ] **Step 5: 提交任务**

```bash
git add apps/web/src/app/search apps/web/src/features/discovery/search-explorer.tsx apps/web/src/features/discovery/search-explorer.test.tsx apps/web/src/app/globals.css
git commit -m "feat(web): add all-major search experience"
```

### Task 5: 建立临时对比状态、详情页和对比页

**Files:**
- Create: `apps/web/src/features/compare/compare-provider.tsx`
- Create: `apps/web/src/features/compare/compare-provider.test.tsx`
- Create: `apps/web/src/features/compare/compare-action.tsx`
- Create: `apps/web/src/features/compare/compare-tray.tsx`
- Create: `apps/web/src/app/programs/[slug]/page.tsx`
- Create: `apps/web/src/app/compare/page.tsx`
- Modify: `apps/web/src/app/layout.tsx`
- Modify: `apps/web/src/features/discovery/search-explorer.tsx`
- Modify: `apps/web/src/app/globals.css`

**Interfaces:**
- Produces: `CompareProvider`, `useCompare()`, `CompareAction({ programSlug })`, `CompareTray`。
- `useCompare()` returns `{ slugs: readonly string[]; toggle(slug: string): void; clear(): void; isFull: boolean }`。
- Consumes: `demoPrograms`, `getDemoProgramBySlug`。

- [ ] **Step 1: 写对比状态失败测试**

```tsx
function Probe() {
  const compare = useCompare();
  return (
    <>
      <output>{compare.slugs.join(",")}</output>
      {['a', 'b', 'c', 'd'].map((slug) => <button key={slug} onClick={() => compare.toggle(slug)}>{slug}</button>)}
    </>
  );
}

render(<CompareProvider><Probe /></CompareProvider>);
await user.click(screen.getByRole("button", { name: "a" }));
await user.click(screen.getByRole("button", { name: "b" }));
await user.click(screen.getByRole("button", { name: "c" }));
await user.click(screen.getByRole("button", { name: "d" }));
expect(screen.getByText("a,b,c")).toBeVisible();
expect(localStorage.getItem("gradmatch.demo.compare")).toBe('["a","b","c"]');
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pnpm --filter @gradmatch/web test -- src/features/compare/compare-provider.test.tsx`

Expected: FAIL，Provider 不存在。

- [ ] **Step 3: 实现最多三个项目的本地对比状态**

Provider 首次挂载从 `gradmatch.demo.compare` 读取字符串数组，过滤非字符串、去重并截取前三项；写入失败时仍维持内存状态。`toggle` 可移除已有项，满三个后忽略新项并通过 `isFull` 让按钮显示“最多对比 3 个”。

在根布局中将 Provider 尽量深地包裹 `{children}` 和 `CompareTray`，保持页面自身为 Server Components。

- [ ] **Step 4: 实现详情页和对比页**

详情页使用 `generateStaticParams()` 返回所有 Demo slug，按 Next.js 16 异步读取 `params`；未知 slug 调用 `notFound()`。展示基础字段、考试科目、计划与费用文本、证据状态、更新时间和演示免责声明。

详情页同时提供“继续搜索”链接到 `/search`，让用户能补充第二个对比项目。

对比页将已选项目按字段形成可横向滚动的语义表格。没有选择时显示返回搜索的操作；底部“保存这组对比”链接到 `/account/login?next=/compare&intent=save`。

- [ ] **Step 5: 运行 Provider、搜索和构建测试**

Run: `pnpm --filter @gradmatch/web test -- src/features/compare/compare-provider.test.tsx src/features/discovery/search-explorer.test.tsx`

Run: `pnpm --filter @gradmatch/web build`

Expected: 测试 PASS，构建退出码 0，所有样本详情页生成成功。

- [ ] **Step 6: 提交任务**

```bash
git add apps/web/src/features/compare apps/web/src/features/discovery/search-explorer.tsx apps/web/src/app/programs apps/web/src/app/compare apps/web/src/app/layout.tsx apps/web/src/app/globals.css
git commit -m "feat(web): add program detail and guest comparison"
```

### Task 6: 重构登录入口为已确认的多方式体验

**Files:**
- Create: `apps/web/src/features/auth/demo-login.tsx`
- Create: `apps/web/src/features/auth/demo-login.test.tsx`
- Modify: `apps/web/src/app/account/login/page.tsx`
- Modify: `apps/web/src/features/auth/auth-forms.tsx`
- Modify: `apps/web/src/features/auth/auth-forms.test.tsx`
- Modify: `apps/web/src/app/account/layout.tsx`
- Modify: `apps/web/src/app/globals.css`

**Interfaces:**
- Produces: `DemoLogin({ nextPath })`。
- Consumes: 现有 `PasswordLoginForm`；演示手机号和二维码不调用 API。

- [ ] **Step 1: 写登录布局和密码切换失败测试**

```tsx
renderWithQuery(<DemoLogin nextPath="/compare" />);
expect(screen.getByRole("heading", { name: "登录后继续你的选择" })).toBeVisible();
expect(screen.getByRole("tab", { name: "微信扫码" })).toBeVisible();
expect(screen.getByRole("tab", { name: "手机验证码" })).toBeVisible();
expect(screen.getByRole("button", { name: "QQ 登录（演示）" })).toBeVisible();
expect(screen.getByText("演示模式不会发送短信或发起第三方授权")).toBeVisible();
```

在现有认证测试中增加：输入登录密码后点击“显示密码”，输入类型变成 `text` 且值不变。

- [ ] **Step 2: 运行测试确认失败**

Run: `pnpm --filter @gradmatch/web test -- src/features/auth/demo-login.test.tsx src/features/auth/auth-forms.test.tsx`

Expected: FAIL，新组件缺失且登录密码没有切换按钮。

- [ ] **Step 3: 实现微信/手机主入口和其他方式**

微信面板使用纯 CSS 绘制非可扫描的演示二维码，并显示“演示二维码”；手机号面板接受 11 位数字，点击后显示统一提示“演示验证码已就绪”，输入 `123456` 后显示登录完成并提供 `继续返回对比` 链接。其他方式折叠区包含 QQ 演示按钮、邮箱验证码入口和真实邮箱密码表单。

不要伪装真实授权成功：微信和 QQ 操作都显示“Demo 未连接第三方服务”。

`account/login/page.tsx` 只接受以 `/` 开头且不以 `//` 开头的 `next`，否则回退 `/`，避免开放重定向。

- [ ] **Step 4: 为密码登录打开眼睛按钮**

给 `PasswordLoginForm` 的密码 `FormField` 增加 `showPasswordToggle`，保持现有提交和无 JavaScript 时 POST 安全行为不变。

- [ ] **Step 5: 运行认证单元测试**

Run: `pnpm --filter @gradmatch/web test -- src/features/auth/demo-login.test.tsx src/features/auth/auth-forms.test.tsx`

Expected: PASS，包括演示边界、返回地址和两处密码眼睛按钮。

- [ ] **Step 6: 提交任务**

```bash
git add apps/web/src/features/auth apps/web/src/app/account apps/web/src/app/globals.css
git commit -m "feat(web): redesign demo login choices"
```

### Task 7: 加入无需 Docker 的完整 Demo 验收

**Files:**
- Create: `apps/web/e2e/demo-journey.spec.ts`
- Create: `apps/web/playwright.demo.config.ts`
- Modify: `apps/web/package.json`
- Modify: `README.md`

**Interfaces:**
- Consumes: `/`、`/search`、`/programs/[slug]`、`/compare`、`/account/login`。
- Produces: `pnpm --filter @gradmatch/web e2e:demo`。

- [ ] **Step 1: 写完整 E2E 测试**

```ts
test("guest discovers, compares and reaches demo login", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "把分散的招生信息，变成清晰的选择。" })).toBeVisible();
  await page.getByRole("searchbox", { name: "搜索院校、专业或专业代码" }).fill("045400");
  await page.getByRole("link", { name: /北京师范大学.*应用心理/u }).click();
  await expect(page.getByText("演示样本，不可作为报考依据")).toBeVisible();
  await page.getByRole("button", { name: "加入对比" }).click();
  await page.getByRole("link", { name: "继续搜索" }).click();
  await page.getByRole("searchbox").fill("金融");
  await page.getByRole("button", { name: /加入对比/u }).first().click();
  await page.getByRole("link", { name: "查看对比" }).click();
  await expect(page.getByRole("table", { name: "项目对比" })).toBeVisible();
  await page.getByRole("link", { name: "保存这组对比" }).click();
  await expect(page.getByRole("heading", { name: "登录后继续你的选择" })).toBeVisible();
});
```

另写首页断言：不出现“平台状态”“development”“服务已准备就绪”；手机项目断言页面没有横向文档溢出。

- [ ] **Step 2: 创建独立 Playwright 配置**

```ts
export default defineConfig({
  testDir: "./e2e",
  testMatch: "demo-journey.spec.ts",
  use: { baseURL: "http://127.0.0.1:3000", trace: "on-first-retry" },
  webServer: {
    command: "pnpm dev",
    url: "http://127.0.0.1:3000",
    reuseExistingServer: true,
    timeout: 120_000,
  },
  projects: [
    { name: "desktop-chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile-chromium", use: { ...devices["Pixel 7"] } },
  ],
});
```

在 `package.json` 增加：`"e2e:demo": "playwright test --config=playwright.demo.config.ts"`。

- [ ] **Step 3: 更新本机运行说明**

README 增加：

```powershell
pnpm --filter @gradmatch/web dev
# 浏览器打开 http://localhost:3000

pnpm --filter @gradmatch/web e2e:demo
```

明确写明 Demo 不要求 Docker 或后端数据库，真实邮箱认证链路仍需要原生依赖。

- [ ] **Step 4: 运行 E2E**

Run: `pnpm --filter @gradmatch/web e2e:demo`

Expected: desktop-chromium 与 mobile-chromium 全部 PASS。

- [ ] **Step 5: 提交任务**

```bash
git add apps/web/e2e/demo-journey.spec.ts apps/web/playwright.demo.config.ts apps/web/package.json README.md
git commit -m "test(web): verify standalone demo journey"
```

### Task 8: 全量质量检查与本机交付

**Files:**
- Modify only if verification reveals a scoped defect.

**Interfaces:**
- Consumes: 前七个任务全部产物。
- Produces: 可在 `http://localhost:3000` 验收的运行中 Demo。

- [ ] **Step 1: 运行 Web 单元测试**

Run: `pnpm --filter @gradmatch/web test`

Expected: 退出码 0，无失败测试。

- [ ] **Step 2: 运行格式、Lint 和类型检查**

Run: `pnpm exec biome check apps/web packages/design-tokens`

Run: `pnpm --filter @gradmatch/web typecheck`

Expected: 两条命令均退出码 0。

- [ ] **Step 3: 运行生产构建**

Run: `pnpm --filter @gradmatch/web build`

Expected: 退出码 0；首页、搜索、对比、账户页和所有 Demo 详情页构建成功。

- [ ] **Step 4: 运行桌面与手机 E2E**

Run: `pnpm --filter @gradmatch/web e2e:demo`

Expected: 两个浏览器项目全部 PASS。

- [ ] **Step 5: 视觉检查关键页面**

启动 `pnpm --filter @gradmatch/web dev`，分别以 1440×1000 和 390×844 检查 `/`、`/search?q=045400`、`/programs/bnu-applied-psychology-045400`、`/compare`、`/account/login`。确认无截断、重叠、横向溢出、空白按钮、内部状态文案或把演示数据伪装成官方事实的情况。

- [ ] **Step 6: 启动 Demo 并交给用户验收**

Run: `pnpm --filter @gradmatch/web dev`

Expected: 进程保持运行，终端显示 `http://localhost:3000` 可访问；向用户提供首页、搜索、详情、对比和登录页入口。
