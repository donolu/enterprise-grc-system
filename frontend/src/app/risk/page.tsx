'use client'

import React, { useCallback, useRef, useState, useEffect } from 'react'
import { Card, Typography, Space, Button, Row, Col, Progress, Table, Tag, message, Modal, Form, Input, Select } from 'antd'
import { SafetyOutlined, PlusOutlined, ExclamationCircleOutlined, WarningOutlined, CheckCircleOutlined, InfoCircleOutlined } from '@ant-design/icons'
import { useRouter } from 'next/navigation'
import { Breadcrumb, KPICard, RiskKPICard, StatusTag, PriorityTag, Loading, ExportButton, FilterPanel } from '@/components/ui'
import { riskService, type Risk, type RiskCategory, type RiskFilters } from '@/lib/services/riskService'

const { Title, Text } = Typography

interface RiskAnalytics {
  totalRisks: number
  highRiskItems: number
  overdueActions: number
  avgRiskScore: number
  riskTrend: number
}

interface ChoiceOption {
  value: string
  label: string
}

interface RiskChoices {
  risk_levels?: ChoiceOption[]
  status_choices?: ChoiceOption[]
  treatment_strategies?: ChoiceOption[]
}

type FilterValue = string | string[] | null | undefined
type FilterValues = Record<string, FilterValue>
type PaginationConfig = { current?: number; pageSize?: number }

export default function RiskPage() {
  const [loading, setLoading] = useState(true)
  const [riskData, setRiskData] = useState<Risk[]>([])
  const riskDataRef = useRef<Risk[]>([])
  const [analytics, setAnalytics] = useState<RiskAnalytics>({
    totalRisks: 0,
    highRiskItems: 0,
    overdueActions: 0,
    avgRiskScore: 0,
    riskTrend: 0
  })
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 })
  const [filters, setFilters] = useState<FilterValues>({})
  const [dynamicFilters, setDynamicFilters] = useState<Array<{
    key: string
    label: string
    type: 'multiSelect' | 'search'
    options?: ChoiceOption[]
    placeholder?: string
  }>>([])
  const [riskCategories, setRiskCategories] = useState<RiskCategory[]>([])
  const [riskChoices, setRiskChoices] = useState<RiskChoices>({})
  const [isAddRiskModalVisible, setIsAddRiskModalVisible] = useState(false)
  const [addRiskForm] = Form.useForm()
  const router = useRouter()

  // Fetch risks data
  const fetchRisks = useCallback(async (currentFilters: RiskFilters = {}, page = 1, pageSize = 10) => {
    try {
      setLoading(true)
      const response = await riskService.getRisks({
        ...currentFilters,
        page,
        pageSize
      })

      const risks = response.results || []
      riskDataRef.current = risks
      setRiskData(risks)
      setPagination({
        current: page,
        pageSize,
        total: response.count || 0
      })
    } catch (error) {
      message.error('Failed to load risk data. Using cached data.')
      console.error('Error fetching risks:', error)
      // Keep existing data if available
      setRiskData((previousRisks) => {
        riskDataRef.current = previousRisks
        // Only show empty state if no data at all
        return previousRisks.length === 0 ? [] : previousRisks
      })
    } finally {
      setLoading(false)
    }
  }, [])

  // Fetch analytics
  const fetchAnalytics = useCallback(async () => {
    try {
      const data = await riskService.getRiskAnalytics()
      setAnalytics(data)
    } catch (error) {
      console.error('Error fetching analytics:', error)
      const currentRisks = riskDataRef.current
      // Set default analytics if API fails
      setAnalytics({
        totalRisks: currentRisks.length || 0,
        highRiskItems: currentRisks.filter(r => r.risk_level === 'high' || r.risk_level === 'critical').length || 0,
        overdueActions: 0,
        avgRiskScore: currentRisks.length ?
          currentRisks.reduce((sum, r) => sum + (r.risk_score || 0), 0) / currentRisks.length : 0,
        riskTrend: 0
      })
    }
  }, [])

  // Fetch dynamic filter data
  const fetchDynamicData = useCallback(async () => {
    try {
      const [categories, choices] = await Promise.all([
        riskService.getRiskCategories(),
        riskService.getRiskChoices()
      ])

      setRiskCategories(categories)
      setRiskChoices(choices)

      // Build dynamic filters
      const filters = [
        {
          key: 'risk_level',
          label: 'Risk Level',
          type: 'multiSelect' as const,
          options: choices.risk_levels || []
        },
        {
          key: 'status',
          label: 'Status',
          type: 'multiSelect' as const,
          options: choices.status_choices || []
        },
        {
          key: 'category',
          label: 'Category',
          type: 'multiSelect' as const,
          options: categories.map(cat => ({ value: cat.id.toString(), label: cat.name }))
        },
        {
          key: 'search',
          label: 'Search',
          type: 'search' as const,
          placeholder: 'Search risks by title or description'
        }
      ]

      setDynamicFilters(filters)
    } catch (error) {
      console.error('Error fetching dynamic filter data:', error)
      // Set fallback filters if API fails
      setDynamicFilters([
        {
          key: 'search',
          label: 'Search',
          type: 'search' as const,
          placeholder: 'Search risks'
        }
      ])
    }
  }, [])

  useEffect(() => {
    fetchRisks()
    fetchAnalytics()
    fetchDynamicData()
  }, [fetchAnalytics, fetchDynamicData, fetchRisks])

  // Handle filter changes
  const handleFilterChange = (newFilters: FilterValues) => {
    setFilters(newFilters)
    fetchRisks(newFilters as RiskFilters, 1, pagination.pageSize)
  }

  // Handle table pagination/sorting
  const handleTableChange = (paginationConfig: PaginationConfig) => {
    fetchRisks(filters as RiskFilters, paginationConfig.current, paginationConfig.pageSize)
  }

  // Handle Add Risk
  const handleAddRisk = () => {
    setIsAddRiskModalVisible(true)
  }

  // Handle Create Assessment
  const handleCreateAssessment = () => {
    router.push('/assessments/create')
  }

  // Handle Risk ID click (navigate to risk details)
  const handleRiskClick = (riskId: string | number) => {
    router.push(`/risk/${riskId}`)
  }

  // Handle Add Risk form submission
  const handleAddRiskSubmit = async (values: Partial<Risk>) => {
    try {
      await riskService.createRisk(values)
      message.success('Risk created successfully')
      setIsAddRiskModalVisible(false)
      addRiskForm.resetFields()
      fetchRisks() // Refresh the list
    } catch (error) {
      message.error('Failed to create risk')
      console.error('Error creating risk:', error)
    }
  }

  // Handle modal cancel
  const handleModalCancel = () => {
    setIsAddRiskModalVisible(false)
    addRiskForm.resetFields()
  }

  const columns = [
    {
      title: 'Risk ID',
      dataIndex: 'risk_id',
      key: 'risk_id',
      render: (text: string, record: Risk) => (
        <Button
          type="link"
          style={{ padding: 0, height: 'auto', color: '#2F6FED' }}
          onClick={() => handleRiskClick(record.id)}
        >
          <Text strong style={{ color: '#2F6FED' }}>{text}</Text>
        </Button>
      )
    },
    {
      title: 'Risk Title',
      dataIndex: 'title',
      key: 'title',
      render: (text: string) => <Text strong>{text}</Text>
    },
    {
      title: 'Category',
      dataIndex: 'category',
      key: 'category',
      render: (category: RiskCategory | null) => {
        if (!category) return <Tag>Uncategorized</Tag>
        return <Tag color={category.color || 'default'}>{category.name}</Tag>
      }
    },
    {
      title: 'Risk Level',
      dataIndex: 'risk_level',
      key: 'risk_level',
      render: (level: string) => <PriorityTag status={level} />
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => <StatusTag status={status} context="risk" />
    },
    {
      title: 'Owner',
      dataIndex: 'risk_owner',
      key: 'risk_owner',
      render: (owner: Risk['risk_owner']) => {
        if (!owner) return <Text type="secondary">Unassigned</Text>
        return <Text>{owner.first_name} {owner.last_name}</Text>
      }
    },
    {
      title: 'Risk Score',
      dataIndex: 'risk_score',
      key: 'risk_score',
      render: (score: number, record: Risk) => {
        if (!score) return <Text type="secondary">Not calculated</Text>
        const maxScore = 25 // 5x5 matrix
        const percentage = Math.min((score / maxScore) * 100, 100)
        return (
          <Space direction="vertical" size={2}>
            <Progress
              percent={percentage}

              status={score > 15 ? 'exception' : score > 10 ? 'active' : 'success'}
            />
            <Text style={{ fontSize: '12px' }}>
              {score}/{maxScore} (I:{record.impact} × L:{record.likelihood})
            </Text>
          </Space>
        )
      }
    },
    {
      title: 'Review Date',
      dataIndex: 'next_review_date',
      key: 'next_review_date',
      render: (date: string, record: Risk) => {
        if (!date) return <Text type="secondary">Not scheduled</Text>
        const isOverdue = record.is_overdue_for_review
        return (
          <Space direction="vertical" size={2}>
            <Text style={{ color: isOverdue ? '#E5484D' : undefined }}>
              {new Date(date).toLocaleDateString()}
            </Text>
            {isOverdue && <Tag color="red">Overdue</Tag>}
          </Space>
        )
      }
    }
  ]

  return (
    <div>
      <Breadcrumb
        items={[
          { title: 'Risk Management', icon: <SafetyOutlined /> }
        ]}
      />

      <div style={{ marginBottom: 24 }}>
        <Title level={2}>
          <SafetyOutlined style={{ marginRight: 8 }} />
          Risk Management
        </Title>
        <Text type="secondary">
          Identify, assess, and manage organizational risks across the enterprise
        </Text>
      </div>

      {/* KPI Cards */}
      <Row gutter={[24, 24]} style={{ marginBottom: 32 }}>
        <Col xs={24} sm={12} lg={6}>
          <RiskKPICard
            title="Total Risks"
            value={analytics.totalRisks || 0}
            description="All identified risks"
            trend={{ value: Math.abs(analytics.riskTrend || 0), isPositive: (analytics.riskTrend || 0) > 0, period: "vs last month" }}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <KPICard
            title="High Risk Items"
            value={analytics.highRiskItems || 0}
            icon={<ExclamationCircleOutlined />}
            color="#E5484D"
            description="Critical & high severity"
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <KPICard
            title="Overdue Actions"
            value={analytics.overdueActions || 0}
            icon={<WarningOutlined />}
            color="#FFB020"
            description="Past due mitigation"
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <KPICard
            title="Avg. Risk Score"
            value={Math.round((analytics.avgRiskScore || 0) * 10) / 10}
            suffix="/25"
            icon={<InfoCircleOutlined />}
            color="#2F6FED"
            trend={{
              value: Math.abs(analytics.riskTrend || 0),
              isPositive: (analytics.riskTrend || 0) < 0, // Lower risk trend is positive
              period: "vs last quarter"
            }}
            description="Overall risk posture"
          />
        </Col>
      </Row>

      {/* Filters */}
      {dynamicFilters.length > 0 && (
        <FilterPanel
          filters={dynamicFilters}
          onFilterChange={handleFilterChange}
          showCount={true}
        />
      )}

      {/* Risk Register Table */}
      <Card
        title={
          <Space>
            <SafetyOutlined />
            <Text strong>Active Risk Register</Text>
          </Space>
        }
        extra={
          <Space>
            <ExportButton
              data={riskData}
              filename="risk-register"
            />
            <Button icon={<PlusOutlined />} onClick={handleAddRisk}>
              Add Risk
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateAssessment}>
              Create Assessment
            </Button>
          </Space>
        }
        style={{ marginBottom: 24 }}
      >
        {loading ? (
          <Loading message="Loading risk data..." />
        ) : (
          <Table
            columns={columns}
            dataSource={riskData.map(risk => ({ ...risk, key: risk.id }))}
            pagination={{
              ...pagination,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total, range) => `${range[0]}-${range[1]} of ${total} risks`
            }}
            onChange={handleTableChange}
            scroll={{ x: 1000 }}
          />
        )}
      </Card>

      {/* Quick Actions */}
      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card hoverable>
            <Space direction="vertical" size={8}>
              <ExclamationCircleOutlined style={{ fontSize: '24px', color: '#E5484D' }} />
              <Text strong>Risk Assessment</Text>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                Conduct comprehensive risk evaluations
              </Text>
              <Button type="link" style={{ padding: 0 }} onClick={handleCreateAssessment}>
                Start Assessment →
              </Button>
            </Space>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card hoverable>
            <Space direction="vertical" size={8}>
              <CheckCircleOutlined style={{ fontSize: '24px', color: '#0EB57D' }} />
              <Text strong>Mitigation Plans</Text>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                Create and track risk treatment actions
              </Text>
              <Button type="link" style={{ padding: 0 }} onClick={() => router.push('/risk/mitigation')}>
                View Plans →
              </Button>
            </Space>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card hoverable>
            <Space direction="vertical" size={8}>
              <InfoCircleOutlined style={{ fontSize: '24px', color: '#2F6FED' }} />
              <Text strong>Risk Reports</Text>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                Generate executive and detailed reports
              </Text>
              <Button type="link" style={{ padding: 0 }} onClick={() => router.push('/reports')}>
                Generate Report →
              </Button>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* Add Risk Modal */}
      <Modal
        title="Add New Risk"
        open={isAddRiskModalVisible}
        onCancel={handleModalCancel}
        footer={null}
        width={600}
      >
        <Form
          form={addRiskForm}
          layout="vertical"
          onFinish={handleAddRiskSubmit}
        >
          <Form.Item
            name="title"
            label="Risk Title"
            rules={[{ required: true, message: 'Please enter risk title' }]}
          >
            <Input placeholder="Enter risk title" />
          </Form.Item>

          <Form.Item
            name="description"
            label="Description"
            rules={[{ required: true, message: 'Please enter risk description' }]}
          >
            <Input.TextArea rows={3} placeholder="Enter risk description" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="category"
                label="Category"
                rules={[{ required: true, message: 'Please select category' }]}
              >
                <Select placeholder="Select category">
                  {riskCategories.map(category => (
                    <Select.Option key={category.id} value={category.id}>
                      {category.name}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="treatment_strategy"
                label="Treatment Strategy"
              >
                <Select placeholder="Select strategy">
                  {riskChoices.treatment_strategies?.map((strategy) => (
                    <Select.Option key={strategy.value} value={strategy.value}>
                      {strategy.label}
                    </Select.Option>
                  )) || []}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="impact"
                label="Impact (1-5)"
                rules={[{ required: true, message: 'Please select impact' }]}
              >
                <Select placeholder="Select impact">
                  {[1, 2, 3, 4, 5].map(num => (
                    <Select.Option key={num} value={num}>{num}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="likelihood"
                label="Likelihood (1-5)"
                rules={[{ required: true, message: 'Please select likelihood' }]}
              >
                <Select placeholder="Select likelihood">
                  {[1, 2, 3, 4, 5].map(num => (
                    <Select.Option key={num} value={num}>{num}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                Create Risk
              </Button>
              <Button onClick={handleModalCancel}>
                Cancel
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
