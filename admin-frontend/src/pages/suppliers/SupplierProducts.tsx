import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Table,
  Button,
  Space,
  Tag,
  Typography,
  Input,
  Select,
  Statistic,
  Tooltip,
  Empty,
  Modal,
  Divider,
  Image,
  App as AntApp,
  Upload,
  Alert
} from 'antd';
import {
  SearchOutlined,
  ReloadOutlined,
  FilterOutlined,
  EyeOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DollarOutlined,
  TeamOutlined,
  CloudUploadOutlined,
  FileExcelOutlined,
  ShoppingOutlined,
  GlobalOutlined,
  ClockCircleOutlined,
  DeleteOutlined,
  ExclamationCircleOutlined,
  SyncOutlined
} from '@ant-design/icons';
import type { UploadProps } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import api from '../../services/api';

const { Title, Text } = Typography;
const { Option } = Select;

interface LocalProduct {
  id: number;
  name: string;
  chinese_name?: string;
  sku: string;
  brand?: string;
  category?: string;
  image_url?: string;
}

interface SupplierProduct {
  id: number;
  supplier_id?: number;
  supplier_name?: string;
  supplier_product_name: string;
  supplier_product_chinese_name?: string;
  supplier_product_specification?: string;
  supplier_product_url: string;
  supplier_image_url: string;
  supplier_price: number;
  supplier_currency: string;
  local_product_id?: number;  // Add this field
  confidence_score: number;
  manual_confirmed: boolean;
  is_active: boolean;
  import_source?: string;
  last_price_update?: string;
  created_at: string;
  local_product?: LocalProduct;
}

interface Supplier {
  id: number;
  name: string;
  country: string;
}

interface Statistics {
  total_products: number;
  confirmed_products: number;
  pending_products: number;
  active_products: number;
  average_confidence: number;
  confirmation_rate: number;
}

const SupplierProductsPage: React.FC = () => {
  const { message, modal } = AntApp.useApp();
  const [products, setProducts] = useState<SupplierProduct[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [localProducts, setLocalProducts] = useState<LocalProduct[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedSupplier, setSelectedSupplier] = useState<number | null>(null);
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [searchText, setSearchText] = useState('');
  const [confirmedFilter, setConfirmedFilter] = useState<string>('all');
  const [selectedProduct, setSelectedProduct] = useState<SupplierProduct | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedLocalProductId, setSelectedLocalProductId] = useState<number | null>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [editingPrice, setEditingPrice] = useState<{[key: number]: number}>({});
  const [editingChineseName, setEditingChineseName] = useState<string | null>(null);
  const [isEditingChineseName, setIsEditingChineseName] = useState(false);
  const [editingSupplierChineseName, setEditingSupplierChineseName] = useState<string | null>(null);
  const [isEditingSupplierChineseName, setIsEditingSupplierChineseName] = useState(false);
  const [editingSpecification, setEditingSpecification] = useState<string | null>(null);
  const [isEditingSpecification, setIsEditingSpecification] = useState(false);
  const [changingSupplier, setChangingSupplier] = useState(false);
  const [newSupplierId, setNewSupplierId] = useState<number | null>(null);
  const [editingUrl, setEditingUrl] = useState<string | null>(null);
  const [isEditingUrl, setIsEditingUrl] = useState(false);
  const [editingLocalName, setEditingLocalName] = useState<string | null>(null);
  const [isEditingLocalName, setIsEditingLocalName] = useState(false);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  });

  useEffect(() => {
    loadSuppliers();
  }, []);

  useEffect(() => {
    if (selectedSupplier) {
      loadProducts();
      loadStatistics();
    }
  }, [selectedSupplier, pagination.current, pagination.pageSize, confirmedFilter, searchText]);

  const loadSuppliers = async () => {
    try {
      const response = await api.get('/suppliers', {
        params: { limit: 1000, active_only: true }
      });
      const suppliersData = response.data?.data?.suppliers || [];
      setSuppliers(suppliersData);
      
      if (suppliersData.length > 0 && !selectedSupplier) {
        setSelectedSupplier(suppliersData[0].id);
      }
    } catch (error) {
      console.error('Error loading suppliers:', error);
      message.error('Failed to load suppliers');
    }
  };

  const loadProducts = async () => {
    if (!selectedSupplier) return;

    try {
      setLoading(true);
      const skip = (pagination.current - 1) * pagination.pageSize;
      
      const response = await api.get(`/suppliers/${selectedSupplier}/products`, {
        params: {
          skip,
          limit: pagination.pageSize,
          confirmed_only: confirmedFilter === 'confirmed',
          search: searchText || undefined,
        }
      });

      const data = response.data?.data;
      setProducts(data?.products || []);
      setPagination(prev => ({
        ...prev,
        total: data?.pagination?.total || 0,
      }));
    } catch (error) {
      console.error('Error loading products:', error);
      message.error('Failed to load supplier products');
    } finally {
      setLoading(false);
    }
  };

  const loadStatistics = async () => {
    if (!selectedSupplier) return;

    try {
      const response = await api.get(`/suppliers/${selectedSupplier}/products/statistics`);
      setStatistics(response.data?.data || null);
    } catch (error) {
      console.error('Error loading statistics:', error);
    }
  };

  const loadLocalProducts = async () => {
    try {
      const response = await api.get('/products', {
        params: { limit: 1000, active_only: true }
      });
      setLocalProducts(response.data?.data?.products || []);
    } catch (error) {
      console.error('Error loading local products:', error);
    }
  };

  const handleMatchProduct = async () => {
    if (!selectedProduct || !selectedSupplier || !selectedLocalProductId) {
      message.error('Selectează un produs local');
      return;
    }

    try {
      setLoading(true);
      await api.post(`/suppliers/${selectedSupplier}/products/${selectedProduct.id}/match`, {
        local_product_id: selectedLocalProductId,
        confidence_score: 1.0,
        manual_confirmed: true
      });

      message.success('Match confirmat cu succes!');
      setDetailModalVisible(false);
      setSelectedLocalProductId(null);
      await loadProducts();
      await loadStatistics();
    } catch (error) {
      message.error('Eroare la confirmarea match-ului');
    } finally {
      setLoading(false);
    }
  };

  const handleUnmatchProduct = async () => {
    if (!selectedProduct || !selectedSupplier) return;

    try {
      setLoading(true);
      await api.delete(`/suppliers/${selectedSupplier}/products/${selectedProduct.id}/match`);
      
      message.success('Match șters cu succes!');
      setDetailModalVisible(false);
      await loadProducts();
      await loadStatistics();
    } catch (error) {
      message.error('Eroare la ștergerea match-ului');
    } finally {
      setLoading(false);
    }
  };

  const handleSupplierChange = (supplierId: number) => {
    setSelectedSupplier(supplierId);
    setPagination(prev => ({ ...prev, current: 1 }));
  };

  const handleTableChange = (newPagination: any) => {
    setPagination({
      current: newPagination.current || 1,
      pageSize: newPagination.pageSize || 20,
      total: pagination.total,
    });
  };

  const handleExcelUpload: UploadProps['customRequest'] = async (options) => {
    const { file, onSuccess, onError } = options;
    
    if (!selectedSupplier) {
      message.error('Selectează un furnizor mai întâi');
      onError?.(new Error('No supplier selected'));
      return;
    }

    try {
      const formData = new FormData();
      formData.append('file', file as File);

      const response = await api.post(
        `/suppliers/${selectedSupplier}/products/import-excel`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      const data = response.data?.data;
      message.success(
        `Import reușit! ${data?.imported_count} produse importate, ${data?.skipped_count} sărite`
      );
      
      if (data?.errors && data.errors.length > 0) {
        Modal.warning({
          title: 'Atenție - Erori la import',
          content: (
            <div>
              <p>Unele rânduri au avut erori:</p>
              <ul style={{ maxHeight: '200px', overflow: 'auto' }}>
                {data.errors.map((error: string, index: number) => (
                  <li key={index}>{error}</li>
                ))}
              </ul>
            </div>
          ),
          width: 600,
        });
      }

      onSuccess?.(response.data);
      await loadProducts();
      await loadStatistics();
    } catch (error: any) {
      console.error('Error uploading Excel:', error);
      const errorMsg = error.response?.data?.detail || 'Failed to upload Excel file';
      message.error(errorMsg);
      onError?.(error);
    }
  };

  const viewProductDetails = async (product: SupplierProduct) => {
    setSelectedProduct(product);
    setSelectedLocalProductId(product.local_product?.id || null);
    setDetailModalVisible(true);
    await loadLocalProducts();
  };

  const handleDeleteProduct = (product: SupplierProduct) => {
    modal.confirm({
      title: 'Șterge produs furnizor',
      icon: <ExclamationCircleOutlined />,
      content: `Ești sigur că vrei să ștergi permanent produsul "${product.supplier_product_name}"?`,
      okText: 'Da, șterge',
      okType: 'danger',
      cancelText: 'Anulează',
      onOk: async () => {
        try {
          await api.delete(`/suppliers/${selectedSupplier}/products/${product.id}`);
          message.success('Produs șters cu succes');
          await loadProducts();
          await loadStatistics();
        } catch (error) {
          message.error('Eroare la ștergerea produsului');
        }
      }
    });
  };

  const handleUpdateChineseName = (product: SupplierProduct) => {
    const hasExistingName = !!product.local_product?.chinese_name;
    
    modal.confirm({
      title: hasExistingName ? 'Actualizează nume chinezesc' : 'Adaugă nume chinezesc',
      icon: <SyncOutlined />,
      content: (
        <div>
          <p>
            {hasExistingName 
              ? 'Vrei să suprascrii numele chinezesc existent cu cel de la furnizor?' 
              : 'Vrei să copiezi numele chinezesc de la furnizor în produsul local?'}
          </p>
          
          {hasExistingName && (
            <div style={{ marginTop: '12px', padding: '8px', background: '#fff2e8', borderRadius: '4px', border: '1px solid #ffbb96' }}>
              <Text strong>Nume chinezesc curent (local):</Text>
              <div style={{ color: '#fa8c16', marginTop: '4px' }}>
                {product.local_product?.chinese_name}
              </div>
            </div>
          )}
          
          <div style={{ marginTop: '12px', padding: '8px', background: '#f0f0f0', borderRadius: '4px' }}>
            <Text strong>Nume chinezesc furnizor {hasExistingName ? '(nou)' : ''}:</Text>
            <div style={{ color: '#1890ff', marginTop: '4px' }}>
              {product.supplier_product_chinese_name}
            </div>
          </div>
          
          <div style={{ marginTop: '8px' }}>
            <Text type="secondary">SKU: {product.local_product?.sku}</Text>
          </div>
        </div>
      ),
      okText: hasExistingName ? 'Da, suprascrie' : 'Da, adaugă',
      okType: hasExistingName ? 'primary' : 'primary',
      cancelText: 'Anulează',
      onOk: async () => {
        try {
          const response = await api.post('/products/chinese-name/update-from-supplier', {
            supplier_product_id: product.id
          });
          
          const newChineseName = response.data?.data?.new_chinese_name || product.supplier_product_chinese_name;
          
          message.success(
            hasExistingName 
              ? `Nume chinezesc actualizat pentru SKU ${product.local_product?.sku}` 
              : `Nume chinezesc adăugat pentru SKU ${product.local_product?.sku}`
          );
          await loadProducts();
          
          // Update selected product if modal is open
          if (selectedProduct?.id === product.id && selectedProduct.local_product) {
            setSelectedProduct({
              ...selectedProduct,
              local_product: {
                ...selectedProduct.local_product,
                chinese_name: newChineseName
              }
            });
          }
        } catch (error: any) {
          message.error(error.response?.data?.detail || 'Eroare la actualizarea numelui chinezesc');
        }
      }
    });
  };

  const handlePriceUpdate = async (productId: number, newPrice: number) => {
    try {
      await api.patch(`/suppliers/${selectedSupplier}/products/${productId}`, {
        supplier_price: newPrice
      });
      message.success('Preț actualizat cu succes');
      await loadProducts();
      setEditingPrice(prev => {
        const updated = {...prev};
        delete updated[productId];
        return updated;
      });
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Eroare la actualizarea prețului');
    }
  };

  const handleUpdateLocalChineseName = async () => {
    if (!selectedProduct?.local_product?.id || !editingChineseName) {
      message.error('Nume chinezesc invalid');
      return;
    }

    try {
      await api.patch(`/products-v1/${selectedProduct.local_product.id}/chinese-name`, {
        chinese_name: editingChineseName
      });
      message.success('Nume chinezesc actualizat cu succes');
      setIsEditingChineseName(false);
      await loadProducts();
      // Update selected product
      if (selectedProduct.local_product) {
        setSelectedProduct({
          ...selectedProduct,
          local_product: {
            ...selectedProduct.local_product,
            chinese_name: editingChineseName
          }
        });
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Eroare la actualizarea numelui chinezesc');
    }
  };

  const handleUpdateSupplierChineseName = async () => {
    if (!selectedProduct?.id || editingSupplierChineseName === null) {
      message.error('Nume chinezesc invalid');
      return;
    }

    try {
      await api.patch(`/suppliers/${selectedSupplier}/products/${selectedProduct.id}/chinese-name`, {
        chinese_name: editingSupplierChineseName
      });
      message.success('Nume chinezesc furnizor actualizat cu succes');
      setIsEditingSupplierChineseName(false);
      await loadProducts();
      // Update selected product
      setSelectedProduct({
        ...selectedProduct,
        supplier_product_chinese_name: editingSupplierChineseName
      });
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Eroare la actualizarea numelui chinezesc');
    }
  };

  const handleUpdateSpecification = async () => {
    if (!selectedProduct?.id || editingSpecification === null) {
      message.error('Specificații invalide');
      return;
    }

    try {
      await api.patch(`/suppliers/${selectedSupplier}/products/${selectedProduct.id}/specification`, {
        specification: editingSpecification
      });
      message.success('Specificații actualizate cu succes');
      setIsEditingSpecification(false);
      await loadProducts();
      // Update selected product
      setSelectedProduct({
        ...selectedProduct,
        supplier_product_specification: editingSpecification
      });
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Eroare la actualizarea specificațiilor');
    }
  };

  const handleChangeSupplier = async () => {
    if (!selectedProduct?.id || !newSupplierId) {
      message.error('Selectează un furnizor valid');
      return;
    }

    modal.confirm({
      title: 'Schimbă Furnizor',
      icon: <ExclamationCircleOutlined />,
      content: (
        <div>
          <p>Ești sigur că vrei să schimbi furnizorul pentru acest produs?</p>
          <div style={{ marginTop: '12px', padding: '8px', background: '#fff2e8', borderRadius: '4px' }}>
            <Text strong>Atenție:</Text>
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
          await api.patch(`/suppliers/${selectedSupplier}/products/${selectedProduct.id}/change-supplier`, {
            new_supplier_id: newSupplierId
          });
          message.success('Furnizor schimbat cu succes');
          setChangingSupplier(false);
          setNewSupplierId(null);
          setDetailModalVisible(false);
          await loadProducts();
          await loadStatistics();
        } catch (error: any) {
          message.error(error.response?.data?.detail || 'Eroare la schimbarea furnizorului');
        }
      }
    });
  };

  const handleUpdateUrl = async () => {
    if (!selectedProduct?.id || !editingUrl) {
      message.error('URL invalid');
      return;
    }

    // Validare URL
    try {
      new URL(editingUrl);
    } catch {
      message.error('URL-ul introdus nu este valid');
      return;
    }

    try {
      await api.patch(`/suppliers/${selectedSupplier}/products/${selectedProduct.id}/url`, {
        url: editingUrl
      });
      message.success('URL actualizat cu succes');
      setIsEditingUrl(false);
      await loadProducts();
      // Update selected product
      setSelectedProduct({
        ...selectedProduct,
        supplier_product_url: editingUrl
      });
    } catch (error: any) {
      // Handle duplicate URL error (409)
      if (error.response?.status === 409) {
        modal.error({
          title: 'URL Duplicat',
          content: (
            <div>
              <p>{error.response?.data?.detail}</p>
              <div style={{ marginTop: '12px', padding: '8px', background: '#fff2e8', borderRadius: '4px' }}>
                <Text strong>Sugestie:</Text>
                <div style={{ marginTop: '4px', fontSize: '12px' }}>
                  Verifică dacă acest produs nu este deja adăugat pentru același furnizor sau 
                  șterge duplicatul înainte de a actualiza URL-ul.
                </div>
              </div>
            </div>
          ),
        });
      } else {
        message.error(error.response?.data?.detail || 'Eroare la actualizarea URL-ului');
      }
    }
  };

  const handleUpdateLocalName = async () => {
    if (!selectedProduct?.local_product?.id || !editingLocalName) {
      message.error('Nume invalid');
      return;
    }

    try {
      await api.patch(`/products-v1/${selectedProduct.local_product.id}/name`, {
        name: editingLocalName
      });
      message.success('Nume produs actualizat cu succes');
      setIsEditingLocalName(false);
      await loadProducts();
      // Update selected product
      if (selectedProduct.local_product) {
        setSelectedProduct({
          ...selectedProduct,
          local_product: {
            ...selectedProduct.local_product,
            name: editingLocalName
          }
        });
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Eroare la actualizarea numelui');
    }
  };

  const handleBulkDelete = () => {
    if (selectedRowKeys.length === 0) {
      message.warning('Selectează cel puțin un produs');
      return;
    }

    modal.confirm({
      title: 'Șterge produse selectate',
      icon: <ExclamationCircleOutlined />,
      content: `Ești sigur că vrei să ștergi permanent ${selectedRowKeys.length} produse?`,
      okText: 'Da, șterge toate',
      okType: 'danger',
      cancelText: 'Anulează',
      onOk: async () => {
        try {
          await api.post(`/suppliers/${selectedSupplier}/products/bulk-delete`, {
            product_ids: selectedRowKeys
          });
          message.success(`${selectedRowKeys.length} produse șterse cu succes`);
          setSelectedRowKeys([]);
          await loadProducts();
          await loadStatistics();
        } catch (error) {
          message.error('Eroare la ștergerea produselor');
        }
      }
    });
  };

  const handleDeleteAllProducts = () => {
    if (!selectedSupplier || !statistics) return;

    modal.confirm({
      title: 'ATENȚIE: Șterge TOATE produsele',
      icon: <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />,
      content: (
        <div>
          <p><strong style={{ color: '#ff4d4f' }}>Această acțiune va șterge TOATE cele {statistics.total_products} produse ale furnizorului!</strong></p>
          <p>Această acțiune este IREVERSIBILĂ.</p>
          <p>Ești absolut sigur?</p>
        </div>
      ),
      okText: 'DA, ȘTERGE TOATE',
      okType: 'danger',
      cancelText: 'Anulează',
      onOk: async () => {
        try {
          const response = await api.delete(`/suppliers/${selectedSupplier}/products/all`);
          const deletedCount = response.data?.data?.deleted_count || 0;
          message.success(`Toate cele ${deletedCount} produse au fost șterse`);
          setSelectedRowKeys([]);
          await loadProducts();
          await loadStatistics();
        } catch (error) {
          message.error('Eroare la ștergerea produselor');
        }
      }
    });
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return '#52c41a';
    if (score >= 0.6) return '#faad14';
    return '#ff4d4f';
  };

  const getConfidenceLabel = (score: number) => {
    if (score >= 0.8) return 'Foarte sigur';
    if (score >= 0.6) return 'Mediu';
    return 'Scăzut';
  };

  // Get selected supplier data for potential future use
  // const selectedSupplierData = suppliers.find(s => s.id === selectedSupplier);

  const columns: ColumnsType<SupplierProduct> = [
    {
      title: 'Imagine Furnizor',
      key: 'supplier_image',
      width: 120,
      render: (_, record) => (
        <Image
          src={record.supplier_image_url}
          alt={record.supplier_product_name}
          width={80}
          height={80}
          style={{ objectFit: 'cover', borderRadius: '4px' }}
          fallback="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='60' height='60'%3E%3Crect width='60' height='60' fill='%23f0f0f0'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23999' font-size='10'%3ENo Image%3C/text%3E%3C/svg%3E"
          preview={{
            mask: <EyeOutlined />
          }}
        />
      ),
    },
    {
      title: 'Produs Furnizor',
      key: 'supplier_product',
      width: 350,
      render: (_, record) => (
        <Space direction="vertical" size={4}>
          <Text strong style={{ fontSize: '14px', color: '#1890ff' }}>
            {record.supplier_product_chinese_name || record.supplier_product_name}
          </Text>
          {record.supplier_product_specification && (
            <Tag color="green" style={{ fontSize: '11px' }}>
              {record.supplier_product_specification}
            </Tag>
          )}
          {record.import_source && (
            <Tag color={record.import_source === 'google_sheets' ? 'blue' : 'orange'} style={{ fontSize: '10px' }}>
              {record.import_source === 'google_sheets' ? 'Google Sheets' : 'Manual'}
            </Tag>
          )}
          <Space size={14}>
            <a 
              href={record.supplier_product_url} 
              target="_blank" 
              rel="noopener noreferrer"
              style={{ fontSize: '12px' }}
            >
              <GlobalOutlined style={{ marginRight: 4 }} />
              Vezi pe 1688.com
            </a>
            {record.supplier_product_chinese_name && record.local_product && (
              <Button
                type="link"
                size="small"
                icon={<SyncOutlined />}
                onClick={() => handleUpdateChineseName(record)}
                style={{ fontSize: '11px', padding: 0 }}
                title={record.local_product.chinese_name 
                  ? 'Actualizează/Suprascrie nume chinezesc existent' 
                  : 'Adaugă nume chinezesc din furnizor'}
              >
                {record.local_product.chinese_name ? '🔄' : '➕'} Actualizează CN
              </Button>
            )}
          </Space>
          
          {/* Preț editabil */}
          <Space size={8} style={{ marginTop: '4px' }}>
            <Text strong style={{ fontSize: '12px' }}>Preț:</Text>
            {editingPrice[record.id] !== undefined ? (
              <Space size={4}>
                <Input
                  type="number"
                  size="small"
                  style={{ width: '80px' }}
                  value={editingPrice[record.id]}
                  onChange={(e) => setEditingPrice(prev => ({
                    ...prev,
                    [record.id]: parseFloat(e.target.value) || 0
                  }))}
                  onPressEnter={() => handlePriceUpdate(record.id, editingPrice[record.id])}
                />
                <Button
                  type="primary"
                  size="small"
                  icon={<CheckCircleOutlined />}
                  onClick={() => handlePriceUpdate(record.id, editingPrice[record.id])}
                />
                <Button
                  size="small"
                  icon={<CloseCircleOutlined />}
                  onClick={() => setEditingPrice(prev => {
                    const updated = {...prev};
                    delete updated[record.id];
                    return updated;
                  })}
                />
              </Space>
            ) : (
              <Space size={4}>
                <Text strong style={{ color: '#1890ff', fontSize: '14px' }}>
                  {record.supplier_price.toFixed(2)} {record.supplier_currency}
                </Text>
                <Button
                  type="link"
                  size="small"
                  icon={<DollarOutlined />}
                  onClick={() => setEditingPrice(prev => ({
                    ...prev,
                    [record.id]: record.supplier_price
                  }))}
                  style={{ fontSize: '11px', padding: 0 }}
                >
                  Editează
                </Button>
              </Space>
            )}
          </Space>
        </Space>
      ),
    },
    {
      title: 'Imagine Local',
      key: 'local_image',
      width: 120,
      render: (_, record) => (
        record.local_product?.image_url ? (
          <Image
            src={record.local_product.image_url}
            alt={record.local_product.name}
            width={80}
            height={80}
            style={{ objectFit: 'cover', borderRadius: '4px' }}
            fallback="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='60' height='60'%3E%3Crect width='60' height='60' fill='%23f0f0f0'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23999' font-size='10'%3ENo Image%3C/text%3E%3C/svg%3E"
            preview={{
              mask: <EyeOutlined />
            }}
          />
        ) : (
          <div style={{
            width: 80,
            height: 80,
            background: '#f5f5f5',
            borderRadius: '4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: '1px dashed #d9d9d9'
          }}>
            <Text type="secondary" style={{ fontSize: '10px', textAlign: 'center' }}>
              No<br/>Image
            </Text>
          </div>
        )
      ),
    },
    {
      title: 'Produs Local',
      key: 'local_product',
      width: 350,
      render: (_, record) => (
        record.local_product ? (
          <Space direction="vertical" size={2}>
            <Text strong style={{ fontSize: '13px' }}>
              {record.local_product.name}
            </Text>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              SKU: {record.local_product.sku}
            </Text>
            {record.local_product.chinese_name && (
              <Text style={{ fontSize: '12px', color: '#52c41a', fontWeight: 'bold' }}>
                🇨🇳 {record.local_product.chinese_name}
              </Text>
            )}
          </Space>
        ) : (
          <Text type="secondary">-</Text>
        )
      ),
    },
    {
      title: 'Scor Potrivire',
      dataIndex: 'confidence_score',
      key: 'confidence_score',
      width: 130,
      sorter: (a, b) => a.confidence_score - b.confidence_score,
      render: (score: number) => (
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '16px', fontWeight: 'bold', color: getConfidenceColor(score) }}>
            {Math.round(score * 100)}%
          </div>
          <Tag color={getConfidenceColor(score)} style={{ fontSize: '11px' }}>
            {getConfidenceLabel(score)}
          </Tag>
        </div>
      ),
    },
    {
      title: 'Status Matching',
      key: 'status',
      width: 140,
      filters: [
        { text: 'Confirmat', value: 'confirmed' },
        { text: 'Pending', value: 'pending' },
        { text: 'Nematchat', value: 'unmatched' },
        { text: 'Activ', value: 'active' },
        { text: 'Inactiv', value: 'inactive' },
      ],
      onFilter: (value, record) => {
        if (value === 'confirmed') return !!(record.local_product_id && record.manual_confirmed);
        if (value === 'pending') return !!(record.local_product_id && !record.manual_confirmed);
        if (value === 'unmatched') return !record.local_product_id;
        if (value === 'active') return record.is_active;
        if (value === 'inactive') return !record.is_active;
        return true;
      },
      render: (_, record) => (
        <Space direction="vertical" size={4} style={{ width: '100%' }}>
          {record.local_product_id ? (
            <>
              <Tag 
                color={record.manual_confirmed ? 'green' : 'orange'}
                icon={record.manual_confirmed ? <CheckCircleOutlined /> : <ClockCircleOutlined />}
                style={{ width: '100%', textAlign: 'center' }}
              >
                {record.manual_confirmed ? 'Confirmat' : 'Pending'}
              </Tag>
              {record.confidence_score !== null && record.confidence_score !== undefined && (
                <div style={{ width: '100%' }}>
                  <Text type="secondary" style={{ fontSize: '11px' }}>
                    Scor: {Math.round(record.confidence_score * 100)}%
                  </Text>
                </div>
              )}
            </>
          ) : (
            <Tag 
              color="red" 
              icon={<CloseCircleOutlined />}
              style={{ width: '100%', textAlign: 'center' }}
            >
              Nematchat
            </Tag>
          )}
          {record.is_active && (
            <Tag color="blue" style={{ fontSize: '11px', width: '100%', textAlign: 'center' }}>
              Activ
            </Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'Data',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 110,
      render: (date: string) => (
        <Text style={{ fontSize: '12px' }}>
          {new Date(date).toLocaleDateString('ro-RO')}
        </Text>
      ),
    },
    {
      title: 'Acțiuni',
      key: 'actions',
      fixed: 'right',
      width: 120,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="Vezi detalii">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => viewProductDetails(record)}
              style={{ color: '#1890ff' }}
            />
          </Tooltip>
          <Tooltip title="Șterge permanent">
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDeleteProduct(record)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      {/* Header */}
      <Card 
        variant="borderless"
        style={{ 
          marginBottom: '24px',
          borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
        }}
      >
        <Row justify="space-between" align="middle">
          <Col>
            <Space direction="vertical" size={0}>
              <Title level={2} style={{ margin: 0, display: 'flex', alignItems: 'center' }}>
                <ShoppingOutlined style={{ marginRight: '12px', color: '#1890ff' }} />
                Produse Furnizori
              </Title>
              <Text type="secondary" style={{ fontSize: '14px' }}>
                Vizualizează și gestionează produsele de la furnizori cu potriviri automate
              </Text>
            </Space>
          </Col>
          <Col>
            <Space size="middle">
              <Upload
                accept=".xlsx,.xls"
                showUploadList={false}
                customRequest={handleExcelUpload}
                disabled={!selectedSupplier}
              >
                <Tooltip title={!selectedSupplier ? "Selectează un furnizor mai întâi" : "Încarcă fișier Excel cu produse"}>
                  <Button 
                    icon={<CloudUploadOutlined />}
                    disabled={!selectedSupplier}
                    size="large"
                    type="primary"
                    style={{ background: '#52c41a', borderColor: '#52c41a' }}
                  >
                    Import Excel
                  </Button>
                </Tooltip>
              </Upload>
              <Tooltip title="Șterge TOATE produsele furnizorului">
                <Button 
                  icon={<DeleteOutlined />}
                  onClick={handleDeleteAllProducts}
                  disabled={!selectedSupplier || !statistics || statistics.total_products === 0}
                  size="large"
                  danger
                  type="primary"
                >
                  Șterge Toate
                </Button>
              </Tooltip>
              <Button 
                icon={<ReloadOutlined />} 
                onClick={loadProducts}
                loading={loading}
                size="large"
              >
                Refresh
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Supplier Selection */}
      <Card 
        variant="borderless"
        style={{ 
          marginBottom: '24px',
          borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
        }}
      >
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <Text strong>Selectează Furnizor:</Text>
              <Select
                size="large"
                value={selectedSupplier}
                onChange={handleSupplierChange}
                style={{ width: '100%', maxWidth: '400px' }}
                suffixIcon={<TeamOutlined />}
                placeholder="Selectează un furnizor"
              >
                {suppliers.map(supplier => (
                  <Option key={supplier.id} value={supplier.id}>
                    <Space>
                      <TeamOutlined />
                      {supplier.name}
                    </Space>
                  </Option>
                ))}
              </Select>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Excel Import Info */}
      {selectedSupplier && (
        <Alert
          message="Import Produse din Excel"
          description={
            <Space direction="vertical" size={4}>
              <Text>📄 <strong>Format așteptat:</strong> Fișier Excel (.xlsx) cu următoarele coloane:</Text>
              <Text style={{ marginLeft: '20px' }}>• <code>url_image_scrapping</code> - URL imagine produs</Text>
              <Text style={{ marginLeft: '20px' }}>• <code>url_product_scrapping</code> - URL pagină produs (1688.com)</Text>
              <Text style={{ marginLeft: '20px' }}>• <code>chinese_name_scrapping</code> - Nume produs în chineză</Text>
              <Text style={{ marginLeft: '20px' }}>• <code>price_scrapping</code> - Preț (format: "CN ¥ 2.45")</Text>
              <Text>💡 <strong>Notă:</strong> Produsele existente (același URL) vor fi actualizate automat</Text>
            </Space>
          }
          type="info"
          showIcon
          icon={<FileExcelOutlined />}
          closable
          style={{ marginBottom: '16px', borderRadius: '8px' }}
        />
      )}

      {/* Statistics Cards */}
      {statistics && selectedSupplier && (
        <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
          <Col xs={24} sm={12} lg={6}>
            <Card 
              variant="borderless"
              style={{ 
                borderRadius: '8px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
              }}
            >
              <Statistic
                title={<span style={{ color: 'rgba(255,255,255,0.9)' }}>Total Produse</span>}
                value={statistics.total_products}
                prefix={<ShoppingOutlined />}
                valueStyle={{ color: '#fff', fontSize: '32px', fontWeight: 'bold' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card 
              variant="borderless"
              style={{ 
                borderRadius: '8px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
              }}
            >
              <Statistic
                title={<span style={{ color: 'rgba(255,255,255,0.9)' }}>Confirmate</span>}
                value={statistics.confirmed_products}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#fff', fontSize: '32px', fontWeight: 'bold' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card 
              variant="borderless"
              style={{ 
                borderRadius: '8px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)'
              }}
            >
              <Statistic
                title={<span style={{ color: 'rgba(255,255,255,0.9)' }}>În Așteptare</span>}
                value={statistics.pending_products}
                prefix={<ClockCircleOutlined />}
                valueStyle={{ color: '#fff', fontSize: '32px', fontWeight: 'bold' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card 
              variant="borderless"
              style={{ 
                borderRadius: '8px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                background: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)'
              }}
            >
              <Statistic
                title={<span style={{ color: 'rgba(255,255,255,0.9)' }}>Scor Mediu</span>}
                value={Math.round(statistics.average_confidence * 100)}
                suffix={<span style={{ color: 'rgba(255,255,255,0.9)', fontSize: '16px' }}>%</span>}
                prefix={<DollarOutlined />}
                valueStyle={{ color: '#fff', fontSize: '32px', fontWeight: 'bold' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Filters */}
      <Card 
        variant="borderless"
        style={{ 
          marginBottom: '16px',
          borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
        }}
      >
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} md={10}>
            <Input
              size="large"
              placeholder="Caută după nume produs..."
              prefix={<SearchOutlined style={{ color: '#1890ff' }} />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              allowClear
              style={{ borderRadius: '6px' }}
            />
          </Col>
          <Col xs={24} md={8}>
            <Select
              size="large"
              placeholder="Filtrează după status"
              value={confirmedFilter}
              onChange={setConfirmedFilter}
              style={{ width: '100%', borderRadius: '6px' }}
              suffixIcon={<FilterOutlined />}
            >
              <Option value="all">📋 Toate produsele</Option>
              <Option value="confirmed">✅ Doar confirmate</Option>
              <Option value="pending">⏳ Doar în așteptare</Option>
            </Select>
          </Col>
          <Col xs={24} md={6}>
            <Button 
              size="large"
              onClick={() => { setSearchText(''); setConfirmedFilter('all'); }}
              style={{ borderRadius: '6px' }}
            >
              Resetează Filtre
            </Button>
          </Col>
        </Row>
      </Card>

      {/* Bulk Actions Card */}
      {selectedRowKeys.length > 0 && (
        <Card 
          variant="borderless"
          style={{ 
            marginBottom: '16px',
            borderRadius: '8px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
            background: '#fff2e8'
          }}
        >
          <Row justify="space-between" align="middle">
            <Col>
              <Text strong style={{ fontSize: '14px', color: '#fa8c16' }}>
                {selectedRowKeys.length} produse selectate
              </Text>
            </Col>
            <Col>
              <Space>
                <Button 
                  danger
                  type="primary"
                  icon={<DeleteOutlined />}
                  onClick={handleBulkDelete}
                  style={{ borderRadius: '6px' }}
                >
                  Șterge Selectate
                </Button>
                <Button 
                  onClick={() => setSelectedRowKeys([])}
                  style={{ borderRadius: '6px' }}
                >
                  Anulează selecția
                </Button>
              </Space>
            </Col>
          </Row>
        </Card>
      )}

      {/* Products Table */}
      <Card 
        variant="borderless"
        style={{ 
          borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
        }}
      >
        {selectedSupplier ? (
          <Table
            columns={columns}
            dataSource={products}
            rowKey="id"
            loading={loading}
            rowSelection={{
              selectedRowKeys,
              onChange: (keys) => setSelectedRowKeys(keys),
              preserveSelectedRowKeys: true,
            }}
            pagination={{
              ...pagination,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total, range) => (
                <Text strong>
                  {range[0]}-{range[1]} din {total} produse
                </Text>
              ),
              pageSizeOptions: ['10', '20', '50', '100'],
            }}
            onChange={handleTableChange}
            scroll={{ x: 1400 }}
            size="middle"
            locale={{
              emptyText: (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description={
                    <Space direction="vertical">
                      <Text type="secondary">Nu există produse pentru acest furnizor</Text>
                    </Space>
                  }
                />
              )
            }}
          />
        ) : (
          <Empty
            description="Selectează un furnizor pentru a vedea produsele"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        )}
      </Card>

      {/* Product Details Modal */}
      <Modal
        title={
          <Space>
            <ShoppingOutlined style={{ color: '#1890ff', fontSize: '20px' }} />
            <Text strong style={{ fontSize: '18px' }}>Detalii Produs Furnizor</Text>
          </Space>
        }
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        width={1199}
        style={{ top: 5 }}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)} size="large">
            Închide
          </Button>
        ]}
      >
        {selectedProduct && (
          <div>
            <Row gutter={24}>
              <Col span={12}>
                <Card title="Produs Furnizor (1688.com)" size="small">
                  <div style={{ textAlign: 'center', marginBottom: '16px' }}>
                    <Image
                      src={selectedProduct.supplier_image_url}
                      alt={selectedProduct.supplier_product_name}
                      width={200}
                      height={200}
                      style={{ objectFit: 'cover', borderRadius: '8px' }}
                    />
                  </div>
                  {/* Nume Chinezesc Furnizor Editabil */}
                  <div style={{ marginBottom: '12px' }}>
                    <Text strong>Nume Chinezesc:</Text>
                    {isEditingSupplierChineseName ? (
                      <div style={{ marginTop: '8px' }}>
                        <Input.TextArea
                          value={editingSupplierChineseName || ''}
                          onChange={(e) => setEditingSupplierChineseName(e.target.value)}
                          placeholder="Introdu numele chinezesc al furnizorului..."
                          autoSize={{ minRows: 2, maxRows: 4 }}
                          style={{ marginBottom: '8px' }}
                        />
                        <Space>
                          <Button
                            type="primary"
                            size="small"
                            icon={<CheckCircleOutlined />}
                            onClick={handleUpdateSupplierChineseName}
                          >
                            Salvează
                          </Button>
                          <Button
                            size="small"
                            icon={<CloseCircleOutlined />}
                            onClick={() => {
                              setIsEditingSupplierChineseName(false);
                              setEditingSupplierChineseName(null);
                            }}
                          >
                            Anulează
                          </Button>
                        </Space>
                      </div>
                    ) : (
                      <div style={{ marginTop: '4px' }}>
                        {selectedProduct.supplier_product_chinese_name ? (
                          <Space direction="vertical" size={4} style={{ width: '100%' }}>
                            <Text style={{ fontSize: '14px', color: '#1890ff', fontWeight: 'bold' }}>
                              🇨🇳 {selectedProduct.supplier_product_chinese_name}
                            </Text>
                            <Button
                              type="link"
                              size="small"
                              icon={<SyncOutlined />}
                              onClick={() => {
                                setEditingSupplierChineseName(selectedProduct.supplier_product_chinese_name || '');
                                setIsEditingSupplierChineseName(true);
                              }}
                              style={{ padding: 0, fontSize: '12px' }}
                            >
                              Editează
                            </Button>
                          </Space>
                        ) : (
                          <Button
                            type="dashed"
                            size="small"
                            icon={<SyncOutlined />}
                            onClick={() => {
                              setEditingSupplierChineseName('');
                              setIsEditingSupplierChineseName(true);
                            }}
                            style={{ marginTop: '4px' }}
                          >
                            Adaugă nume chinezesc
                          </Button>
                        )}
                      </div>
                    )}
                  </div>
                  {/* Specificații Editabile */}
                  <div style={{ marginBottom: '12px' }}>
                    <Text strong>Specificații:</Text>
                    {isEditingSpecification ? (
                      <div style={{ marginTop: '8px' }}>
                        <Input
                          value={editingSpecification || ''}
                          onChange={(e) => setEditingSpecification(e.target.value)}
                          placeholder="Introdu specificațiile produsului..."
                          style={{ marginBottom: '8px' }}
                        />
                        <Space>
                          <Button
                            type="primary"
                            size="small"
                            icon={<CheckCircleOutlined />}
                            onClick={handleUpdateSpecification}
                          >
                            Salvează
                          </Button>
                          <Button
                            size="small"
                            icon={<CloseCircleOutlined />}
                            onClick={() => {
                              setIsEditingSpecification(false);
                              setEditingSpecification(null);
                            }}
                          >
                            Anulează
                          </Button>
                        </Space>
                      </div>
                    ) : (
                      <div style={{ marginTop: '4px' }}>
                        {selectedProduct.supplier_product_specification ? (
                          <Space direction="vertical" size={4} style={{ width: '100%' }}>
                            <Tag color="green" style={{ fontSize: '12px' }}>
                              {selectedProduct.supplier_product_specification}
                            </Tag>
                            <Button
                              type="link"
                              size="small"
                              icon={<SyncOutlined />}
                              onClick={() => {
                                setEditingSpecification(selectedProduct.supplier_product_specification || '');
                                setIsEditingSpecification(true);
                              }}
                              style={{ padding: 0, fontSize: '12px' }}
                            >
                              Editează
                            </Button>
                          </Space>
                        ) : (
                          <Button
                            type="dashed"
                            size="small"
                            icon={<SyncOutlined />}
                            onClick={() => {
                              setEditingSpecification('');
                              setIsEditingSpecification(true);
                            }}
                            style={{ marginTop: '4px' }}
                          >
                            Adaugă specificații
                          </Button>
                        )}
                      </div>
                    )}
                  </div>
                  <div style={{ marginBottom: '8px' }}>
                    <Text><strong>Preț:</strong> {selectedProduct.supplier_price} {selectedProduct.supplier_currency}</Text>
                  </div>
                  
                  {/* URL Editabil */}
                  <div style={{ marginBottom: '12px' }}>
                    <Text strong>URL Produs:</Text>
                    {isEditingUrl ? (
                      <div style={{ marginTop: '8px' }}>
                        <Input
                          value={editingUrl || ''}
                          onChange={(e) => setEditingUrl(e.target.value)}
                          placeholder="https://detail.1688.com/offer/..."
                          style={{ marginBottom: '8px' }}
                        />
                        <Space>
                          <Button
                            type="primary"
                            size="small"
                            icon={<CheckCircleOutlined />}
                            onClick={handleUpdateUrl}
                          >
                            Salvează
                          </Button>
                          <Button
                            size="small"
                            icon={<CloseCircleOutlined />}
                            onClick={() => {
                              setIsEditingUrl(false);
                              setEditingUrl(null);
                            }}
                          >
                            Anulează
                          </Button>
                        </Space>
                      </div>
                    ) : (
                      <div style={{ marginTop: '4px' }}>
                        <Space direction="vertical" size={4} style={{ width: '100%' }}>
                          <a 
                            href={selectedProduct.supplier_product_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            style={{ fontSize: '12px', wordBreak: 'break-all' }}
                          >
                            <GlobalOutlined style={{ marginRight: 4 }} />
                            {selectedProduct.supplier_product_url}
                          </a>
                          <Button
                            type="link"
                            size="small"
                            icon={<SyncOutlined />}
                            onClick={() => {
                              setEditingUrl(selectedProduct.supplier_product_url);
                              setIsEditingUrl(true);
                            }}
                            style={{ padding: 0, fontSize: '12px' }}
                          >
                            Editează URL
                          </Button>
                        </Space>
                      </div>
                    )}
                  </div>
                  
                  {/* Schimbare Furnizor */}
                  <div style={{ marginBottom: '12px' }}>
                    <Text strong>Furnizor:</Text>
                    {changingSupplier ? (
                      <div style={{ marginTop: '8px' }}>
                        <Select
                          value={newSupplierId}
                          onChange={(value) => setNewSupplierId(value)}
                          placeholder="Selectează furnizor nou..."
                          style={{ width: '100%', marginBottom: '8px' }}
                        >
                          {suppliers
                            .filter(s => s.id !== selectedSupplier)
                            .map(supplier => (
                              <Option key={supplier.id} value={supplier.id}>
                                {supplier.name}
                              </Option>
                            ))}
                        </Select>
                        <Space>
                          <Button
                            type="primary"
                            size="small"
                            icon={<CheckCircleOutlined />}
                            onClick={handleChangeSupplier}
                            disabled={!newSupplierId}
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
                            {selectedProduct.supplier_name || suppliers.find(s => s.id === selectedSupplier)?.name || 'Necunoscut'}
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
                  
                  {/* Sursă Import */}
                  {selectedProduct.import_source && (
                    <div style={{ marginBottom: '8px' }}>
                      <Text><strong>Sursă Import:</strong></Text>
                      <div style={{ marginTop: '4px' }}>
                        <Tag color={selectedProduct.import_source === 'google_sheets' ? 'blue' : 'orange'}>
                          {selectedProduct.import_source === 'google_sheets' ? 'Google Sheets' : 'Manual'}
                        </Tag>
                      </div>
                    </div>
                  )}
                </Card>
              </Col>

              <Col span={12}>
                <Card title="Produs Local" size="small">
                  {selectedProduct.local_product ? (
                    <>
                      {selectedProduct.local_product.image_url && (
                        <div style={{ textAlign: 'center', marginBottom: '16px' }}>
                          <Image
                            src={selectedProduct.local_product.image_url}
                            alt={selectedProduct.local_product.name}
                            width={200}
                            height={200}
                            style={{ objectFit: 'cover', borderRadius: '8px' }}
                            fallback="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Crect width='200' height='200' fill='%23f0f0f0'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23999' font-size='16'%3ENo Image%3C/text%3E%3C/svg%3E"
                          />
                        </div>
                      )}
                      
                      {/* Nume Română Editabil */}
                      <div style={{ marginBottom: '12px' }}>
                        <Text strong>Nume Produs (Română):</Text>
                        {isEditingLocalName ? (
                          <div style={{ marginTop: '8px' }}>
                            <Input.TextArea
                              value={editingLocalName || ''}
                              onChange={(e) => setEditingLocalName(e.target.value)}
                              placeholder="Introdu numele produsului în română..."
                              autoSize={{ minRows: 2, maxRows: 4 }}
                              style={{ marginBottom: '8px' }}
                            />
                            <Space>
                              <Button
                                type="primary"
                                size="small"
                                icon={<CheckCircleOutlined />}
                                onClick={handleUpdateLocalName}
                              >
                                Salvează
                              </Button>
                              <Button
                                size="small"
                                icon={<CloseCircleOutlined />}
                                onClick={() => {
                                  setIsEditingLocalName(false);
                                  setEditingLocalName(null);
                                }}
                              >
                                Anulează
                              </Button>
                            </Space>
                          </div>
                        ) : (
                          <div style={{ marginTop: '4px' }}>
                            <Space direction="vertical" size={4} style={{ width: '100%' }}>
                              <Text strong style={{ fontSize: '16px', color: '#1890ff' }}>
                                {selectedProduct.local_product.name}
                              </Text>
                              <Button
                                type="link"
                                size="small"
                                icon={<SyncOutlined />}
                                onClick={() => {
                                  setEditingLocalName(selectedProduct.local_product?.name || '');
                                  setIsEditingLocalName(true);
                                }}
                                style={{ padding: 0, fontSize: '12px' }}
                              >
                                Editează nume
                              </Button>
                            </Space>
                          </div>
                        )}
                      </div>
                      
                      {/* Nume Chinezesc Editabil */}
                      <div style={{ marginBottom: '12px' }}>
                        <Text strong>Nume Chinezesc:</Text>
                        {isEditingChineseName ? (
                          <div style={{ marginTop: '8px' }}>
                            <Input.TextArea
                              value={editingChineseName || ''}
                              onChange={(e) => setEditingChineseName(e.target.value)}
                              placeholder="Introdu numele chinezesc..."
                              autoSize={{ minRows: 2, maxRows: 4 }}
                              style={{ marginBottom: '8px' }}
                            />
                            <Space>
                              <Button
                                type="primary"
                                size="small"
                                icon={<CheckCircleOutlined />}
                                onClick={handleUpdateLocalChineseName}
                              >
                                Salvează
                              </Button>
                              <Button
                                size="small"
                                icon={<CloseCircleOutlined />}
                                onClick={() => {
                                  setIsEditingChineseName(false);
                                  setEditingChineseName(null);
                                }}
                              >
                                Anulează
                              </Button>
                            </Space>
                          </div>
                        ) : (
                          <div style={{ marginTop: '4px' }}>
                            {selectedProduct.local_product.chinese_name ? (
                              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                                <Text style={{ fontSize: '14px', color: '#52c41a', fontWeight: 'bold' }}>
                                  🇨🇳 {selectedProduct.local_product.chinese_name}
                                </Text>
                                <Button
                                  type="link"
                                  size="small"
                                  icon={<SyncOutlined />}
                                  onClick={() => {
                                    setEditingChineseName(selectedProduct.local_product?.chinese_name || '');
                                    setIsEditingChineseName(true);
                                  }}
                                  style={{ padding: 0, fontSize: '12px' }}
                                >
                                  Editează
                                </Button>
                              </Space>
                            ) : (
                              <Button
                                type="dashed"
                                size="small"
                                icon={<SyncOutlined />}
                                onClick={() => {
                                  setEditingChineseName('');
                                  setIsEditingChineseName(true);
                                }}
                                style={{ marginTop: '4px' }}
                              >
                                Adaugă nume chinezesc
                              </Button>
                            )}
                          </div>
                        )}
                      </div>
                      
                      {selectedProduct.local_product.category && (
                        <div style={{ marginBottom: '8px' }}>
                          <Text><strong>Categorie:</strong> {selectedProduct.local_product.category}</Text>
                        </div>
                      )}
                      <Divider style={{ margin: '12px 0' }} />
                      {!selectedProduct.manual_confirmed && (
                        <Button
                          type="primary"
                          icon={<CheckCircleOutlined />}
                          onClick={handleMatchProduct}
                          loading={loading}
                          style={{ width: '100%', marginBottom: '8px', background: '#52c41a', borderColor: '#52c41a' }}
                        >
                          Confirmă Match
                        </Button>
                      )}
                      <Button
                        danger
                        icon={<CloseCircleOutlined />}
                        onClick={handleUnmatchProduct}
                        loading={loading}
                        style={{ width: '100%' }}
                      >
                        Șterge Match
                      </Button>
                      
                      {/* SKU și Brand - mutate mai jos */}
                      <Divider style={{ margin: '12px 0' }} />
                      <div style={{ marginBottom: '8px' }}>
                        <Text><strong>SKU:</strong> {selectedProduct.local_product.sku}</Text>
                      </div>
                      {selectedProduct.local_product.brand && (
                        <div style={{ marginBottom: '8px' }}>
                          <Text><strong>Brand:</strong> {selectedProduct.local_product.brand}</Text>
                        </div>
                      )}
                    </>
                  ) : (
                    <>
                      <Text type="secondary" style={{ display: 'block', marginBottom: '12px' }}>
                        Nu există produs local asociat
                      </Text>
                      <Divider style={{ margin: '12px 0' }} />
                      <div style={{ marginBottom: '12px' }}>
                        <Text strong>Asociază cu produs local:</Text>
                        <Select
                          showSearch
                          placeholder="Selectează produs local"
                          style={{ width: '100%', marginTop: '8px' }}
                          value={selectedLocalProductId}
                          onChange={setSelectedLocalProductId}
                          filterOption={(input, option) =>
                            (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                          }
                          options={localProducts.map(p => ({
                            value: p.id,
                            label: `${p.name} (SKU: ${p.sku})`
                          }))}
                        />
                      </div>
                      <Button
                        type="primary"
                        icon={<CheckCircleOutlined />}
                        onClick={handleMatchProduct}
                        loading={loading}
                        disabled={!selectedLocalProductId}
                        style={{ width: '100%' }}
                      >
                        Confirmă Match
                      </Button>
                    </>
                  )}
                </Card>
              </Col>
            </Row>

            <Divider />

            <Card title="Informații Potrivire" size="small">
              <Row gutter={16}>
                <Col span={8}>
                  <Statistic
                    title="Scor Potrivire"
                    value={Math.round(selectedProduct.confidence_score * 100)}
                    suffix="%"
                    valueStyle={{
                      color: getConfidenceColor(selectedProduct.confidence_score)
                    }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="Status Confirmare"
                    value={selectedProduct.manual_confirmed ? 'Confirmat' : 'În așteptare'}
                    valueStyle={{
                      color: selectedProduct.manual_confirmed ? '#52c41a' : '#faad14'
                    }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="Data Creare"
                    value={new Date(selectedProduct.created_at).toLocaleDateString('ro-RO')}
                  />
                </Col>
              </Row>
            </Card>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default SupplierProductsPage;
