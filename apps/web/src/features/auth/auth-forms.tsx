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
  password: z.string().min(12, "密码至少需要 12 个字符"),
});

const codeSchema = z.object({
  code: z.string().min(6, "请输入邮件中的验证码"),
});

type EmailValues = z.infer<typeof emailSchema>;
type PasswordValues = z.infer<typeof passwordSchema>;
type CodeValues = z.infer<typeof codeSchema>;

const browserPath = { params: { path: { client: "browser" as const } } };

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
  type = "text",
  ...inputProps
}: Readonly<{
  error: string | undefined;
  id: string;
  label: string;
  type?: "email" | "password" | "text";
}> &
  ComponentPropsWithoutRef<typeof Input>) {
  return (
    <div className="form-field">
      <label htmlFor={id}>{label}</label>
      <Input aria-invalid={Boolean(error)} id={id} type={type} {...inputProps} />
      {error ? <span className="field-error">{error}</span> : null}
    </div>
  );
}

export function SignupForm() {
  const form = useForm<PasswordValues>({ resolver: zodResolver(passwordSchema) });
  const mutation = useMutation({
    mutationFn: async (values: PasswordValues) => {
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
    <form className="auth-form" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
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
    <form className="auth-form" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
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
