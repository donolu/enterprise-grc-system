"use client";

import { useMemo } from "react";
import { Progress, Tooltip, Typography } from "antd";

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
      <Progress percent={percentage} showInfo={false} strokeColor="#0b8f84" railColor="#e5efed" />
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
      {frameworks.length === 0 ? <div className="grc-viz-empty">No framework assessments yet.</div> : <div className="framework-readiness-list">{frameworks.map((framework) => <div className="framework-readiness-item" key={framework.name}><div className="framework-readiness-label"><strong>{framework.name}</strong><span>{Math.round(framework.completionRate)}%</span></div><Progress percent={Math.round(framework.completionRate)} showInfo={false} strokeColor={framework.completionRate >= 80 ? "#0b8f84" : "#d29c4c"} railColor="#e9efed" /><div className="framework-readiness-meta"><span>Score {framework.averageScore == null ? "—" : `${Math.round(framework.averageScore)}%`}</span><span>{framework.overdue ?? 0} overdue</span></div></div>)}</div>}
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

type RiskPosition = { impact: number; likelihood: number };

export function RiskHeatMap({ risks }: { risks: RiskPosition[] }) {
  const cells = useMemo(() => {
    const counts = new Map<string, number>();
    risks.forEach((risk) => {
      const key = `${risk.impact}-${risk.likelihood}`;
      counts.set(key, (counts.get(key) ?? 0) + 1);
    });
    return Array.from({ length: 25 }, (_, index) => {
      const impact = Math.floor(index / 5) + 1;
      const likelihood = (index % 5) + 1;
      return { impact, likelihood, count: counts.get(`${impact}-${likelihood}`) ?? 0 };
    });
  }, [risks]);

  return (
    <div className="heatmap-wrap">
      <div className="heatmap-y-label">IMPACT</div>
      <div className="heatmap-content">
        <div className="heatmap-grid" role="group" aria-label="Risk heat map showing impact against likelihood">
          {cells.map((cell) => {
            const label = `${cell.count} risk${cell.count === 1 ? "" : "s"}, impact ${cell.impact}, likelihood ${cell.likelihood}`;
            return <Tooltip key={`${cell.impact}-${cell.likelihood}`} title={label}><div className={`heat-cell heat-${Math.min(cell.impact * cell.likelihood, 25)}`} role="img" aria-label={label}>{cell.count > 0 ? cell.count : ""}</div></Tooltip>;
          })}
        </div>
        <div className="heatmap-x-axis"><span>Low</span><span>LIKELIHOOD</span><span>High</span></div>
      </div>
    </div>
  );
}

export function TrendLine({ data, colour = "#0b8f84" }: { data: number[]; colour?: string }) {
  if (!data.length) return <div className="trend-empty">No trend data</div>;
  const max = Math.max(...data, 1);
  const points = data.map((value, index) => `${(index / Math.max(data.length - 1, 1)) * 100},${36 - (value / max) * 30}`).join(" ");
  return <svg className="trend-line" viewBox="0 0 100 40" preserveAspectRatio="none" aria-label="Trend line" role="img"><polyline points={points} fill="none" stroke={colour} strokeWidth="2.4" vectorEffect="non-scaling-stroke" /></svg>;
}
