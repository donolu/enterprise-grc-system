'use client'

import React from 'react'
import { Card, Typography, Space, Button, Table, Tag, Progress } from 'antd'
import { TeamOutlined, ArrowLeftOutlined, ClockCircleOutlined, WarningOutlined } from '@ant-design/icons'
import { useRouter } from 'next/navigation'
import { Breadcrumb } from '@/components/ui'

const { Title, Text } = Typography

export default function VendorContractsPage() {
  const router = useRouter()

  // Mock contract data
  const contracts = [
    {
      id: 1,
      vendor: 'Microsoft Corporation',
      contractId: 'CONT-2024-001',
      startDate: '2023-01-01',
      endDate: '2024-12-31',
      value: 120000,
      status: 'active',
      autoRenewal: true,
      daysToExpiry: 128
    },
    {
      id: 2,
      vendor: 'Amazon Web Services',
      contractId: 'CONT-2024-002',
      startDate: '2023-06-01',
      endDate: '2024-11-30',
      value: 85000,
      status: 'expiring_soon',
      autoRenewal: false,
      daysToExpiry: 97
    }
  ]

  const columns = [
    {
      title: 'Contract ID',
      dataIndex: 'contractId',
      key: 'contractId',
      render: (text: string) => <Text strong style={{ color: '#2F6FED' }}>{text}</Text>
    },
    {
      title: 'Vendor',
      dataIndex: 'vendor',
      key: 'vendor',
    },
    {
      title: 'Value',
      dataIndex: 'value',
      key: 'value',
      render: (value: number) => `$${value.toLocaleString()}`
    },
    {
      title: 'Start Date',
      dataIndex: 'startDate',
      key: 'startDate',
    },
    {
      title: 'End Date',
      dataIndex: 'endDate',
      key: 'endDate',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colors = {
          active: 'green',
          expiring_soon: 'orange',
          expired: 'red'
        }
        return <Tag color={colors[status as keyof typeof colors]}>{status.replace('_', ' ').toUpperCase()}</Tag>
      }
    },
    {
      title: 'Days to Expiry',
      dataIndex: 'daysToExpiry',
      key: 'daysToExpiry',
      render: (days: number) => (
        <Space>
          <Text style={{ color: days < 90 ? '#E5484D' : days < 180 ? '#FFB020' : '#0EB57D' }}>
            {days} days
          </Text>
          {days < 90 && <WarningOutlined style={{ color: '#E5484D' }} />}
        </Space>
      )
    }
  ]

  return (
    <div>
      <Breadcrumb
        items={[
          { title: 'Vendor Management', href: '/vendors', icon: <TeamOutlined /> },
          { title: 'Contract Management' }
        ]}
      />

      <div style={{ marginBottom: 24 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => router.back()}>
            Back
          </Button>
        </Space>
      </div>

      <Title level={2}>
        <ClockCircleOutlined style={{ marginRight: 8 }} />
        Contract Management
      </Title>
      <Text type="secondary">
        Track vendor contracts, renewals, and expirations
      </Text>

      <Card style={{ marginTop: 24 }}>
        <Table
          columns={columns}
          dataSource={contracts.map(contract => ({ ...contract, key: contract.id }))}
          pagination={false}
        />
      </Card>
    </div>
  )
}