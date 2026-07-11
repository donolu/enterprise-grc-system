"use client";
import { Card, Statistic, Progress, Typography, Space } from "antd";
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  MinusOutlined,
  RiseOutlined,
  FallOutlined
} from "@ant-design/icons";
import { useTheme } from "@/theme";

interface KPICardProps {
  title: string;
  value: number;
  suffix?: string;
  prefix?: string;
  trend?: {
    value: number;
    isPositive?: boolean;
    period?: string;
  };
  progress?: {
    percent: number;
    showInfo?: boolean;
    status?: 'success' | 'exception' | 'normal' | 'active';
    strokeColor?: string;
  };
  color?: string;
  icon?: React.ReactNode;
  loading?: boolean;
  extra?: React.ReactNode;
  onClick?: () => void;
  description?: string;
  size?: 'small' | 'default' | 'large';
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  suffix,
  prefix,
  trend,
  progress,
  color = "#2F6FED",
  icon,
  loading = false,
  extra,
  onClick,
  description,
  size = "default"
}) => {
  const { mode } = useTheme();
  const isDark = mode === 'dark';

  const cardStyle = {
    borderRadius: 12,
    boxShadow: isDark
      ? "0 6px 24px rgba(0,0,0,0.15)"
      : "0 6px 24px rgba(15,18,25,0.06)",
    border: `1px solid ${isDark ? '#2A3441' : '#E7EBF0'}`,
    cursor: onClick ? 'pointer' : 'default',
    transition: 'all 0.3s ease',
    background: isDark ? '#1E2532' : '#FFFFFF',
    minHeight: size === 'small' ? 140 : size === 'large' ? 200 : 160,
    display: 'flex',
    flexDirection: 'column' as const,
    ...(onClick && {
      '&:hover': {
        transform: 'translateY(-2px)',
        boxShadow: isDark
          ? "0 12px 32px rgba(0,0,0,0.2)"
          : "0 12px 32px rgba(15,18,25,0.08)",
      }
    })
  };

  const titleStyle = {
    fontSize: size === 'small' ? 13 : size === 'large' ? 15 : 14,
    color: isDark ? '#CBD5E1' : '#64748B',
    marginBottom: size === 'small' ? 8 : 12,
    fontWeight: 500,
  };

  const valueStyle = {
    fontSize: size === 'small' ? 20 : size === 'large' ? 32 : 24,
    fontWeight: 700,
    color: isDark ? '#F8FAFC' : '#0F172A',
    fontFamily: 'Inter, system-ui, sans-serif',
  };

  const renderTrendIndicator = () => {
    if (!trend) return null;

    const isPositive = trend.isPositive ?? trend.value > 0;
    const trendColor = isPositive ? '#0EB57D' : '#E5484D';
    const TrendIcon = isPositive ? ArrowUpOutlined : ArrowDownOutlined;

    return (
      <Space size={4} style={{ fontSize: 12 }}>
        <TrendIcon style={{ color: trendColor, fontSize: 10 }} />
        <span style={{ color: trendColor, fontWeight: 600 }}>
          {Math.abs(trend.value)}%
        </span>
        {trend.period && (
          <span style={{ color: isDark ? '#94A3B8' : '#94A3B8' }}>
            {trend.period}
          </span>
        )}
      </Space>
    );
  };

  return (
    <Card
      style={cardStyle}
      styles={{
        body: {
          padding: size === 'small' ? 16 : size === 'large' ? 28 : 20,
          minHeight: '100%',
          display: 'flex',
          flexDirection: 'column' as const,
        }
      }}
      loading={loading}
      onClick={onClick}
    >
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        height: '100%',
        flexGrow: 1
      }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            {icon && (
              <div style={{
                color: color,
                fontSize: size === 'small' ? 16 : size === 'large' ? 24 : 18
              }}>
                {icon}
              </div>
            )}
            <Typography.Text style={titleStyle}>
              {title}
            </Typography.Text>
          </div>

          <div style={{ marginBottom: description || progress || trend ? 12 : 0 }}>
            <Statistic
              value={value}
              suffix={suffix}
              prefix={prefix}
              valueStyle={valueStyle}
            />
          </div>

          {description && (
            <Typography.Text
              style={{
                fontSize: 12,
                color: isDark ? '#94A3B8' : '#94A3B8',
                display: 'block',
                marginBottom: 6
              }}
            >
              {description}
            </Typography.Text>
          )}

          {progress && (
            <Progress
              percent={progress.percent}
              showInfo={progress.showInfo}
              status={progress.status}
              strokeColor={progress.strokeColor || color}
              trailColor={isDark ? '#2A3441' : '#F1F5F9'}
              size={size === 'small' ? 'small' : 'default'}
              style={{ marginBottom: trend ? 6 : 0 }}
            />
          )}

          {trend && (
            <div style={{ marginTop: 4 }}>
              {renderTrendIndicator()}
            </div>
          )}
        </div>

        {extra && (
          <div style={{ marginLeft: 12 }}>
            {extra}
          </div>
        )}
      </div>
    </Card>
  );
};

// Preset KPI card variants
export const ComplianceKPICard: React.FC<Omit<KPICardProps, 'icon' | 'color'> & {
  compliancePercentage: number
}> = ({ compliancePercentage, ...props }) => (
  <KPICard
    {...props}
    icon={<RiseOutlined />}
    color="#0EB57D"
    progress={{
      percent: compliancePercentage,
      showInfo: false,
      status: compliancePercentage >= 80 ? 'success' : compliancePercentage >= 60 ? 'normal' : 'exception'
    }}
  />
);

export const PolicyKPICard: React.FC<Omit<KPICardProps, 'icon' | 'color'>> = (props) => (
  <KPICard
    {...props}
    icon={<RiseOutlined />}
    color="#FFB020"
  />
);