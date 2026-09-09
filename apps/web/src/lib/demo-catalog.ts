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

const demoSourceLabel = "演示样本，不可作为报考依据";

export const examRegistrationTrend = [
  {
    year: 2025,
    value: 388,
    unit: "万",
    metric: "全国硕士研究生招生考试报名人数",
    sourceLabel: "教育部",
    sourceUrl: "https://www.moe.gov.cn/jyb_xwfb/gzdt_gzdt/moe_1485/202411/t20241121_1163982.html",
    updatedAt: "2024-11-21",
  },
  {
    year: 2026,
    value: 343,
    unit: "万",
    metric: "全国硕士研究生招生考试报名人数",
    sourceLabel: "教育部",
    sourceUrl: "https://www.moe.gov.cn/jyb_xwfb/gzdt_gzdt/moe_1485/202511/t20251124_1421370.html",
    updatedAt: "2025-11-24",
  },
] as const;

export const degreeStructure = {
  label: "演示结构数据",
  disclaimer: "比例仅用于界面演示，统计口径尚待复核，不代表官方事实",
  items: [
    { degreeType: "academic", label: "学术学位", value: 40 },
    { degreeType: "professional", label: "专业学位", value: 60 },
  ],
} as const;

export const demoPrograms: readonly DemoProgram[] = [
  {
    slug: "sufe-finance-025100",
    institution: "上海财经大学",
    school: "金融学院",
    programCode: "025100",
    title: "金融",
    discipline: "经济学",
    degreeType: "professional",
    region: "上海",
    studyMode: "全日制",
    examSubjects: ["思想政治理论（演示）", "英语（二）（演示）", "经济类综合能力（演示）"],
    targetYear: 2027,
    planLabel: "招生计划：演示信息",
    tuitionLabel: "学费：演示信息",
    evidenceState: "demo",
    sourceLabel: demoSourceLabel,
    updatedAt: "2026-09-09",
  },
  {
    slug: "cupl-juris-master-035101",
    institution: "中国政法大学",
    school: "法律硕士学院",
    programCode: "035101",
    title: "法律（非法学）",
    discipline: "法学",
    degreeType: "professional",
    region: "北京",
    studyMode: "全日制",
    examSubjects: ["思想政治理论（演示）", "英语（一）（演示）", "法律硕士专业基础（演示）"],
    targetYear: 2027,
    planLabel: "招生计划：演示信息",
    tuitionLabel: "学费：演示信息",
    evidenceState: "demo",
    sourceLabel: demoSourceLabel,
    updatedAt: "2026-09-09",
  },
  {
    slug: "bnu-applied-psychology-045400",
    institution: "北京师范大学",
    school: "心理学部",
    programCode: "045400",
    title: "应用心理",
    discipline: "教育学",
    degreeType: "professional",
    region: "北京",
    studyMode: "全日制",
    examSubjects: ["思想政治理论（演示）", "英语（二）（演示）", "心理学专业综合（演示）"],
    targetYear: 2027,
    planLabel: "招生计划：演示信息",
    tuitionLabel: "学费：演示信息",
    evidenceState: "demo",
    sourceLabel: demoSourceLabel,
    updatedAt: "2026-09-09",
  },
  {
    slug: "bupt-computer-science-081200",
    institution: "北京邮电大学",
    school: "计算机学院",
    programCode: "081200",
    title: "计算机科学与技术",
    discipline: "工学",
    degreeType: "academic",
    region: "北京",
    studyMode: "全日制",
    examSubjects: ["思想政治理论（演示）", "英语（一）（演示）", "数学（一）（演示）"],
    targetYear: 2027,
    planLabel: "招生计划：演示信息",
    tuitionLabel: "学费：演示信息",
    evidenceState: "demo",
    sourceLabel: demoSourceLabel,
    updatedAt: "2026-09-09",
  },
  {
    slug: "fudan-chinese-language-literature-050100",
    institution: "复旦大学",
    school: "中国语言文学系",
    programCode: "050100",
    title: "中国语言文学",
    discipline: "文学",
    degreeType: "academic",
    region: "上海",
    studyMode: "全日制",
    examSubjects: ["思想政治理论（演示）", "英语（一）（演示）", "中国语言文学基础（演示）"],
    targetYear: 2027,
    planLabel: "招生计划：演示信息",
    tuitionLabel: "学费：演示信息",
    evidenceState: "demo",
    sourceLabel: demoSourceLabel,
    updatedAt: "2026-09-09",
  },
];

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

export function getDemoProgramBySlug(slug: string): DemoProgram | undefined {
  return demoPrograms.find((program) => program.slug === slug);
}
