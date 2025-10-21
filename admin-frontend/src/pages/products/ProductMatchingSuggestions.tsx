import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Typography,
  Image,
  message,
  Empty,
  Statistic,
  Row,
  Col,
  InputNumber,
  Modal,
  Select,
  Alert,
} from 'antd';
import {
  SyncOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  EyeOutlined,
  ThunderboltOutlined,
  FireOutlined,
  CloseOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import api from '../../services/api';

const { Title, Text } = Typography;

interface LocalProductSuggestion {
  local_product_id: number;
  local_product_name: string;
  local_product_chinese_name?: string;
  local_product_sku: string;
  local_product_brand?: string;
  local_product_image_url?: string;
  similarity_score: number;
  similarity_percent: number;
  common_tokens: string[];
  common_tokens_count: number;
  confidence_level: 'high' | 'medium' | 'low';
}

interface SupplierProductWithSuggestions {
  id: number;
  supplier_id: number;
  supplier_name: string;
  supplier_product_name: string;
  supplier_product_chinese_name?: string;
  supplier_product_specification?: string;
  supplier_product_url: string;
  supplier_image_url: string;
  supplier_price: number;
  supplier_currency: string;
  created_at: string;
  suggestions: LocalProductSuggestion[];
  suggestions_count: number;
  best_match_score: number;
}

const ProductMatchingSuggestionsPage: React.FC = () => {
  const [products, setProducts] = useState<SupplierProductWithSuggestions[]>([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  });
  const [minSimilarity, setMinSimilarity] = useState(0.85);
  const [maxSuggestions, setMaxSuggestions] = useState(5);
  const [supplierId, setSupplierId] = useState<number | null>(null);
  const [suppliers, setSuppliers] = useState<Array<{ id: number; name: string }>>([]);
  const [loadingSuppliers, setLoadingSuppliers] = useState(false);
  // Ensure filterType is always one of the valid values
  const [filterType, setFilterType] = useState<'all' | 'with-suggestions' | 'without-suggestions' | 'high-score'>('all');
  
  // Validate and normalize filter type
  const getValidFilterType = (type: string): 'all' | 'with-suggestions' | 'without-suggestions' | 'high-score' => {
    const validTypes = ['all', 'with-suggestions', 'without-suggestions', 'high-score'];
    return validTypes.includes(type) ? type as any : 'all';
  };
  const [statistics, setStatistics] = useState({
    total: 0,
    withSuggestions: 0,
    withoutSuggestions: 0,
    averageScore: 0,
    highScoreCount: 0,
  });
  const [editingPrice, setEditingPrice] = useState<{ [key: number]: number }>({});

  const fetchSuppliers = useCallback(async () => {
    setLoadingSuppliers(true);
    try {
      const response = await api.get('/suppliers');
      if (response.data.status === 'success') {
        // API returns { status: 'success', data: { suppliers: [...], pagination: {...} } }
        const suppliersList = response.data.data?.suppliers || response.data.data;
        // Ensure suppliersList is an array
        if (Array.isArray(suppliersList)) {
          setSuppliers(suppliersList);
          // Auto-select first supplier if available
          setSupplierId((currentId) => {
            if (!currentId && suppliersList.length > 0) {
              return suppliersList[0].id;
            }
            return currentId;
          });
        } else {
          console.error('Suppliers data is not an array:', suppliersList);
          setSuppliers([]);
        }
      }
    } catch (error) {
      message.error('Eroare la încărcarea furnizorilor');
      console.error('Error fetching suppliers:', error);
      setSuppliers([]); // Set empty array on error
    } finally {
      setLoadingSuppliers(false);
    }
  }, []);

  const currentPage = pagination.current;
  const pageSize = pagination.pageSize;

  const fetchProducts = useCallback(async () => {
    if (!supplierId) return;
    
    setLoading(true);
    try {
      const skip = (currentPage - 1) * pageSize;
      const validFilterType = getValidFilterType(filterType);
      
      // Debug log
      console.log('Fetching products with params:', {
        supplierId,
        skip,
        limit: pageSize,
        min_similarity: minSimilarity,
        max_suggestions: maxSuggestions,
        filter_type: validFilterType,
      });
      
      const response = await api.get(
        `/suppliers/${supplierId}/products/unmatched-with-suggestions`,
        {
          params: {
            skip,
            limit: pageSize,
            min_similarity: minSimilarity,
            max_suggestions: maxSuggestions,
            filter_type: validFilterType,
          },
          paramsSerializer: params => {
            return Object.entries(params)
              .filter(([_, value]) => value !== undefined && value !== null)
              .map(([key, value]) => `${key}=${encodeURIComponent(String(value))}`)
              .join('&');
          },
        }
      );

      if (response.data.status === 'success') {
        const productsData = response.data.data.products;
        setProducts(productsData);
        setPagination((prev) => ({
          ...prev,
          total: response.data.data.pagination.total,
        }));
        
        // Calculate statistics
        const withSuggestions = productsData.filter((p: SupplierProductWithSuggestions) => p.suggestions_count > 0).length;
        const withoutSuggestions = productsData.length - withSuggestions;
        const highScoreCount = productsData.filter((p: SupplierProductWithSuggestions) => p.best_match_score >= 0.95).length;
        const totalScore = productsData.reduce((sum: number, p: SupplierProductWithSuggestions) => sum + p.best_match_score, 0);
        const averageScore = productsData.length > 0 ? totalScore / productsData.length : 0;
        
        setStatistics({
          total: productsData.length,
          withSuggestions,
          withoutSuggestions,
          averageScore,
          highScoreCount,
        });
      }
    } catch (error: any) {
      console.error('Error fetching products:', error);
      
      // Handle 422 validation error specifically
      if (error.response?.status === 422) {
        const errorDetails = error.response.data?.detail || 'Invalid request parameters';
        console.error('Validation error details:', errorDetails);
        
        // Try to recover by resetting to default filter
        if (filterType !== 'all') {
          console.log('Resetting filter to default due to validation error');
          setFilterType('all');
          // Retry with default filter
          return fetchProducts();
        }
        
        message.error(`Validation error: ${errorDetails}`);
      } else {
        message.error('Failed to load products');
      }
    } finally {
      setLoading(false);
    }
  }, [supplierId, currentPage, pageSize, minSimilarity, maxSuggestions, filterType]);

  useEffect(() => {
    fetchSuppliers();
  }, [fetchSuppliers]);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  const handleMatch = async (supplierProductId: number, localProductId: number) => {
    try {
      await api.post(`/suppliers/${supplierId}/products/${supplierProductId}/match`, {
        local_product_id: localProductId,
        confidence_score: 1.0,
        manual_confirmed: true,
      });

      message.success('Match confirmat cu succes!');
      fetchProducts(); // Refresh list
    } catch (error) {
      message.error('Eroare la confirmarea match-ului');
      console.error('Error confirming match:', error);
    }
  };

  const handlePriceUpdate = async (supplierProductId: number, newPrice: number) => {
    try {
      await api.patch(`/suppliers/${supplierId}/products/${supplierProductId}`, {
        supplier_price: newPrice,
      });

      message.success('Preț actualizat cu succes!');
      
      // Update local state
      setProducts((prevProducts) =>
        prevProducts.map((p) =>
          p.id === supplierProductId ? { ...p, supplier_price: newPrice } : p
        )
      );
      
      // Clear editing state
      setEditingPrice((prev) => {
        const newState = { ...prev };
        delete newState[supplierProductId];
        return newState;
      });
    } catch (error) {
      message.error('Eroare la actualizarea prețului');
      console.error('Error updating price:', error);
    }
  };

  const handleRemoveSuggestion = async (supplierProductId: number, localProductId: number) => {
    try {
      // Call API to persist elimination in database
      await api.delete(
        `/suppliers/${supplierId}/products/${supplierProductId}/suggestions/${localProductId}`
      );

      // Remove suggestion from local state immediately (optimistic update)
      setProducts((prevProducts) =>
        prevProducts.map((p) => {
          if (p.id === supplierProductId) {
            const updatedSuggestions = p.suggestions.filter(
              (s) => s.local_product_id !== localProductId
            );
            return {
              ...p,
              suggestions: updatedSuggestions,
              suggestions_count: updatedSuggestions.length,
              best_match_score: updatedSuggestions.length > 0 ? updatedSuggestions[0].similarity_score : 0,
            };
          }
          return p;
        })
      );

      message.success('Sugestie eliminată permanent! Nu va mai reapărea.');
    } catch (error) {
      message.error('Eroare la eliminarea sugestiei');
      console.error('Error removing suggestion:', error);
      // Revert on error
      fetchProducts();
    }
  };

  const handleBulkConfirm = async () => {
    const highScoreProducts = products.filter(
      (p) => p.best_match_score >= 0.95 && p.suggestions_count > 0
    );

    if (highScoreProducts.length === 0) {
      message.warning('Nu există produse cu scor >95% pentru confirmare automată');
      return;
    }

    const confirmResult = await new Promise<boolean>((resolve) => {
      Modal.confirm({
        title: 'Confirmare Bulk Match',
        content: `Doriți să confirmați automat ${highScoreProducts.length} matches cu scor >95%?`,
        okText: 'Da, confirmă',
        cancelText: 'Anulează',
        onOk: () => resolve(true),
        onCancel: () => resolve(false),
      });
    });

    if (!confirmResult) return;

    let successCount = 0;
    let errorCount = 0;

    for (const product of highScoreProducts) {
      try {
        await handleMatch(product.id, product.suggestions[0].local_product_id);
        successCount++;
      } catch (error) {
        errorCount++;
      }
    }

    if (successCount > 0) {
      message.success(`${successCount} matches confirmate cu succes!`);
    }
    if (errorCount > 0) {
      message.error(`${errorCount} matches au eșuat`);
    }

    fetchProducts();
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 0.95) return '#52c41a'; // Verde închis - excelent
    if (score >= 0.90) return '#73d13d'; // Verde - foarte bun
    if (score >= 0.85) return '#95de64'; // Verde deschis - bun
    return '#faad14'; // Portocaliu - mediu
  };

  const getConfidenceLabel = (score: number) => {
    if (score >= 0.95) return 'Excelent';
    if (score >= 0.90) return 'Foarte bun';
    if (score >= 0.85) return 'Bun';
    return 'Mediu';
  };

  const renderSuggestions = (record: SupplierProductWithSuggestions) => {
    if (!record.suggestions || record.suggestions.length === 0) {
      return (
        <Card
          size="small"
          style={{
            background: '#fafafa',
            borderLeft: '4px solid #d9d9d9',
          }}
        >
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <div>
                <Text type="secondary">Nu există sugestii automate</Text>
                <div style={{ marginTop: '8px', fontSize: '12px', color: '#999' }}>
                  Încercați să reduceți pragul de similaritate sau verificați dacă produsul local are nume chinezesc
                </div>
              </div>
            }
            style={{ margin: '8px 0' }}
          />
        </Card>
      );
    }

    return (
      <div style={{ padding: '8px 0' }}>
        {record.suggestions.map((suggestion, index) => (
          <Card
            key={suggestion.local_product_id}
            size="small"
            style={{
              marginBottom: index < record.suggestions.length - 1 ? '8px' : 0,
              borderLeft: `4px solid ${getConfidenceColor(suggestion.similarity_score)}`,
            }}
          >
            <Row gutter={16} align="middle">
              <Col span={3}>
                {suggestion.local_product_image_url ? (
                  <Image
                    src={suggestion.local_product_image_url}
                    alt={suggestion.local_product_name}
                    width={60}
                    height={60}
                    style={{ objectFit: 'cover', borderRadius: '4px' }}
                    fallback="/placeholder-product.png"
                  />
                ) : (
                  <div
                    style={{
                      width: 60,
                      height: 60,
                      background: '#f0f0f0',
                      borderRadius: '4px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <Text type="secondary" style={{ fontSize: '10px' }}>
                      No Image
                    </Text>
                  </div>
                )}
              </Col>
              <Col span={13}>
                <div>
                  <Text strong style={{ fontSize: '13px' }}>
                    {suggestion.local_product_name}
                  </Text>
                  {suggestion.local_product_chinese_name && (
                    <div style={{ fontSize: '12px', color: '#52c41a', marginTop: '2px' }}>
                      🇨🇳 {suggestion.local_product_chinese_name}
                    </div>
                  )}
                  <div style={{ fontSize: '11px', color: '#666', marginTop: '4px' }}>
                    <Text type="secondary">SKU: {suggestion.local_product_sku}</Text>
                    {suggestion.local_product_brand && (
                      <Tag color="blue" style={{ marginLeft: '8px', fontSize: '10px' }}>
                        {suggestion.local_product_brand}
                      </Tag>
                    )}
                  </div>
                  <div style={{ fontSize: '10px', color: '#999', marginTop: '4px' }}>
                    Tokeni comuni: {suggestion.common_tokens.join(', ')}
                  </div>
                </div>
              </Col>
              <Col span={4} style={{ textAlign: 'center' }}>
                <div style={{ marginBottom: '8px' }}>
                  <div
                    style={{
                      fontSize: '20px',
                      fontWeight: 'bold',
                      color: getConfidenceColor(suggestion.similarity_score),
                    }}
                  >
                    {Math.round(suggestion.similarity_percent)}%
                  </div>
                  <Tag
                    color={getConfidenceColor(suggestion.similarity_score)}
                    style={{ fontSize: '10px' }}
                  >
                    {getConfidenceLabel(suggestion.similarity_score)}
                  </Tag>
                </div>
              </Col>
              <Col span={4} style={{ textAlign: 'right' }}>
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  <Button
                    type="primary"
                    icon={<CheckCircleOutlined />}
                    onClick={() => handleMatch(record.id, suggestion.local_product_id)}
                    size="small"
                    block
                  >
                    Confirmă Match
                  </Button>
                  <Button
                    danger
                    icon={<CloseOutlined />}
                    onClick={() => handleRemoveSuggestion(record.id, suggestion.local_product_id)}
                    size="small"
                    block
                  >
                    Elimină Sugestie
                  </Button>
                </Space>
              </Col>
            </Row>
          </Card>
        ))}
      </div>
    );
  };

  const columns: ColumnsType<SupplierProductWithSuggestions> = [
    {
      title: 'Imagine Furnizor',
      key: 'supplier_image',
      width: 100,
      render: (_, record) => (
        <Image
          src={record.supplier_image_url}
          alt={record.supplier_product_chinese_name || record.supplier_product_name}
          width={80}
          height={80}
          style={{ objectFit: 'cover', borderRadius: '4px' }}
          fallback="/placeholder-product.png"
          preview={{
            mask: <EyeOutlined />,
          }}
        />
      ),
    },
    {
      title: 'Produs Furnizor (Chinezește)',
      key: 'supplier_product',
      width: 300,
      render: (_, record) => (
        <div>
          <Text strong style={{ fontSize: '13px', color: '#1890ff' }}>
            {record.supplier_product_chinese_name || record.supplier_product_name}
          </Text>
          <div style={{ fontSize: '12px', color: '#666', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>Preț:</span>
            <InputNumber
              size="small"
              value={editingPrice[record.id] ?? record.supplier_price}
              onChange={(value) => {
                if (value !== null) {
                  setEditingPrice((prev) => ({ ...prev, [record.id]: value }));
                }
              }}
              onPressEnter={() => {
                const newPrice = editingPrice[record.id];
                if (newPrice !== undefined && newPrice !== record.supplier_price) {
                  handlePriceUpdate(record.id, newPrice);
                }
              }}
              onBlur={() => {
                const newPrice = editingPrice[record.id];
                if (newPrice !== undefined && newPrice !== record.supplier_price) {
                  handlePriceUpdate(record.id, newPrice);
                }
              }}
              min={0}
              step={0.01}
              precision={2}
              style={{ width: '100px' }}
            />
            <span>{record.supplier_currency}</span>
          </div>
          <a
            href={record.supplier_product_url}
            target="_blank"
            rel="noopener noreferrer"
            style={{ fontSize: '11px' }}
          >
            Vezi pe 1688.com
          </a>
        </div>
      ),
    },
    {
      title: 'Sugestii Auto-Match',
      key: 'suggestions',
      render: (_, record) => (
        <div>
          {record.suggestions_count > 0 ? (
            <div style={{ marginBottom: '8px' }}>
              <Tag
                color={record.best_match_score >= 0.95 ? 'green' : 'orange'}
                icon={record.best_match_score >= 0.95 ? <FireOutlined /> : <ThunderboltOutlined />}
              >
                {record.suggestions_count} sugestii (max {Math.round(record.best_match_score * 100)}%)
              </Tag>
            </div>
          ) : (
            <Tag color="default">Fără sugestii</Tag>
          )}
          {renderSuggestions(record)}
        </div>
      ),
    },
  ];

  const expandedRowRender = () => {
    return null; // Suggestions are already shown in the main table
  };

  // Note: Filtering is now done on the current page only
  // For proper filtering across all pages, backend support is needed
  const filteredProducts = products.filter((product) => {
    switch (filterType) {
      case 'with-suggestions':
        return product.suggestions_count > 0;
      case 'without-suggestions':
        return product.suggestions_count === 0;
      case 'high-score':
        return product.best_match_score >= 0.95;
      case 'all':
      default:
        return true;
    }
  });

  return (
    <div style={{ padding: '24px' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={2} style={{ margin: 0 }}>
              <SyncOutlined style={{ marginRight: '8px' }} />
              Product Matching cu Sugestii Automate
            </Title>
            <p style={{ color: '#666', margin: '8px 0 0 0' }}>
              Sugestii automate bazate pe tokenizare jieba (similaritate {Math.round(minSimilarity * 100)}%-100%)
            </p>
            <div style={{ marginTop: '12px' }}>
              <Text strong style={{ marginRight: '8px' }}>Furnizor:</Text>
              <Select
                style={{ width: 300 }}
                placeholder="Selectează furnizor"
                value={supplierId}
                onChange={(value) => {
                  setSupplierId(value);
                  setPagination((prev) => ({ ...prev, current: 1 })); // Reset to first page
                }}
                loading={loadingSuppliers}
                options={Array.isArray(suppliers) ? suppliers.map((s) => ({
                  label: s.name,
                  value: s.id,
                })) : []}
              />
            </div>
          </div>
          <Space>
            <Button
              type="primary"
              icon={<ThunderboltOutlined />}
              onClick={handleBulkConfirm}
              disabled={statistics.highScoreCount === 0}
            >
              Confirmă Automat ({statistics.highScoreCount})
            </Button>
            <Button icon={<ReloadOutlined />} onClick={fetchProducts} loading={loading}>
              Reîmprospătează
            </Button>
          </Space>
        </div>
      </div>

      {/* Statistics */}
      <Card 
        style={{ marginBottom: '16px' }}
        title={supplierId && Array.isArray(suppliers) ? `Statistici - ${suppliers.find(s => s.id === supplierId)?.name || 'Furnizor'}` : 'Statistici'}
      >
        <Row gutter={16}>
          <Col span={4}>
            <Statistic
              title="Total produse"
              value={pagination.total}
              prefix={<SyncOutlined />}
            />
          </Col>
          <Col span={5}>
            <Statistic
              title="Cu sugestii"
              value={statistics.withSuggestions}
              valueStyle={{ color: '#52c41a' }}
              suffix={`/ ${statistics.total}`}
            />
          </Col>
          <Col span={5}>
            <Statistic
              title="Fără sugestii"
              value={statistics.withoutSuggestions}
              valueStyle={{ color: '#ff4d4f' }}
              suffix={`/ ${statistics.total}`}
            />
          </Col>
          <Col span={5}>
            <Statistic
              title="Scor >95%"
              value={statistics.highScoreCount}
              valueStyle={{ color: '#1890ff' }}
              prefix={<FireOutlined />}
            />
          </Col>
          <Col span={5}>
            <Statistic
              title="Scor mediu"
              value={Math.round(statistics.averageScore * 100)}
              suffix="%"
              precision={0}
            />
          </Col>
        </Row>
      </Card>

      {/* Filters */}
      <Card style={{ marginBottom: '24px' }}>
        <Row gutter={16} align="middle" style={{ marginBottom: '16px' }}>
          <Col span={6}>
            <div>
              <Text strong>Similaritate minimă:</Text>
              <div style={{ marginTop: '8px' }}>
                <InputNumber
                  min={0.5}
                  max={1.0}
                  step={0.05}
                  value={minSimilarity}
                  onChange={(value) => value && setMinSimilarity(value)}
                  formatter={(value) => `${Math.round((value || 0) * 100)}%`}
                  parser={(value) => (parseFloat(value?.replace('%', '') || '0') / 100)}
                  style={{ width: '100%' }}
                />
              </div>
            </div>
          </Col>
          <Col span={6}>
            <div>
              <Text strong>Număr maxim sugestii:</Text>
              <div style={{ marginTop: '8px' }}>
                <InputNumber
                  min={1}
                  max={10}
                  value={maxSuggestions}
                  onChange={(value) => value && setMaxSuggestions(value)}
                  style={{ width: '100%' }}
                />
              </div>
            </div>
          </Col>
          <Col span={12}>
            <div>
              <Text strong>Filtrare rapidă:</Text>
              <div style={{ marginTop: '8px' }}>
                <Space>
                  <Button
                    type={filterType === 'all' ? 'primary' : 'default'}
                    onClick={() => setFilterType('all')}
                    size="small"
                  >
                    Toate ({statistics.total})
                  </Button>
                  <Button
                    type={filterType === 'with-suggestions' ? 'primary' : 'default'}
                    onClick={() => setFilterType('with-suggestions')}
                    size="small"
                  >
                    Cu sugestii ({statistics.withSuggestions})
                  </Button>
                  <Button
                    type={filterType === 'without-suggestions' ? 'primary' : 'default'}
                    onClick={() => setFilterType('without-suggestions')}
                    size="small"
                  >
                    Fără sugestii ({statistics.withoutSuggestions})
                  </Button>
                  <Button
                    type={filterType === 'high-score' ? 'primary' : 'default'}
                    onClick={() => setFilterType('high-score')}
                    size="small"
                    icon={<FireOutlined />}
                  >
                    Scor &gt;95% ({statistics.highScoreCount})
                  </Button>
                </Space>
              </div>
              {filterType !== 'all' && (
                <Alert
                  message="Notă: Filtrarea se aplică doar pe produsele din pagina curentă"
                  description="Pentru a vedea toate produsele cu sugestii, navigați prin toate paginile sau contactați administratorul pentru implementare filtrare server-side."
                  type="info"
                  showIcon
                  closable
                  style={{ marginTop: '12px' }}
                />
              )}
            </div>
          </Col>
        </Row>
      </Card>

      {/* Table */}
      <Card>
        {!supplierId ? (
          <Empty
            description="Selectați un furnizor pentru a vedea produsele nematchate"
            style={{ padding: '40px 0' }}
          />
        ) : (
          <Table
            columns={columns}
            dataSource={filteredProducts}
            rowKey="id"
            loading={loading}
            pagination={{
              ...pagination,
              showSizeChanger: true,
              pageSizeOptions: ['10', '20', '30', '50'],
              showTotal: (total) => `Total ${total} produse (${filteredProducts.length} afișate)`,
              onChange: (page, pageSize) => {
                setPagination((prev) => ({
                  ...prev,
                  current: page,
                  pageSize: Math.min(pageSize || prev.pageSize, 50), // Max 50 per API limit
                }));
              },
            }}
            expandable={{
              expandedRowRender,
              defaultExpandAllRows: false,
            }}
          />
        )}
      </Card>
    </div>
  );
};

export default ProductMatchingSuggestionsPage;
