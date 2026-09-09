"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { EvidenceChip } from "../../components/site/evidence-chip";
import {
  type DegreeType,
  type DemoProgram,
  type DemoSearchFilters,
  searchDemoPrograms,
} from "../../lib/demo-catalog";

type SearchExplorerProps = Readonly<{
  initialQuery: string;
  programs: readonly DemoProgram[];
}>;

const degreeLabels = {
  academic: "学术学位",
  professional: "专业学位",
} satisfies Record<DegreeType, string>;

export function SearchExplorer({ initialQuery, programs }: SearchExplorerProps) {
  const [query, setQuery] = useState(initialQuery);
  const [region, setRegion] = useState("");
  const [degreeType, setDegreeType] = useState("");
  const [studyMode, setStudyMode] = useState("");
  const regions = useMemo(
    () =>
      Array.from(new Set(programs.map((program) => program.region))).sort((a, b) =>
        a.localeCompare(b, "zh-CN"),
      ),
    [programs],
  );
  const results = useMemo(() => {
    const allowedSlugs = new Set(programs.map((program) => program.slug));
    const filters: DemoSearchFilters = {
      ...(degreeType ? { degreeType: degreeType as DegreeType } : {}),
      ...(region ? { region } : {}),
      ...(studyMode ? { studyMode: studyMode as DemoProgram["studyMode"] } : {}),
    };
    return searchDemoPrograms(query, filters).filter((program) => allowedSlugs.has(program.slug));
  }, [degreeType, programs, query, region, studyMode]);

  function clearFilters() {
    setQuery("");
    setRegion("");
    setDegreeType("");
    setStudyMode("");
  }

  return (
    <div className="search-explorer">
      <section className="search-hero" aria-labelledby="search-title">
        <div className="content-shell search-hero-inner">
          <p className="eyebrow">全国院校与专业</p>
          <h1 id="search-title">从专业和学校，找到适合比较的项目。</h1>
          <p className="search-lede">输入院校、培养单位、专业名称或代码，再用统一口径缩小范围。</p>
          <label className="search-query-field">
            <span className="visually-hidden">搜索院校、专业或专业代码</span>
            <input
              aria-label="搜索院校、专业或专业代码"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="例如：北京师范大学、应用心理、045400"
              type="search"
              value={query}
            />
          </label>
        </div>
      </section>

      <section className="content-shell search-results-section" aria-labelledby="results-title">
        <div className="demo-banner" role="note">
          <strong>跨学科演示样本</strong>
          <span>当前结果用于验证产品体验，不代表全国完整数据，也不能作为报考依据。</span>
        </div>

        <div className="search-layout">
          <aside className="search-filters" aria-label="筛选条件">
            <div className="filter-heading">
              <p className="eyebrow">缩小范围</p>
              <h2>筛选条件</h2>
            </div>
            <label>
              <span>地区</span>
              <select value={region} onChange={(event) => setRegion(event.target.value)}>
                <option value="">全部地区</option>
                {regions.map((item) => (
                  <option value={item} key={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>学位类型</span>
              <select value={degreeType} onChange={(event) => setDegreeType(event.target.value)}>
                <option value="">全部类型</option>
                <option value="academic">学术学位</option>
                <option value="professional">专业学位</option>
              </select>
            </label>
            <label>
              <span>学习方式</span>
              <select value={studyMode} onChange={(event) => setStudyMode(event.target.value)}>
                <option value="">全部方式</option>
                <option value="全日制">全日制</option>
                <option value="非全日制">非全日制</option>
              </select>
            </label>
            <button className="filter-reset" onClick={clearFilters} type="button">
              清除筛选
            </button>
          </aside>

          <div className="search-results">
            <div className="results-heading">
              <div>
                <p className="eyebrow">搜索结果</p>
                <h2 id="results-title">找到 {results.length} 个演示项目</h2>
              </div>
              <p aria-live="polite">统一展示基础字段与数据状态</p>
            </div>

            {results.length ? (
              <div className="program-card-list">
                {results.map((program) => (
                  <article className="program-card" data-testid="program-card" key={program.slug}>
                    <div className="program-card-topline">
                      <span>{program.discipline}</span>
                      <EvidenceChip state={program.evidenceState} />
                    </div>
                    <div>
                      <p className="program-institution">{program.institution}</p>
                      <h3>{program.title}</h3>
                      <p className="program-school">{program.school}</p>
                    </div>
                    <dl className="program-meta">
                      <div>
                        <dt>专业代码</dt>
                        <dd>{program.programCode}</dd>
                      </div>
                      <div>
                        <dt>学位类型</dt>
                        <dd>{degreeLabels[program.degreeType]}</dd>
                      </div>
                      <div>
                        <dt>地区</dt>
                        <dd>{program.region}</dd>
                      </div>
                      <div>
                        <dt>学习方式</dt>
                        <dd>{program.studyMode}</dd>
                      </div>
                    </dl>
                    <div className="program-card-footer">
                      <span>{program.targetYear} 招生年度</span>
                      <Link href={`/programs/${program.slug}`}>查看详情</Link>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="search-empty">
                <p className="eyebrow">没有匹配项</p>
                <h3>暂未找到匹配项目</h3>
                <p>请检查关键词，或清除筛选后查看全部演示样本。</p>
                <button className="button button-secondary" onClick={clearFilters} type="button">
                  清除筛选
                </button>
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
