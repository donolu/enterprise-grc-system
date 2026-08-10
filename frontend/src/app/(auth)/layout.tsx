export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <main className="auth-shell">
      <section className="auth-intro" aria-label="GRCsuite introduction">
        <div>
          <div className="auth-brand"><span className="auth-brand-mark">G</span> GRCsuite</div>
          <p className="auth-kicker">Governance, risk and compliance</p>
          <h1>Make evidence<br /><em>decision-ready.</em></h1>
          <p className="auth-intro-copy">One calm workspace for the controls, risks and actions that keep your organisation moving.</p>
        </div>
        <div className="auth-intro-foot"><span className="auth-status-dot" aria-hidden="true" /><span>Secure workspace access</span></div>
      </section>
      <section className="auth-panel"><div className="auth-panel-inner">{children}</div></section>
    </main>
  );
}
