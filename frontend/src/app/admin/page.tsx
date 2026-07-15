'use client'

import React, { useMemo, useState } from 'react'
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Form,
  Input,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Typography,
  Upload,
  message,
} from 'antd'
import {
  DatabaseOutlined,
  FileSearchOutlined,
  SettingOutlined,
  UploadOutlined,
} from '@ant-design/icons'
import type { UploadProps } from 'antd'
import {
  importTemplateLibrary,
  TemplateImportResponse,
  TemplateImportSample,
} from '@/lib/services/catalogService'

const { Title, Text } = Typography

const moduleOptions = [
  { value: 'policy', label: 'Policy' },
  { value: 'standard', label: 'Standard' },
  { value: 'procedure', label: 'Procedure' },
  { value: 'iso_mandatory', label: 'ISO mandatory document' },
  { value: 'pci', label: 'PCI' },
  { value: 'risk', label: 'Risk' },
  { value: 'asset', label: 'Asset' },
  { value: 'other', label: 'Other' },
]

const documentTypeOptions = [
  { value: 'policy', label: 'Policy' },
  { value: 'standard', label: 'Standard' },
  { value: 'procedure', label: 'Procedure' },
  { value: 'mandatory_document', label: 'Mandatory document' },
  { value: 'risk_register', label: 'Risk register' },
  { value: 'asset_register', label: 'Asset register' },
  { value: 'framework_spreadsheet', label: 'Framework spreadsheet' },
  { value: 'template', label: 'Template' },
  { value: 'sample', label: 'Sample' },
  { value: 'other', label: 'Other' },
]

export default function AdminPage() {
  const [form] = Form.useForm()
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<TemplateImportResponse | null>(null)
  const [result, setResult] = useState<TemplateImportResponse | null>(null)
  const [loadingPreview, setLoadingPreview] = useState(false)
  const [loadingImport, setLoadingImport] = useState(false)

  const uploadProps: UploadProps = {
    accept: '.zip,.doc,.docx,.xls,.xlsx,.pdf,.ppt,.pptx,.csv,.txt',
    maxCount: 1,
    beforeUpload: selectedFile => {
      setFile(selectedFile as File)
      setPreview(null)
      setResult(null)
      return false
    },
    onRemove: () => {
      setFile(null)
      setPreview(null)
      setResult(null)
    },
  }

  const runImport = async (dryRun: boolean) => {
    if (!file) {
      message.error('Select a template ZIP or document first')
      return
    }

    const values = form.getFieldsValue()
    const setLoading = dryRun ? setLoadingPreview : setLoadingImport
    setLoading(true)

    try {
      const response = await importTemplateLibrary({
        file,
        dryRun,
        framework: values.framework,
        frameworkVersion: values.frameworkVersion,
        module: values.module,
        documentType: values.documentType,
      })

      if (dryRun) {
        setPreview(response)
        message.success('Import preview generated')
      } else {
        setResult(response)
        message.success('Template library imported')
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Import failed')
    } finally {
      setLoading(false)
    }
  }

  const activeSummary = result || preview
  const moduleRows = useMemo(
    () => Object.entries(activeSummary?.modules || {}).map(([module, count]) => ({ module, count })),
    [activeSummary],
  )

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>
          <SettingOutlined style={{ marginRight: 8 }} />
          System Administration
        </Title>
        <Text type="secondary">
          Manage catalogue data, template packs and controlled imports.
        </Text>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={10}>
          <Card
            title={
              <Space>
                <DatabaseOutlined />
                Template Library Import
              </Space>
            }
          >
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
              <Alert
                type="info"
                showIcon
                message="Upload an Axim ZIP pack or a single template file."
                description="Run a preview first to confirm classification counts before importing into the tenant library."
              />

              <Upload {...uploadProps}>
                <Button icon={<UploadOutlined />}>Select file</Button>
              </Upload>

              <Form form={form} layout="vertical">
                <Row gutter={12}>
                  <Col xs={24} sm={12}>
                    <Form.Item label="Framework" name="framework">
                      <Input placeholder="PCI-DSS" />
                    </Form.Item>
                  </Col>
                  <Col xs={24} sm={12}>
                    <Form.Item label="Framework version" name="frameworkVersion">
                      <Input placeholder="4.0" />
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={12}>
                  <Col xs={24} sm={12}>
                    <Form.Item label="Module override" name="module">
                      <Select allowClear options={moduleOptions} />
                    </Form.Item>
                  </Col>
                  <Col xs={24} sm={12}>
                    <Form.Item label="Document type override" name="documentType">
                      <Select allowClear options={documentTypeOptions} />
                    </Form.Item>
                  </Col>
                </Row>
              </Form>

              <Space wrap>
                <Button
                  icon={<FileSearchOutlined />}
                  onClick={() => runImport(true)}
                  loading={loadingPreview}
                  disabled={!file}
                >
                  Preview
                </Button>
                <Button
                  type="primary"
                  icon={<UploadOutlined />}
                  onClick={() => runImport(false)}
                  loading={loadingImport}
                  disabled={!file || !preview}
                >
                  Import
                </Button>
              </Space>
            </Space>
          </Card>
        </Col>

        <Col xs={24} lg={14}>
          <Card title="Import Summary">
            {!activeSummary ? (
              <div style={{ padding: '32px 0', textAlign: 'center' }}>
                <FileSearchOutlined style={{ fontSize: 40, color: '#8c8c8c', marginBottom: 12 }} />
                <div>
                  <Text type="secondary">Preview an upload to see classification counts.</Text>
                </div>
              </div>
            ) : (
              <Space direction="vertical" size={16} style={{ width: '100%' }}>
                <Row gutter={[16, 16]}>
                  <Col xs={12} md={6}>
                    <Statistic
                      title="Importable"
                      value={activeSummary.importable_count ?? activeSummary.total_importable ?? 0}
                    />
                  </Col>
                  <Col xs={12} md={6}>
                    <Statistic title="Imported" value={activeSummary.imported_count ?? 0} />
                  </Col>
                  <Col xs={12} md={6}>
                    <Statistic title="Updated" value={activeSummary.updated_count ?? 0} />
                  </Col>
                  <Col xs={12} md={6}>
                    <Statistic title="Skipped" value={activeSummary.skipped_count} />
                  </Col>
                </Row>

                <Descriptions size="small" column={1} bordered>
                  <Descriptions.Item label="Mode">
                    {activeSummary.dry_run ? 'Preview' : 'Imported'}
                  </Descriptions.Item>
                </Descriptions>

                <Table
                  size="small"
                  rowKey="module"
                  pagination={false}
                  dataSource={moduleRows}
                  columns={[
                    { title: 'Module', dataIndex: 'module' },
                    { title: 'Count', dataIndex: 'count', width: 120 },
                  ]}
                />

                {preview?.samples?.length ? (
                  <Table<TemplateImportSample>
                    size="small"
                    rowKey="source_filename"
                    pagination={false}
                    dataSource={preview.samples}
                    columns={[
                      { title: 'File', dataIndex: 'source_filename' },
                      { title: 'Module', dataIndex: 'module', width: 140 },
                      { title: 'Type', dataIndex: 'document_type', width: 170 },
                      { title: 'Linkage', dataIndex: 'linkage_status', width: 120 },
                    ]}
                  />
                ) : null}
              </Space>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}
