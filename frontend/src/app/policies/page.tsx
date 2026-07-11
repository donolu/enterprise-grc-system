'use client'

import React, { useEffect, useState } from 'react'
import { Card, Row, Col, Typography, Button, Empty, Spin, message, Badge, Tag } from 'antd'
import { FileTextOutlined, CheckCircleOutlined, ClockCircleOutlined, ExclamationCircleOutlined } from '@ant-design/icons'
import { api } from '@/lib/api'
import { useTheme } from '@/theme'

const { Title, Text, Paragraph } = Typography

interface PolicyForAcknowledgment {
  distribution_id: string
  policy: {
    id: string
    title: string
    policy_code: string
    category: string | null
    policy_type: string
  }
  version: {
    id: string
    version_number: string
    effective_date: string
    summary: string | null
    document: string | null
  }
  distribution: {
    distributed_at: string
    reminder_count: number
    last_reminder_sent: string | null
    is_overdue: boolean
  }
}

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<PolicyForAcknowledgment[]>([])
  const [loading, setLoading] = useState(true)
  const [acknowledging, setAcknowledging] = useState<string | null>(null)
  const { mode } = useTheme()
  const isDark = mode === 'dark'

  useEffect(() => {
    fetchMyPolicies()
  }, [])

  const fetchMyPolicies = async () => {
    try {
      setLoading(true)

      // Mock data for development
      const mockPolicies = [
        {
          distribution_id: '1',
          policy: {
            id: '1',
            title: 'Information Security Policy',
            policy_code: 'ISP-001',
            category: 'Security',
            policy_type: 'Mandatory'
          },
          version: {
            id: '1',
            version_number: '2.1',
            effective_date: '2024-01-15',
            summary: 'Updated security policy with new remote work guidelines and multi-factor authentication requirements.',
            document: null
          },
          distribution: {
            distributed_at: '2024-08-15T10:00:00Z',
            reminder_count: 1,
            last_reminder_sent: '2024-08-22T10:00:00Z',
            is_overdue: true
          }
        },
        {
          distribution_id: '2',
          policy: {
            id: '2',
            title: 'Data Privacy & Protection Policy',
            policy_code: 'DPP-001',
            category: 'Privacy',
            policy_type: 'Mandatory'
          },
          version: {
            id: '2',
            version_number: '1.3',
            effective_date: '2024-03-01',
            summary: 'Comprehensive data privacy policy aligned with GDPR and CCPA requirements.',
            document: '/documents/privacy-policy-v1.3.pdf'
          },
          distribution: {
            distributed_at: '2024-08-10T09:00:00Z',
            reminder_count: 0,
            last_reminder_sent: null,
            is_overdue: false
          }
        }
      ]

      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 600))
      setPolicies(mockPolicies)

      // Uncomment when backend is ready:
      // const response = await api.get('/api/policies/policies/my_policies/')
      // setPolicies(response.data.policies || [])
    } catch (error) {
      console.error('Failed to fetch policies:', error)
      message.error('Backend not available - showing demo data')
    } finally {
      setLoading(false)
    }
  }

  const handleAcknowledge = async (policyId: string) => {
    try {
      setAcknowledging(policyId)
      await api.post(`/api/policies/policies/${policyId}/acknowledge/`)
      message.success('Policy acknowledged successfully!')

      // Remove the acknowledged policy from the list
      setPolicies(prev => prev.filter(p => p.policy.id !== policyId))
    } catch (error: any) {
      console.error('Failed to acknowledge policy:', error)
      const errorMsg = error.response?.data?.error || 'Failed to acknowledge policy'
      message.error(errorMsg)
    } finally {
      setAcknowledging(null)
    }
  }

  const handleViewDocument = (documentUrl: string) => {
    window.open(documentUrl, '_blank')
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }

  const getDaysAgo = (dateString: string) => {
    const days = Math.floor((new Date().getTime() - new Date(dateString).getTime()) / (1000 * 60 * 60 * 24))
    return days
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>Loading your policies...</div>
      </div>
    )
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>
          <FileTextOutlined style={{ marginRight: 8 }} />
          Policy Acknowledgments
        </Title>
        <Text type="secondary">
          Review and acknowledge the policies assigned to you. These policies require your acknowledgment to ensure compliance.
        </Text>
      </div>

      {policies.length === 0 ? (
        <Card>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <span>
                <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                All caught up! You have no policies requiring acknowledgment.
              </span>
            }
          />
        </Card>
      ) : (
        <>
          <div style={{ marginBottom: 16 }}>
            <Text strong>{policies.length} policies require your acknowledgment</Text>
            {policies.some(p => p.distribution.is_overdue) && (
              <Badge
                count={policies.filter(p => p.distribution.is_overdue).length}
                style={{ backgroundColor: '#f5222d', marginLeft: 8 }}
              />
            )}
          </div>

          <Row gutter={[16, 16]}>
            {policies.map((policy) => (
              <Col xs={24} lg={12} key={policy.policy.id}>
                <Card
                  title={
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <Text strong>{policy.policy.title}</Text>
                        {policy.distribution.is_overdue && (
                          <Badge status="error" text="Overdue" />
                        )}
                      </div>
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        {policy.policy.policy_code} - Version {policy.version.version_number}
                      </Text>
                    </div>
                  }
                  extra={
                    <div>
                      {policy.policy.category && (
                        <Tag color={getCategoryColor(policy.policy.category)}>
                          {policy.policy.category}
                        </Tag>
                      )}
                    </div>
                  }
                  actions={[
                    ...(policy.version.document ? [
                      <Button
                        key="view"
                        type="link"
                        icon={<FileTextOutlined />}
                        onClick={() => handleViewDocument(policy.version.document!)}
                      >
                        View Document
                      </Button>
                    ] : []),
                    <Button
                      key="acknowledge"
                      type="primary"
                      icon={<CheckCircleOutlined />}
                      loading={acknowledging === policy.policy.id}
                      onClick={() => handleAcknowledge(policy.policy.id)}
                      style={{ backgroundColor: '#52c41a', borderColor: '#52c41a' }}
                    >
                      Acknowledge
                    </Button>
                  ]}
                  style={{
                    borderColor: policy.distribution.is_overdue ? '#f5222d' : undefined,
                    backgroundColor: policy.distribution.is_overdue
                      ? (isDark ? 'rgba(245, 34, 45, 0.05)' : '#fff2f0')
                      : undefined
                  }}
                >
                  <div style={{ marginBottom: 12 }}>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Text strong style={{ color: isDark ? '#F8FAFC' : undefined }}>Type:</Text>
                        <br />
                        <Text style={{ color: isDark ? '#CBD5E1' : undefined }}>{policy.policy.policy_type}</Text>
                      </Col>
                      <Col span={12}>
                        <Text strong style={{ color: isDark ? '#F8FAFC' : undefined }}>Effective Date:</Text>
                        <br />
                        <Text style={{ color: isDark ? '#CBD5E1' : undefined }}>{formatDate(policy.version.effective_date)}</Text>
                      </Col>
                    </Row>
                  </div>

                  <div style={{ marginBottom: 12 }}>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Text strong style={{ color: isDark ? '#F8FAFC' : undefined }}>Distributed:</Text>
                        <br />
                        <Text style={{ color: isDark ? '#CBD5E1' : undefined }}>
                          {getDaysAgo(policy.distribution.distributed_at)} days ago
                        </Text>
                      </Col>
                      <Col span={12}>
                        <Text strong style={{ color: isDark ? '#F8FAFC' : undefined }}>Reminders:</Text>
                        <br />
                        <Text style={{ color: isDark ? '#CBD5E1' : undefined }}>{policy.distribution.reminder_count} sent</Text>
                      </Col>
                    </Row>
                  </div>

                  {policy.version.summary && (
                    <div style={{ marginBottom: 12 }}>
                      <Text strong style={{ color: isDark ? '#F8FAFC' : undefined }}>Summary:</Text>
                      <Paragraph
                        ellipsis={{ rows: 3, expandable: true, symbol: 'more' }}
                        style={{
                          margin: '4px 0 0 0',
                          color: isDark ? '#CBD5E1' : undefined
                        }}
                      >
                        {policy.version.summary}
                      </Paragraph>
                    </div>
                  )}

                  {policy.distribution.is_overdue && (
                    <div
                      style={{
                        padding: '8px 12px',
                        background: isDark ? 'rgba(245, 34, 45, 0.1)' : '#ffebee',
                        border: `1px solid ${isDark ? 'rgba(245, 34, 45, 0.3)' : '#ffcdd2'}`,
                        borderRadius: '6px',
                        marginTop: 12
                      }}
                    >
                      <ExclamationCircleOutlined style={{ color: '#f5222d', marginRight: 8 }} />
                      <Text style={{ color: isDark ? '#ff7875' : '#cf1322' }}>
                        This policy acknowledgment is overdue. Please review and acknowledge as soon as possible.
                      </Text>
                    </div>
                  )}
                </Card>
              </Col>
            ))}
          </Row>
        </>
      )}
    </div>
  )
}