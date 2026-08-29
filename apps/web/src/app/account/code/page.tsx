import { OneTimeCodeForm } from "../../../features/auth/auth-forms";

export default function OneTimeCodePage() {
  return (
    <>
      <p className="eyebrow">无密码登录</p>
      <h1>使用邮箱验证码</h1>
      <p>验证码会发送到已验证邮箱；它不会替代你的账户安全设置。</p>
      <OneTimeCodeForm />
      <p className="account-footnote">
        <a href="/account/login">改用密码登录</a>
      </p>
    </>
  );
}
