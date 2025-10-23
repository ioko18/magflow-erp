import React, { useMemo, useState, useEffect } from 'react';
import {
  Card,
  Input,
  Table,
  Row,
  Col,
  Typography,
  Tag,
  Image,
  Space,
  Statistic,
  Alert,
  Button,
  Tooltip,
  message,
  Spin,
  Modal,
  Divider,
  Select,
  Slider,
  App as AntApp,
} from 'antd';
import { EyeOutlined, ShoppingOutlined, CheckCircleOutlined, CloseCircleOutlined, SyncOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import useChineseNameSearch, {
  SupplierMatch,
  LocalProductMatch,
} from '../../hooks/useChineseNameSearch';
import api from '../../services/api';

const { Title } = Typography;

const getConfidenceColor = (score: number) => {
  if (score >= 0.95) return '#52c41a';
  if (score >= 0.85) return '#73d13d';
  if (score >= 0.75) return '#95de64';
  return '#faad14';
};

const getConfidenceLabel = (score: number) => {
  if (score >= 0.95) return 'Excelent';
  if (score >= 0.85) return 'Foarte bun';
  if (score >= 0.75) return 'Bun';
  return 'Mediu';
};

const validImageExtensions = /(\.jpg|\.jpeg|\.png|\.gif|\.webp|\.bmp)$/i;

const getImageUrl = (record: any) => {
  const supplierImage = record.supplier_image_url;
  if (supplierImage && validImageExtensions.test(new URL(supplierImage).pathname)) {
    return supplierImage;
  }

  const localImage = record.local_product?.image_url;
  if (localImage && validImageExtensions.test(new URL(localImage).pathname)) {
    return localImage;
  }

  return null;
};

const ChineseNameSearchPage: React.FC = () => {
  const { modal } = AntApp.useApp();
  const [searchValue, setSearchValue] = useState('');
  const [supplierPageSize, setSupplierPageSize] = useState(() => {
    const saved = localStorage.getItem('chineseSearch_supplierPageSize');
    return saved ? parseInt(saved, 10) : 39;
  });
  const [localPageSize, setLocalPageSize] = useState(() => {
    const saved = localStorage.getItem('chineseSearch_localPageSize');
    return saved ? parseInt(saved, 10) : 39;
  });
  const [selectedSupplierKeys, setSelectedSupplierKeys] = useState<React.Key[]>([]);
  const [selectedLocalKeys, setSelectedLocalKeys] = useState<React.Key[]>([]);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedSupplierProduct, setSelectedSupplierProduct] = useState<SupplierMatch | null>(null);
  const [messageApi, contextHolder] = message.useMessage();
  const [suppliers, setSuppliers] = useState<Array<{ id: number; name: string }>>([]);
  const [changingSupplier, setChangingSupplier] = useState(false);
  const [newSupplierId, setNewSupplierId] = useState<number | null>(null);
  const [loadingSuppliers, setLoadingSuppliers] = useState(false);

  const {
    supplierMatches,
    localMatches,
    loading,
    error,
    setChineseName,
    minSimilarity,
    setMinSimilarity,
    linkSupplierProduct,
    linkingIds,
    updateLocalChineseName,
    updatingLocalIds,
    updateSupplierProductName,
    updatingSupplierNameIds,
    updateSupplierProductUrl,
    updatingSupplierUrlIds,
    changeSupplierForProduct,
    changingSupplierIds,
  } = useChineseNameSearch();

  const handleSearch = (value: string) => {
    setChineseName(value);
  };

  const handleSupplierPageSizeChange = (size: number) => {
    setSupplierPageSize(size);
    localStorage.setItem('chineseSearch_supplierPageSize', size.toString());
  };

  const handleLocalPageSizeChange = (size: number) => {
    setLocalPageSize(size);
    localStorage.setItem('chineseSearch_localPageSize', size.toString());
  };

  useEffect(() => {
    const loadSuppliers = async () => {
      try {
        setLoadingSuppliers(true);
        const response = await api.get('/suppliers', {
          params: { limit: 1000, active_only: true }
        });
        const suppliersData = response.data?.data?.suppliers || [];
        setSuppliers(suppliersData);
      } catch (err) {
        console.error('Error loading suppliers:', err);
        messageApi.error('Eroare la încărcarea furnizorilor');
      } finally {
        setLoadingSuppliers(false);
      }
    };
    loadSuppliers();
  }, [messageApi]);

  const handleChangeSupplier = async () => {
    if (!selectedSupplierProduct?.supplier_product_id || !newSupplierId) {
      messageApi.error('Selectează un furnizor valid');
      return;
    }

    modal.confirm({
      title: 'Schimbă Furnizor',
      icon: <ExclamationCircleOutlined />,
      content: (
        <div>
          <p>Ești sigur că vrei să schimbi furnizorul pentru acest produs?</p>
          <div style={{ marginTop: '12px', padding: '8px', background: '#fff2e8', borderRadius: '4px' }}>
            <Typography.Text strong>Atenție:</Typography.Text>
            <div style={{ marginTop: '4px', fontSize: '12px' }}>
              Produsul va fi mutat la noul furnizor. Această acțiune poate afecta rapoartele și statisticile.
            </div>
          </div>
        </div>
      ),
      okText: 'Da, schimbă furnizorul',
      okType: 'primary',
      cancelText: 'Anulează',
      onOk: async () => {
        try {
          await changeSupplierForProduct(
            selectedSupplierProduct.supplier_product_id,
            selectedSupplierProduct.supplier_id,
            newSupplierId
          );
          messageApi.success('Furnizor schimbat cu succes');
          setChangingSupplier(false);
          setNewSupplierId(null);
          setDetailModalVisible(false);
        } catch (err) {
          const errorObj = err as Error;
          messageApi.error(errorObj.message || 'Eroare la schimbarea furnizorului');
        }
      }
    });
  };

  const handleLocalChineseNameChange = async (productId: number, value: string) => {
    const trimmed = value.trim();
    try {
      await updateLocalChineseName(productId, trimmed ? trimmed : null);
      messageApi.success('Numele chinezesc a fost actualizat.');
    } catch (err) {
      const errorObj = err as Error;
      messageApi.error(errorObj.message || 'Actualizarea numelui a eșuat.');
      throw errorObj;
    }
  };

  const handleSupplierProductUrlChange = async (record: SupplierMatch, value: string) => {
    const trimmed = value.trim();

    if (!trimmed) {
      messageApi.error('URL-ul produsului nu poate fi gol.');
      throw new Error('URL-ul produsului nu poate fi gol.');
    }

    try {
      new URL(trimmed);
    } catch {
      messageApi.error('URL-ul introdus nu este valid.');
      throw new Error('URL-ul introdus nu este valid.');
    }

    try {
      await updateSupplierProductUrl(record.supplier_product_id, record.supplier_id, trimmed);
      messageApi.success('URL-ul produsului furnizorului a fost actualizat.');
    } catch (err) {
      const errorObj = err as Error;
      messageApi.error(errorObj.message || 'Actualizarea URL-ului furnizorului a eșuat.');
      throw errorObj;
    }
  };

  const handleSupplierProductNameChange = async (record: SupplierMatch, value: string) => {
    try {
      await updateSupplierProductName(record.supplier_product_id, record.supplier_id, value);
      messageApi.success('Numele produsului furnizorului a fost actualizat.');
    } catch (err) {
      const errorObj = err as Error;
      messageApi.error(errorObj.message || 'Actualizarea numelui furnizorului a eșuat.');
      throw errorObj;
    }
  };

  const handleViewSupplierDetails = (record: SupplierMatch) => {
    setSelectedSupplierProduct(record);
    setDetailModalVisible(true);
  };

  const supplierColumns = [
    {
      title: 'Produs',
      key: 'product',
      width: 480,
      render: (record: SupplierMatch) => {
        const imageUrl = (() => {
          try {
            return getImageUrl(record);
          } catch (error) {
            return null;
          }
        })();

        return (
          <Space>
            <Image
              src={imageUrl || '/placeholder-product.png'}
              alt={record.supplier_product_chinese_name || record.supplier_product_name}
              width={150}
              height={150}
              style={{ objectFit: 'cover', borderRadius: 4 }}
              fallback="/placeholder-product.png"
            />
            <div>
              <Typography.Paragraph
                style={{ marginBottom: 0 }}
                editable={{
                  onChange: value => handleSupplierProductNameChange(record, value),
                  tooltip: 'Editează numele produsului furnizorului',
                }}
              >
                {record.supplier_product_chinese_name || record.supplier_product_name || 'Click pentru a adăuga numele produsului'}
              </Typography.Paragraph>
              {updatingSupplierNameIds.has(record.supplier_product_id) ? (
                <Spin size="small" style={{ marginTop: 4 }} />
              ) : null}
              {typeof record.supplier_price === 'number' ? (
                <div style={{ fontSize: 13, color: '#434343', fontWeight: 500 }}>
                  {record.supplier_price}{' '}<span style={{ fontWeight: 400 }}>{record.supplier_currency}</span>
                </div>
              ) : null}
              {record.supplier_name ? (
                <div style={{ fontSize: 14, color: '#8c8c8c', marginTop: 6 }}>
                  Furnizor: {record.supplier_name}
                </div>
              ) : null}
              <Typography.Paragraph
                style={{ marginTop: 6, marginBottom: 2, fontSize: 12, color: '#1677ff' }}
                editable={{
                  onChange: value => handleSupplierProductUrlChange(record, value),
                  tooltip: 'Editează link-ul produsului furnizorului',
                }}
              >
                {record.supplier_product_url ? (
                  <a href={record.supplier_product_url} target="_blank" rel="noopener noreferrer" style={{ color: '#1677ff' }}>
                    {record.supplier_product_url}
                  </a>
                ) : (
                  <span style={{ color: '#8c8c8c' }}>Click pentru a adăuga link-ul produsului</span>
                )}
              </Typography.Paragraph>
              {updatingSupplierUrlIds.has(record.supplier_product_id) ? (
                <Spin size="small" style={{ marginTop: 6 }} />
              ) : null}
              {record.local_product?.sku ? (
                <div style={{ fontSize: 13, color: '#52c41a' }}>
                  Asociat cu SKU: {record.local_product.sku}
                </div>
              ) : null}
              <div style={{ marginTop: 6 }}>
                <Tag color={getConfidenceColor(record.similarity_score)}>
                  {Math.round(record.similarity_score * 100)}% - {getConfidenceLabel(record.similarity_score)}
                </Tag>
              </div>
              <div style={{ marginTop: 6 }}>
                <Button
                  type="link"
                  icon={<EyeOutlined />}
                  onClick={() => handleViewSupplierDetails(record)}
                >
                  Vezi detalii
                </Button>
              </div>
            </div>
          </Space>
        );
      },
    },
    
  ];

  const localColumns = [
    {
      title: 'Produs local',
      key: 'product',
      width: 470,
      render: (record: LocalProductMatch) => (
        <Space>
          <Image
            src={record.image_url || '/placeholder-product.png'}
            alt={record.name}
            width={110}
            height={110}
            style={{ objectFit: 'cover', borderRadius: 4 }}
            fallback="/placeholder-product.png"
          />
          <div>
            <div><strong>{record.name}</strong></div>
            <Typography.Paragraph
              style={{ marginTop: 8, marginBottom: 0 }}
              editable={{
                onChange: value => handleLocalChineseNameChange(record.id, value),
                tooltip: 'Editează numele chinezesc',
              }}
            >
              {record.chinese_name || ''}
            </Typography.Paragraph>
            {record.sku ? (
              <div style={{ marginTop: 8, fontSize: 15, color: '#52c41a' }}>SKU: {record.sku}</div>
            ) : null}
            <div style={{ marginTop: 8 }}>
              <Tag color={getConfidenceColor(record.similarity_score)}>
                {Math.round(record.similarity_score * 100)}% - {getConfidenceLabel(record.similarity_score)}
              </Tag>
            </div>
            <div style={{ marginTop: 8 }}>
              <Tag color={record.supplier_match_count && record.supplier_match_count > 0 ? '#1890ff' : '#d9d9d9'}>
                Furnizori asociați: {record.supplier_match_count ?? 0}
              </Tag>
            </div>
            {updatingLocalIds.has(record.id) ? <Spin size="small" style={{ marginTop: 8 }} /> : null}
          </div>
        </Space>
      ),
    },
  ];

  const handleLink = async (supplierProductId: number) => {
    if (!selectedLocalKeys.length) {
      messageApi.warning('Selectează un produs local din tabelul din dreapta.');
      return;
    }

    const localProductId = Number(selectedLocalKeys[0]);

    try {
      await linkSupplierProduct(supplierProductId, localProductId);
      messageApi.success('Produsul furnizor a fost asociat cu succes.');
      setSelectedSupplierKeys([]);
      setSelectedLocalKeys([]);
    } catch (err) {
      const errorObj = err as Error;
      messageApi.error(errorObj.message || 'Asocierea a eșuat.');
    }
  };

  const statistics = useMemo(() => {
    if (!supplierMatches.length) {
      return {
        total: 0,
        averageScore: 0,
        highScoreCount: 0,
      };
    }

    const totalScore = supplierMatches.reduce((sum, match) => sum + match.similarity_score, 0);
    const highScoreCount = supplierMatches.filter(match => match.similarity_score >= 0.95).length;

    return {
      total: supplierMatches.length,
      averageScore: totalScore / supplierMatches.length,
      highScoreCount,
    };
  }, [supplierMatches]);

  return (
    <div style={{ padding: 16, maxWidth: '100%', overflowX: 'hidden' }}>
      {contextHolder}
      <Row gutter={16} style={{ marginBottom: 2 }}>
        <Col span={24}>
          <Card>
            <Title level={2} style={{ marginBottom: 2 }}>
              Căutare după nume chinezesc
            </Title>
            <Input.Search
              placeholder="Introduceți numele chinezesc al produsului"
              enterButton="Caută"
              size="large"
              value={searchValue}
              onChange={event => setSearchValue(event.target.value)}
              onSearch={handleSearch}
              loading={loading}
            />
            <div style={{ marginTop: 16, marginBottom: 8 }}>
              <Typography.Text strong>Precizie căutare: {Math.round(minSimilarity * 100)}%</Typography.Text>
              <Tooltip title="Ajustează precizia căutării. Valori mai mici permit rezultate mai diverse (fuzzy matching).">
                <Slider
                  min={0.3}
                  max={1.0}
                  step={0.05}
                  value={minSimilarity}
                  onChange={setMinSimilarity}
                  marks={{
                    0.3: '30%',
                    0.5: '50%',
                    0.75: '75%',
                    1.0: '100%',
                  }}
                  style={{ marginTop: 8 }}
                />
              </Tooltip>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                💡 Threshold-ul mai mic (30-50%) permite găsirea produselor cu nume parțiale sau similare (ex: "100X60X10m" va găsi "100X60X10mm")
              </Typography.Text>
            </div>
            {error ? (
              <Alert
                type="error"
                message="Eroare la încărcarea rezultatelor"
                description={error.message}
                showIcon
                style={{ margin: 16 }}
              />
            ) : null}
          </Card>
        </Col>
      </Row>

      {supplierMatches.length > 0 && (
        <Row gutter={16} style={{ marginBottom: 2 }}>
          <Col span={24}>
            <Card>
              <Space size={16} wrap>
                <Statistic title="Total rezultate" value={statistics.total} />
                <Statistic 
                  title="Scor mediu" 
                  value={Math.round(statistics.averageScore * 100)} 
                  suffix="%" 
                />
                <Statistic 
                  title="Potriviri excelente" 
                  value={statistics.highScoreCount} 
                  valueStyle={{ color: '#52c41a' }} 
                />
              </Space>
            </Card>
          </Col>
        </Row>
      )}

      <Row gutter={12} wrap={false} style={{ marginBottom: 2 }}>
        <Col span={12}>
          <Card bodyStyle={{ padding: 12 }}>
            <Title level={4} style={{ whiteSpace: 'nowrap' }}>Rezultate Furnizori</Title>
            <Table<SupplierMatch>
              rowKey="supplier_product_id"
              columns={supplierColumns}
              dataSource={supplierMatches}
              loading={loading}
              pagination={{
                pageSize: supplierPageSize,
                showSizeChanger: true,
                pageSizeOptions: ['1', '10', '20', '39', '50', '100'],
                showTotal: (total, range) => `${range[0]}-${range[1]} din ${total} produse`,
                onShowSizeChange: (_, size) => handleSupplierPageSizeChange(size),
              }}
              rowSelection={{
                type: 'radio',
                selectedRowKeys: selectedSupplierKeys,
                onChange: keys => setSelectedSupplierKeys(keys),
              }}
              scroll={{ x: 640 }}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card bodyStyle={{ padding: 12 }}>
            <Title level={4} style={{ whiteSpace: 'nowrap' }}>Produse Locale</Title>
            <Table<LocalProductMatch>
              rowKey="id"
              columns={localColumns}
              dataSource={localMatches}
              loading={loading}
              pagination={{
                pageSize: localPageSize,
                showSizeChanger: true,
                pageSizeOptions: ['1', '10', '20', '39', '50', '100'],
                showTotal: (total, range) => `${range[0]}-${range[1]} din ${total} produse`,
                onShowSizeChange: (_, size) => handleLocalPageSizeChange(size),
              }}
              rowSelection={{
                type: 'radio',
                selectedRowKeys: selectedLocalKeys,
                onChange: keys => setSelectedLocalKeys(keys),
              }}
              scroll={{ x: 660 }}
            />
            <div style={{ marginTop: 16, textAlign: 'right' }}>
              <Tooltip title={!selectedSupplierKeys.length || !selectedLocalKeys.length ? 'Selectează câte un produs din fiecare tabel.' : ''}>
                <Button
                  type="primary"
                  disabled={!selectedSupplierKeys.length || !selectedLocalKeys.length}
                  onClick={() => handleLink(Number(selectedSupplierKeys[0]))}
                  loading={selectedSupplierKeys.some(key => linkingIds.has(Number(key)))}
                >
                  Asociază produsele selectate
                </Button>
              </Tooltip>
            </div>
          </Card>
        </Col>
      </Row>

      <Modal
        title={
          <Space>
            <ShoppingOutlined style={{ color: '#1890ff', fontSize: 20 }} />
            <Typography.Text strong style={{ fontSize: 18 }}>Detalii Produs Furnizor - căutare după nume chinezesc</Typography.Text>
          </Space>
        }
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        width={800}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            Închide
          </Button>,
        ]}
      >
        {selectedSupplierProduct ? (
          <Row gutter={24}>
            <Col span={12}>
              <Typography.Title level={5}>Produs Furnizor</Typography.Title>
              <Space direction="vertical" size={12} style={{ width: '100%' }}>
                {(() => {
                  let supplierImage: string | null = null;
                  try {
                    supplierImage = getImageUrl(selectedSupplierProduct);
                  } catch {
                    supplierImage = null;
                  }

                  const imageSrc = supplierImage || selectedSupplierProduct.supplier_image_url || '/placeholder-product.png';

                  return (
                    <Image
                      src={imageSrc}
                      alt={selectedSupplierProduct.supplier_product_name}
                      width={220}
                      height={220}
                      style={{ objectFit: 'cover', borderRadius: 8 }}
                      fallback="/placeholder-product.png"
                    />
                  );
                })()}
                <Typography.Text strong>
                  {selectedSupplierProduct.supplier_product_chinese_name || selectedSupplierProduct.supplier_product_name}
                </Typography.Text>
                <Typography.Text>
                  <strong>Preț:</strong>{' '}
                  {typeof selectedSupplierProduct.supplier_price === 'number'
                    ? `${selectedSupplierProduct.supplier_price} ${selectedSupplierProduct.supplier_currency ?? ''}`
                    : 'N/A'}
                </Typography.Text>
                {selectedSupplierProduct.supplier_product_url ? (
                  <Typography.Link
                    href={selectedSupplierProduct.supplier_product_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {selectedSupplierProduct.supplier_product_url}
                  </Typography.Link>
                ) : null}
                <div style={{ marginBottom: '12px' }}>
                  <Typography.Text strong>Furnizor:</Typography.Text>
                  {changingSupplier ? (
                    <div style={{ marginTop: '8px' }}>
                      <Select
                        value={newSupplierId}
                        onChange={(value) => setNewSupplierId(value)}
                        placeholder="Selectează furnizor nou..."
                        style={{ width: '100%', marginBottom: '8px' }}
                        loading={loadingSuppliers}
                      >
                        {suppliers
                          .filter(s => s.id !== selectedSupplierProduct.supplier_id)
                          .map(supplier => (
                            <Select.Option key={supplier.id} value={supplier.id}>
                              {supplier.name}
                            </Select.Option>
                          ))}
                      </Select>
                      <Space>
                        <Button
                          type="primary"
                          size="small"
                          icon={<CheckCircleOutlined />}
                          onClick={handleChangeSupplier}
                          disabled={!newSupplierId || changingSupplierIds.has(selectedSupplierProduct.supplier_product_id)}
                          loading={changingSupplierIds.has(selectedSupplierProduct.supplier_product_id)}
                        >
                          Schimbă
                        </Button>
                        <Button
                          size="small"
                          icon={<CloseCircleOutlined />}
                          onClick={() => {
                            setChangingSupplier(false);
                            setNewSupplierId(null);
                          }}
                        >
                          Anulează
                        </Button>
                      </Space>
                    </div>
                  ) : (
                    <div style={{ marginTop: '4px' }}>
                      <Space>
                        <Tag color="blue" style={{ fontSize: '13px' }}>
                          {selectedSupplierProduct.supplier_name || 'Necunoscut'}
                        </Tag>
                        <Button
                          type="link"
                          size="small"
                          icon={<SyncOutlined />}
                          onClick={() => setChangingSupplier(true)}
                          style={{ padding: 0, fontSize: '12px' }}
                        >
                          Schimbă furnizor
                        </Button>
                      </Space>
                    </div>
                  )}
                </div>
                {selectedSupplierProduct.supplier_product_specification ? (
                  <Typography.Text>
                    <strong>Specificații:</strong> {selectedSupplierProduct.supplier_product_specification}
                  </Typography.Text>
                ) : null}
              </Space>
            </Col>
            <Col span={12}>
              <Typography.Title level={5}>Produs Local</Typography.Title>
              {selectedSupplierProduct.local_product ? (
                <Space direction="vertical" size={12} style={{ width: '100%' }}>
                  <Image
                    src={selectedSupplierProduct.local_product.image_url || '/placeholder-product.png'}
                    alt={selectedSupplierProduct.local_product.name}
                    width={220}
                    height={220}
                    style={{ objectFit: 'cover', borderRadius: 8 }}
                    fallback="/placeholder-product.png"
                  />
                  <Typography.Text strong>
                    {selectedSupplierProduct.local_product.name}
                  </Typography.Text>
                  {selectedSupplierProduct.local_product.chinese_name ? (
                    <Typography.Text>
                      <strong>Nume Chinezesc:</strong> {selectedSupplierProduct.local_product.chinese_name}
                    </Typography.Text>
                  ) : null}
                  {selectedSupplierProduct.local_product.sku ? (
                    <Typography.Text>
                      <strong>SKU:</strong> {selectedSupplierProduct.local_product.sku}
                    </Typography.Text>
                  ) : null}
                  {selectedSupplierProduct.local_product.brand ? (
                    <Typography.Text>
                      <strong>Brand:</strong> {selectedSupplierProduct.local_product.brand}
                    </Typography.Text>
                  ) : null}
                </Space>
              ) : (
                <Typography.Text type="secondary">
                  Nu există produs local asociat.
                </Typography.Text>
              )}
              <Divider />
              <Space direction="vertical" style={{ width: '100%' }}>
                <Typography.Text>
                  <strong>Similaritate:</strong>{' '}
                  {Math.round(selectedSupplierProduct.similarity_score * 100)}%
                </Typography.Text>
                <Typography.Text>
                  <strong>Manual confirmat:</strong>{' '}
                  {selectedSupplierProduct.manual_confirmed ? 'Da' : 'Nu'}
                </Typography.Text>
                <Divider />

              </Space>
            </Col>
          </Row>
        ) : null}
      </Modal>
    </div>
  );
};

export default ChineseNameSearchPage;
