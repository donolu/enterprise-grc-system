'use client'

import React, { useState, useEffect } from 'react'
import { Card, Typography, Space, Button, Row, Col, Table, Tag, Progress, Avatar, message, Modal, Form, Input, Select } from 'antd'
import { TeamOutlined, PlusOutlined, WarningOutlined, CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons'
import { useRouter } from 'next/navigation'
import { Breadcrumb, VendorKPICard, KPICard, StatusTag, PriorityTag, Loading, ExportButton, FilterPanel } from '@/components/ui'
import { vendorService, type Vendor, type VendorCategory } from '@/lib/services/vendorService'

const { Title, Text } = Typography

export default function VendorsPage() {
  const [loading, setLoading] = useState(true)
  const [vendorData, setVendorData] = useState<Vendor[]>([])
  const [analytics, setAnalytics] = useState<any>({
    totalVendors: 0,
    contractsExpiring: 0,
    highRiskVendors: 0,
    avgPerformance: 0,
    performanceTrend: 0
  })
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 })
  const [filters, setFilters] = useState<any>({})
  const [dynamicFilters, setDynamicFilters] = useState<any[]>([])
  const [vendorCategories, setVendorCategories] = useState<VendorCategory[]>([])
  const [vendorChoices, setVendorChoices] = useState<any>({})
  const [isAddVendorModalVisible, setIsAddVendorModalVisible] = useState(false)
  const [addVendorForm] = Form.useForm()
  const router = useRouter()

  // Fetch vendors data
  const fetchVendors = async (currentFilters = filters, page = 1, pageSize = 10) => {
    try {
      setLoading(true)
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
      message.error('Failed to load vendor data')
      console.error('Error fetching vendors:', error)
    } finally {
      setLoading(false)
    }
  }

  // Fetch analytics
  const fetchAnalytics = async () => {
    try {
      const data = await vendorService.getVendorAnalytics()
      setAnalytics(data)
    } catch (error) {
      console.error('Error fetching analytics:', error)
    }
  }

  // Fetch dynamic filter data
  const fetchDynamicData = async () => {
    try {
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
      console.error('Error fetching dynamic filter data:', error)
      // Set fallback filters if API fails
      setDynamicFilters([
        {
          key: 'search',
          label: 'Search',
          type: 'search' as const,
          placeholder: 'Search vendors'
        }
      ])
    }
  }

  useEffect(() => {
    fetchVendors()
    fetchAnalytics()
    fetchDynamicData()
  }, [])

  // Handle filter changes
  const handleFilterChange = (newFilters: any) => {
    setFilters(newFilters)
    fetchVendors(newFilters, 1, pagination.pageSize)
  }

  // Handle table pagination/sorting
  const handleTableChange = (paginationConfig: any) => {
    fetchVendors(filters, paginationConfig.current, paginationConfig.pageSize)
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
  const handleAddVendorSubmit = async (values: any) => {
    try {
      await vendorService.createVendor(values)
      message.success('Vendor created successfully')
      setIsAddVendorModalVisible(false)
      addVendorForm.resetFields()
      fetchVendors() // Refresh the list
    } catch (error) {
      message.error('Failed to create vendor')
      console.error('Error creating vendor:', error)
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
      render: (owner: any) => {
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

      <div style={{ marginBottom: 24 }}>
        <Title level={2}>
          <TeamOutlined style={{ marginRight: 8 }} />
          Vendor Management
        </Title>
        <Text type="secondary">
          Manage vendor relationships, assessments, and risk profiles across the organization
        </Text>
      </div>

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
            trend={{ value: Math.abs(analytics.performanceTrend || 0), isPositive: (analytics.performanceTrend || 0) > 0, period: "vs last quarter" }}
            description="Vendor performance score"
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
              <Text strong>Security Assessment</Text>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                Conduct vendor security evaluations
              </Text>
              <Button type="link" style={{ padding: 0 }} onClick={() => router.push('/assessments/create?type=vendor')}>
                Start Assessment →
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
              <Text strong>Risk Assessment</Text>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                Evaluate vendor risk profiles
              </Text>
              <Button type="link" style={{ padding: 0 }} onClick={() => router.push('/vendors/risk-assessment')}>
                Assess Risk →
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
                  {vendorChoices.vendor_type_choices?.map((type: any) => (
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