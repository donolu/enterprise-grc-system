"use client";

import { Progress, Typography } from "antd";

const { Text } = Typography;

export interface FrameworkReadinessItem {
  name: string;
  completionRate: number;
  averageScore?: number;
  overdue?: number;
}

export function ControlCoverage({ total, automated }: { total: number; automated: number }) {
  const percentage = total > 0 ? Math.round((automated / total) * 100) : 0;
  return (
    <section className="grc-viz-panel" aria-labelledby="control-coverage-title">
      <div className="grc-viz-heading">
        <div>
          <span className="section-kicker">CONTROL ENVIRONMENT</span>
          <h3 id="control-coverage-title">Control coverage</h3>
        </div>
        <strong className="grc-viz-score">{percentage}%</strong>
      </div>
      <Progress percent={percentage} showInfo={false} strokeColor="#0b8f84" trailColor="#e5efed" />
      <div className="grc-viz-caption"><span>{automated} automated controls</span><span>{total} total controls</span></div>
    </section>
  );
}

export function FrameworkReadiness({ frameworks }: { frameworks: FrameworkReadinessItem[] }) {
  return (
    <section className="grc-viz-panel" aria-labelledby="framework-readiness-title">
      <div className="grc-viz-heading">
        <div>
          <span className="section-kicker">ASSURANCE LANDSCAPE</span>
          <h3 id="framework-readiness-title">Framework readiness</h3>
        </div>
        <Text type="secondary">{frameworks.length} frameworks</Text>
      </div>
      {frameworks.length === 0 ? <div className="grc-viz-empty">No framework assessments yet.</div> : <div className="framework-readiness-list">{frameworks.map((framework) => <div className="framework-readiness-item" key={framework.name}><div className="framework-readiness-label"><strong>{framework.name}</strong><span>{Math.round(framework.completionRate)}%</span></div><Progress percent={Math.round(framework.completionRate)} showInfo={false} strokeColor={framework.completionRate >= 80 ? "#0b8f84" : "#d29c4c"} trailColor="#e9efed" /><div className="framework-readiness-meta"><span>Score {framework.averageScore == null ? "—" : `${Math.round(framework.averageScore)}%`}</span><span>{framework.overdue ?? 0} overdue</span></div></div>)}</div>}
    </section>
  );
}

export function TrendSparkline({ values, label }: { values: number[]; label: string }) {
  if (values.length < 2) return <div className="grc-viz-empty">Not enough trend data.</div>;
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = Math.max(max - min, 1);
  const points = values.map((value, index) => `${(index / (values.length - 1)) * 100},${36 - ((value - min) / range) * 30}`).join(" ");
  return <svg className="grc-sparkline" viewBox="0 0 100 40" preserveAspectRatio="none" role="img" aria-label={label}><polyline points={points} fill="none" stroke="#0b8f84" strokeWidth="2.4" vectorEffect="non-scaling-stroke" /></svg>;
}

export function TrendPanel({ values, label, heading }: { values: number[]; label: string; heading: string }) {
  return <section className="grc-viz-panel" aria-labelledby={`${heading.toLowerCase().replaceAll(" ", "-")}-title`}><div className="grc-viz-heading"><div><span className="section-kicker">MOVEMENT</span><h3 id={`${heading.toLowerCase().replaceAll(" ", "-")}-title`}>{heading}</h3></div></div><TrendSparkline values={values} label={label} /></section>;
}
