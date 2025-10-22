import React, { useMemo, useState } from 'react';
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
} from 'antd';
import useChineseNameSearch, {
  SupplierMatch,
  LocalProductMatch,
} from '../../hooks/useChineseNameSearch';

const { Title } = Typography;

const getConfidenceColor = (score: number) => {
  if (score >= 0.95) return '#52c41a';
  if (score >= 0.9) return '#73d13d';
  if (score >= 0.75) return '#95de64';
  return '#faad14';
};

const getConfidenceLabel = (score: number) => {
  if (score >= 0.95) return 'Excelent';
  if (score >= 0.9) return 'Foarte bun';
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
  const [searchValue, setSearchValue] = useState('');
  const [selectedSupplierKeys, setSelectedSupplierKeys] = useState<React.Key[]>([]);
  const [selectedLocalKeys, setSelectedLocalKeys] = useState<React.Key[]>([]);
  const [messageApi, contextHolder] = message.useMessage();

  const {
    supplierMatches,
    localMatches,
    loading,
    error,
    setChineseName,
    linkSupplierProduct,
    linkingIds,
    updateLocalChineseName,
    updatingLocalIds,
    updateSupplierProductName,
    updatingSupplierNameIds,
  } = useChineseNameSearch();

  const handleSearch = (value: string) => {
    setChineseName(value);
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

  const supplierColumns = [
    {
      title: 'Produs',
      key: 'product',
      width: 680,
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
                style={{ marginBottom: 0, fontWeight: 600 }}
                editable={{
                  onChange: value => handleSupplierProductNameChange(record, value),
                  tooltip: 'Editează numele produsului furnizorului',
                }}
              >
                {record.supplier_product_chinese_name || 'Click pentru a adăuga numele produsului'}
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
                <div style={{ fontSize: 14, color: '#8c8c8c', marginTop: 2 }}>
                  Furnizor: {record.supplier_name}
                </div>
              ) : null}
              {record.supplier_product_url ? (
                <div style={{ marginTop: 4 }}>
                  <a href={record.supplier_product_url} target="_blank" rel="noopener noreferrer">
                    Deschide produs
                  </a>
                </div>
              ) : null}
              {record.local_product?.sku ? (
                <div style={{ fontSize: 13, color: '#52c41a' }}>
                  Asociat cu: {record.local_product.sku}
                </div>
              ) : null}
              <div style={{ marginTop: 4 }}>
                <Tag color={getConfidenceColor(record.similarity_score)}>
                  {Math.round(record.similarity_score * 100)}% - {getConfidenceLabel(record.similarity_score)}
                </Tag>
              </div>
            </div>
          </Space>
        );
      },
    },
    {
      title: 'Acțiuni',
      key: 'actions',
      width: 80,
      render: (record: SupplierMatch) => (
        <Space>
          <Tooltip title={record.local_product ? 'Produs deja asociat' : 'Selectează un produs local și apasă "Asociază"'}>
            <Button
              type="default"
              disabled={!selectedLocalKeys.length || !!record.local_product}
              onClick={() => handleLink(record.supplier_product_id)}
              loading={linkingIds.has(record.supplier_product_id)}
            >
              Asociază
            </Button>
          </Tooltip>
        </Space>
      ),
    },
  ];

  const localColumns = [
    {
      title: 'SKU',
      dataIndex: 'sku',
      key: 'sku',
      width: 70,
    },
    {
      title: 'Produs local',
      key: 'product',
      width: 420,
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
              style={{ marginTop: 8, marginBottom: 0, maxWidth: 260 }}
              editable={{
                onChange: value => handleLocalChineseNameChange(record.id, value),
                tooltip: 'Editează numele chinezesc',
              }}
            >
              {record.chinese_name || 'Click pentru a adăuga nume chinezesc'}
            </Typography.Paragraph>
            {updatingLocalIds.has(record.id) ? <Spin size="small" style={{ marginTop: 4 }} /> : null}
          </div>
        </Space>
      ),
    },
    {
      title: 'Similaritate',
      key: 'similarity',
      width: 90,
      render: (record: LocalProductMatch) => (
        <Tag color={getConfidenceColor(record.similarity_score)}>
          {Math.round(record.similarity_score * 100)}% - {getConfidenceLabel(record.similarity_score)}
        </Tag>
      ),
    },
    {
      title: 'Furnizori asociați',
      dataIndex: 'supplier_match_count',
      key: 'supplier_match_count',
      width: 160,
      render: (value: number = 0) => <Tag color={value > 0 ? '#1890ff' : '#d9d9d9'}>{value}</Tag>,
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
    <div style={{ padding: 24, maxWidth: '100%', overflowX: 'auto' }}>
      {contextHolder}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={24}>
          <Card>
            <Title level={2} style={{ marginBottom: 24 }}>
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
        <Row gutter={16} style={{ marginBottom: 16 }}>
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

      <Row gutter={16} wrap={false} style={{ overflowX: 'auto' }}>
        <Col flex="1 1 60%">
          <Card bodyStyle={{ padding: 16 }}>
            <Title level={4} style={{ whiteSpace: 'nowrap' }}>Rezultate Furnizori</Title>
            <Table<SupplierMatch>
              rowKey="supplier_product_id"
              columns={supplierColumns}
              dataSource={supplierMatches}
              loading={loading}
              pagination={{ pageSize: 10 }}
              rowSelection={{
                type: 'radio',
                selectedRowKeys: selectedSupplierKeys,
                onChange: keys => setSelectedSupplierKeys(keys),
              }}
              scroll={{ x: 799 }}
            />
          </Card>
        </Col>
        <Col flex="0 0 460px" style={{ minWidth: 490 }}>
          <Card bodyStyle={{ padding: 16 }}>
            <Title level={4} style={{ whiteSpace: 'nowrap' }}>Produse Locale</Title>
            <Table<LocalProductMatch>
              rowKey="id"
              columns={localColumns}
              dataSource={localMatches}
              loading={loading}
              pagination={{ pageSize: 10 }}
              rowSelection={{
                type: 'radio',
                selectedRowKeys: selectedLocalKeys,
                onChange: keys => setSelectedLocalKeys(keys),
              }}
              scroll={{ x: 1040 }}
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
    </div>
  );
};

export default ChineseNameSearchPage;
