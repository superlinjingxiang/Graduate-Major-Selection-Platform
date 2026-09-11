"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { type ComponentPropsWithoutRef, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { browserAuthClient } from "../../lib/api-client";

const emailSchema = z.object({
  email: z.email("请输入有效邮箱地址"),
});

const passwordSchema = emailSchema.extend({
  password: z.string().min(8, "密码至少需要 8 个字符"),
});

const codeSchema = z.object({
  code: z.string().min(6, "请输入邮件中的验证码"),
});

type EmailValues = z.infer<typeof emailSchema>;
type PasswordValues = z.infer<typeof passwordSchema>;
type CodeValues = z.infer<typeof codeSchema>;

const browserPath = { params: { path: { client: "browser" as const } } };

let browserAuthConfigRequest: Promise<void> | undefined;

function hasBrowserCsrfCookie() {
  return (
    typeof document !== "undefined" &&
    document.cookie.split(";").some((cookie) => cookie.trim().startsWith("csrftoken="))
  );
}

async function ensureBrowserAuthInitialized() {
  if (hasBrowserCsrfCookie()) return;

  browserAuthConfigRequest ??= browserAuthClient
    .GET("/_allauth/{client}/v1/config", browserPath)
    .then((result) => {
      if (!result.response.ok) throw new Error("browser authentication config failed");
    })
    .finally(() => {
      browserAuthConfigRequest = undefined;
    });

  await browserAuthConfigRequest;
}

function FormNotice({ kind, message }: Readonly<{ kind: "error" | "success"; message: string }>) {
  return (
    <p aria-live="polite" className={`form-notice form-notice-${kind}`}>
      {message}
    </p>
  );
}

function FormField({
  error,
  id,
  label,
  showPasswordToggle = false,
  type = "text",
  ...inputProps
}: Readonly<{
  error: string | undefined;
  id: string;
  label: string;
  showPasswordToggle?: boolean;
  type?: "email" | "password" | "text";
}> &
  ComponentPropsWithoutRef<typeof Input>) {
  const [isPasswordVisible, setIsPasswordVisible] = useState(false);
  const input = (
    <Input
      aria-invalid={Boolean(error)}
      id={id}
      type={showPasswordToggle && isPasswordVisible ? "text" : type}
      {...inputProps}
    />
  );

  return (
    <div className="form-field">
      <label htmlFor={id}>{label}</label>
      {showPasswordToggle ? (
        <div className="input-with-action">
          {input}
          <button
            aria-label={isPasswordVisible ? "隐藏密码" : "显示密码"}
            className="password-toggle"
            onClick={() => setIsPasswordVisible((visible) => !visible)}
            type="button"
          >
            <svg aria-hidden="true" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {isPasswordVisible ? (
                <>
                  <path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z" />
                  <circle cx="12" cy="12" r="2.5" />
                </>
              ) : (
                <>
                  <path d="m3 3 18 18" />
                  <path d="M10.6 6.2A10.6 10.6 0 0 1 12 6c6 0 9.5 6 9.5 6a17.5 17.5 0 0 1-3.2 3.8" />
                  <path d="M6.2 6.2A17.9 17.9 0 0 0 2.5 12s3.5 6 9.5 6c1.1 0 2.1-.2 3-.5" />
                  <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" />
                </>
              )}
            </svg>
          </button>
        </div>
      ) : (
        input
      )}
      {error ? <span className="field-error">{error}</span> : null}
    </div>
  );
}

export function SignupForm() {
  const form = useForm<PasswordValues>({ resolver: zodResolver(passwordSchema) });
  const mutation = useMutation({
    mutationFn: async (values: PasswordValues) => {
      await ensureBrowserAuthInitialized();
      const result = await browserAuthClient.POST("/_allauth/{client}/v1/auth/signup", {
        ...browserPath,
        body: values,
      });
      if (result.response.status !== 401) {
        throw new Error("signup failed");
      }
    },
  });

  return (
    <form
      className="auth-form"
      method="post"
      onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
    >
      <FormField
        error={form.formState.errors.email?.message}
        label="邮箱"
        {...form.register("email")}
        id="signup-email"
        type="email"
      />
      <FormField
        error={form.formState.errors.password?.message}
        label="密码"
        {...form.register("password")}
        id="signup-password"
        showPasswordToggle
        type="password"
      />
      <Button disabled={mutation.isPending} type="submit">
        创建账户
      </Button>
      {mutation.isSuccess ? (
        <FormNotice kind="success" message="验证邮件已发送，请完成邮箱验证。" />
      ) : null}
      {mutation.isError ? <FormNotice kind="error" message="请求未完成，请稍后重试。" /> : null}
    </form>
  );
}

export function PasswordLoginForm() {
  const form = useForm<PasswordValues>({ resolver: zodResolver(passwordSchema) });
  const mutation = useMutation({
    mutationFn: async (values: PasswordValues) => {
      await ensureBrowserAuthInitialized();
      const result = await browserAuthClient.POST("/_allauth/{client}/v1/auth/login", {
        ...browserPath,
        body: values,
      });
      if (result.response.status !== 200) {
        throw new Error("password login failed");
      }
    },
  });

  return (
    <form
      className="auth-form"
      method="post"
      onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
    >
      <FormField
        error={form.formState.errors.email?.message}
        label="邮箱"
        {...form.register("email")}
        id="login-email"
        type="email"
      />
      <FormField
        error={form.formState.errors.password?.message}
        label="密码"
        {...form.register("password")}
        id="login-password"
        showPasswordToggle
        type="password"
      />
      <Button disabled={mutation.isPending} type="submit">
        密码登录
      </Button>
      {mutation.isSuccess ? <FormNotice kind="success" message="登录成功。" /> : null}
      {mutation.isError ? <FormNotice kind="error" message="请求未完成，请稍后重试。" /> : null}
    </form>
  );
}

export function OneTimeCodeForm() {
  const [stage, setStage] = useState<"request" | "confirm" | "complete">("request");
  const emailForm = useForm<EmailValues>({ resolver: zodResolver(emailSchema) });
  const codeForm = useForm<CodeValues>({ resolver: zodResolver(codeSchema) });
  const requestMutation = useMutation({
    mutationFn: async (values: EmailValues) => {
      await ensureBrowserAuthInitialized();
      const result = await browserAuthClient.POST("/_allauth/{client}/v1/auth/code/request", {
        ...browserPath,
        body: values,
      });
      if (result.response.status !== 401) {
        throw new Error("code request failed");
      }
    },
    onSuccess: () => setStage("confirm"),
  });
  const confirmMutation = useMutation({
    mutationFn: async (values: CodeValues) => {
      await ensureBrowserAuthInitialized();
      const result = await browserAuthClient.POST("/_allauth/{client}/v1/auth/code/confirm", {
        ...browserPath,
        body: values,
      });
      if (result.response.status !== 200) {
        throw new Error("code confirmation failed");
      }
    },
    onSuccess: () => setStage("complete"),
  });

  if (stage === "complete") {
    return <FormNotice kind="success" message="登录成功。" />;
  }

  if (stage === "confirm") {
    return (
      <form
        key="confirm-code"
        className="auth-form"
        method="post"
        onSubmit={codeForm.handleSubmit((values) => confirmMutation.mutate(values))}
      >
        <FormField
          error={codeForm.formState.errors.code?.message}
          label="验证码"
          {...codeForm.register("code")}
          id="login-code"
        />
        <Button disabled={confirmMutation.isPending} type="submit">
          确认登录
        </Button>
        {confirmMutation.isError ? (
          <FormNotice kind="error" message="请求未完成，请稍后重试。" />
        ) : null}
      </form>
    );
  }

  return (
    <form
      key="request-code"
      className="auth-form"
      method="post"
      onSubmit={emailForm.handleSubmit((values) => requestMutation.mutate(values))}
    >
      <FormField
        error={emailForm.formState.errors.email?.message}
        label="邮箱"
        {...emailForm.register("email")}
        id="code-email"
        type="email"
      />
      <Button disabled={requestMutation.isPending} type="submit">
        发送登录验证码
      </Button>
      {requestMutation.isError ? (
        <FormNotice kind="error" message="请求未完成，请稍后重试。" />
      ) : null}
    </form>
  );
}

export function EmailVerificationForm({ initialKey }: Readonly<{ initialKey: string }>) {
  const mutation = useMutation({
    mutationFn: async () => {
      await ensureBrowserAuthInitialized();
      const result = await browserAuthClient.POST("/_allauth/{client}/v1/auth/email/verify", {
        ...browserPath,
        body: { key: initialKey },
      });
      if (result.response.status !== 200 && result.response.status !== 401) {
        throw new Error("email verification failed");
      }
    },
  });

  return (
    <div className="auth-form">
      <p>我们会使用邮件链接中的安全验证信息确认你的邮箱。</p>
      <Button disabled={mutation.isPending} onClick={() => mutation.mutate()}>
        确认邮箱
      </Button>
      {mutation.isSuccess ? (
        <FormNotice kind="success" message="邮箱已验证，现在可以登录。" />
      ) : null}
      {mutation.isError ? <FormNotice kind="error" message="请求未完成，请稍后重试。" /> : null}
    </div>
  );
}

export function LogoutButton() {
  const mutation = useMutation({
    mutationFn: async () => {
      await ensureBrowserAuthInitialized();
      const result = await browserAuthClient.DELETE(
        "/_allauth/{client}/v1/auth/session",
        browserPath,
      );
      if (result.response.status !== 401) {
        throw new Error("logout failed");
      }
    },
  });

  return (
    <div className="auth-form">
      <Button disabled={mutation.isPending} onClick={() => mutation.mutate()} variant="secondary">
        退出登录
      </Button>
      {mutation.isSuccess ? <FormNotice kind="success" message="你已安全退出。" /> : null}
      {mutation.isError ? <FormNotice kind="error" message="请求未完成，请稍后重试。" /> : null}
    </div>
  );
}
