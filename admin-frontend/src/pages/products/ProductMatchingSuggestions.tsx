import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Divider,
  Empty,
  Image,
  InputNumber,
  message,
  Modal,
  Row,
  Select,
  Skeleton,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseOutlined,
  EyeOutlined,
  FireOutlined,
  ReloadOutlined,
  SyncOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useProductMatching } from '../../hooks/useProductMatching';
import type {
  LocalProductSuggestion,
  SupplierProductWithSuggestions,
} from '../../hooks/useProductMatching';
import api from '../../services/api';

const { Title, Text } = Typography;

const FILTER_TYPES = ['all', 'with-suggestions', 'without-suggestions', 'high-score'] as const;

type FilterType = (typeof FILTER_TYPES)[number];

type SupplierOption = {
  id: number;
  name: string;
};

type QueryState = {
  minSimilarity: number;
  maxSuggestions: number;
  filterType: FilterType;
};

type StatisticsState = {
  total: number;
  withSuggestions: number;
  withoutSuggestions: number;
  highScoreCount: number;
  averageScore: number;
};

const DEFAULT_QUERY: QueryState = {
  minSimilarity: 0.9,
  maxSuggestions: 5,
  filterType: 'all',
};

const filterTypeLabels: Record<FilterType, string> = {
  all: 'Toate',
  'with-suggestions': 'Cu sugestii',
  'without-suggestions': 'Fără sugestii',
  'high-score': 'Scor >95%'
};

const getConfidenceColor = (score: number) => {
  if (score >= 0.95) return '#52c41a';
  if (score >= 0.9) return '#73d13d';
  if (score >= 0.85) return '#95de64';
  return '#faad14';
};

const getConfidenceLabel = (score: number) => {
  if (score >= 0.95) return 'Excelent';
  if (score >= 0.9) return 'Foarte bun';
  if (score >= 0.85) return 'Bun';
  return 'Mediu';
};

const ProductMatchingSuggestionsPage: React.FC = () => {
  const [suppliers, setSuppliers] = useState<SupplierOption[]>([]);
  const [supplierId, setSupplierId] = useState<number | null>(null);
  const [loadingSuppliers, setLoadingSuppliers] = useState(false);
  const [queryState, setQueryState] = useState<QueryState>(DEFAULT_QUERY);
  const [editingPrice, setEditingPrice] = useState<Record<number, number | undefined>>({});
  const [activeFilter, setActiveFilter] = useState<FilterType>('all');

  const pageSize = 20;

  const {
    products,
    loading,
    error,
    pagination,
    fetchProducts,
    fetchAllProducts,
    confirmMatch,
    removeSuggestion,
    updatePrice,
    isFallback,
    viewMode,
    lastFetchInfo,
  } = useProductMatching({
    supplierId,
    minSimilarity: queryState.minSimilarity,
    maxSuggestions: queryState.maxSuggestions,
    pageSize,
    filterType: queryState.filterType,
  });

  const statistics = useMemo<StatisticsState>(() => {
    const withSuggestions = products.filter((product) => product.suggestions_count > 0).length;
    const withoutSuggestions = products.length - withSuggestions;
    const highScoreCount = products.filter((product) => product.best_match_score >= 0.95).length;
    const totalScore = products.reduce((sum, product) => sum + product.best_match_score, 0);
    const averageScore = products.length ? totalScore / products.length : 0;

    return {
      total: pagination.total,
      withSuggestions,
      withoutSuggestions,
      highScoreCount,
      averageScore,
    };
  }, [products, pagination.total]);

  const fetchSuppliers = useCallback(async () => {
    setLoadingSuppliers(true);
    try {
      const response = await api.get('/suppliers');
      if (response.data.status === 'success') {
        const suppliersList: SupplierOption[] = response.data.data?.suppliers ?? response.data.data ?? [];
        if (Array.isArray(suppliersList)) {
          setSuppliers(suppliersList);
          setSupplierId((prev) => prev ?? suppliersList[0]?.id ?? null);
        } else {
          message.warning('Structura furnizorilor este necunoscută');
          setSuppliers([]);
        }
      }
    } catch (err) {
      message.error('Eroare la încărcarea furnizorilor');
      console.error('Error fetching suppliers:', err);
      setSuppliers([]);
    } finally {
      setLoadingSuppliers(false);
    }
  }, []);

  useEffect(() => {
    fetchSuppliers();
  }, [fetchSuppliers]);

  useEffect(() => {
    if (!suppliers.length) {
      return;
    }
    if (supplierId && suppliers.some((supplier) => supplier.id === supplierId)) {
      return;
    }
    setSupplierId(suppliers[0]?.id ?? null);
  }, [suppliers, supplierId]);

  useEffect(() => {
    if (!supplierId) {
      return;
    }
    fetchProducts(1);
  }, [supplierId, queryState.minSimilarity, queryState.maxSuggestions, queryState.filterType, fetchProducts]);

  const handleSupplierChange = useCallback((value: number) => {
    setSupplierId(value);
    setEditingPrice({});
  }, []);

  const handleRefresh = useCallback(() => {
    if (!supplierId) {
      return;
    }
    fetchProducts(pagination.current || 1);
  }, [fetchProducts, pagination, supplierId]);

  const handlePriceInputChange = useCallback((productId: number, value: number | null) => {
    setEditingPrice((prev) => ({
      ...prev,
      [productId]: value ?? undefined,
    }));
  }, []);

  const handlePriceCommit = useCallback(
    async (productId: number, currentPrice: number) => {
      const newPrice = editingPrice[productId];
      if (newPrice === undefined || newPrice === currentPrice) {
        return;
      }

      const result = await updatePrice(productId, newPrice);
      if (result.success) {
        message.success('Preț actualizat cu succes!');
        setEditingPrice((prev) => {
          const next = { ...prev };
          delete next[productId];
          return next;
        });
      } else {
        message.error('Eroare la actualizarea prețului');
      }
    },
    [editingPrice, updatePrice],
  );

  const handleMatch = useCallback(
    async (productId: number, localProductId: number) => {
      const result = await confirmMatch(productId, localProductId);
      if (result.success) {
        message.success('Match confirmat cu succes!');
        fetchProducts(pagination.current || 1);
      } else {
        message.error('Eroare la confirmarea match-ului');
      }
    },
    [confirmMatch, fetchProducts, pagination],
  );

  const handleRemoveSuggestion = useCallback(
    async (productId: number, localProductId: number) => {
      const result = await removeSuggestion(productId, localProductId);
      if (result.success) {
        message.success('Sugestie eliminată permanent! Nu va mai reapărea.');
      } else {
        message.error('Eroare la eliminarea sugestiei');
      }
    },
    [removeSuggestion],
  );

  const handleBulkConfirm = useCallback(async () => {
    const highScoreProducts = products.filter(
      (product) => product.best_match_score >= 0.95 && product.suggestions.length > 0,
    );

    if (!highScoreProducts.length) {
      message.warning('Nu există produse cu scor >95% pentru confirmare automată');
      return;
    }

    const confirmed = await new Promise<boolean>((resolve) => {
      Modal.confirm({
        title: 'Confirmare Bulk Match',
        content: `Doriți să confirmați automat ${highScoreProducts.length} matches cu scor >95%?`,
        okText: 'Da, confirmă',
        cancelText: 'Anulează',
        onOk: () => resolve(true),
        onCancel: () => resolve(false),
      });
    });

    if (!confirmed) {
      return;
    }

    let successCount = 0;
    let errorCount = 0;

    await Promise.all(
      highScoreProducts.map(async (product) => {
        const bestSuggestion = product.suggestions[0];
        const result = await confirmMatch(product.id, bestSuggestion.local_product_id);
        if (result.success) {
          successCount += 1;
        } else {
          errorCount += 1;
        }
      }),
    );

    if (successCount) {
      message.success(`${successCount} matches confirmate cu succes!`);
    }
    if (errorCount) {
      message.error(`${errorCount} matches au eșuat`);
    }

    fetchProducts(pagination.current || 1);
  }, [confirmMatch, fetchProducts, pagination, products]);

  const renderSuggestions = useCallback(
    (record: SupplierProductWithSuggestions) => {
      if (!record.suggestions.length) {
        return (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="Nu există sugestii automate"
            style={{ padding: '12px 0' }}
          />
        );
      }

      return (
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          {record.suggestions.map((suggestion: LocalProductSuggestion) => (
            <Card
              key={suggestion.local_product_id}
              size="small"
              bordered
              style={{ borderLeft: `4px solid ${getConfidenceColor(suggestion.similarity_score)}` }}
            >
              <Row gutter={16} align="middle">
                <Col span={4}>
                  {suggestion.local_product_image_url ? (
                    <Image
                      src={suggestion.local_product_image_url}
                      alt={suggestion.local_product_name}
                      width={60}
                      height={60}
                      style={{ objectFit: 'cover', borderRadius: 4 }}
                      fallback="/placeholder-product.png"
                    />
                  ) : (
                    <div
                      style={{
                        width: 60,
                        height: 60,
                        background: '#f0f0f0',
                        borderRadius: 4,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <Text type="secondary" style={{ fontSize: 10 }}>
                        Fără imagine
                      </Text>
                    </div>
                  )}
                </Col>
                <Col span={12}>
                  <Space direction="vertical" size={2} style={{ width: '100%' }}>
                    <Text strong>{suggestion.local_product_name}</Text>
                    {suggestion.local_product_chinese_name && (
                      <Text style={{ color: '#52c41a' }}>🇨🇳 {suggestion.local_product_chinese_name}</Text>
                    )}
                    <Space size="small">
                      <Text type="secondary">SKU: {suggestion.local_product_sku}</Text>
                      {suggestion.local_product_brand && (
                        <Tag color="blue">{suggestion.local_product_brand}</Tag>
                      )}
                    </Space>
                    {!!suggestion.common_tokens.length && (
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        Tokeni comuni: {suggestion.common_tokens.join(', ')}
                      </Text>
                    )}
                  </Space>
                </Col>
                <Col span={4}>
                  <Space direction="vertical" align="center" size={4} style={{ width: '100%' }}>
                    <Badge
                      count={`${Math.round(suggestion.similarity_percent)}%`}
                      style={{ backgroundColor: getConfidenceColor(suggestion.similarity_score) }}
                    />
                    <Tag color={getConfidenceColor(suggestion.similarity_score)}>
                      {getConfidenceLabel(suggestion.similarity_score)}
                    </Tag>
                  </Space>
                </Col>
                <Col span={4}>
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    <Button
                      type="primary"
                      icon={<CheckCircleOutlined />}
                      size="small"
                      block
                      onClick={() => handleMatch(record.id, suggestion.local_product_id)}
                    >
                      Confirmă match
                    </Button>
                    <Button
                      danger
                      icon={<CloseOutlined />}
                      size="small"
                      block
                      onClick={() => handleRemoveSuggestion(record.id, suggestion.local_product_id)}
                    >
                      Elimină
                    </Button>
                  </Space>
                </Col>
              </Row>
            </Card>
          ))}
        </Space>
      );
    },
    [handleMatch, handleRemoveSuggestion],
  );

  const columns = useMemo<ColumnsType<SupplierProductWithSuggestions>>(
    () => [
      {
        title: 'Produs furnizor',
        key: 'supplier_product',
        width: 360,
        render: (_, record) => (
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            <Space align="start">
              <Image
                src={record.supplier_image_url}
                alt={record.supplier_product_chinese_name || record.supplier_product_name}
                width={70}
                height={70}
                style={{ objectFit: 'cover', borderRadius: 4 }}
                fallback="/placeholder-product.png"
                preview={{ mask: <EyeOutlined /> }}
              />
              <Space direction="vertical" size={4} style={{ flex: 1 }}>
                <Text strong>{record.supplier_product_chinese_name || record.supplier_product_name}</Text>
                <a href={record.supplier_product_url} target="_blank" rel="noopener noreferrer">
                  Deschide produsul 1688
                </a>
                <Space size="small" align="center">
                  <span>Preț:</span>
                  <InputNumber
                    size="small"
                    value={editingPrice[record.id] ?? record.supplier_price}
                    onChange={(value) => handlePriceInputChange(record.id, value)}
                    onPressEnter={() => handlePriceCommit(record.id, record.supplier_price)}
                    onBlur={() => handlePriceCommit(record.id, record.supplier_price)}
                    min={0}
                    step={0.01}
                    precision={2}
                    style={{ width: 120 }}
                  />
                  <span>{record.supplier_currency}</span>
                </Space>
              </Space>
            </Space>
          </Space>
        ),
      },
      {
        title: 'Sugestii',
        key: 'suggestions_summary',
        width: 220,
        render: (_, record) => (
          <Space direction="vertical" size={4} style={{ width: '100%' }}>
            {record.suggestions_count > 0 ? (
              <Tag
                color={record.best_match_score >= 0.95 ? 'green' : 'orange'}
                icon={record.best_match_score >= 0.95 ? <FireOutlined /> : <ThunderboltOutlined />}
              >
                {record.suggestions_count} sugestii (max {Math.round(record.best_match_score * 100)}%)
              </Tag>
            ) : (
              <Tag>Fără sugestii</Tag>
            )}
            {record.suggestions[0] && (
              <Text type="secondary">
                Cea mai bună potrivire: {record.suggestions[0].local_product_name}
              </Text>
            )}
          </Space>
        ),
      },
      {
        title: 'Detalii sugestii',
        key: 'suggestions',
        render: (_, record) => renderSuggestions(record),
      },
    ],
    [editingPrice, handlePriceCommit, handlePriceInputChange, renderSuggestions],
  );

  const handleFilterChange = useCallback((type: FilterType) => {
    setActiveFilter(type);
    setQueryState((prev) => ({
      ...prev,
      filterType: type,
    }));
  }, []);

  const handleResetFilters = useCallback(() => {
    setQueryState(DEFAULT_QUERY);
    setActiveFilter('all');
  }, []);

  const handleViewAll = useCallback(() => {
    fetchAllProducts(1);
  }, [fetchAllProducts]);

  return (
    <div style={{ padding: 24 }}>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={16}>
          <Card>
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              <Title level={2} style={{ margin: 0 }}>
                <SyncOutlined style={{ marginRight: 8 }} /> Product Matching
              </Title>
              <Text type="secondary">
                Selectează un furnizor și explorează toate produsele fără potrivire. Ajustează criteriile pentru a găsi cele mai relevante sugestii și confirmă rapid potrivirile de încredere.
              </Text>
              <Space size={12} wrap>
                {FILTER_TYPES.map((type) => (
                  <Button
                    key={type}
                    type={activeFilter === type ? 'primary' : 'default'}
                    icon={type === 'high-score' ? <FireOutlined /> : undefined}
                    size="small"
                    onClick={() => handleFilterChange(type)}
                  >
                    {filterTypeLabels[type]} (
                    {type === 'all'
                      ? pagination.total
                      : type === 'with-suggestions'
                      ? statistics.withSuggestions
                      : type === 'without-suggestions'
                      ? statistics.withoutSuggestions
                      : statistics.highScoreCount}
                    )
                  </Button>
                ))}
                <Button type="link" onClick={handleResetFilters}>
                  Resetează filtrele
                </Button>
                <Button type="dashed" onClick={handleViewAll} disabled={!supplierId || viewMode === 'all'}>
                  Vezi toate produsele furnizorului
                </Button>
              </Space>
            </Space>
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Space size={16} wrap>
              <Statistic title="Cu sugestii" value={statistics.withSuggestions} valueStyle={{ color: '#52c41a' }} />
              <Statistic title="Fără sugestii" value={statistics.withoutSuggestions} valueStyle={{ color: '#ff4d4f' }} />
              <Statistic title="Scor mediu" value={Math.round(statistics.averageScore * 100)} suffix="%" />
            </Space>
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card title="Preferințe" extra={<Button onClick={handleRefresh} icon={<ReloadOutlined />} loading={loading}>Actualizează</Button>}>
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                <Text strong>Furnizor</Text>
                {loadingSuppliers ? (
                  <Skeleton.Input active style={{ width: '100%' }} size="small" />
                ) : (
                  <Select
                    placeholder="Selectează furnizor"
                    value={supplierId}
                    onChange={handleSupplierChange}
                    loading={loadingSuppliers}
                    options={suppliers.map((supplier) => ({
                      label: supplier.name,
                      value: supplier.id,
                    }))}
                    style={{ width: '100%' }}
                  />
                )}
              </Space>

              <Divider style={{ margin: '12px 0' }} />

              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                <Text strong>Similaritate minimă</Text>
                <InputNumber
                  min={0.5}
                  max={1}
                  step={0.05}
                  value={queryState.minSimilarity}
                  onChange={(value) =>
                    value &&
                    setQueryState((prev) => ({
                      ...prev,
                      minSimilarity: value,
                    }))
                  }
                  formatter={(value) => `${Math.round((value ?? 0) * 100)}%`}
                  parser={(value) => (parseFloat(value?.replace('%', '') || '0') / 100)}
                  style={{ width: '100%' }}
                />
              </Space>

              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                <Text strong>Număr maxim de sugestii</Text>
                <InputNumber
                  min={1}
                  max={10}
                  value={queryState.maxSuggestions}
                  onChange={(value) =>
                    value &&
                    setQueryState((prev) => ({
                      ...prev,
                      maxSuggestions: value,
                    }))
                  }
                  style={{ width: '100%' }}
                />
              </Space>

              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                disabled={!statistics.highScoreCount}
                onClick={handleBulkConfirm}
              >
                Confirmă automat {statistics.highScoreCount}
              </Button>
            </Space>
          </Card>
        </Col>
        <Col span={16}>
          <Card
            title="Rezultate"
            bodyStyle={{ padding: 0 }}
            extra={
              isFallback ? (
                <Space size="small">
                  <Tag color="gold">
                    Vizualizați toate produsele (fără sugestii). Ajustați criteriile pentru a restrânge lista.
                  </Tag>
                  {lastFetchInfo && (
                    <Tag color="blue">
                      {lastFetchInfo.received} / {lastFetchInfo.total} produse • pagina {lastFetchInfo.page}
                    </Tag>
                  )}
                </Space>
              ) : lastFetchInfo ? (
                <Tag color="green">
                  Sugestii automate ({lastFetchInfo.received} / {lastFetchInfo.total})
                </Tag>
              ) : undefined
            }
          >
            {!supplierId ? (
              <Empty
                description="Selectați un furnizor pentru a începe"
                style={{ padding: '40px 0' }}
              />
            ) : (
              <Table
                columns={columns}
                dataSource={products}
                rowKey="id"
                loading={loading}
                locale={{
                  emptyText: isFallback
                    ? 'Nu există produse care să necesite matching. Lista afișează toate produsele furnizorului.'
                    : 'Nu s-au găsit produse nematchate pentru criteriile curente.',
                }}
                pagination={{
                  current: pagination.current,
                  pageSize,
                  total: pagination.total,
                  showSizeChanger: false,
                  showTotal: (total) => `Total ${total} produse (${products.length} afișate)`,
                  onChange: (page) => fetchProducts(page),
                }}
              />
            )}
          </Card>
          {error && (
            <Alert
              style={{ marginTop: 16 }}
              type="error"
              message="Nu s-au putut încărca produsele"
              description={error.message}
              showIcon
            />
          )}
          {lastFetchInfo && lastFetchInfo.source === 'error' && (
            <Alert
              style={{ marginTop: 16 }}
              type="warning"
              message="Fallback indisponibil"
              description="Solicitarea pentru toate produsele a eșuat. Verificați răspunsul API sau reîncercați."
              showIcon
            />
          )}
          {queryState.minSimilarity < 0.5 && (
            <Alert
              style={{ marginTop: 16 }}
              type="warning"
              message="Avertisment: Similaritate minimă setată foarte jos"
              description="Valorile sub 0.5 pot returna rezultate neașteptate"
              showIcon
            />
          )}
        </Col>
      </Row>
    </div>
  );
};

export default ProductMatchingSuggestionsPage;
