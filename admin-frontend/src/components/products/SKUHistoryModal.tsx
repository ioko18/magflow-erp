import React, { useState, useEffect, useCallback } from 'react';
import { Modal, Table, Tag, Space, Typography, Alert, Spin, Input, Button } from 'antd';
import { HistoryOutlined, SearchOutlined, ClockCircleOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import api from '../../services/api';

const { Text, Title } = Typography;
const { Search } = Input;

interface SKUHistoryEntry {
  old_sku: string;
  new_sku: string;
  changed_at: string;
  changed_by_email: string | null;
  change_reason: string | null;
}

interface SearchResult {
  notFound?: boolean;
  searchedSKU?: string;
  product?: {
    current_sku: string;
    name: string;
    base_price: number;
    currency: string;
  };
  sku_history?: Array<{
    old_sku: string;
  }>;
}

interface SKUHistoryModalProps {
  visible: boolean;
  productId: number | null;
  currentSKU: string | null;
  onClose: () => void;
}

const SKUHistoryModal: React.FC<SKUHistoryModalProps> = ({
  visible,
  productId,
  currentSKU,
  onClose,
}) => {
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<SKUHistoryEntry[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchResult, setSearchResult] = useState<SearchResult | null>(null);

  const loadSKUHistory = useCallback(async () => {
    if (!productId) return;

    setLoading(true);
    try {
      const response = await api.get(`/products/${productId}/sku-history`);
      setHistory(response.data);
    } catch (error) {
      console.error('Failed to load SKU history:', error);
    } finally {
      setLoading(false);
    }
  }, [productId]);

  useEffect(() => {
    if (visible && productId) {
      loadSKUHistory();
    }
  }, [visible, productId, loadSKUHistory]);

  const handleSearchOldSKU = async (oldSKU: string) => {
    if (!oldSKU.trim()) return;

    setSearchLoading(true);
    setSearchResult(null);
    try {
      const response = await api.get(`/products/search-by-old-sku/${oldSKU.trim()}`);
      setSearchResult(response.data.data);
    } catch (error) {
      const err = error as { response?: { status?: number } };
      if (err.response?.status === 404) {
        setSearchResult({ notFound: true, searchedSKU: oldSKU });
      } else {
        console.error('Failed to search by old SKU:', error);
      }
    } finally {
      setSearchLoading(false);
    }
  };

  const columns: ColumnsType<SKUHistoryEntry> = [
    {
      title: 'Old SKU',
      dataIndex: 'old_sku',
      key: 'old_sku',
      render: (sku: string) => (
        <Tag color="orange" style={{ fontFamily: 'monospace', fontSize: '13px' }}>
          {sku}
        </Tag>
      ),
    },
    {
      title: 'New SKU',
      dataIndex: 'new_sku',
      key: 'new_sku',
      render: (sku: string) => (
        <Tag color="green" style={{ fontFamily: 'monospace', fontSize: '13px' }}>
          {sku}
        </Tag>
      ),
    },
    {
      title: 'Changed At',
      dataIndex: 'changed_at',
      key: 'changed_at',
      render: (date: string) => (
        <Space>
          <ClockCircleOutlined />
          <Text>{new Date(date).toLocaleString('ro-RO')}</Text>
        </Space>
      ),
    },
    {
      title: 'Changed By',
      dataIndex: 'changed_by_email',
      key: 'changed_by_email',
      render: (email: string | null) => (
        <Text type="secondary">{email || 'System Import'}</Text>
      ),
    },
    {
      title: 'Reason',
      dataIndex: 'change_reason',
      key: 'change_reason',
      render: (reason: string | null) => (
        <Text type="secondary" style={{ fontSize: '12px' }}>
          {reason || '-'}
        </Text>
      ),
    },
  ];

  return (
    <Modal
      title={
        <Space>
          <HistoryOutlined />
          <span>SKU History</span>
          {currentSKU && (
            <Tag color="blue" style={{ fontFamily: 'monospace' }}>
              Current: {currentSKU}
            </Tag>
          )}
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={1000}
      footer={null}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* Search by Old SKU */}
        <div>
          <Title level={5}>Search Product by Old SKU</Title>
          <Search
            placeholder="Enter old SKU to find current product (e.g., a.1108E, AAA129)"
            allowClear
            enterButton={
              <Button type="primary" icon={<SearchOutlined />}>
                Search
              </Button>
            }
            size="large"
            onSearch={handleSearchOldSKU}
            loading={searchLoading}
          />
          {searchResult && (
            <div style={{ marginTop: 16 }}>
              {searchResult.notFound ? (
                <Alert
                  message="Not Found"
                  description={`No product found with old SKU: ${searchResult.searchedSKU}`}
                  type="warning"
                  showIcon
                />
              ) : searchResult.product ? (
                <Alert
                  message="Product Found!"
                  description={
                    <div>
                      <p>
                        <strong>Current SKU:</strong>{' '}
                        <Tag color="green" style={{ fontFamily: 'monospace' }}>
                          {searchResult.product.current_sku}
                        </Tag>
                      </p>
                      <p>
                        <strong>Name:</strong> {searchResult.product.name}
                      </p>
                      <p>
                        <strong>Price:</strong> {searchResult.product.base_price}{' '}
                        {searchResult.product.currency}
                      </p>
                      {searchResult.sku_history && searchResult.sku_history.length > 0 && (
                        <p>
                          <strong>All Old SKUs:</strong>{' '}
                          {searchResult.sku_history.map((h) => (
                            <Tag key={h.old_sku} color="orange" style={{ margin: '2px' }}>
                              {h.old_sku}
                            </Tag>
                          ))}
                        </p>
                      )}
                    </div>
                  }
                  type="success"
                  showIcon
                />
              ) : null}
            </div>
          )}
        </div>

        {/* SKU History Table */}
        <div>
          <Title level={5}>SKU Change History for Current Product</Title>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <Spin size="large" />
            </div>
          ) : history.length === 0 ? (
            <Alert
              message="No SKU History"
              description="This product has no recorded SKU changes. The current SKU has been used since the product was created."
              type="info"
              showIcon
            />
          ) : (
            <>
              <Alert
                message={`Found ${history.length} SKU change${history.length > 1 ? 's' : ''}`}
                description="This shows all previous SKUs that this product has used, including those imported from Google Sheets."
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />
              <Table
                columns={columns}
                dataSource={history}
                rowKey={(record) => `${record.old_sku}-${record.changed_at}`}
                pagination={false}
                size="small"
              />
            </>
          )}
        </div>
      </Space>
    </Modal>
  );
};

export default SKUHistoryModal;
