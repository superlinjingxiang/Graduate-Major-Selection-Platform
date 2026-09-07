"use client";

import {
  type DecisionOutcome,
  type DecisionSnapshot,
  publicReasonCopy,
} from "@gradmatch/domain/decision";
import { type FormEvent, useState } from "react";

import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { browserCoreClient } from "../../lib/api-client";
import type { PilotOffering } from "../../lib/pilot-api";

const OUTCOME_COPY: Record<DecisionOutcome, Readonly<{ title: string; description: string }>> = {
  shortlist_ready: {
    title: "可以开始核对候选清单",
    description: "已确认信息支持继续核对这些项目；结论不代表排序或录取判断。",
  },
  no_suitable_offering: {
    title: "当前范围内没有可继续的项目",
    description: "已确认条件与本次固定范围不符，可以修改事实后重新生成。",
  },
  awaiting_official_information: {
    title: "等待 2027 官方信息",
    description: "目前缺少完成资格判断所需的官方信息，未知项继续保持未知。",
  },
  postpone_application: {
    title: "暂缓本轮申请准备",
    description: "当前已确认条件不适合继续本轮流程，可以在情况变化后重新核对。",
  },
};

type DecisionSummaryProps = Readonly<{
  offerings: readonly PilotOffering[];
  snapshot: DecisionSnapshot;
}>;

function offeringDecisionLabel(snapshot: DecisionSnapshot, offeringId: string) {
  if (snapshot.deferred.includes(offeringId)) return "资格状态：等待官方信息";
  if (snapshot.excluded.includes(offeringId)) return "资格状态：不符合已确认条件";
  if (snapshot.retained.includes(offeringId)) return "资格状态：符合已确认条件";
  return "资格状态：需要重新核对";
}

function publicValue(value: unknown): string {
  if (value === true) return "是";
  if (value === false) return "否";
  if (value === null) return "未提供";
  if (typeof value === "string" || typeof value === "number") return String(value);
  return JSON.stringify(value);
}

function CorrectionForm({ offerings }: Readonly<{ offerings: readonly PilotOffering[] }>) {
  const [state, setState] = useState<"idle" | "pending" | "success" | "error">("idle");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setState("pending");
    const values = new FormData(event.currentTarget);
    try {
      const result = await browserCoreClient.POST("/api/v1/corrections", {
        body: {
          explanation: String(values.get("explanation") ?? ""),
          field_key: String(values.get("field_key") ?? ""),
          offering_id: String(values.get("offering_id") ?? ""),
          proposed_source_url: String(values.get("proposed_source_url") ?? ""),
        },
      });
      setState(result.data ? "success" : "error");
    } catch {
      setState("error");
    }
  }

  return (
    <form className="correction-form" onSubmit={(event) => void submit(event)}>
      <div className="form-field">
        <label htmlFor="correction-offering">需要纠错的项目</label>
        <select className="input" id="correction-offering" name="offering_id" required>
          <option value="">请选择</option>
          {offerings.map((offering) => (
            <option key={offering.id} value={offering.id}>
              {offering.institution_name} · {offering.program_code} {offering.title}
            </option>
          ))}
        </select>
      </div>
      <div className="form-field">
        <label htmlFor="correction-field">需要纠错的信息</label>
        <select className="input" id="correction-field" name="field_key" required>
          <option value="">请选择</option>
          <option value="eligibility.requirements">报考资格条件</option>
          <option value="offering.program">专业或培养项目信息</option>
          <option value="offering.publication">招生信息发布状态</option>
        </select>
      </div>
      <div className="form-field">
        <label htmlFor="correction-source">官方来源链接</label>
        <Input id="correction-source" name="proposed_source_url" required type="url" />
      </div>
      <div className="form-field">
        <label htmlFor="correction-explanation">情况说明</label>
        <textarea
          className="input textarea"
          id="correction-explanation"
          minLength={10}
          name="explanation"
          required
          rows={4}
        />
      </div>
      <Button disabled={state === "pending"} type="submit" variant="secondary">
        {state === "pending" ? "正在提交…" : "确认提交纠错"}
      </Button>
      <div aria-live="polite">
        {state === "success" ? (
          <p className="form-notice form-notice-success">纠错已提交，我们会依据官方来源复核。</p>
        ) : null}
        {state === "error" ? (
          <p className="form-notice form-notice-error">纠错暂未提交，请稍后重试。</p>
        ) : null}
      </div>
    </form>
  );
}

export function DecisionSummary({ offerings, snapshot }: DecisionSummaryProps) {
  const [showCorrection, setShowCorrection] = useState(false);
  const outcome = OUTCOME_COPY[snapshot.outcome];

  return (
    <div className="decision-layout">
      <section className="decision-hero panel" aria-labelledby="decision-title">
        <p className="eyebrow">资格快照</p>
        <h1 id="decision-title">{outcome.title}</h1>
        <p className="decision-lede">{outcome.description}</p>
        <p className="evidence-freshness">证据时效：2027 招生年度；官方信息发布后需重新复核。</p>
      </section>

      <section className="decision-section panel" aria-labelledby="reason-title">
        <h2 id="reason-title">为什么是这个结论</h2>
        <ul className="plain-list">
          {snapshot.key_unknowns.map((reason) => (
            <li key={reason}>{publicReasonCopy(reason)}</li>
          ))}
          {snapshot.key_unknowns.length === 0 ? <li>当前没有待补充的关键未知项。</li> : null}
        </ul>
      </section>

      <section className="decision-section panel" aria-labelledby="offering-result-title">
        <h2 id="offering-result-title">项目核对结果</h2>
        <div className="result-offerings">
          {offerings.map((offering) => (
            <article className="result-offering" key={offering.id}>
              <h3>
                {offering.institution_name} · {offering.program_code} {offering.title}
              </h3>
              <p>{offeringDecisionLabel(snapshot, offering.id)}</p>
              <p>信息来源：学校官方招生信息（发布后复核）</p>
              <p>证据状态：2027 官方招生信息待发布</p>
            </article>
          ))}
        </div>
      </section>

      {snapshot.updates.length > 0 ? (
        <section className="decision-section panel" aria-labelledby="snapshot-updates-title">
          <h2 id="snapshot-updates-title">信息更新</h2>
          <div className="result-offerings">
            {snapshot.updates.map((update) => (
              <article className="result-offering" key={update.notification_id}>
                <h3>已复核：{update.corrected_field}</h3>
                <p>
                  原值：{publicValue(update.old_value)} → 新值：{publicValue(update.new_value)}
                </p>
                <p>
                  官方来源：
                  <a href={update.source.url} rel="noreferrer" target="_blank">
                    {update.source.title}
                  </a>
                </p>
                <p>来源位置：{update.source.locator || "请查看来源全文"}</p>
                <ul className="plain-list">
                  {update.next_actions.map((action) => (
                    <li key={action}>{action}</li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      <section className="decision-section panel" aria-labelledby="next-actions-title">
        <h2 id="next-actions-title">下一步行动</h2>
        <ul className="plain-list">
          {snapshot.next_actions.map((action) => (
            <li key={action}>{action}</li>
          ))}
        </ul>
        <Button
          aria-expanded={showCorrection}
          className="correction-toggle"
          onClick={() => setShowCorrection((visible) => !visible)}
          variant="quiet"
        >
          提交信息纠错
        </Button>
        {showCorrection ? <CorrectionForm offerings={offerings} /> : null}
      </section>
    </div>
  );
}
