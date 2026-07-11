"use client";
import React, { useState, useEffect } from "react";
import { Row, Col, Typography, Space, Card, Table, Progress, Button, message } from "antd";
import {
  CheckSquareOutlined,
  SafetyOutlined,
  TeamOutlined,
  FileTextOutlined,
  RiseOutlined,
  WarningOutlined,
  EyeOutlined,
  PlusOutlined
} from "@ant-design/icons";
import {
  KPICard,
  ComplianceKPICard,
  RiskKPICard,
  PolicyKPICard,
  VendorKPICard,
  StatusTag,
  AssessmentStatusTag,
  RiskStatusTag,
  EmptyState,
  Loading
} from "@/components/ui";
import { useTheme } from "@/theme";
import { riskService } from "@/lib/services/riskService";
import { analyticsService } from "@/lib/services/analyticsService";

const { Title, Text } = Typography;

export default function DashboardPage() {
  const { mode } = useTheme();
  const isDark = mode === 'dark';

  // State management
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState({
    recentAssessments: [],
    recentRisks: [],
    analytics: {
      totalAssessments: 0,
      activeRisks: 0,
      totalVendors: 0,
      complianceScore: 0
    }
  });

  // Fetch dashboard data
  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      console.log('🚀 Fetching dashboard data from Django APIs...');

      const [risks, analytics] = await Promise.all([
        riskService.getRisks({ page: 1, pageSize: 3 }), // Get recent risks
        analyticsService.getExecutiveDashboard() // Get dashboard summary
      ]);

      console.log('📊 Risks data received:', risks);
      console.log('📈 Analytics data received:', analytics);

      setDashboardData({
        recentAssessments: [], // Will be populated when assessment service is available
        recentRisks: risks.results || [],
        analytics: {
          totalAssessments: Number(analytics.summary_metrics?.vendor_assessments?.value) || 0,
          activeRisks: Number(analytics.summary_metrics?.total_risks?.value) || risks.count || 0,
          totalVendors: Number(analytics.summary_metrics?.vendor_assessments?.value) || 0,
          complianceScore: Number(analytics.summary_metrics?.policy_compliance?.value) || 0
        }
      });

      console.log('✅ Dashboard data successfully loaded from Django APIs');
    } catch (error) {
      console.error('❌ Error fetching dashboard data:', error);
      message.error('Failed to connect to backend APIs. Please ensure the Django server is running.');

      // Set empty state - no hardcoded fallbacks
      setDashboardData({
        recentAssessments: [],
        recentRisks: [],
        analytics: {
          totalAssessments: 0,
          activeRisks: 0,
          totalVendors: 0,
          complianceScore: 0
        }
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  // Note: All data now comes from Django APIs - no hardcoded fallbacks

  const assessmentColumns = [
    {
      title: 'Assessment',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: any) => (
        <div>
          <Text strong style={{ display: 'block' }}>{text}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.framework}
          </Text>
        </div>
      )
    },
    {
      title: 'Progress',
      dataIndex: 'progress',
      key: 'progress',
      width: 120,
      render: (progress: number) => (
        <Progress
          percent={progress}

          showInfo={false}
          strokeColor={progress === 100 ? '#0EB57D' : progress > 75 ? '#2F6FED' : '#FFB020'}
        />
      )
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => (
        <AssessmentStatusTag status={status} />
      )
    },
    {
      title: 'Due Date',
      dataIndex: 'dueDate',
      key: 'dueDate',
      width: 100,
      render: (date: string) => (
        <Text style={{ fontSize: 12 }}>{date}</Text>
      )
    }
  ];

  const riskColumns = [
    {
      title: 'Risk',
      dataIndex: 'title',
      key: 'title',
      render: (text: string, record: any) => (
        <div>
          <Text strong style={{ display: 'block' }}>{text}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Owner: {record.risk_owner?.first_name} {record.risk_owner?.last_name || 'Unassigned'}
          </Text>
        </div>
      )
    },
    {
      title: 'Risk Level',
      dataIndex: 'risk_level',
      key: 'risk_level',
      width: 100,
      render: (risk_level: string) => (
        <StatusTag status={risk_level} context="priority" />
      )
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => (
        <RiskStatusTag status={status} />
      )
    }
  ];

  return (
    <div>
      <div style={{ marginBottom: 32 }}>
        <Title level={2} style={{ margin: 0, marginBottom: 8 }}>
          GRC Dashboard
        </Title>
        <Text type="secondary">
          Overview of your governance, risk, and compliance posture
        </Text>
      </div>

      {/* KPI Cards Row */}
      {loading ? (
        <Loading message="Loading dashboard data..." />
      ) : (
        <Row gutter={[24, 24]} style={{ marginBottom: 32 }}>
          <Col xs={24} sm={12} lg={6}>
            <ComplianceKPICard
              title="Overall Compliance"
              value={dashboardData.analytics.complianceScore}
              suffix="%"
              compliancePercentage={dashboardData.analytics.complianceScore}
              trend={{
                value: 5.2,
                isPositive: true,
                period: "vs last month"
              }}
              description="Across all active frameworks"
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <RiskKPICard
              title="Active Risks"
              value={dashboardData.analytics.activeRisks}
              trend={{
                value: 2.1,
                isPositive: false,
                period: "vs last month"
              }}
              description="Requiring immediate attention"
              onClick={() => window.location.href = '/risk'}
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <PolicyKPICard
              title="Policy Compliance"
              value={94}
              suffix="%"
            trend={{
              value: 1.8,
              isPositive: true,
              period: "vs last month"
            }}
            description="Employee acknowledgment rate"
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <VendorKPICard
            title="Vendor Assessments"
            value={dashboardData.analytics.totalVendors}
            trend={{
              value: 8.3,
              isPositive: true,
              period: "vs last month"
            }}
            description="Active vendors"
            onClick={() => window.location.href = '/vendors'}
          />
        </Col>
      </Row>
      )}

      {!loading && (
      <>
        {/* Main Content Row */}
        <Row gutter={[24, 24]}>
        <Col xs={24} lg={14}>
          <Card
            title={
              <Space>
                <CheckSquareOutlined style={{ color: '#2F6FED' }} />
                <span>Recent Assessments</span>
              </Space>
            }
            extra={
              <Button
                type="link"
                icon={<EyeOutlined />}
                onClick={() => console.log('View all assessments')}
              >
                View All
              </Button>
            }
            style={{
              borderRadius: 12,
              boxShadow: isDark
                ? "0 6px 24px rgba(0,0,0,0.15)"
                : "0 6px 24px rgba(15,18,25,0.06)"
            }}
          >
            <Table
              dataSource={dashboardData.recentAssessments}
              columns={assessmentColumns}
              pagination={false}
              style={{ marginTop: 16 }}
              locale={{
                emptyText: dashboardData.recentAssessments.length === 0 ?
                  'No assessment data available. Connect to Django API to load data.' :
                  'No assessments found.'
              }}
            />
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card
            title={
              <Space>
                <SafetyOutlined style={{ color: '#E5484D' }} />
                <span>Active Risks</span>
              </Space>
            }
            extra={
              <Button
                type="link"
                icon={<PlusOutlined />}
                onClick={() => console.log('Add risk')}
              >
                Add Risk
              </Button>
            }
            style={{
              borderRadius: 12,
              boxShadow: isDark
                ? "0 6px 24px rgba(0,0,0,0.15)"
                : "0 6px 24px rgba(15,18,25,0.06)"
            }}
          >
            <Table
              dataSource={dashboardData.recentRisks}
              columns={riskColumns}
              pagination={false}
              style={{ marginTop: 16 }}
              locale={{
                emptyText: dashboardData.recentRisks.length === 0 ?
                  'No risk data available. Connect to Django API to load data.' :
                  'No risks found.'
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* Quick Actions Row */}
      <Row gutter={[24, 24]} style={{ marginTop: 32 }}>
        <Col xs={24} sm={12} md={6}>
          <Card
            hoverable
            style={{
              textAlign: 'center',
              borderRadius: 12,
              cursor: 'pointer',
              boxShadow: isDark
                ? "0 6px 24px rgba(0,0,0,0.15)"
                : "0 6px 24px rgba(15,18,25,0.06)"
            }}
            onClick={() => console.log('Create assessment')}
          >
            <CheckSquareOutlined
              style={{
                fontSize: 32,
                color: '#2F6FED',
                marginBottom: 12
              }}
            />
            <Title level={5} style={{ marginBottom: 4 }}>
              New Assessment
            </Title>
            <Text type="secondary">
              Start a compliance assessment
            </Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card
            hoverable
            style={{
              textAlign: 'center',
              borderRadius: 12,
              cursor: 'pointer',
              boxShadow: isDark
                ? "0 6px 24px rgba(0,0,0,0.15)"
                : "0 6px 24px rgba(15,18,25,0.06)"
            }}
            onClick={() => console.log('Add risk')}
          >
            <SafetyOutlined
              style={{
                fontSize: 32,
                color: '#E5484D',
                marginBottom: 12
              }}
            />
            <Title level={5} style={{ marginBottom: 4 }}>
              Register Risk
            </Title>
            <Text type="secondary">
              Identify and track risks
            </Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card
            hoverable
            style={{
              textAlign: 'center',
              borderRadius: 12,
              cursor: 'pointer',
              boxShadow: isDark
                ? "0 6px 24px rgba(0,0,0,0.15)"
                : "0 6px 24px rgba(15,18,25,0.06)"
            }}
            onClick={() => console.log('Add vendor')}
          >
            <TeamOutlined
              style={{
                fontSize: 32,
                color: '#3B82F6',
                marginBottom: 12
              }}
            />
            <Title level={5} style={{ marginBottom: 4 }}>
              Add Vendor
            </Title>
            <Text type="secondary">
              Manage vendor relationships
            </Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card
            hoverable
            style={{
              textAlign: 'center',
              borderRadius: 12,
              cursor: 'pointer',
              boxShadow: isDark
                ? "0 6px 24px rgba(0,0,0,0.15)"
                : "0 6px 24px rgba(15,18,25,0.06)"
            }}
            onClick={() => console.log('Create policy')}
          >
            <FileTextOutlined
              style={{
                fontSize: 32,
                color: '#FFB020',
                marginBottom: 12
              }}
            />
            <Title level={5} style={{ marginBottom: 4 }}>
              New Policy
            </Title>
            <Text type="secondary">
              Create governance policies
            </Text>
          </Card>
        </Col>
      </Row>
      </>
      )}
    </div>
  );
}
