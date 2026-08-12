'use client'

import React, { useCallback, useState, useEffect } from 'react'
import { Alert, Card, Typography, Space, Button, Row, Col, Table, Tag, Progress, Avatar, message, Modal, Form, Input, Select } from 'antd'
import { TeamOutlined, PlusOutlined, WarningOutlined, CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons'
import { useRouter } from 'next/navigation'
import { Breadcrumb, EmptyState, VendorKPICard, KPICard, StatusTag, PriorityTag, Loading, ExportButton, FilterPanel, PageHeader } from '@/components/ui'
import type { FilterValues } from '@/components/ui/FilterPanel'
import { getErrorMessage } from '@/lib/api'
import { vendorService, type Vendor, type VendorAnalytics, type VendorCategory, type VendorFilters } from '@/lib/services/vendorService'

const { Text } = Typography

interface ChoiceOption {
  value: string
  label: string
}

interface VendorChoices {
  risk_level_choices?: ChoiceOption[]
  status_choices?: ChoiceOption[]
  vendor_type_choices?: ChoiceOption[]
}

type PaginationConfig = { current?: number; pageSize?: number }

export default function VendorsPage() {
  const [loading, setLoading] = useState(true)
  const [directoryError, setDirectoryError] = useState<string | null>(null)
  const [analyticsError, setAnalyticsError] = useState<string | null>(null)
  const [filterError, setFilterError] = useState<string | null>(null)
  const [vendorData, setVendorData] = useState<Vendor[]>([])
  const [analytics, setAnalytics] = useState<VendorAnalytics>({
    totalVendors: 0,
    contractsExpiring: 0,
    highRiskVendors: 0,
    avgPerformance: 0,
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
  const [vendorCategories, setVendorCategories] = useState<VendorCategory[]>([])
  const [vendorChoices, setVendorChoices] = useState<VendorChoices>({})
  const [isAddVendorModalVisible, setIsAddVendorModalVisible] = useState(false)
  const [addVendorForm] = Form.useForm()
  const router = useRouter()

  // Fetch vendors data
  const fetchVendors = useCallback(async (currentFilters: VendorFilters = {}, page = 1, pageSize = 10) => {
    try {
      setLoading(true)
      setDirectoryError(null)
      const response = await vendorService.getVendors({
        ...currentFilters,
        page,
        pageSize
      })

      setVendorData(response.results)
      setPagination({
        current: page,
        pageSize,
        total: response.count
      })
    } catch (error) {
      setVendorData([])
      setPagination({ current: page, pageSize, total: 0 })
      setDirectoryError(getErrorMessage(error))
    } finally {
      setLoading(false)
    }
  }, [])

  // Fetch analytics
  const fetchAnalytics = useCallback(async () => {
    try {
      setAnalyticsError(null)
      const data = await vendorService.getVendorAnalytics()
      setAnalytics(data)
    } catch (error) {
      setAnalyticsError(getErrorMessage(error))
    }
  }, [])

  // Fetch dynamic filter data
  const fetchDynamicData = useCallback(async () => {
    try {
      setFilterError(null)
      const [categories, choices] = await Promise.all([
        vendorService.getVendorCategories(),
        vendorService.getVendorChoices()
      ])

      setVendorCategories(categories)
      setVendorChoices(choices)

      // Build dynamic filters
      const filters = [
        {
          key: 'risk_level',
          label: 'Risk Level',
          type: 'multiSelect' as const,
          options: choices.risk_level_choices || []
        },
        {
          key: 'status',
          label: 'Status',
          type: 'multiSelect' as const,
          options: choices.status_choices || []
        },
        {
          key: 'vendor_type',
          label: 'Vendor Type',
          type: 'multiSelect' as const,
          options: choices.vendor_type_choices || []
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
          placeholder: 'Search vendors by name or description'
        }
      ]

      setDynamicFilters(filters)
    } catch (error) {
      setVendorCategories([])
      setVendorChoices({})
      setFilterError(getErrorMessage(error))
      setDynamicFilters([
        {
          key: 'search',
          label: 'Search',
          type: 'search' as const,
          placeholder: 'Search vendors'
        }
      ])
    }
  }, [])

  useEffect(() => {
    fetchVendors()
    fetchAnalytics()
    fetchDynamicData()
  }, [fetchAnalytics, fetchDynamicData, fetchVendors])

  // Handle filter changes
  const handleFilterChange = (newFilters: FilterValues) => {
    setFilters(newFilters)
    fetchVendors(newFilters as VendorFilters, 1, pagination.pageSize)
  }

  // Handle table pagination/sorting
  const handleTableChange = (paginationConfig: PaginationConfig) => {
    fetchVendors(filters as VendorFilters, paginationConfig.current, paginationConfig.pageSize)
  }

  // Handle Add Vendor
  const handleAddVendor = () => {
    setIsAddVendorModalVisible(true)
  }

  // Handle Contract Renewals
  const handleContractRenewals = () => {
    router.push('/vendors/contracts')
  }

  // Handle Vendor click (navigate to vendor details)
  const handleVendorClick = (vendorId: string | number) => {
    router.push(`/vendors/${vendorId}`)
  }

  // Handle Add Vendor form submission
  const handleAddVendorSubmit = async (values: Partial<Vendor>) => {
    try {
      await vendorService.createVendor(values)
      message.success('Vendor created successfully')
      setIsAddVendorModalVisible(false)
      addVendorForm.resetFields()
      fetchVendors() // Refresh the list
    } catch (error) {
      message.error(getErrorMessage(error))
    }
  }

  // Handle modal cancel
  const handleModalCancel = () => {
    setIsAddVendorModalVisible(false)
    addVendorForm.resetFields()
  }

  const columns = [
    {
      title: 'Vendor',
      key: 'vendor',
      render: (record: Vendor) => (
        <Button
          type="link"
          style={{ padding: 0, height: 'auto' }}
          onClick={() => handleVendorClick(record.id)}
        >
          <Space>
            <Avatar style={{ backgroundColor: '#2F6FED' }}>
              {record.name.substring(0, 2).toUpperCase()}
            </Avatar>
            <div style={{ textAlign: 'left' }}>
              <Text strong>{record.name}</Text>
              <br />
              <Text type="secondary" style={{ fontSize: '12px' }}>{record.vendor_id}</Text>
              {record.legal_name && record.legal_name !== record.name && (
                <><br /><Text type="secondary" style={{ fontSize: '11px' }}>({record.legal_name})</Text></>
              )}
            </div>
          </Space>
        </Button>
      )
    },
    {
      title: 'Category',
      dataIndex: 'category',
      key: 'category',
      render: (category: VendorCategory | null) => {
        if (!category) return <Tag>Uncategorized</Tag>
        return <Tag color={category.color_code || 'default'}>{category.name}</Tag>
      }
    },
    {
      title: 'Type',
      dataIndex: 'vendor_type',
      key: 'vendor_type',
      render: (type: string) => {
        const typeLabels: { [key: string]: string } = {
          'supplier': 'Supplier',
          'service_provider': 'Service Provider',
          'consultant': 'Consultant',
          'contractor': 'Contractor',
          'partner': 'Strategic Partner',
          'subcontractor': 'Subcontractor'
        }
        return <Text>{typeLabels[type] || type}</Text>
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
      render: (status: string) => <StatusTag status={status} context="vendor" />
    },
    {
      title: 'Annual Spend',
      dataIndex: 'annual_spend',
      key: 'annual_spend',
      render: (amount: number | null) => {
        if (!amount) return <Text type="secondary">Not specified</Text>
        return <Text>${amount.toLocaleString()}</Text>
      },
      sorter: (a: Vendor, b: Vendor) => {
        const aSpend = a.annual_spend || 0
        const bSpend = b.annual_spend || 0
        return aSpend - bSpend
      }
    },
    {
      title: 'Risk Score',
      dataIndex: 'risk_score',
      key: 'risk_score',
      render: (score: number | null) => {
        if (!score) return <Text type="secondary">Not assessed</Text>
        // Assuming risk score is 0-100 scale for vendors
        const percentage = Math.min(Math.max(score, 0), 100)
        return (
          <Space direction="vertical" size={2}>
            <Progress
              percent={percentage}

              status={score >= 70 ? 'exception' : score >= 40 ? 'active' : 'success'}
            />
            <Text style={{ fontSize: '12px' }}>Risk: {score}/100</Text>
          </Space>
        )
      }
    },
    {
      title: 'Owner',
      dataIndex: 'assigned_to',
      key: 'assigned_to',
      render: (owner: Vendor['assigned_to']) => {
        if (!owner) return <Text type="secondary">Unassigned</Text>
        return <Text>{owner.first_name} {owner.last_name}</Text>
      }
    }
  ]

  return (
    <div>
      <Breadcrumb
        items={[
          { title: 'Vendor Management', icon: <TeamOutlined /> }
        ]}
      />

      <PageHeader eyebrow="THIRD-PARTY ASSURANCE" title="Vendor management" description="Manage vendor relationships, assessments, and risk profiles across the organisation." icon={<TeamOutlined />} />

      {/* KPI Cards */}
      <Row gutter={[24, 24]} style={{ marginBottom: 32 }}>
        <Col xs={24} sm={12} lg={6}>
          <VendorKPICard
            title="Total Vendors"
            value={analytics.totalVendors || 0}
            description="Active vendor relationships"
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <KPICard
            title="Contracts Expiring"
            value={analytics.contractsExpiring || 0}
            icon={<WarningOutlined />}
            color="#FFB020"
            description="Next 90 days"
            progress={{ percent: 25, status: 'exception' }}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <KPICard
            title="High Risk Vendors"
            value={analytics.highRiskVendors || 0}
            icon={<WarningOutlined />}
            color="#E5484D"
            description="Require attention"
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <KPICard
            title="Avg Performance"
            value={analytics.avgPerformance || 0}
            suffix="%"
            icon={<CheckCircleOutlined />}
            color="#0EB57D"
            description="Vendor performance score"
          />
        </Col>
      </Row>

      {analyticsError ? (
        <Alert
          type="warning"
          showIcon
          message="Vendor metrics could not be loaded"
          description={analyticsError}
          action={<Button size="small" onClick={() => void fetchAnalytics()}>Retry</Button>}
          style={{ marginBottom: 24 }}
        />
      ) : null}

      {/* Filters */}
      {filterError ? (
        <Alert
          type="warning"
          showIcon
          message="Some vendor filters are unavailable"
          description={filterError}
          action={<Button size="small" onClick={() => void fetchDynamicData()}>Retry</Button>}
          style={{ marginBottom: 24 }}
        />
      ) : null}
      {dynamicFilters.length > 0 && (
        <FilterPanel
          filters={dynamicFilters}
          onFilterChange={handleFilterChange}
          showCount={true}
        />
      )}

      {/* Vendor Directory Table */}
      <Card
        title={
          <Space>
            <TeamOutlined />
            <Text strong>Vendor Directory</Text>
          </Space>
        }
        extra={
          <Space>
            <ExportButton
              data={vendorData}
              filename="vendor-directory"
            />
            <Button icon={<ClockCircleOutlined />} onClick={handleContractRenewals}>
              Contract Renewals
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAddVendor}>
              Add Vendor
            </Button>
          </Space>
        }
        style={{ marginBottom: 24 }}
      >
        {loading ? (
          <Loading message="Loading vendor data..." />
        ) : directoryError ? (
          <EmptyState
            type="error"
            title="Vendors could not be loaded"
            description={directoryError}
            action={{ text: 'Try again', onClick: () => void fetchVendors(filters as VendorFilters, pagination.current, pagination.pageSize) }}
          />
        ) : (
          <Table
            columns={columns}
            dataSource={vendorData.map(vendor => ({ ...vendor, key: vendor.id }))}
            pagination={{
              ...pagination,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total, range) => `${range[0]}-${range[1]} of ${total} vendors`
            }}
            onChange={handleTableChange}
            scroll={{ x: 1200 }}
          />
        )}
      </Card>

      {/* Quick Actions */}
      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card hoverable>
            <Space direction="vertical" size={8}>
              <CheckCircleOutlined style={{ fontSize: '24px', color: '#0EB57D' }} />
              <Text strong>Assessment catalogue</Text>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                Import the controls needed before starting supplier reviews
              </Text>
              <Button type="link" style={{ padding: 0 }} onClick={() => router.push('/assessments')}>
                Open setup →
              </Button>
            </Space>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card hoverable>
            <Space direction="vertical" size={8}>
              <ClockCircleOutlined style={{ fontSize: '24px', color: '#FFB020' }} />
              <Text strong>Contract Management</Text>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                Track renewals and expirations
              </Text>
              <Button type="link" style={{ padding: 0 }} onClick={() => router.push('/vendors/contracts')}>
                View Contracts →
              </Button>
            </Space>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card hoverable>
            <Space direction="vertical" size={8}>
              <WarningOutlined style={{ fontSize: '24px', color: '#E5484D' }} />
              <Text strong>Vendor review readiness</Text>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                Prepare the controls used to assess vendor risk
              </Text>
              <Button type="link" style={{ padding: 0 }} onClick={() => router.push('/assessments')}>
                Open setup →
              </Button>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* Add Vendor Modal */}
      <Modal
        title="Add New Vendor"
        open={isAddVendorModalVisible}
        onCancel={handleModalCancel}
        footer={null}
        width={700}
      >
        <Form
          form={addVendorForm}
          layout="vertical"
          onFinish={handleAddVendorSubmit}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="Vendor Name"
                rules={[{ required: true, message: 'Please enter vendor name' }]}
              >
                <Input placeholder="Enter vendor name" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="legal_name"
                label="Legal Name"
              >
                <Input placeholder="Legal business name (if different)" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="business_description"
            label="Business Description"
          >
            <Input.TextArea rows={3} placeholder="Describe the vendor's business" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="category"
                label="Category"
                rules={[{ required: true, message: 'Please select category' }]}
              >
                <Select placeholder="Select category">
                  {vendorCategories.map(category => (
                    <Select.Option key={category.id} value={category.id}>
                      {category.name}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="vendor_type"
                label="Vendor Type"
                rules={[{ required: true, message: 'Please select vendor type' }]}
              >
                <Select placeholder="Select vendor type">
                  {vendorChoices.vendor_type_choices?.map((type) => (
                    <Select.Option key={type.value} value={type.value}>
                      {type.label}
                    </Select.Option>
                  )) || []}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="website"
                label="Website"
              >
                <Input placeholder="https://vendor-website.com" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="annual_spend"
                label="Annual Spend"
              >
                <Input type="number" placeholder="Annual spend amount" addonBefore="$" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                Create Vendor
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
