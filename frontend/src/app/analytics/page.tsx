'use client'

import React, { useEffect, useState } from 'react'
import { Card, Row, Col, Typography, Spin, message, Tabs, Space, Divider } from 'antd'
import {
  BarChartOutlined,
  DashboardOutlined,
  SecurityScanOutlined,
  TeamOutlined,
  FileTextOutlined,
  BookOutlined,
  TrophyOutlined,
  RiseOutlined
} from '@ant-design/icons'
import { api } from '@/lib/api'
import {
  KPICard,
  ComplianceKPICard,
  RiskKPICard,
  VendorKPICard,
  PolicyKPICard
} from '@/components/ui'
import { StatusTag, AssessmentStatusTag, RiskStatusTag } from '@/components/ui/StatusTag'
import { PriorityTag } from '@/components/ui'
import { EmptyState } from '@/components/ui/EmptyState'

const { Title, Text, Paragraph } = Typography
const { TabPane } = Tabs

interface ExecutiveDashboardData {
  risk_summary: {
    total_risks: number
    active_risks: number
    critical_high_risks: number
    overdue_actions: number
  }
  compliance_summary: {
    total_assessments: number
    active_assessments: number
    completed_assessments: number
    overdue_assessments: number
    avg_completion_rate: number
  }
  policy_summary: {
    total_policies: number
    active_policies: number
    pending_acknowledgments: number
    overdue_acknowledgments: number
    acknowledgment_rate: number
  }
  vendor_summary: {
    total_vendors: number
    active_vendors: number
    high_risk_vendors: number
    contracts_expiring_soon: number
    overdue_tasks: number
  }
  training_summary: {
    total_videos: number
    total_views: number
    unique_viewers: number
    completion_rate: number
    active_campaigns: number
  }
  generated_at: string
}

interface ComplianceDashboardData {
  framework_statistics: Array<{
    name: string
    framework_type: string
    total_assessments: number
    completed_assessments: number
    in_progress_assessments: number
    overdue_assessments: number
    completion_rate: number
    avg_score: number
  }>
  overall_metrics: {
    total_frameworks: number
    active_frameworks: number
    total_controls: number
    automated_controls: number
    avg_maturity_score: number
  }
}

interface VendorRiskData {
  vendor_risk_statistics: {
    risk_distribution: Record<string, number>
    total_vendors: number
    active_vendors: number
    total_annual_spend: number
    avg_performance_score: number
  }
  contract_management: {
    expiring_30_days: number
    expiring_90_days: number
    expired_contracts: number
    renewals_needed: number
  }
  task_analytics: {
    total_tasks: number
    overdue_tasks: number
    due_this_week: number
    completion_rate: number
  }
}

interface PolicyData {
  policy_statistics: {
    total_policies: number
    active_policies: number
    policies_requiring_acknowledgment: number
    draft_policies: number
  }
  acknowledgment_analytics: {
    total_distributions: number
    acknowledged_distributions: number
    pending_acknowledgments: number
    overdue_acknowledgments: number
    acknowledgment_rate: number
  }
}

interface TrainingData {
  video_engagement: {
    total_videos: number
    total_views: number
    unique_viewers: number
    total_watch_time: number
    avg_completion_rate: number
  }
  user_engagement: {
    active_learners_30_days: number
    completed_videos_30_days: number
    avg_videos_per_user: number
    completion_rate: number
  }
}

export default function AnalyticsPage() {
  const [executiveData, setExecutiveData] = useState<ExecutiveDashboardData | null>(null)
  const [complianceData, setComplianceData] = useState<ComplianceDashboardData | null>(null)
  const [vendorData, setVendorData] = useState<VendorRiskData | null>(null)
  const [policyData, setPolicyData] = useState<PolicyData | null>(null)
  const [trainingData, setTrainingData] = useState<TrainingData | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('executive')

  useEffect(() => {
    fetchAnalyticsData()
  }, [])

  const fetchAnalyticsData = async () => {
    try {
      setLoading(true)

      // Mock data for development - replace with real API calls when backend is ready
      const mockExecutiveData = {
        risk_summary: {
          total_risks: 42,
          active_risks: 38,
          critical_high_risks: 8,
          overdue_actions: 3,
        },
        compliance_summary: {
          total_assessments: 156,
          active_assessments: 23,
          completed_assessments: 128,
          overdue_assessments: 5,
          avg_completion_rate: 87.2,
        },
        policy_summary: {
          total_policies: 24,
          active_policies: 22,
          pending_acknowledgments: 15,
          overdue_acknowledgments: 2,
          acknowledgment_rate: 92.5,
        },
        vendor_summary: {
          total_vendors: 89,
          active_vendors: 82,
          high_risk_vendors: 6,
          contracts_expiring_soon: 4,
          overdue_tasks: 7,
        },
        training_summary: {
          total_videos: 45,
          total_views: 1247,
          unique_viewers: 156,
          completion_rate: 78.3,
          active_campaigns: 3,
        },
        generated_at: new Date().toISOString(),
      }

      const mockComplianceData = {
        framework_statistics: [
          {
            name: 'SOC 2 Type II',
            framework_type: 'security',
            total_assessments: 45,
            completed_assessments: 38,
            in_progress_assessments: 5,
            overdue_assessments: 2,
            completion_rate: 84.4,
            avg_score: 87.2,
          },
          {
            name: 'ISO 27001',
            framework_type: 'security',
            total_assessments: 67,
            completed_assessments: 59,
            in_progress_assessments: 6,
            overdue_assessments: 2,
            completion_rate: 88.1,
            avg_score: 91.3,
          },
          {
            name: 'NIST CSF',
            framework_type: 'cybersecurity',
            total_assessments: 44,
            completed_assessments: 31,
            in_progress_assessments: 12,
            overdue_assessments: 1,
            completion_rate: 70.5,
            avg_score: 82.7,
          },
        ],
        overall_metrics: {
          total_frameworks: 5,
          active_frameworks: 5,
          total_controls: 234,
          automated_controls: 89,
          avg_maturity_score: 3.2,
        },
      }

      const mockVendorData = {
        vendor_risk_statistics: {
          risk_distribution: { low: 35, medium: 28, high: 15, critical: 3 },
          total_vendors: 89,
          active_vendors: 82,
          total_annual_spend: 2400000,
          avg_performance_score: 87.3,
        },
        contract_management: {
          expiring_30_days: 2,
          expiring_90_days: 8,
          expired_contracts: 1,
          renewals_needed: 12,
        },
        task_analytics: {
          total_tasks: 156,
          overdue_tasks: 7,
          due_this_week: 18,
          completion_rate: 84.2,
        },
      }

      const mockPolicyData = {
        policy_statistics: {
          total_policies: 24,
          active_policies: 22,
          policies_requiring_acknowledgment: 18,
          draft_policies: 2,
        },
        acknowledgment_analytics: {
          total_distributions: 287,
          acknowledged_distributions: 265,
          pending_acknowledgments: 22,
          overdue_acknowledgments: 4,
          acknowledgment_rate: 92.3,
        },
      }

      const mockTrainingData = {
        video_engagement: {
          total_videos: 45,
          total_views: 1247,
          unique_viewers: 156,
          total_watch_time: 8450,
          avg_completion_rate: 78.3,
        },
        user_engagement: {
          active_learners_30_days: 89,
          completed_videos_30_days: 234,
          avg_videos_per_user: 2.8,
          completion_rate: 78.3,
        },
      }

      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 800))

      setExecutiveData(mockExecutiveData)
      setComplianceData(mockComplianceData)
      setVendorData(mockVendorData)
      setPolicyData(mockPolicyData)
      setTrainingData(mockTrainingData)

      // Uncomment when backend API is ready:
      /*
      const [executiveResponse, complianceResponse, vendorResponse, policyResponse, trainingResponse] = await Promise.all([
        api.get('/analytics/executive/'),
        api.get('/analytics/compliance/'),
        api.get('/analytics/vendor-risk/'),
        api.get('/analytics/policy-management/'),
        api.get('/analytics/training-effectiveness/')
      ])

      setExecutiveData(executiveResponse.data)
      setComplianceData(complianceResponse.data)
      setVendorData(vendorResponse.data)
      setPolicyData(policyResponse.data)
      setTrainingData(trainingResponse.data)
      */

    } catch (error) {
      console.error('Failed to fetch analytics data:', error)
      message.error('Backend not available - showing demo data')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>
          <Text type="secondary">Loading analytics dashboard...</Text>
        </div>
      </div>
    )
  }

  const renderExecutiveDashboard = () => (
    <div>
      <Title level={3}>
        <TrophyOutlined style={{ marginRight: 8 }} />
        Executive Overview
      </Title>
      <Paragraph type="secondary">
        High-level KPIs and metrics across all GRC modules for executive reporting
      </Paragraph>

      {/* Executive KPI Cards */}
      <Row gutter={[24, 24]} style={{ marginBottom: 32 }}>
        <Col xs={24} sm={12} lg={6}>
          <RiskKPICard
            title="Active Risks"
            value={executiveData?.risk_summary.active_risks || 0}
            trend={{
              value: 8.2,
              isPositive: false,
              period: "vs last month"
            }}
            description="Total active risks requiring attention"
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <ComplianceKPICard
            title="Compliance Score"
            value={Math.round(executiveData?.compliance_summary.avg_completion_rate || 0)}
            suffix="%"
            compliancePercentage={Math.round(executiveData?.compliance_summary.avg_completion_rate || 0)}
            trend={{
              value: 3.5,
              isPositive: true,
              period: "vs last quarter"
            }}
            description="Average compliance across frameworks"
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <VendorKPICard
            title="Vendor Risk"
            value={vendorData?.vendor_risk_statistics.total_vendors || 0}
            description="Active vendors under management"
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <PolicyKPICard
            title="Policy Compliance"
            value={Math.round(executiveData?.policy_summary.acknowledgment_rate || 0)}
            suffix="%"
            description="Policy acknowledgment compliance"
          />
        </Col>
      </Row>

      {/* Quick Stats Grid */}
      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card
            title={
              <Space>
                <SecurityScanOutlined />
                <Text strong>Risk Management</Text>
              </Space>
            }

          >
            <Row gutter={16}>
              <Col span={12}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#f5222d' }}>
                    {executiveData?.risk_summary.critical_high_risks || 0}
                  </div>
                  <Text type="secondary" style={{ fontSize: '12px' }}>Critical/High Risks</Text>
                </div>
              </Col>
              <Col span={12}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#faad14' }}>
                    {executiveData?.risk_summary.overdue_actions || 0}
                  </div>
                  <Text type="secondary" style={{ fontSize: '12px' }}>Overdue Actions</Text>
                </div>
              </Col>
            </Row>
          </Card>
        </Col>

        <Col xs={24} md={12}>
          <Card
            title={
              <Space>
                <FileTextOutlined />
                <Text strong>Compliance Status</Text>
              </Space>
            }

          >
            <Row gutter={16}>
              <Col span={12}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#52c41a' }}>
                    {executiveData?.compliance_summary.completed_assessments || 0}
                  </div>
                  <Text type="secondary" style={{ fontSize: '12px' }}>Completed</Text>
                </div>
              </Col>
              <Col span={12}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#f5222d' }}>
                    {executiveData?.compliance_summary.overdue_assessments || 0}
                  </div>
                  <Text type="secondary" style={{ fontSize: '12px' }}>Overdue</Text>
                </div>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  )

  const renderComplianceDashboard = () => (
    <div>
      <Title level={3}>
        <FileTextOutlined style={{ marginRight: 8 }} />
        Compliance Analytics
      </Title>
      <Paragraph type="secondary">
        Framework completion rates, control effectiveness, and assessment progress tracking
      </Paragraph>

      {/* Compliance Overview KPIs */}
      <Row gutter={[24, 24]} style={{ marginBottom: 32 }}>
        <Col xs={24} sm={8}>
          <KPICard
            title="Active Frameworks"
            value={complianceData?.overall_metrics.active_frameworks || 0}
            icon={<FileTextOutlined />}
            color="#1890ff"
            description="Compliance frameworks in use"
          />
        </Col>
        <Col xs={24} sm={8}>
          <KPICard
            title="Total Controls"
            value={complianceData?.overall_metrics.total_controls || 0}
            icon={<SecurityScanOutlined />}
            color="#52c41a"
            progress={{
              percent: Math.round(
                ((complianceData?.overall_metrics.automated_controls || 0) /
                 Math.max(complianceData?.overall_metrics.total_controls || 1, 1)) * 100
              ),
              showInfo: true,
              status: 'success'
            }}
            description="Automated control coverage"
          />
        </Col>
        <Col xs={24} sm={8}>
          <KPICard
            title="Maturity Score"
            value={Math.round(complianceData?.overall_metrics.avg_maturity_score || 0)}
            suffix="/5"
            icon={<TrophyOutlined />}
            color="#722ed1"
            trend={{
              value: 0.3,
              isPositive: true,
              period: "vs last assessment"
            }}
            description="Average control maturity"
          />
        </Col>
      </Row>

      {/* Framework Performance */}
      <Card title="Framework Performance" style={{ marginBottom: 24 }}>
        {complianceData?.framework_statistics.length === 0 ? (
          <EmptyState description="No framework data available" />
        ) : (
          <Row gutter={[16, 16]}>
            {complianceData?.framework_statistics.map((framework, index) => (
              <Col xs={24} lg={12} key={index}>
                <Card style={{ height: '100%' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                    <div>
                      <Text strong>{framework.name}</Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: '12px' }}>{framework.framework_type}</Text>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#1890ff' }}>
                        {framework.completion_rate}%
                      </div>
                      <Text type="secondary" style={{ fontSize: '11px' }}>Completion</Text>
                    </div>
                  </div>

                  <Row gutter={8} style={{ marginTop: 8 }}>
                    <Col span={8}>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#52c41a' }}>
                          {framework.completed_assessments}
                        </div>
                        <Text type="secondary" style={{ fontSize: '10px' }}>Complete</Text>
                      </div>
                    </Col>
                    <Col span={8}>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#faad14' }}>
                          {framework.in_progress_assessments}
                        </div>
                        <Text type="secondary" style={{ fontSize: '10px' }}>In Progress</Text>
                      </div>
                    </Col>
                    <Col span={8}>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#f5222d' }}>
                          {framework.overdue_assessments}
                        </div>
                        <Text type="secondary" style={{ fontSize: '10px' }}>Overdue</Text>
                      </div>
                    </Col>
                  </Row>
                </Card>
              </Col>
            ))}
          </Row>
        )}
      </Card>
    </div>
  )

  const renderVendorDashboard = () => (
    <div>
      <Title level={3}>
        <TeamOutlined style={{ marginRight: 8 }} />
        Vendor Risk Analytics
      </Title>
      <Paragraph type="secondary">
        Vendor risk distribution, contract management, and task analytics
      </Paragraph>

      {/* Vendor Risk Overview */}
      <Row gutter={[24, 24]} style={{ marginBottom: 32 }}>
        <Col xs={24} sm={8}>
          <VendorKPICard
            title="Total Vendors"
            value={vendorData?.vendor_risk_statistics.total_vendors || 0}
            description="Active vendor relationships"
          />
        </Col>
        <Col xs={24} sm={8}>
          <KPICard
            title="Annual Spend"
            value={Math.round((vendorData?.vendor_risk_statistics.total_annual_spend || 0) / 1000000)}
            suffix="M"
            prefix="$"
            icon={<RiseOutlined />}
            color="#faad14"
            description="Total vendor spend"
          />
        </Col>
        <Col xs={24} sm={8}>
          <KPICard
            title="Contracts Expiring"
            value={vendorData?.contract_management.expiring_90_days || 0}
            icon={<FileTextOutlined />}
            color="#f5222d"
            description="Next 90 days"
            progress={{
              percent: Math.round(
                ((vendorData?.contract_management.expiring_30_days || 0) /
                 Math.max(vendorData?.contract_management.expiring_90_days || 1, 1)) * 100
              ),
              status: 'exception'
            }}
          />
        </Col>
      </Row>

      {/* Risk Distribution & Contract Status */}
      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card title="Risk Distribution">
            <Row gutter={8}>
              {['low', 'medium', 'high', 'critical'].map(level => (
                <Col span={6} key={level}>
                  <div style={{ textAlign: 'center', padding: '8px 0' }}>
                    <div style={{
                      fontSize: '20px',
                      fontWeight: 'bold',
                      color: level === 'critical' ? '#f5222d' :
                             level === 'high' ? '#faad14' :
                             level === 'medium' ? '#1890ff' : '#52c41a'
                    }}>
                      {vendorData?.vendor_risk_statistics.risk_distribution[level] || 0}
                    </div>
                    <Text type="secondary" style={{ fontSize: '11px', textTransform: 'capitalize' }}>
                      {level}
                    </Text>
                  </div>
                </Col>
              ))}
            </Row>
          </Card>
        </Col>

        <Col xs={24} md={12}>
          <Card title="Task Analytics">
            <Row gutter={8}>
              <Col span={8}>
                <div style={{ textAlign: 'center', padding: '8px 0' }}>
                  <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#f5222d' }}>
                    {vendorData?.task_analytics.overdue_tasks || 0}
                  </div>
                  <Text type="secondary" style={{ fontSize: '11px' }}>Overdue</Text>
                </div>
              </Col>
              <Col span={8}>
                <div style={{ textAlign: 'center', padding: '8px 0' }}>
                  <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#faad14' }}>
                    {vendorData?.task_analytics.due_this_week || 0}
                  </div>
                  <Text type="secondary" style={{ fontSize: '11px' }}>Due This Week</Text>
                </div>
              </Col>
              <Col span={8}>
                <div style={{ textAlign: 'center', padding: '8px 0' }}>
                  <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#52c41a' }}>
                    {Math.round(vendorData?.task_analytics.completion_rate || 0)}%
                  </div>
                  <Text type="secondary" style={{ fontSize: '11px' }}>Complete</Text>
                </div>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  )

  const renderPolicyDashboard = () => (
    <div>
      <Title level={3}>
        <BookOutlined style={{ marginRight: 8 }} />
        Policy Management
      </Title>
      <Paragraph type="secondary">
        Policy acknowledgment tracking and compliance monitoring
      </Paragraph>

      <Row gutter={[24, 24]}>
        <Col xs={24} sm={8}>
          <PolicyKPICard
            title="Policy Compliance"
            value={Math.round(policyData?.acknowledgment_analytics.acknowledgment_rate || 0)}
            suffix="%"
            description="Overall acknowledgment rate"
          />
        </Col>
        <Col xs={24} sm={8}>
          <KPICard
            title="Active Policies"
            value={policyData?.policy_statistics.active_policies || 0}
            icon={<BookOutlined />}
            color="#1890ff"
            description="Policies currently active"
          />
        </Col>
        <Col xs={24} sm={8}>
          <KPICard
            title="Pending Acknowledgments"
            value={policyData?.acknowledgment_analytics.pending_acknowledgments || 0}
            icon={<FileTextOutlined />}
            color="#faad14"
            description="Requiring user acknowledgment"
            progress={{
              percent: Math.round(
                ((policyData?.acknowledgment_analytics.overdue_acknowledgments || 0) /
                 Math.max(policyData?.acknowledgment_analytics.pending_acknowledgments || 1, 1)) * 100
              ),
              status: 'exception'
            }}
          />
        </Col>
      </Row>
    </div>
  )

  const renderTrainingDashboard = () => (
    <div>
      <Title level={3}>
        <BookOutlined style={{ marginRight: 8 }} />
        Training Effectiveness
      </Title>
      <Paragraph type="secondary">
        Training engagement metrics and security awareness program performance
      </Paragraph>

      <Row gutter={[24, 24]}>
        <Col xs={24} sm={8}>
          <KPICard
            title="Completion Rate"
            value={Math.round(trainingData?.user_engagement.completion_rate || 0)}
            suffix="%"
            icon={<TrophyOutlined />}
            color="#52c41a"
            trend={{
              value: 4.2,
              isPositive: true,
              period: "vs last month"
            }}
            description="Video completion rate"
          />
        </Col>
        <Col xs={24} sm={8}>
          <KPICard
            title="Active Learners"
            value={trainingData?.user_engagement.active_learners_30_days || 0}
            icon={<TeamOutlined />}
            color="#1890ff"
            description="Last 30 days"
          />
        </Col>
        <Col xs={24} sm={8}>
          <KPICard
            title="Total Watch Time"
            value={Math.round((trainingData?.video_engagement.total_watch_time || 0) / 60)}
            suffix=" hrs"
            icon={<BookOutlined />}
            color="#722ed1"
            description="Cumulative learning time"
          />
        </Col>
      </Row>
    </div>
  )

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>
          <BarChartOutlined style={{ marginRight: 8 }} />
          Analytics & Reporting
        </Title>
        <Text type="secondary">
          Comprehensive GRC platform analytics with executive insights and operational metrics
        </Text>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        size="large"
        tabBarStyle={{ marginBottom: 24 }}
      >
        <TabPane
          tab={
            <Space>
              <DashboardOutlined />
              Executive
            </Space>
          }
          key="executive"
        >
          {renderExecutiveDashboard()}
        </TabPane>

        <TabPane
          tab={
            <Space>
              <FileTextOutlined />
              Compliance
            </Space>
          }
          key="compliance"
        >
          {renderComplianceDashboard()}
        </TabPane>

        <TabPane
          tab={
            <Space>
              <TeamOutlined />
              Vendors
            </Space>
          }
          key="vendors"
        >
          {renderVendorDashboard()}
        </TabPane>

        <TabPane
          tab={
            <Space>
              <BookOutlined />
              Policies
            </Space>
          }
          key="policies"
        >
          {renderPolicyDashboard()}
        </TabPane>

        <TabPane
          tab={
            <Space>
              <BookOutlined />
              Training
            </Space>
          }
          key="training"
        >
          {renderTrainingDashboard()}
        </TabPane>
      </Tabs>
    </div>
  )
}
