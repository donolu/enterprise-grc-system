'use client'

import React, { useState, useEffect } from 'react'
import { Card, Typography, Space, Button, Row, Col, Form, Input, Select, DatePicker, Radio, Divider, Steps, message } from 'antd'
import { SafetyOutlined, ArrowLeftOutlined, CheckOutlined } from '@ant-design/icons'
import { useRouter, useSearchParams } from 'next/navigation'
import { Breadcrumb } from '@/components/ui'
import { riskService } from '@/lib/services/riskService'
import { vendorService } from '@/lib/services/vendorService'

const { Title, Text, Paragraph } = Typography
const { TextArea } = Input
const { Step } = Steps

export default function CreateAssessmentPage() {
  const [currentStep, setCurrentStep] = useState(0)
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [assessmentType, setAssessmentType] = useState<'risk' | 'vendor' | 'security'>('risk')
  const [risks, setRisks] = useState([])
  const [vendors, setVendors] = useState([])
  const router = useRouter()
  const searchParams = useSearchParams()

  useEffect(() => {
    // Check URL params for assessment type
    const type = searchParams.get('type')
    if (type === 'vendor') {
      setAssessmentType('vendor')
    } else if (type === 'security') {
      setAssessmentType('security')
    }

    // Fetch risks and vendors for selection
    fetchData()
  }, [searchParams])

  const fetchData = async () => {
    try {
      const [riskData, vendorData] = await Promise.all([
        riskService.getRisks({ pageSize: 100 }),
        vendorService.getVendors({ pageSize: 100 })
      ])
      setRisks(riskData.results)
      setVendors(vendorData.results)
    } catch (error) {
      console.error('Error fetching data:', error)
    }
  }

  const handleNext = () => {
    form.validateFields().then(() => {
      setCurrentStep(currentStep + 1)
    }).catch(() => {
      message.error('Please fill in all required fields')
    })
  }

  const handlePrevious = () => {
    setCurrentStep(currentStep - 1)
  }

  const handleSubmit = async (values: any) => {
    try {
      setLoading(true)

      // Simulate assessment creation API call
      await new Promise(resolve => setTimeout(resolve, 2000))

      message.success('Assessment created successfully!')

      // Redirect based on assessment type
      if (assessmentType === 'vendor') {
        router.push('/vendors')
      } else {
        router.push('/assessments')
      }
    } catch (error) {
      message.error('Failed to create assessment')
      console.error('Error creating assessment:', error)
    } finally {
      setLoading(false)
    }
  }

  const steps = [
    {
      title: 'Assessment Type',
      content: (
        <div>
          <Title level={4}>Select Assessment Type</Title>
          <Radio.Group
            value={assessmentType}
            onChange={(e) => setAssessmentType(e.target.value)}
            style={{ width: '100%' }}
          >
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              <Card hoverable>
                <Radio value="risk">
                  <div style={{ marginLeft: 8 }}>
                    <Text strong>Risk Assessment</Text>
                    <br />
                    <Text type="secondary">Evaluate and analyze organizational risks</Text>
                  </div>
                </Radio>
              </Card>

              <Card hoverable>
                <Radio value="vendor">
                  <div style={{ marginLeft: 8 }}>
                    <Text strong>Vendor Security Assessment</Text>
                    <br />
                    <Text type="secondary">Assess vendor security controls and compliance</Text>
                  </div>
                </Radio>
              </Card>

              <Card hoverable>
                <Radio value="security">
                  <div style={{ marginLeft: 8 }}>
                    <Text strong>Security Assessment</Text>
                    <br />
                    <Text type="secondary">Comprehensive security evaluation</Text>
                  </div>
                </Radio>
              </Card>
            </Space>
          </Radio.Group>
        </div>
      )
    },
    {
      title: 'Basic Information',
      content: (
        <div>
          <Title level={4}>Assessment Details</Title>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="title"
                label="Assessment Title"
                rules={[{ required: true, message: 'Please enter assessment title' }]}
              >
                <Input placeholder="Enter assessment title" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="assessor"
                label="Lead Assessor"
                rules={[{ required: true, message: 'Please enter lead assessor' }]}
              >
                <Input placeholder="Enter assessor name" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="description"
            label="Description"
            rules={[{ required: true, message: 'Please enter description' }]}
          >
            <TextArea rows={3} placeholder="Describe the assessment scope and objectives" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="startDate"
                label="Start Date"
                rules={[{ required: true, message: 'Please select start date' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="dueDate"
                label="Due Date"
                rules={[{ required: true, message: 'Please select due date' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          {assessmentType === 'risk' && (
            <Form.Item
              name="riskIds"
              label="Related Risks"
            >
              <Select
                mode="multiple"
                placeholder="Select related risks (optional)"
                allowClear
              >
                {risks.map((risk: any) => (
                  <Select.Option key={risk.id} value={risk.id}>
                    {risk.risk_id} - {risk.title}
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>
          )}

          {assessmentType === 'vendor' && (
            <Form.Item
              name="vendorIds"
              label="Vendors to Assess"
              rules={[{ required: true, message: 'Please select vendors to assess' }]}
            >
              <Select
                mode="multiple"
                placeholder="Select vendors to assess"
                allowClear
              >
                {vendors.map((vendor: any) => (
                  <Select.Option key={vendor.id} value={vendor.id}>
                    {vendor.name} ({vendor.vendor_id})
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>
          )}
        </div>
      )
    },
    {
      title: 'Scope & Methodology',
      content: (
        <div>
          <Title level={4}>Assessment Scope</Title>

          <Form.Item
            name="scope"
            label="Assessment Scope"
            rules={[{ required: true, message: 'Please define assessment scope' }]}
          >
            <TextArea
              rows={4}
              placeholder="Define what will be assessed, boundaries, and exclusions"
            />
          </Form.Item>

          <Form.Item
            name="methodology"
            label="Methodology"
            rules={[{ required: true, message: 'Please select methodology' }]}
          >
            <Select placeholder="Select assessment methodology">
              <Select.Option value="nist">NIST Cybersecurity Framework</Select.Option>
              <Select.Option value="iso27001">ISO 27001</Select.Option>
              <Select.Option value="cis">CIS Controls</Select.Option>
              <Select.Option value="custom">Custom Framework</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="criteria"
            label="Success Criteria"
          >
            <TextArea
              rows={3}
              placeholder="Define what constitutes successful completion of this assessment"
            />
          </Form.Item>

          <Form.Item
            name="priority"
            label="Priority"
            rules={[{ required: true, message: 'Please select priority' }]}
          >
            <Select placeholder="Select assessment priority">
              <Select.Option value="low">Low</Select.Option>
              <Select.Option value="medium">Medium</Select.Option>
              <Select.Option value="high">High</Select.Option>
              <Select.Option value="critical">Critical</Select.Option>
            </Select>
          </Form.Item>
        </div>
      )
    }
  ]

  return (
    <div>
      <Breadcrumb
        items={[
          { title: 'Assessments', href: '/assessments' },
          { title: 'Create Assessment' }
        ]}
      />

      <div style={{ marginBottom: 24 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => router.back()}>
            Back
          </Button>
        </Space>
      </div>

      <Card style={{ maxWidth: 900, margin: '0 auto' }}>
        <Title level={2} style={{ textAlign: 'center', marginBottom: 32 }}>
          <SafetyOutlined style={{ marginRight: 8 }} />
          Create New Assessment
        </Title>

        <Steps current={currentStep} style={{ marginBottom: 32 }}>
          {steps.map(item => (
            <Step key={item.title} title={item.title} />
          ))}
        </Steps>

        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <div style={{ minHeight: 400 }}>
            {steps[currentStep].content}
          </div>

          <Divider />

          <Row justify="space-between">
            <Col>
              {currentStep > 0 && (
                <Button onClick={handlePrevious}>
                  Previous
                </Button>
              )}
            </Col>
            <Col>
              {currentStep < steps.length - 1 ? (
                <Button type="primary" onClick={handleNext}>
                  Next
                </Button>
              ) : (
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={loading}
                  icon={<CheckOutlined />}
                >
                  Create Assessment
                </Button>
              )}
            </Col>
          </Row>
        </Form>
      </Card>
    </div>
  )
}