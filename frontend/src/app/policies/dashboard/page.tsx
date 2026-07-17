'use client'

import React, { useEffect, useState } from 'react'
import {
  Card,
  Row,
  Col,
  Typography,
  Statistic,
  Progress,
  Input,
  Select,
  Button,
  Tag,
  Table,
  Badge,
  Empty,
  Spin,
  message,
  Space
} from 'antd'
import {
  DashboardOutlined,
  FileTextOutlined,
  UsergroupAddOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  SearchOutlined,
  ReloadOutlined,
  TrophyOutlined,
  WarningOutlined
} from '@ant-design/icons'
import { api } from '@/lib/api'

const { Title, Text } = Typography
const { Search } = Input
const { Option } = Select

interface PolicyStats {
  policy: {
    id: string
    title: string
    policy_code: string
    category: string | null
    status: string
  }
  current_version: {
    id: string
    version_number: string
    effective_date: string
  }
  stats: {
    total_distributed: number
    total_acknowledged: number
    acknowledgment_rate: number
    pending_count: number
    overdue_count: number
  }
  pending_users: Array<{
    id: string
    email: string
    first_name: string
    last_name: string
    distributed_at: string
    reminder_count: number
  }>
}

export default function PolicyDashboardPage() {
  const [dashboardData, setDashboardData] = useState<PolicyStats[]>([])
  const [filteredData, setFilteredData] = useState<PolicyStats[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterStatus, setFilterStatus] = useState<'all' | 'low-rate' | 'overdue'>('all')
  const [sortBy, setSortBy] = useState<'rate' | 'overdue' | 'name'>('rate')

  useEffect(() => {
    fetchDashboardData()
  }, [])

  useEffect(() => {
    filterAndSortData()
  }, [dashboardData, searchTerm, filterStatus, sortBy])

  const fetchDashboardData = async () => {
    try {
      setLoading(true)
      const response = await api.get('/policies/policies/acknowledgment_dashboard/')
      setDashboardData(response.data)
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
      message.error('Failed to load dashboard data')
    } finally {
      setLoading(false)
    }
  }

  const filterAndSortData = () => {
    let filtered = [...dashboardData]

    // Apply search filter
    if (searchTerm) {
      filtered = filtered.filter(policy =>
        policy.policy.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        policy.policy.policy_code.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (policy.policy.category && policy.policy.category.toLowerCase().includes(searchTerm.toLowerCase()))
      )
    }

    // Apply status filter
    switch (filterStatus) {
      case 'low-rate':
        filtered = filtered.filter(policy => policy.stats.acknowledgment_rate < 70)
        break
      case 'overdue':
        filtered = filtered.filter(policy => policy.stats.overdue_count > 0)
        break
    }

    // Apply sorting
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'rate':
          return a.stats.acknowledgment_rate - b.stats.acknowledgment_rate
        case 'overdue':
          return b.stats.overdue_count - a.stats.overdue_count
        case 'name':
          return a.policy.title.localeCompare(b.policy.title)
        default:
          return 0
      }
    })

    setFilteredData(filtered)
  }

  const getOverallStats = () => {
    if (dashboardData.length === 0) {
      return {
        totalPolicies: 0,
        totalDistributions: 0,
        totalAcknowledgments: 0,
        overallRate: 0,
        overdueCount: 0
      }
    }

    const totalDistributions = dashboardData.reduce((sum, policy) => sum + policy.stats.total_distributed, 0)
    const totalAcknowledgments = dashboardData.reduce((sum, policy) => sum + policy.stats.total_acknowledged, 0)
    const overdueCount = dashboardData.reduce((sum, policy) => sum + policy.stats.overdue_count, 0)

    return {
      totalPolicies: dashboardData.length,
      totalDistributions,
      totalAcknowledgments,
      overallRate: totalDistributions > 0 ? Math.round((totalAcknowledgments / totalDistributions) * 100) : 0,
      overdueCount
    }
  }

  const overallStats = getOverallStats()

  const getProgressStatus = (rate: number) => {
    if (rate >= 90) return 'success'
    if (rate >= 70) return 'active'
    return 'exception'
  }

  const getCategoryColor = (category: string | null) => {
    const colors = {
      'Security': 'red',
      'Privacy': 'blue',
      'HR': 'green',
      'Finance': 'gold',
      'Operations': 'purple',
      'Compliance': 'cyan'
    }
    return colors[category as keyof typeof colors] || 'default'
  }

  const columns = [
    {
      title: 'Policy',
      dataIndex: 'policy',
      key: 'policy',
      render: (policy: any) => (
        <div>
          <Text strong>{policy.title}</Text>
          <br />
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {policy.policy_code}
          </Text>
          {policy.category && (
            <Tag color={getCategoryColor(policy.category)} style={{ marginLeft: 8 }}>
              {policy.category}
            </Tag>
          )}
        </div>
      )
    },
    {
      title: 'Acknowledgment Rate',
      dataIndex: 'stats',
      key: 'rate',
      render: (stats: any) => (
        <div>
          <Progress
            percent={stats.acknowledgment_rate}

            status={getProgressStatus(stats.acknowledgment_rate)}
            format={(percent) => `${percent}%`}
          />
        </div>
      ),
      sorter: (a: PolicyStats, b: PolicyStats) => a.stats.acknowledgment_rate - b.stats.acknowledgment_rate
    },
    {
      title: 'Stats',
      dataIndex: 'stats',
      key: 'stats',
      render: (stats: any) => (
        <Space direction="vertical">
          <Text>
            <CheckCircleOutlined style={{ color: '#52c41a' }} /> {stats.total_acknowledged} / {stats.total_distributed}
          </Text>
          <Text type="warning">
            <ClockCircleOutlined /> {stats.pending_count} pending
          </Text>
          {stats.overdue_count > 0 && (
            <Text type="danger">
              <ExclamationCircleOutlined /> {stats.overdue_count} overdue
            </Text>
          )}
        </Space>
      )
    },
    {
      title: 'Pending Users',
      dataIndex: 'pending_users',
      key: 'pending_users',
      render: (pending_users: any[]) => (
        <div>
          {pending_users.slice(0, 3).map((user, index) => (
            <Tag key={user.id}>
              {user.first_name} {user.last_name}
              {user.reminder_count > 0 && (
                <Badge count={user.reminder_count} style={{ marginLeft: 4 }} />
              )}
            </Tag>
          ))}
          {pending_users.length > 3 && (
            <Tag>+{pending_users.length - 3} more</Tag>
          )}
        </div>
      )
    }
  ]

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>Loading dashboard data...</div>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={2}>
            <DashboardOutlined style={{ marginRight: 8 }} />
            Policy Acknowledgment Dashboard
          </Title>
          <Text type="secondary">
            Monitor policy acknowledgment rates and compliance status across your organization
          </Text>
        </div>
        <Button
          icon={<ReloadOutlined />}
          onClick={fetchDashboardData}
          loading={loading}
        >
          Refresh
        </Button>
      </div>

      {/* Overview Stats */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Total Policies"
              value={overallStats.totalPolicies}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Total Distributed"
              value={overallStats.totalDistributions}
              prefix={<UsergroupAddOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Acknowledged"
              value={overallStats.totalAcknowledgments}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Overall Rate"
              value={overallStats.overallRate}
              suffix="%"
              prefix={overallStats.overallRate >= 90 ? <TrophyOutlined /> : <WarningOutlined />}
              valueStyle={{
                color: overallStats.overallRate >= 90 ? '#52c41a' :
                       overallStats.overallRate >= 70 ? '#faad14' : '#f5222d'
              }}
            />
          </Card>
        </Col>
      </Row>

      {overallStats.overdueCount > 0 && (
        <Card
          style={{
            marginBottom: 24,
            borderColor: '#f5222d',
            backgroundColor: '#fff2f0'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <ExclamationCircleOutlined style={{ color: '#f5222d', fontSize: '20px', marginRight: 12 }} />
            <div>
              <Text strong style={{ color: '#f5222d' }}>
                {overallStats.overdueCount} users have overdue policy acknowledgments
              </Text>
              <br />
              <Text type="secondary">
                These users should be contacted directly to ensure policy compliance.
              </Text>
            </div>
          </div>
        </Card>
      )}

      {/* Filters */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={16}>
          <Col xs={24} sm={8}>
            <Search
              placeholder="Search policies by title, code, or category..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              allowClear
            />
          </Col>
          <Col xs={12} sm={4}>
            <Select
              value={filterStatus}
              onChange={setFilterStatus}
              style={{ width: '100%' }}
            >
              <Option value="all">All Policies</Option>
              <Option value="low-rate">Low Rate (&lt;70%)</Option>
              <Option value="overdue">Has Overdue</Option>
            </Select>
          </Col>
          <Col xs={12} sm={4}>
            <Select
              value={sortBy}
              onChange={setSortBy}
              style={{ width: '100%' }}
            >
              <Option value="rate">By Rate (Low First)</Option>
              <Option value="overdue">By Overdue Count</Option>
              <Option value="name">By Name</Option>
            </Select>
          </Col>
        </Row>
      </Card>

      {/* Policy Table */}
      <Card
        title={`Policies (${filteredData.length})`}
        extra={
          <Space>
            {filterStatus === 'low-rate' && (
              <Tag color="orange">Showing low acknowledgment rates only</Tag>
            )}
            {filterStatus === 'overdue' && (
              <Tag color="red">Showing policies with overdue acknowledgments only</Tag>
            )}
          </Space>
        }
      >
        {filteredData.length === 0 ? (
          <Empty
            description={
              dashboardData.length === 0
                ? "No policies found"
                : "No policies match your current filters"
            }
          />
        ) : (
          <Table
            columns={columns}
            dataSource={filteredData}
            rowKey={(record) => record.policy.id}
            pagination={{
              pageSize: 10,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total, range) =>
                `${range[0]}-${range[1]} of ${total} policies`
            }}
            scroll={{ x: 1000 }}
          />
        )}
      </Card>
    </div>
  )
}
