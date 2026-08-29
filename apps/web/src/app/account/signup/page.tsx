import { SignupForm } from "../../../features/auth/auth-forms";

export default function SignupPage() {
  return (
    <>
      <p className="eyebrow">创建账户</p>
      <h1>从可信身份开始</h1>
      <p>使用邮箱注册。完成验证后，你可以使用密码或一次性验证码登录。</p>
      <SignupForm />
      <p className="account-footnote">
        已有账户？<a href="/account/login">密码登录</a>
      </p>
    </>
  );
}
