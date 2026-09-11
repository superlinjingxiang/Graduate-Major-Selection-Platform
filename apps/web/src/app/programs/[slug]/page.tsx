import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { EvidenceChip } from "../../../components/site/evidence-chip";
import { SiteFooter } from "../../../components/site/site-footer";
import { SiteHeader } from "../../../components/site/site-header";
import { CompareAction } from "../../../features/compare/compare-action";
import { demoPrograms, getDemoProgramBySlug } from "../../../lib/demo-catalog";

const degreeLabels = {
  academic: "学术学位",
  professional: "专业学位",
} as const;

export function generateStaticParams() {
  return demoPrograms.map(({ slug }) => ({ slug }));
}

export async function generateMetadata({
  params,
}: PageProps<"/programs/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const program = getDemoProgramBySlug(slug);
  return program
    ? { title: `${program.institution} ${program.title}｜GradMatch` }
    : { title: "项目未找到｜GradMatch" };
}

export default async function ProgramPage({ params }: PageProps<"/programs/[slug]">) {
  const { slug } = await params;
  const program = getDemoProgramBySlug(slug);
  if (!program) notFound();

  return (
    <main className="product-page">
      <SiteHeader />
      <article className="program-detail">
        <header className="program-detail-hero">
          <div className="content-shell">
            <div className="program-detail-topline">
              <span>{program.discipline}</span>
              <EvidenceChip state={program.evidenceState} />
            </div>
            <p className="program-detail-institution">{program.institution}</p>
            <h1>{program.title}</h1>
            <p className="program-detail-subtitle">
              {program.programCode} · {program.school} · {degreeLabels[program.degreeType]}
            </p>
            <div className="program-detail-actions">
              <CompareAction programSlug={program.slug} />
              <Link href="/search">继续搜索</Link>
            </div>
          </div>
        </header>

        <div className="content-shell program-detail-grid">
          <section className="detail-card" aria-labelledby="basic-information-title">
            <p className="eyebrow">基础信息</p>
            <h2 id="basic-information-title">统一口径查看项目</h2>
            <dl className="detail-list">
              <div>
                <dt>招生年度</dt>
                <dd>{program.targetYear}</dd>
              </div>
              <div>
                <dt>地区</dt>
                <dd>{program.region}</dd>
              </div>
              <div>
                <dt>学习方式</dt>
                <dd>{program.studyMode}</dd>
              </div>
              <div>
                <dt>公开计划</dt>
                <dd>{program.planLabel}</dd>
              </div>
              <div>
                <dt>学费</dt>
                <dd>{program.tuitionLabel}</dd>
              </div>
            </dl>
          </section>

          <section className="detail-card" aria-labelledby="exam-subjects-title">
            <p className="eyebrow">考试信息</p>
            <h2 id="exam-subjects-title">考试科目</h2>
            <ol className="subject-list">
              {program.examSubjects.map((subject) => (
                <li key={subject}>{subject}</li>
              ))}
            </ol>
          </section>

          <aside className="detail-trust-card" aria-labelledby="data-boundary-title">
            <EvidenceChip state={program.evidenceState} />
            <h2 id="data-boundary-title">演示样本，不可作为报考依据</h2>
            <p>该项目用于验证页面与比较体验。正式使用时请以招生单位当年发布的文件为准。</p>
            <dl>
              <div>
                <dt>数据说明</dt>
                <dd>{program.sourceLabel}</dd>
              </div>
              <div>
                <dt>更新时间</dt>
                <dd>
                  <time dateTime={program.updatedAt}>{program.updatedAt}</time>
                </dd>
              </div>
            </dl>
          </aside>
        </div>
      </article>
      <SiteFooter />
    </main>
  );
}
