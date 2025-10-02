/**
 * Product Family Group Component
 * 
 * Display and manage product families (variant grouping)
 * Based on eMAG API v4.4.9 family fields
 */

import React from 'react'
import { Card, Tag, Space, Typography, Tooltip, Badge } from 'antd'
import {
  AppstoreOutlined,
  GroupOutlined
} from '@ant-design/icons'

const { Text } = Typography

interface ProductFamilyGroupProps {
  familyId?: number | null
  familyName?: string | null
  familyTypeId?: number | null
  productCount?: number
  onClick?: () => void
}

/**
 * Family Type IDs (from eMAG API):
 * 1 - Size variants (S, M, L, XL)
 * 2 - Color variants
 * 3 - Capacity variants (64GB, 128GB, 256GB)
 * 4 - Other variants
 */

const getFamilyTypeConfig = (typeId: number | null | undefined) => {
  switch (typeId) {
    case 1:
      return {
        color: 'blue',
        icon: <AppstoreOutlined />,
        text: 'Size Variants',
        description: 'Products with different sizes'
      }
    case 2:
      return {
        color: 'purple',
        icon: <AppstoreOutlined />,
        text: 'Color Variants',
        description: 'Products with different colors'
      }
    case 3:
      return {
        color: 'cyan',
        icon: <AppstoreOutlined />,
        text: 'Capacity Variants',
        description: 'Products with different capacities'
      }
    case 4:
      return {
        color: 'geekblue',
        icon: <AppstoreOutlined />,
        text: 'Other Variants',
        description: 'Other product variants'
      }
    default:
      return {
        color: 'default',
        icon: <GroupOutlined />,
        text: 'Product Family',
        description: 'Related product variants'
      }
  }
}

const ProductFamilyGroup: React.FC<ProductFamilyGroupProps> = ({
  familyId,
  familyName,
  familyTypeId,
  productCount,
  onClick
}) => {
  // If no family data, don't render
  if (!familyId && !familyName) {
    return null
  }

  const config = getFamilyTypeConfig(familyTypeId)

  return (
    <Tooltip title={config.description}>
      <Tag
        color={config.color}
        icon={config.icon}
        style={{ cursor: onClick ? 'pointer' : 'default' }}
        onClick={onClick}
      >
        <Space size="small">
          {familyName || `Family #${familyId}`}
          {productCount !== undefined && productCount > 0 && (
            <Badge count={productCount} style={{ backgroundColor: '#52c41a' }} />
          )}
        </Space>
      </Tag>
    </Tooltip>
  )
}

export const ProductFamilyCard: React.FC<{
  familyId: number
  familyName: string
  familyTypeId?: number
  products: Array<{
    id: string
    sku: string
    name: string
    price: number
    currency: string
    stock: number
  }>
  onProductClick?: (productId: string) => void
}> = ({ familyName, familyTypeId, products, onProductClick }) => {
  const config = getFamilyTypeConfig(familyTypeId)

  return (
    <Card
      title={
        <Space>
          {config.icon}
          <span>{familyName}</span>
          <Tag color={config.color}>{config.text}</Tag>
        </Space>
      }
      extra={
        <Text type="secondary">
          {products.length} variant{products.length !== 1 ? 's' : ''}
        </Text>
      }
      size="small"
    >
      <Space direction="vertical" style={{ width: '100%' }}>
        {products.map((product) => (
          <Card.Grid
            key={product.id}
            style={{ width: '100%', cursor: 'pointer' }}
            onClick={() => onProductClick?.(product.id)}
          >
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                <Text strong>{product.name}</Text>
                <Text type="secondary">{product.sku}</Text>
              </Space>
              <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                <Text>
                  {product.price.toFixed(2)} {product.currency}
                </Text>
                <Tag color={product.stock > 0 ? 'success' : 'error'}>
                  Stock: {product.stock}
                </Tag>
              </Space>
            </Space>
          </Card.Grid>
        ))}
      </Space>
    </Card>
  )
}

export default ProductFamilyGroup
