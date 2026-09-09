const footerLabels = ["数据来源", "纠错反馈", "隐私政策", "用户协议"] as const;

export function SiteFooter() {
  return (
    <footer className="global-footer">
      <div className="content-shell global-footer-inner">
        <p className="footer-brand">GradMatch</p>
        <ul className="footer-links" aria-label="站点信息">
          {footerLabels.map((label) => (
            <li key={label}>{label}</li>
          ))}
        </ul>
      </div>
    </footer>
  );
}
