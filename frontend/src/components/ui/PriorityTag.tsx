'use client'

import React from 'react'
import { Tag } from 'antd'
import {
  ExclamationCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined
} from '@ant-design/icons'

interface PriorityTagProps {
  status: 'low' | 'medium' | 'high' | 'critical' | string
  showIcon?: boolean
}

export const PriorityTag: React.FC<PriorityTagProps> = ({
  status,
  showIcon = true
}) => {
  const statusConfig = {
    low: {
      color: '#10b981',
      backgroundColor: '#ecfdf5',
      borderColor: '#10b981',
      label: 'Low',
      icon: <CheckCircleOutlined />
    },
    medium: {
      color: '#f59e0b',
      backgroundColor: '#fffbeb',
      borderColor: '#f59e0b',
      label: 'Medium',
      icon: <InfoCircleOutlined />
    },
    high: {
      color: '#ef4444',
      backgroundColor: '#fef2f2',
      borderColor: '#ef4444',
      label: 'High',
      icon: <WarningOutlined />
    },
    critical: {
      color: '#dc2626',
      backgroundColor: '#fef2f2',
      borderColor: '#dc2626',
      label: 'Critical',
      icon: <ExclamationCircleOutlined />
    }
  }

  const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.medium

  return (
    <Tag
      style={{
        color: config.color,
        backgroundColor: config.backgroundColor,
        borderColor: config.borderColor,
        borderStyle: 'solid',
        borderWidth: '1px'
      }}
      icon={showIcon ? config.icon : undefined}
    >
      {config.label}
    </Tag>
  )
}

export default PriorityTag