import { PasswordLoginForm } from "../../../features/auth/auth-forms";

export default function LoginPage() {
  return (
    <>
      <p className="eyebrow">欢迎回来</p>
      <h1>使用密码登录</h1>
      <p>请使用已经完成邮箱验证的 GradMatch 账户。</p>
      <PasswordLoginForm />
      <p className="account-footnote">
        <a href="/account/code">改用验证码登录</a>
      </p>
    </>
  );
}
