'use client'

import React from 'react'
import { KPICard } from './KPICard'
import { SafetyOutlined } from '@ant-design/icons'

interface RiskKPICardProps {
  title: string
  value: number
  description?: string
  trend?: {
    value: number
    isPositive?: boolean
    period?: string
  }
  onClick?: () => void
}

export const RiskKPICard: React.FC<RiskKPICardProps> = ({
  title,
  value,
  description,
  trend,
  onClick
}) => {
  return (
    <KPICard
      title={title}
      value={value}
      icon={<SafetyOutlined />}
      color="#E5484D"
      description={description}
      trend={trend}
      onClick={onClick}
    />
  )
}

export default RiskKPICard