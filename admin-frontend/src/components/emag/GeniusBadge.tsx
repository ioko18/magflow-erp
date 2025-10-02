/**
 * Genius Program Badge Component
 * 
 * Displays eMAG Genius program eligibility and status
 * Based on eMAG API v4.4.9 genius_eligibility fields
 */

import React from 'react'
import { Tag, Tooltip, Space } from 'antd'
import {
  ThunderboltOutlined,
  RocketOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined
} from '@ant-design/icons'

interface GeniusBadgeProps {
  eligibility?: number | null  // 0=not eligible, 1=eligible
  eligibilityType?: number | null  // 1=Full, 2=EasyBox, 3=HD
  computed?: number | null  // 0=not active, 1=Full, 2=EasyBox, 3=HD
  showDetails?: boolean
}

/**
 * Genius Eligibility Types (from API v4.4.9):
 * 1 - Full Genius (all delivery methods)
 * 2 - EasyBox only
 * 3 - Home Delivery only
 */

const getGeniusTypeConfig = (type: number | null | undefined) => {
  switch (type) {
    case 1:
      return {
        color: 'gold',
        icon: <ThunderboltOutlined />,
        text: 'Genius Full',
        description: 'Full Genius program - all delivery methods'
      }
    case 2:
      return {
        color: 'blue',
        icon: <RocketOutlined />,
        text: 'Genius EasyBox',
        description: 'Genius EasyBox only'
      }
    case 3:
      return {
        color: 'cyan',
        icon: <RocketOutlined />,
        text: 'Genius HD',
        description: 'Genius Home Delivery only'
      }
    default:
      return {
        color: 'default',
        icon: <ThunderboltOutlined />,
        text: 'Genius',
        description: 'Genius program'
      }
  }
}

const GeniusBadge: React.FC<GeniusBadgeProps> = ({
  eligibility,
  eligibilityType,
  computed,
  showDetails = true
}) => {
  // If not eligible, show nothing or a disabled badge
  if (eligibility === 0 || eligibility === null || eligibility === undefined) {
    if (!showDetails) return null
    
    return (
      <Tooltip title="Not eligible for Genius program">
        <Tag color="default" icon={<CloseCircleOutlined />}>
          No Genius
        </Tag>
      </Tooltip>
    )
  }

  // Eligible but not active
  if (computed === 0 || computed === null || computed === undefined) {
    const config = getGeniusTypeConfig(eligibilityType)
    return (
      <Tooltip title={`Eligible for ${config.text} but not currently active`}>
        <Tag color="warning" icon={config.icon}>
          {config.text} (Eligible)
        </Tag>
      </Tooltip>
    )
  }

  // Active Genius
  const config = getGeniusTypeConfig(computed)
  return (
    <Tooltip title={`${config.description} - Currently active`}>
      <Tag color={config.color} icon={<CheckCircleOutlined />}>
        {config.text} ⚡
      </Tag>
    </Tooltip>
  )
}

export const GeniusEligibilityFilter: React.FC<{
  value?: string
  onChange?: (value: string | undefined) => void
}> = ({ value, onChange }) => {
  return (
    <Space>
      <Tag.CheckableTag
        checked={value === 'all' || value === undefined}
        onChange={() => onChange?.(undefined)}
      >
        All Products
      </Tag.CheckableTag>
      <Tag.CheckableTag
        checked={value === 'eligible'}
        onChange={() => onChange?.('eligible')}
      >
        <ThunderboltOutlined /> Genius Eligible
      </Tag.CheckableTag>
      <Tag.CheckableTag
        checked={value === 'active'}
        onChange={() => onChange?.('active')}
      >
        <CheckCircleOutlined /> Genius Active
      </Tag.CheckableTag>
      <Tag.CheckableTag
        checked={value === 'not_eligible'}
        onChange={() => onChange?.('not_eligible')}
      >
        <CloseCircleOutlined /> Not Eligible
      </Tag.CheckableTag>
    </Space>
  )
}

export default GeniusBadge
