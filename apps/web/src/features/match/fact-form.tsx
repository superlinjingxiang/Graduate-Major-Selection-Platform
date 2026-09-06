"use client";

import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { browserCoreClient } from "../../lib/api-client";

type FactFormProps = Readonly<{
  offeringIds: readonly string[];
}>;

export function FactForm({ offeringIds }: FactFormProps) {
  const router = useRouter();
  const [scopeConfirmed, setScopeConfirmed] = useState(false);
  const [scopeError, setScopeError] = useState("");
  const mutation = useMutation({
    mutationFn: async (form: HTMLFormElement) => {
      const values = new FormData(form);
      const educationLevel = String(values.get("education_level") ?? "");
      const undergraduateMajor = String(values.get("undergraduate_major") ?? "").trim();
      const confirmedFacts: Record<string, unknown> = {
        admission_pathway: "unified_exam",
        region: "北京",
        study_mode: "full_time",
        target_year: 2027,
      };
      if (educationLevel) confirmedFacts.education_level = educationLevel;
      if (undergraduateMajor) confirmedFacts.undergraduate_major = undergraduateMajor;

      const factResult = await browserCoreClient.POST("/api/v1/fact-sets", {
        body: { confirmed_facts: confirmedFacts },
      });
      if (!factResult.data) throw new Error("Fact set creation failed");

      for (const offeringId of offeringIds) {
        const assessmentResult = await browserCoreClient.POST("/api/v1/eligibility-assessments", {
          body: {
            fact_revision: factResult.data.version,
            fact_set_id: factResult.data.fact_set_id,
            offering_id: offeringId,
          },
        });
        if (!assessmentResult.data) throw new Error("Eligibility assessment failed");
      }

      const comparisonResult = await browserCoreClient.POST("/api/v1/comparison-runs", {
        body: {
          fact_revision: factResult.data.version,
          fact_set_id: factResult.data.fact_set_id,
          offering_ids: [...offeringIds],
        },
      });
      if (!comparisonResult.data) throw new Error("Comparison creation failed");

      const snapshotResult = await browserCoreClient.POST("/api/v1/decision-snapshots", {
        body: { comparison_run_id: comparisonResult.data.comparison_run_id },
      });
      if (!snapshotResult.data) throw new Error("Snapshot creation failed");
      return snapshotResult.data.snapshot_id;
    },
    onSuccess: (snapshotId) => router.push(`/match/result/${snapshotId}`),
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!scopeConfirmed) {
      setScopeError("请先确认报考范围");
      return;
    }
    setScopeError("");
    mutation.mutate(event.currentTarget);
  }

  return (
    <form className="fact-form panel" onSubmit={submit}>
      <div>
        <p className="eyebrow">你的已确认信息</p>
        <h2>补充必要事实</h2>
        <p className="section-copy">不确定的项目可以留空；留空会保持未知，不会被系统自行推断。</p>
      </div>

      <div className="form-field">
        <label htmlFor="education-level">当前学历情况（可选）</label>
        <select className="input" id="education-level" name="education_level" defaultValue="">
          <option value="">未知 / 暂不确认</option>
          <option value="bachelor">本科或已获学士学位</option>
          <option value="equivalent">同等学力</option>
          <option value="other">其他已确认情况</option>
        </select>
      </div>

      <div className="form-field">
        <label htmlFor="undergraduate-major">本科专业（可选）</label>
        <Input id="undergraduate-major" name="undergraduate_major" placeholder="不确定时请留空" />
      </div>

      <label className="scope-confirmation" htmlFor="scope-confirmation">
        <input
          aria-describedby={scopeError ? "scope-error" : undefined}
          aria-invalid={Boolean(scopeError)}
          checked={scopeConfirmed}
          id="scope-confirmation"
          onChange={(event) => {
            setScopeConfirmed(event.target.checked);
            if (event.target.checked) setScopeError("");
          }}
          type="checkbox"
        />
        <span>我确认以上报考范围</span>
      </label>
      {scopeError ? (
        <p className="field-error" id="scope-error" role="alert">
          {scopeError}
        </p>
      ) : null}

      <Button disabled={mutation.isPending} type="submit">
        {mutation.isPending ? "正在生成…" : "生成资格快照"}
      </Button>
      {mutation.isError ? (
        <p className="form-notice form-notice-error" role="alert">
          暂时无法生成资格快照，请稍后重试。
        </p>
      ) : null}
    </form>
  );
}
