/**
 * EAN Search Modal Component
 * 
 * Search for products by EAN code using eMAG API v4.4.9
 * Allows quick product lookup and offer attachment
 */

import React, { useState } from 'react'
import {
  Modal,
  Input,
  Button,
  Table,
  Space,
  message,
  Alert,
  Spin,
  Typography,
  Divider
} from 'antd'
import {
  SearchOutlined,
  BarcodeOutlined,
  LinkOutlined
} from '@ant-design/icons'
import api from '../../services/api'
import type { ColumnsType } from 'antd/es/table'

const { Text, Title } = Typography

interface EanSearchModalProps {
  visible: boolean
  onClose: () => void
  onProductSelected?: (product: EmagProduct) => void
}

interface EmagProduct {
  id: number
  name: string
  part_number: string
  part_number_key: string
  category_id: number
  category_name: string
  brand: string
  ean: string[]
  images: string[]
  sale_price: number
  currency: string
  vat_rate: number
}

const EanSearchModal: React.FC<EanSearchModalProps> = ({
  visible,
  onClose,
  onProductSelected
}) => {
  const [eanInput, setEanInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [searchResults, setSearchResults] = useState<EmagProduct[]>([])
  const [searched, setSearched] = useState(false)

  const handleSearch = async () => {
    if (!eanInput.trim()) {
      message.warning('Please enter at least one EAN code')
      return
    }

    // Split by comma, newline, or space and clean up
    const eanCodes = eanInput
      .split(/[,\n\s]+/)
      .map(ean => ean.trim())
      .filter(ean => ean.length > 0)

    if (eanCodes.length === 0) {
      message.warning('No valid EAN codes found')
      return
    }

    if (eanCodes.length > 100) {
      message.warning('Maximum 100 EAN codes allowed per search')
      return
    }

    setLoading(true)
    setSearched(true)

    try {
      const response = await api.post('/emag/ean-matching/find-by-eans', {
        ean_codes: eanCodes
      })

      if (response.data && response.data.products) {
        setSearchResults(response.data.products)
        
        if (response.data.products.length === 0) {
          message.info('No products found for the provided EAN codes')
        } else {
          message.success(`Found ${response.data.products.length} product(s)`)
        }
      } else {
        setSearchResults([])
        message.info('No products found')
      }
    } catch (error: any) {
      console.error('EAN search failed:', error)
      message.error(error.response?.data?.detail || 'Failed to search products by EAN')
      setSearchResults([])
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setEanInput('')
    setSearchResults([])
    setSearched(false)
  }

  const handleSelectProduct = (product: EmagProduct) => {
    onProductSelected?.(product)
    message.success(`Selected product: ${product.name}`)
  }

  const columns: ColumnsType<EmagProduct> = [
    {
      title: 'Product',
      dataIndex: 'name',
      key: 'name',
      width: '30%',
      render: (name: string, record: EmagProduct) => (
        <Space direction="vertical" size="small">
          <Text strong>{name}</Text>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {record.brand}
          </Text>
        </Space>
      )
    },
    {
      title: 'Part Number',
      dataIndex: 'part_number',
      key: 'part_number',
      width: '15%',
      render: (partNumber: string, record: EmagProduct) => (
        <Space direction="vertical" size="small">
          <Text copyable>{partNumber}</Text>
          {record.part_number_key && (
            <Text type="secondary" style={{ fontSize: '11px' }}>
              Key: {record.part_number_key}
            </Text>
          )}
        </Space>
      )
    },
    {
      title: 'EAN',
      dataIndex: 'ean',
      key: 'ean',
      width: '15%',
      render: (eans: string[]) => (
        <Space direction="vertical" size="small">
          {eans.slice(0, 2).map((ean, idx) => (
            <Text key={idx} copyable style={{ fontSize: '12px' }}>
              <BarcodeOutlined /> {ean}
            </Text>
          ))}
          {eans.length > 2 && (
            <Text type="secondary" style={{ fontSize: '11px' }}>
              +{eans.length - 2} more
            </Text>
          )}
        </Space>
      )
    },
    {
      title: 'Category',
      dataIndex: 'category_name',
      key: 'category_name',
      width: '20%',
      ellipsis: true
    },
    {
      title: 'Price',
      dataIndex: 'sale_price',
      key: 'sale_price',
      width: '10%',
      render: (price: number, record: EmagProduct) => (
        <Text strong>
          {price.toFixed(2)} {record.currency}
        </Text>
      )
    },
    {
      title: 'Action',
      key: 'action',
      width: '10%',
      render: (_: any, record: EmagProduct) => (
        <Button
          type="primary"
          size="small"
          icon={<LinkOutlined />}
          onClick={() => handleSelectProduct(record)}
        >
          Select
        </Button>
      )
    }
  ]

  return (
    <Modal
      title={
        <Space>
          <BarcodeOutlined />
          <span>Search Products by EAN</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={1200}
      footer={[
        <Button key="reset" onClick={handleReset}>
          Reset
        </Button>,
        <Button key="close" onClick={onClose}>
          Close
        </Button>
      ]}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <Alert
          message="EAN Search"
          description="Enter one or more EAN codes (comma, space, or newline separated) to search for products in the eMAG catalog. Maximum 100 EAN codes per search."
          type="info"
          showIcon
        />

        <Space.Compact style={{ width: '100%' }}>
          <Input.TextArea
            placeholder="Enter EAN codes (e.g., 5901234123457, 5901234123458)&#10;You can enter multiple codes separated by comma, space, or newline"
            value={eanInput}
            onChange={(e) => setEanInput(e.target.value)}
            rows={3}
            disabled={loading}
          />
        </Space.Compact>

        <Space>
          <Button
            type="primary"
            icon={<SearchOutlined />}
            onClick={handleSearch}
            loading={loading}
            disabled={!eanInput.trim()}
          >
            Search
          </Button>
          <Button onClick={handleReset} disabled={loading}>
            Clear
          </Button>
        </Space>

        {loading && (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <Spin size="large" tip="Searching eMAG catalog..." />
          </div>
        )}

        {!loading && searched && (
          <>
            <Divider />
            <Title level={5}>
              Search Results {searchResults.length > 0 && `(${searchResults.length})`}
            </Title>
            <Table
              columns={columns}
              dataSource={searchResults}
              rowKey="id"
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showTotal: (total) => `Total ${total} products`
              }}
              locale={{
                emptyText: 'No products found for the provided EAN codes'
              }}
            />
          </>
        )}
      </Space>
    </Modal>
  )
}

export default EanSearchModal
