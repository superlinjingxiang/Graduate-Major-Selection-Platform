"use client";

import Link from "next/link";
import { type FormEvent, useId, useState } from "react";

import { PasswordLoginForm } from "./auth-forms";
import { sanitizeNextPath } from "./login-path";

type LoginMethod = "wechat" | "phone";
type PhoneStage = "request" | "confirm" | "complete";

export function DemoLogin({ nextPath }: Readonly<{ nextPath: string }>) {
  const safeNextPath = sanitizeNextPath(nextPath);
  const [method, setMethod] = useState<LoginMethod>("wechat");
  const [phone, setPhone] = useState("");
  const [phoneStage, setPhoneStage] = useState<PhoneStage>("request");
  const [code, setCode] = useState("");
  const [phoneError, setPhoneError] = useState("");
  const [socialNotice, setSocialNotice] = useState("");
  const tabId = useId();

  function requestDemoCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!/^\d{11}$/u.test(phone)) {
      setPhoneError("请输入 11 位手机号");
      return;
    }
    setPhoneError("");
    setPhoneStage("confirm");
  }

  function confirmDemoCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (code !== "123456") {
      setPhoneError("演示验证码为 123456");
      return;
    }
    setPhoneError("");
    setPhoneStage("complete");
  }

  return (
    <div className="demo-login">
      <aside className="login-context" aria-label="登录说明">
        <p className="eyebrow">GradMatch 账户</p>
        <h1>登录后继续你的选择</h1>
        <p>保存院校与专业对比，在不同设备上接着完成自己的决策。</p>
        <ol className="login-benefits">
          <li>
            <span>01</span>
            <div>
              <strong>保存临时对比</strong>
              <p>把分散的招生项目留在同一张对比表中。</p>
            </div>
          </li>
          <li>
            <span>02</span>
            <div>
              <strong>持续跟踪变化</strong>
              <p>正式数据接入后，可关注简章、目录与计划更新。</p>
            </div>
          </li>
        </ol>
        <p className="login-demo-boundary">演示模式不会发送短信或发起第三方授权</p>
      </aside>

      <section className="login-methods" aria-label="选择登录方式">
        <div className="login-tabs" role="tablist" aria-label="主要登录方式">
          <button
            aria-controls={`${tabId}-wechat`}
            aria-selected={method === "wechat"}
            id={`${tabId}-wechat-tab`}
            onClick={() => setMethod("wechat")}
            role="tab"
            type="button"
          >
            微信扫码
          </button>
          <button
            aria-controls={`${tabId}-phone`}
            aria-selected={method === "phone"}
            id={`${tabId}-phone-tab`}
            onClick={() => setMethod("phone")}
            role="tab"
            type="button"
          >
            手机验证码
          </button>
        </div>

        {method === "wechat" ? (
          <div
            aria-labelledby={`${tabId}-wechat-tab`}
            className="login-tab-panel wechat-panel"
            id={`${tabId}-wechat`}
            role="tabpanel"
          >
            <div aria-label="演示二维码，不可扫描" className="demo-qr" role="img">
              <span aria-hidden="true" />
            </div>
            <strong>演示二维码</strong>
            <p>正式版本将在这里接入微信开放平台。当前二维码不可扫描。</p>
            <button
              className="social-demo-button"
              onClick={() => setSocialNotice("Demo 未连接第三方服务")}
              type="button"
            >
              查看微信登录说明
            </button>
          </div>
        ) : (
          <div
            aria-labelledby={`${tabId}-phone-tab`}
            className="login-tab-panel phone-panel"
            id={`${tabId}-phone`}
            role="tabpanel"
          >
            {phoneStage === "request" ? (
              <form className="demo-phone-form" onSubmit={requestDemoCode}>
                <label htmlFor={`${tabId}-phone-input`}>手机号</label>
                <input
                  autoComplete="tel"
                  className="input"
                  id={`${tabId}-phone-input`}
                  inputMode="numeric"
                  maxLength={11}
                  onChange={(event) => setPhone(event.target.value.replace(/\D/gu, ""))}
                  placeholder="请输入 11 位手机号"
                  value={phone}
                />
                <button className="button button-primary" type="submit">
                  获取演示验证码
                </button>
              </form>
            ) : null}

            {phoneStage === "confirm" ? (
              <form className="demo-phone-form" onSubmit={confirmDemoCode}>
                <p className="demo-code-ready" role="status">
                  演示验证码已就绪
                </p>
                <p className="demo-phone-caption">
                  已发送至 {phone.slice(0, 3)}****{phone.slice(-4)}
                </p>
                <label htmlFor={`${tabId}-code-input`}>验证码</label>
                <input
                  autoComplete="one-time-code"
                  className="input"
                  id={`${tabId}-code-input`}
                  inputMode="numeric"
                  maxLength={6}
                  onChange={(event) => setCode(event.target.value.replace(/\D/gu, ""))}
                  placeholder="输入 123456"
                  value={code}
                />
                <button className="button button-primary" type="submit">
                  完成演示登录
                </button>
                <button
                  className="login-text-button"
                  onClick={() => {
                    setPhoneStage("request");
                    setCode("");
                    setPhoneError("");
                  }}
                  type="button"
                >
                  修改手机号
                </button>
              </form>
            ) : null}

            {phoneStage === "complete" ? (
              <div className="demo-login-complete" role="status">
                <span aria-hidden="true">✓</span>
                <strong>演示登录已完成</strong>
                <p>本次仅演示页面流程，没有创建真实会话。</p>
                <Link className="button button-primary" href={safeNextPath}>
                  {safeNextPath === "/compare" ? "继续返回对比" : "继续浏览"}
                </Link>
              </div>
            ) : null}

            {phoneError ? (
              <p aria-live="polite" className="form-notice form-notice-error">
                {phoneError}
              </p>
            ) : null}
          </div>
        )}

        {socialNotice ? (
          <p aria-live="polite" className="social-demo-notice">
            {socialNotice}
          </p>
        ) : null}

        <details className="other-login-methods" open>
          <summary>其他登录方式</summary>
          <div className="other-login-content">
            <button
              className="social-demo-button social-demo-button-qq"
              onClick={() => setSocialNotice("Demo 未连接第三方服务")}
              type="button"
            >
              <span aria-hidden="true">Q</span>
              QQ 登录（演示）
            </button>
            <Link className="social-demo-button" href="/account/code">
              邮箱验证码登录
            </Link>
            <div className="email-password-login">
              <h2>邮箱密码登录</h2>
              <PasswordLoginForm />
            </div>
          </div>
        </details>

        <p className="login-legal">
          登录即表示你同意用户协议与隐私政策。还没有账户？{" "}
          <Link href="/account/signup">创建账户</Link>
        </p>
      </section>
    </div>
  );
}
