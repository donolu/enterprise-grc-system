'use client'

import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Button, Card, Space, Table, Tag, Typography } from 'antd'
import { ArrowLeftOutlined, ClockCircleOutlined, TeamOutlined, WarningOutlined } from '@ant-design/icons'
import { useRouter } from 'next/navigation'
import { api, getErrorMessage } from '@/lib/api'
import { Breadcrumb, EmptyState, Loading, PageHeader } from '@/components/ui'

const { Text } = Typography

interface VendorContract {
  id: number
  vendor_id: string
  name: string
  primary_contract_number: string
  contract_start_date: string | null
  contract_end_date: string | null
  auto_renewal: boolean
  renewal_notice_days: number
  days_until_contract_expiry: number | null
}

interface PaginatedResponse<T> {
  results: T[]
}

function formatDate(value: string | null) {
  if (!value) return 'Not recorded'
  return new Date(value).toLocaleDateString('en-GB', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function contractStatus(days: number | null, renewalNoticeDays: number) {
  if (days === null) return { label: 'Not recorded', colour: 'default' }
  if (days < 0) return { label: 'Expired', colour: 'red' }
  if (days <= renewalNoticeDays) return { label: 'Renewal due', colour: 'orange' }
  return { label: 'Active', colour: 'green' }
}

export default function VendorContractsPage() {
  const router = useRouter()
  const [contracts, setContracts] = useState<VendorContract[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const fetchContracts = useCallback(async () => {
    try {
      setLoading(true)
      setLoadError(null)
      const response = await api.get<PaginatedResponse<VendorContract>>('/vendors/vendors/', {
        params: { page_size: 100 },
      })
      setContracts(response.data.results.filter((vendor) => Boolean(vendor.primary_contract_number || vendor.contract_end_date)))
    } catch (error: unknown) {
      setContracts([])
      setLoadError(getErrorMessage(error))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetchContracts()
  }, [fetchContracts])

  const columns = useMemo(() => [
    {
      title: 'Contract',
      dataIndex: 'primary_contract_number',
      key: 'primary_contract_number',
      render: (contractNumber: string, contract: VendorContract) => (
        <Button type="link" style={{ padding: 0 }} onClick={() => router.push(`/vendors/${contract.id}`)}>
          {contractNumber || contract.vendor_id}
        </Button>
      ),
    },
    {
      title: 'Vendor',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, contract: VendorContract) => (
        <Button type="link" style={{ padding: 0 }} onClick={() => router.push(`/vendors/${contract.id}`)}>
          {name}
        </Button>
      ),
    },
    {
      title: 'Start date',
      dataIndex: 'contract_start_date',
      key: 'contract_start_date',
      render: formatDate,
    },
    {
      title: 'End date',
      dataIndex: 'contract_end_date',
      key: 'contract_end_date',
      render: formatDate,
    },
    {
      title: 'Status',
      key: 'status',
      render: (_: unknown, contract: VendorContract) => {
        const status = contractStatus(contract.days_until_contract_expiry, contract.renewal_notice_days)
        return <Tag color={status.colour}>{status.label}</Tag>
      },
    },
    {
      title: 'Expiry',
      dataIndex: 'days_until_contract_expiry',
      key: 'days_until_contract_expiry',
      render: (days: number | null, contract: VendorContract) => {
        if (days === null) return <Text type="secondary">Not recorded</Text>
        const needsAttention = days <= contract.renewal_notice_days
        return (
          <Space size={6}>
            <Text type={needsAttention ? 'danger' : undefined}>
              {days < 0 ? `${Math.abs(days)} days overdue` : `${days} days`}
            </Text>
            {needsAttention && <WarningOutlined style={{ color: '#E5484D' }} />}
          </Space>
        )
      },
    },
    {
      title: 'Renewal',
      dataIndex: 'auto_renewal',
      key: 'auto_renewal',
      render: (autoRenewal: boolean) => autoRenewal ? 'Automatic' : 'Manual',
    },
  ], [router])

  if (loading) return <Loading message="Loading vendor contracts..." />

  return (
    <div>
      <Breadcrumb items={[
        { title: 'Vendor Management', href: '/vendors', icon: <TeamOutlined /> },
        { title: 'Contract Management' },
      ]} />

      <div style={{ marginBottom: 24 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/vendors')}>Back to vendors</Button>
      </div>

      <PageHeader
        eyebrow="THIRD-PARTY ASSURANCE"
        title="Contract management"
        description="Track the contract dates and renewal settings recorded against your vendors."
        icon={<ClockCircleOutlined />}
      />

      {loadError ? (
        <EmptyState
          type="error"
          title="Contracts could not be loaded"
          description={loadError}
          action={{ text: 'Try again', onClick: () => void fetchContracts() }}
        />
      ) : contracts.length === 0 ? (
        <EmptyState
          type="vendors"
          title="No vendor contracts recorded"
          description="Contract records will appear here once a vendor has a contract number or end date."
          action={{ text: 'Open vendor management', onClick: () => router.push('/vendors') }}
        />
      ) : (
        <Card style={{ marginTop: 24 }}>
          <Table columns={columns} dataSource={contracts} rowKey="id" pagination={{ pageSize: 20 }} />
        </Card>
      )}
    </div>
  )
}
