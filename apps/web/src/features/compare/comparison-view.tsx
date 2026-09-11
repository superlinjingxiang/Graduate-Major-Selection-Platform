"use client";

import Link from "next/link";

import { type DemoProgram, demoPrograms } from "../../lib/demo-catalog";
import { CompareAction } from "./compare-action";
import { useCompare } from "./compare-provider";

const degreeLabels = {
  academic: "学术学位",
  professional: "专业学位",
} as const;

type ComparisonRow = Readonly<{
  label: string;
  value: (program: DemoProgram) => string;
}>;

const rows: readonly ComparisonRow[] = [
  { label: "专业代码", value: (program) => program.programCode },
  { label: "学位类型", value: (program) => degreeLabels[program.degreeType] },
  { label: "培养单位", value: (program) => program.school },
  { label: "地区", value: (program) => program.region },
  { label: "学习方式", value: (program) => program.studyMode },
  { label: "招生年度", value: (program) => String(program.targetYear) },
  { label: "公开计划", value: (program) => program.planLabel },
  { label: "学费", value: (program) => program.tuitionLabel },
  { label: "考试科目", value: (program) => program.examSubjects.join("、") },
  { label: "数据状态", value: (program) => program.sourceLabel },
];

export function ComparisonView() {
  const { clear, slugs } = useCompare();
  const programs = slugs
    .map((slug) => demoPrograms.find((program) => program.slug === slug))
    .filter((program): program is DemoProgram => Boolean(program));

  if (!programs.length) {
    return (
      <section className="comparison-empty" aria-labelledby="comparison-empty-title">
        <p className="eyebrow">临时对比</p>
        <h1 id="comparison-empty-title">还没有选择对比项目</h1>
        <p>先从不同院校或专业中选择两到三个项目，再回到这里查看差异。</p>
        <Link className="button button-primary" href="/search">
          去搜索项目
        </Link>
      </section>
    );
  }

  return (
    <section className="comparison-section" aria-labelledby="comparison-title">
      <div className="comparison-heading">
        <div>
          <p className="eyebrow">临时对比</p>
          <h1 id="comparison-title">把关键差异放在同一张表里。</h1>
          <p>当前内容均为跨学科演示样本，不能作为报考依据。</p>
        </div>
        <button className="filter-reset" onClick={clear} type="button">
          清空对比
        </button>
      </div>

      <div className="comparison-table-wrap">
        <table aria-label="项目对比" className="comparison-table">
          <thead>
            <tr>
              <th scope="col">比较维度</th>
              {programs.map((program) => (
                <th scope="col" key={program.slug}>
                  <span>{program.institution}</span>
                  <strong>{program.title}</strong>
                  <CompareAction programSlug={program.slug} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.label}>
                <th scope="row">{row.label}</th>
                {programs.map((program) => (
                  <td key={program.slug}>{row.value(program)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="comparison-save">
        <div>
          <strong>登录后保存这组对比</strong>
          <p>登录只在需要跨设备保存和持续提醒时出现。</p>
        </div>
        <Link className="button button-primary" href="/account/login?next=/compare&intent=save">
          保存这组对比
        </Link>
      </div>
    </section>
  );
}
