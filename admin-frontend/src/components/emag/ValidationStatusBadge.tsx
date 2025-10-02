/**
 * Validation Status Badge Component
 * 
 * Displays eMAG product validation status with color-coded badges
 * Based on eMAG API v4.4.9 validation_status field
 */

import React from 'react'
import { Tag, Tooltip } from 'antd'
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  SyncOutlined,
  QuestionCircleOutlined
} from '@ant-design/icons'

interface ValidationStatusBadgeProps {
  status?: number | null
  description?: string | null
  showDescription?: boolean
}

/**
 * eMAG Validation Status Codes (from API v4.4.9):
 * 0 - Draft (not sent for validation)
 * 1 - Pending validation
 * 2 - Approved
 * 3 - Rejected
 * 4 - Pending changes
 * 5 - Inactive
 * 6 - Deleted
 * 7 - Pending deletion
 * 8 - Pending activation
 * 9 - Pending deactivation
 * 10 - Pending update
 * 11 - Pending category change
 * 12 - Pending brand change
 */

const getValidationStatusConfig = (status: number | null | undefined) => {
  switch (status) {
    case 0:
      return {
        color: 'default',
        icon: <QuestionCircleOutlined />,
        text: 'Draft',
        description: 'Not sent for validation'
      }
    case 1:
      return {
        color: 'processing',
        icon: <ClockCircleOutlined />,
        text: 'Pending',
        description: 'Awaiting validation'
      }
    case 2:
      return {
        color: 'success',
        icon: <CheckCircleOutlined />,
        text: 'Approved',
        description: 'Product approved and active'
      }
    case 3:
      return {
        color: 'error',
        icon: <CloseCircleOutlined />,
        text: 'Rejected',
        description: 'Product rejected - needs changes'
      }
    case 4:
      return {
        color: 'warning',
        icon: <WarningOutlined />,
        text: 'Changes Required',
        description: 'Pending changes from seller'
      }
    case 5:
      return {
        color: 'default',
        icon: <CloseCircleOutlined />,
        text: 'Inactive',
        description: 'Product is inactive'
      }
    case 6:
      return {
        color: 'error',
        icon: <CloseCircleOutlined />,
        text: 'Deleted',
        description: 'Product deleted'
      }
    case 7:
      return {
        color: 'warning',
        icon: <SyncOutlined />,
        text: 'Pending Deletion',
        description: 'Scheduled for deletion'
      }
    case 8:
      return {
        color: 'processing',
        icon: <SyncOutlined />,
        text: 'Pending Activation',
        description: 'Scheduled for activation'
      }
    case 9:
      return {
        color: 'processing',
        icon: <SyncOutlined />,
        text: 'Pending Deactivation',
        description: 'Scheduled for deactivation'
      }
    case 10:
      return {
        color: 'processing',
        icon: <SyncOutlined />,
        text: 'Pending Update',
        description: 'Update in progress'
      }
    case 11:
      return {
        color: 'processing',
        icon: <SyncOutlined />,
        text: 'Category Change',
        description: 'Category change pending'
      }
    case 12:
      return {
        color: 'processing',
        icon: <SyncOutlined />,
        text: 'Brand Change',
        description: 'Brand change pending'
      }
    default:
      return {
        color: 'default',
        icon: <QuestionCircleOutlined />,
        text: 'Unknown',
        description: 'Status not available'
      }
  }
}

const ValidationStatusBadge: React.FC<ValidationStatusBadgeProps> = ({
  status,
  description,
  showDescription = true
}) => {
  const config = getValidationStatusConfig(status)
  const tooltipText = description || config.description

  return (
    <Tooltip title={showDescription ? tooltipText : undefined}>
      <Tag color={config.color} icon={config.icon}>
        {config.text}
      </Tag>
    </Tooltip>
  )
}

export default ValidationStatusBadge
