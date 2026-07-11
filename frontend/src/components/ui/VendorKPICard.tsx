'use client'

import React from 'react'
import { KPICard } from './KPICard'
import { TeamOutlined } from '@ant-design/icons'

interface VendorKPICardProps {
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

export const VendorKPICard: React.FC<VendorKPICardProps> = ({
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
      icon={<TeamOutlined />}
      color="#2F6FED"
      description={description}
      trend={trend}
      onClick={onClick}
    />
  )
}

export default VendorKPICard