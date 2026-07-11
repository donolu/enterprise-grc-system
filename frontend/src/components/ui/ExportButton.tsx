'use client'

import React from 'react'
import { Button, Dropdown, Space, message } from 'antd'
import { DownloadOutlined, FileExcelOutlined, FilePdfOutlined, FileTextOutlined } from '@ant-design/icons'
import { useTheme } from '@/theme'

interface ExportButtonProps {
  data: any[]
  filename?: string
  disabled?: boolean
  size?: 'small' | 'middle' | 'large'
}

export const ExportButton: React.FC<ExportButtonProps> = ({
  data,
  filename = 'export',
  disabled = false,
  size = 'middle'
}) => {
  const { mode } = useTheme()
  const isDark = mode === 'dark'

  // Helper function to flatten complex objects for CSV export
  const flattenObject = (obj: any, prefix = ''): any => {
    const flattened: any = {}

    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        const value = obj[key]
        const newKey = prefix ? `${prefix}_${key}` : key

        if (value === null || value === undefined) {
          flattened[newKey] = ''
        } else if (Array.isArray(value)) {
          // Handle arrays by joining with semicolon
          flattened[newKey] = value.map(item =>
            typeof item === 'object' ? JSON.stringify(item) : String(item)
          ).join('; ')
        } else if (typeof value === 'object' && value.constructor === Object) {
          // Handle nested objects - extract common fields
          if (value.name || value.title) {
            flattened[newKey] = value.name || value.title
          } else if (value.first_name && value.last_name) {
            flattened[newKey] = `${value.first_name} ${value.last_name}`
          } else if (value.username) {
            flattened[newKey] = value.username
          } else {
            // For complex objects, store as JSON but limit length
            const jsonStr = JSON.stringify(value)
            flattened[newKey] = jsonStr.length > 100 ? jsonStr.substring(0, 100) + '...' : jsonStr
          }
        } else {
          flattened[newKey] = String(value)
        }
      }
    }

    return flattened
  }

  const exportToCSV = () => {
    if (!data || data.length === 0) {
      message.warning('No data to export')
      return
    }

    try {
      // Flatten all objects first
      const flattenedData = data.map(item => flattenObject(item))

      // Get headers from first flattened object
      const headers = Object.keys(flattenedData[0])

      // Convert data to CSV format
      const csvContent = [
        headers.join(','), // Header row
        ...flattenedData.map(row =>
          headers.map(header => {
            let value = row[header] || ''

            // Convert to string and handle special characters
            value = String(value)

            // Handle values that contain commas, quotes, or newlines
            if (value.includes(',') || value.includes('"') || value.includes('\n') || value.includes('\r')) {
              value = `"${value.replace(/"/g, '""')}"`
            }

            return value
          }).join(',')
        )
      ].join('\n')

      // Create and download file
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      const link = document.createElement('a')
      const url = URL.createObjectURL(blob)
      link.setAttribute('href', url)
      link.setAttribute('download', `${filename}.csv`)
      link.style.visibility = 'hidden'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)

      message.success('CSV file downloaded successfully')
    } catch (error) {
      message.error('Failed to export CSV file')
      console.error('CSV export error:', error)
    }
  }

  const exportToJSON = () => {
    if (!data || data.length === 0) {
      message.warning('No data to export')
      return
    }

    try {
      const jsonContent = JSON.stringify(data, null, 2)
      const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' })
      const link = document.createElement('a')
      const url = URL.createObjectURL(blob)
      link.setAttribute('href', url)
      link.setAttribute('download', `${filename}.json`)
      link.style.visibility = 'hidden'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)

      message.success('JSON file downloaded successfully')
    } catch (error) {
      message.error('Failed to export JSON file')
      console.error('JSON export error:', error)
    }
  }

  const exportToPDF = () => {
    message.info('PDF export will be available soon')
    // This would integrate with a PDF generation service or library
  }

  const menuItems = [
    {
      key: 'csv',
      icon: <FileExcelOutlined />,
      label: 'Export as CSV',
      onClick: exportToCSV
    },
    {
      key: 'json',
      icon: <FileTextOutlined />,
      label: 'Export as JSON',
      onClick: exportToJSON
    },
    {
      key: 'pdf',
      icon: <FilePdfOutlined />,
      label: 'Export as PDF',
      onClick: exportToPDF,
      disabled: true // Coming soon
    }
  ]

  return (
    <Dropdown
      menu={{ items: menuItems }}
      placement="bottomRight"
      disabled={disabled}
    >
      <Button
        icon={<DownloadOutlined />}
        size={size}
        disabled={disabled}
        style={{
          borderColor: isDark ? '#2A3441' : '#E7EBF0'
        }}
      >
        Export
      </Button>
    </Dropdown>
  )
}

export default ExportButton