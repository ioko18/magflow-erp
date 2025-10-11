/**
 * Purchase Order Status Badge Component
 * Displays a colored badge for purchase order status
 */

import React from 'react';
import type { PurchaseOrderStatus } from '../../types/purchaseOrder';

interface PurchaseOrderStatusBadgeProps {
  status: PurchaseOrderStatus;
  className?: string;
}

const statusConfig: Record<PurchaseOrderStatus, {
  label: string;
  color: string;
  bgColor: string;
  icon?: string;
}> = {
  draft: {
    label: 'Draft',
    color: 'text-gray-700',
    bgColor: 'bg-gray-100',
    icon: '📝',
  },
  sent: {
    label: 'Sent',
    color: 'text-blue-700',
    bgColor: 'bg-blue-100',
    icon: '📤',
  },
  confirmed: {
    label: 'Confirmed',
    color: 'text-indigo-700',
    bgColor: 'bg-indigo-100',
    icon: '✅',
  },
  partially_received: {
    label: 'Partially Received',
    color: 'text-yellow-700',
    bgColor: 'bg-yellow-100',
    icon: '📦',
  },
  received: {
    label: 'Received',
    color: 'text-green-700',
    bgColor: 'bg-green-100',
    icon: '✓',
  },
  cancelled: {
    label: 'Cancelled',
    color: 'text-red-700',
    bgColor: 'bg-red-100',
    icon: '✗',
  },
};

export const PurchaseOrderStatusBadge: React.FC<PurchaseOrderStatusBadgeProps> = ({
  status,
  className = '',
}) => {
  const config = statusConfig[status];

  if (!config) {
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 ${className}`}>
        {status}
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.bgColor} ${config.color} ${className}`}
      title={config.label}
    >
      {config.icon && <span className="mr-1">{config.icon}</span>}
      {config.label}
    </span>
  );
};

export default PurchaseOrderStatusBadge;
