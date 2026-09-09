import type { CSSProperties } from "react";

import { EvidenceChip } from "../components/site/evidence-chip";
import { SiteFooter } from "../components/site/site-footer";
import { SiteHeader } from "../components/site/site-header";
import { CatalogSearch } from "../features/discovery/catalog-search";
import { degreeStructure, demoPrograms, examRegistrationTrend } from "../lib/demo-catalog";

const disciplineEntries = [
  ["经济学", "金融、应用经济学与相关专业"],
  ["法学", "法律、法学与公共治理方向"],
  ["教育学", "心理、教育与人才发展方向"],
  ["工学", "计算机、电子信息与工程方向"],
  ["文学", "语言、传播与人文研究方向"],
] as const;

const tools = [
  ["查院校专业", "按代码、地区和培养方式找到可比较的项目。", "/search"],
  ["做择校判断", "从报考事实开始，获得有证据边界的匹配建议。", "/match"],
  ["整理关注清单", "把分散项目收进同一套比较框架。", "/account/signup"],
] as const;

export default function HomePage() {
  const latestPrograms = demoPrograms.slice(0, 3);

  return (
    <div className="home-page">
      <SiteHeader />

      <main>
        <section className="home-hero">
          <div className="content-shell home-hero-inner">
            <p className="home-kicker">研究生招生信息工作台</p>
            <h1>把分散的招生信息，变成清晰的选择。</h1>
            <p className="home-hero-copy">
              汇集院校、专业与招生动态，用明确的来源标记，帮你更快找到值得继续核对的方向。
            </p>
            <CatalogSearch programs={demoPrograms} />
            <p className="search-prompt">
              热门检索：<a href="/search?q=金融">金融</a>
              <a href="/search?q=计算机">计算机</a>
              <a href="/search?q=法律">法律</a>
            </p>
          </div>
        </section>

        <section
          className="content-shell section-shell home-data-section"
          aria-labelledby="trend-title"
        >
          <div className="section-intro">
            <p className="section-number">01 / DATA</p>
            <div>
              <h2 id="trend-title">报名热度正在回落，选择更需要依据。</h2>
              <p className="section-description">
                全国硕士研究生招生考试报名人数，保留原始口径与可追溯来源。
              </p>
            </div>
          </div>

          <article className="official-data-card">
            <div className="data-card-heading">
              <div>
                <p className="data-label">官方报名人数</p>
                <p className="data-summary">
                  <strong>343 万</strong>
                  <span>2026 年</span>
                </p>
              </div>
              <EvidenceChip state="confirmed" />
            </div>

            <figure className="registration-figure">
              <ol className="registration-bars" aria-label="2025 至 2026 年报名人数趋势">
                {examRegistrationTrend.map((item) => (
                  <li className="registration-year" key={item.year}>
                    <span className="registration-value">
                      {item.value}
                      {item.unit}人
                    </span>
                    <span
                      aria-hidden="true"
                      className="registration-bar"
                      style={{ "--bar-size": `${(item.value / 400) * 100}%` } as CSSProperties}
                    />
                    <span className="registration-label">{item.year}</span>
                  </li>
                ))}
              </ol>
              <figcaption>
                较上年减少 45 万人。来源：
                <a href={examRegistrationTrend[1].sourceUrl}>教育部，2025-11-24 发布</a>
              </figcaption>
            </figure>
          </article>
        </section>

        <section className="home-demo-section" aria-labelledby="structure-title">
          <div className="content-shell section-shell structure-layout">
            <div className="section-intro section-intro-light">
              <p className="section-number">02 / STRUCTURE</p>
              <div>
                <div className="section-title-row">
                  <h2 id="structure-title">{degreeStructure.label}</h2>
                  <EvidenceChip state="demo" />
                </div>
                <p className="section-description section-description-light">
                  {degreeStructure.disclaimer}
                </p>
              </div>
            </div>

            <div className="degree-structure-card">
              <div className="degree-track" aria-label="学术学位 40%，专业学位 60%" role="img">
                {degreeStructure.items.map((item) => (
                  <span
                    className={`degree-segment degree-segment-${item.degreeType}`}
                    key={item.degreeType}
                    style={{ width: `${item.value}%` }}
                  />
                ))}
              </div>
              <dl className="degree-legend">
                {degreeStructure.items.map((item) => (
                  <div key={item.degreeType}>
                    <dt>{item.label}</dt>
                    <dd>{item.value}%</dd>
                  </div>
                ))}
              </dl>
            </div>
          </div>
        </section>

        <section className="content-shell section-shell" aria-labelledby="discipline-title">
          <div className="section-intro">
            <p className="section-number">03 / DISCIPLINES</p>
            <div>
              <h2 id="discipline-title">从专业门类进入，不被院校名单淹没。</h2>
              <p className="section-description">
                先建立方向感，再深入比较培养方式、考试科目与招生变化。
              </p>
            </div>
          </div>

          <div className="discipline-grid">
            {disciplineEntries.map(([name, description], index) => (
              <a
                className="discipline-card"
                href={`/search?q=${encodeURIComponent(name)}`}
                key={name}
              >
                <span className="discipline-index">0{index + 1}</span>
                <h3>{name}</h3>
                <p>{description}</p>
                <span className="card-arrow" aria-hidden="true">
                  ↗
                </span>
              </a>
            ))}
          </div>
        </section>

        <section className="home-tools-section" aria-labelledby="tools-title">
          <div className="content-shell section-shell">
            <div className="section-intro section-intro-light">
              <p className="section-number">04 / TOOLS</p>
              <div>
                <h2 id="tools-title">免费的工具，先帮你减少信息噪音。</h2>
                <p className="section-description section-description-light">
                  每一步都留下可复核的信息，不用先购买才能开始判断。
                </p>
              </div>
            </div>

            <div className="tool-grid">
              {tools.map(([title, description, href]) => (
                <a href={href} className="tool-card" key={title}>
                  <h3>{title}</h3>
                  <p>{description}</p>
                  <span>立即使用 →</span>
                </a>
              ))}
            </div>
          </div>
        </section>

        <section className="content-shell section-shell" aria-labelledby="updates-title">
          <div className="section-intro">
            <p className="section-number">05 / UPDATES</p>
            <div>
              <h2 id="updates-title">最近收录的专业变化</h2>
              <p className="section-description">
                演示条目用于展示信息结构，正式决策前仍需回到院校官方来源。
              </p>
            </div>
          </div>

          <div className="updates-list">
            {latestPrograms.map((program) => (
              <a href={`/programs/${program.slug}`} className="update-row" key={program.slug}>
                <div>
                  <span className="update-code">{program.programCode}</span>
                  <h3>
                    {program.institution} · {program.title}
                  </h3>
                  <p>{program.school}</p>
                </div>
                <div className="update-status">
                  <EvidenceChip state={program.evidenceState} />
                  <time dateTime={program.updatedAt}>{program.updatedAt}</time>
                </div>
              </a>
            ))}
          </div>
        </section>

        <section className="content-shell membership-preview" aria-labelledby="membership-title">
          <div>
            <p className="section-number">GRADMATCH PLUS</p>
            <h2 id="membership-title">把检索，变成持续更新的择校工作台。</h2>
            <p className="membership-description">
              保存比较清单、跟踪专业变化，并在关键字段更新时收到提醒。
            </p>
          </div>
          <a className="membership-cta" href="/account/signup">
            创建账户
            <span aria-hidden="true">→</span>
          </a>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
