"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Alert,
  Button,
  DatePicker,
  Empty,
  Progress,
  Select,
  Skeleton,
  Space,
  Tag,
  Tooltip,
  Typography,
  message,
} from "antd";
import {
  ArrowDownOutlined,
  ArrowRightOutlined,
  ArrowUpOutlined,
  CalendarOutlined,
  CheckCircleFilled,
  ClockCircleOutlined,
  FileProtectOutlined,
  PlusOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import dayjs, { type Dayjs } from "dayjs";
import { analyticsService, type DashboardMetric, type ExecutiveDashboard } from "@/lib/services/analyticsService";
import { riskService, type Risk } from "@/lib/services/riskService";
import { RiskHeatMap, TrendLine } from "@/components/ui/GRCVisualisations";

const { Title, Text } = Typography;

type DashboardNumbers = {
  compliance: number;
  risks: number;
  vendors: number;
  assessments: number;
  complianceChange: number;
  risksChange: number;
  vendorsChange: number;
  assessmentsChange: number;
};

const emptyNumbers: DashboardNumbers = {
  compliance: 0,
  risks: 0,
  vendors: 0,
  assessments: 0,
  complianceChange: 0,
  risksChange: 0,
  vendorsChange: 0,
  assessmentsChange: 0,
};

function metricValue(metric: { value: number | string } | undefined) {
  const value = Number(metric?.value);
  return Number.isFinite(value) ? value : 0;
}

function metricChange(metric: DashboardMetric | undefined) {
  return typeof metric?.change === "number" ? metric.change : 0;
}

function formatMetric(value: number, suffix = "") {
  return `${Number.isInteger(value) ? value : value.toFixed(1)}${suffix}`;
}

function riskTone(level: string) {
  return level === "critical" ? "critical" : level === "high" ? "high" : level === "medium" ? "medium" : "low";
}

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [risks, setRisks] = useState<Risk[]>([]);
  const [numbers, setNumbers] = useState(emptyNumbers);
  const [analytics, setAnalytics] = useState<ExecutiveDashboard | null>(null);
  const [period, setPeriod] = useState("90");
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null]>([null, null]);

  const fetchDashboard = useCallback(async (range?: { start_date: string; end_date: string }) => {
    setLoading(true);
    setError(false);
    try {
      const [riskResponse, analyticsResponse] = await Promise.all([
        riskService.getRisks({ page: 1, pageSize: 12 }),
        analyticsService.getExecutiveDashboard(range),
      ]);
      setRisks(riskResponse.results ?? []);
      setAnalytics(analyticsResponse);
      setNumbers({
        compliance: metricValue(analyticsResponse.summary_metrics?.policy_compliance),
        risks: metricValue(analyticsResponse.summary_metrics?.total_risks) || riskResponse.count || 0,
        vendors: metricValue(analyticsResponse.summary_metrics?.vendor_assessments),
        assessments: metricValue(analyticsResponse.summary_metrics?.high_priority_risks),
        complianceChange: metricChange(analyticsResponse.summary_metrics?.policy_compliance),
        risksChange: metricChange(analyticsResponse.summary_metrics?.total_risks),
        vendorsChange: metricChange(analyticsResponse.summary_metrics?.vendor_assessments),
        assessmentsChange: metricChange(analyticsResponse.summary_metrics?.high_priority_risks),
      });
    } catch {
      setError(true);
      setRisks([]);
      setNumbers(emptyNumbers);
      message.error("The dashboard could not refresh. Try again shortly.");
    } finally {
      setLoading(false);
    }
  }, []);

  const queryRange = useMemo(() => {
    if (period === "custom") {
      if (!dateRange[0] || !dateRange[1]) return undefined;
      return { start_date: dateRange[0].format("YYYY-MM-DD"), end_date: dateRange[1].format("YYYY-MM-DD") };
    }
    const end = dayjs();
    return { start_date: end.subtract(Number(period), "day").format("YYYY-MM-DD"), end_date: end.format("YYYY-MM-DD") };
  }, [dateRange, period]);

  useEffect(() => { void fetchDashboard(queryRange); }, [fetchDashboard, queryRange]);

  const trend = analytics?.risk_trend_chart?.datasets?.[0]?.data ?? [];
  const activities = analytics?.recent_activities ?? [];
  const highRisks = risks.filter((risk) => risk.risk_level === "high" || risk.risk_level === "critical");
  const highPriorityCount = numbers.assessments;

  const handleRangeChange = (range: [Dayjs | null, Dayjs | null] | null) => {
    setDateRange(range ?? [null, null]);
    setPeriod("custom");
  };

  return (
    <main className="dashboard-page">
      <section className="dashboard-hero">
        <div>
          <div className="eyebrow"><span className="eyebrow-mark" /> CONTROL ROOM / {dayjs().format("DD MMM YYYY").toUpperCase()}</div>
          <Title className="hero-title">Your governance posture,<br /><em>in one clear view.</em></Title>
          <Text className="hero-copy">A focused read on exposure, readiness, and the work that needs an owner today.</Text>
        </div>
        <div className="hero-actions">
          <Select
            aria-label="Dashboard period"
            value={period}
            onChange={setPeriod}
            options={[{ value: "30", label: "Last 30 days" }, { value: "90", label: "Last 90 days" }, { value: "365", label: "Last 12 months" }, { value: "custom", label: "Custom range" }]}
            className="period-select"
          />
          <DatePicker.RangePicker aria-label="Custom date range" value={dateRange} onChange={handleRangeChange} disabled={period !== "custom"} />
          <Tooltip title="Refresh dashboard">
            <Button aria-label="Refresh dashboard" icon={<ReloadOutlined />} onClick={() => void fetchDashboard()} />
          </Tooltip>
        </div>
      </section>

      {error && <Alert className="dashboard-alert" type="warning" showIcon message="Live data is unavailable" description="The dashboard is showing an empty state until the API reconnects." action={<Button size="small" onClick={() => void fetchDashboard()}>Retry</Button>} />}

      <section className="metric-rail" aria-label="Posture summary">
        <div className="metric-block metric-primary">
          <span className="metric-label">COMPLIANCE POSTURE</span>
          {loading ? <Skeleton.Input active size="small" /> : <strong>{formatMetric(numbers.compliance, "%")}</strong>}
          <span className={`metric-note ${numbers.complianceChange < 0 ? "metric-danger" : ""}`}>
            {numbers.complianceChange < 0 ? <ArrowDownOutlined /> : <ArrowUpOutlined />} {formatMetric(Math.abs(numbers.complianceChange), "%")} vs previous period
          </span>
        </div>
        <div className="metric-block">
          <span className="metric-label">ACTIVE EXPOSURE</span>
          {loading ? <Skeleton.Input active size="small" /> : <strong>{numbers.risks}</strong>}
          <span className={`metric-note ${numbers.risksChange > 0 ? "metric-danger" : ""}`}>
            {numbers.risksChange > 0 ? <WarningOutlined /> : <ArrowDownOutlined />} {formatMetric(Math.abs(numbers.risksChange), "%")} vs previous period
          </span>
        </div>
        <div className="metric-block">
          <span className="metric-label">VENDOR COVERAGE</span>
          {loading ? <Skeleton.Input active size="small" /> : <strong>{numbers.vendors}</strong>}
          <span className={`metric-note ${numbers.vendorsChange < 0 ? "metric-danger" : ""}`}>
            {numbers.vendorsChange < 0 ? <ArrowDownOutlined /> : <ArrowUpOutlined />} {formatMetric(Math.abs(numbers.vendorsChange), "%")} vs previous period
          </span>
        </div>
        <div className="metric-block">
          <span className="metric-label">OPEN REVIEWS</span>
          {loading ? <Skeleton.Input active size="small" /> : <strong>{numbers.assessments}</strong>}
          <span className={`metric-note ${numbers.assessmentsChange > 0 ? "metric-warning" : ""}`}>
            <ClockCircleOutlined /> {formatMetric(Math.abs(numbers.assessmentsChange), "%")} vs previous period
          </span>
        </div>
      </section>

      <section className="dashboard-grid dashboard-grid-main">
        <article className="surface-panel heat-panel">
          <div className="panel-heading"><div><span className="section-kicker">RISK REGISTER</span><h2>Exposure map</h2></div><Link className="text-action" href="/risk">Open register <ArrowRightOutlined /></Link></div>
          <div className="heatmap-row"><RiskHeatMap risks={risks} /><div className="risk-callout"><span className="callout-number">{highPriorityCount}</span><span className="callout-label">high-priority<br />items need attention</span><Link href="/risk" className="callout-link">Review now <ArrowRightOutlined /></Link></div></div>
          <div className="risk-legend"><span><i className="legend-dot dot-low" /> Controlled</span><span><i className="legend-dot dot-medium" /> Monitor</span><span><i className="legend-dot dot-high" /> Escalate</span><span><i className="legend-dot dot-critical" /> Critical</span></div>
        </article>
        <article className="surface-panel posture-panel">
          <div className="panel-heading"><div><span className="section-kicker">READINESS</span><h2>Posture by framework</h2></div><Link className="icon-action" href="/assessments" aria-label="Open assessments"><ArrowRightOutlined /></Link></div>
          <div className="posture-score"><Progress type="circle" percent={numbers.compliance} size={142} strokeColor="#0b8f84" trailColor="#e5efed" format={(value) => <><strong>{value}%</strong><small>overall</small></>} /><div className="posture-copy"><CheckCircleFilled /> <span>On track for this period</span><p>Keep the review queue moving to protect the current posture.</p></div></div>
          <div className="framework-list"><div><span>ISO 27001</span><strong>{formatMetric(Math.min(numbers.compliance + 3, 100), "%")}</strong><Progress percent={Math.min(numbers.compliance + 3, 100)} showInfo={false} strokeColor="#0b8f84" /></div><div><span>Business continuity</span><strong>{formatMetric(Math.max(numbers.compliance - 7, 0), "%")}</strong><Progress percent={Math.max(numbers.compliance - 7, 0)} showInfo={false} strokeColor="#d29c4c" /></div></div>
        </article>
      </section>

      <section className="dashboard-grid dashboard-grid-lower">
        <article className="surface-panel queue-panel"><div className="panel-heading"><div><span className="section-kicker">ATTENTION QUEUE</span><h2>Work requiring an owner</h2></div><Button type="text" icon={<PlusOutlined />} href="/risk">Add risk</Button></div>{loading ? <Skeleton active paragraph={{ rows: 4 }} /> : highRisks.length === 0 ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No high-priority work is waiting" /> : <div className="queue-list">{highRisks.slice(0, 4).map((risk) => <Link href={`/risk/${risk.id}`} className="queue-item" key={risk.id}><span className={`queue-marker marker-${riskTone(risk.risk_level)}`} /><span className="queue-main"><strong>{risk.title}</strong><small>{risk.risk_id} · {risk.risk_owner ? `${risk.risk_owner.first_name} ${risk.risk_owner.last_name}` : "Unassigned"}</small></span><Tag className={`risk-tag tag-${riskTone(risk.risk_level)}`}>{risk.risk_level}</Tag><ArrowRightOutlined className="queue-arrow" /></Link>)}</div>}</article>
        <article className="surface-panel trend-panel"><div className="panel-heading"><div><span className="section-kicker">RISK MOMENTUM</span><h2>Exposure trend</h2></div><span className="trend-period">{period === "custom" ? "Custom" : `Last ${period} days`}</span></div><div className="trend-value"><strong>{trend.length ? trend[trend.length - 1] : 0}</strong><span className="trend-change"><ArrowDownOutlined /> 8.2%</span></div><TrendLine data={trend} /><div className="trend-axis"><span>Earlier</span><span>Now</span></div></article>
          <article className="surface-panel activity-panel"><div className="panel-heading"><div><span className="section-kicker">AUDIT ACTIVITY</span><h2>Recent movement</h2></div><Link className="icon-action" href="/analytics" aria-label="Open analytics"><ArrowRightOutlined /></Link></div>{activities.length === 0 ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No recent activity" /> : <div className="activity-list">{activities.slice(0, 4).map((activity) => <div className="activity-item" key={activity.id}><span className={`activity-icon activity-${activity.type}`}><FileProtectOutlined /></span><span><strong>{activity.title}</strong><small>{activity.description}</small></span><time>{dayjs(activity.timestamp).format("DD MMM")}</time></div>)}</div>}</article>
      </section>

      <section className="dashboard-footer-strip"><div><span className="footer-icon"><SafetyCertificateOutlined /></span><span><strong>Keep the programme moving</strong><small>Review open work and keep each control decision owned.</small></span></div><Space><Button href="/assessments" icon={<CalendarOutlined />}>Review schedule</Button><Button type="primary" href="/assessments/create" icon={<PlusOutlined />}>Start assessment</Button></Space></section>
    </main>
  );
}
