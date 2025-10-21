import React, { useState, useEffect } from 'react';
import {
  Card, Row, Col, Table, Button, Space, Tag, Typography, Select, Statistic,
  Empty, message as antMessage, Badge, Checkbox, Image, Alert, Tooltip, notification, Modal, InputNumber
} from 'antd';
import {
  WarningOutlined, DownloadOutlined, ReloadOutlined,
  CheckCircleOutlined, CloseCircleOutlined, InfoCircleOutlined,
  ShopOutlined, DollarOutlined, LinkOutlined, FilterOutlined,
  CloudSyncOutlined, FileAddOutlined, EditOutlined, SaveOutlined,
  FireOutlined, RiseOutlined, FallOutlined, LineChartOutlined,
  ClockCircleOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import api from '../../services/api';
import { bulkCreateDrafts } from '../../api/purchaseOrders';
import { updateSupplierProduct, updateSheetSupplierPrice } from '../../api/suppliers';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

// ============================================================================
// TypeScript Interfaces
// ============================================================================

interface Supplier {
  supplier_id: string;
  supplier_name: string;
  supplier_type: string;
  price: number;
  currency: string;
  price_ron: number | null;
  supplier_url: string | null;
  supplier_contact: string | null;
  chinese_name: string | null;
  specification: string | null;
  is_preferred: boolean;
  is_verified: boolean;
  last_updated: string | null;
}

interface LowStockProduct {
  inventory_item_id: number;
  product_id: number;
  sku: string;
  name: string;
  chinese_name: string | null;
  part_number_key: string | null;
  product_url: string | null;
  image_url: string | null;
  warehouse_id: number;
  warehouse_name: string;
  warehouse_code: string;
  quantity: number;
  reserved_quantity: number;
  available_quantity: number;
  minimum_stock: number;
  reorder_point: number;
  maximum_stock: number | null;
  manual_reorder_quantity: number | null;
  unit_cost: number | null;
  stock_status: string;
  reorder_quantity: number;
  location: string | null;
  base_price: number;
  currency: string;
  is_discontinued: boolean;
  suppliers: Supplier[];
  supplier_count: number;
  sold_last_6_months: number;
  avg_monthly_sales: number;
  sales_sources: Record<string, number>;
}

interface Statistics {
  total_low_stock: number;
  out_of_stock: number;
  critical: number;
  low_stock: number;
  products_with_suppliers: number;
  products_without_suppliers: number;
}

interface SelectedSupplier {
  product_id: number;
  sku: string;
  supplier_id: string;
  supplier_name: string;
  reorder_quantity: number;
}

// ============================================================================
// Main Component
// ============================================================================

const LowStockSuppliersPage: React.FC = () => {
  const [notificationApi, contextHolder] = notification.useNotification();
  const [products, setProducts] = useState<LowStockProduct[]>([]);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [creatingDrafts, setCreatingDrafts] = useState(false);
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [accountFilter, setAccountFilter] = useState<string>('fbe');
  const [warehouseFilter, setWarehouseFilter] = useState<number | null>(null);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 50, total: 0 });
  const [selectedSuppliers, setSelectedSuppliers] = useState<Map<number, SelectedSupplier>>(new Map());
  const [expandedRows, setExpandedRows] = useState<number[]>([]);
  const [showOnlyVerified, setShowOnlyVerified] = useState(false);
  const [editingReorder, setEditingReorder] = useState<Map<number, number>>(new Map());
  const [savingReorder, setSavingReorder] = useState<Set<number>>(new Set());
  const [editingReorderQty, setEditingReorderQty] = useState<Map<number, number>>(new Map());
  const [savingReorderQty, setSavingReorderQty] = useState<Set<number>>(new Set());
  const [editingPrice, setEditingPrice] = useState<Map<string, number>>(new Map());
  const [savingPrice, setSavingPrice] = useState<Set<string>>(new Set());

  // ============================================================================
  // Data Loading
  // ============================================================================

  useEffect(() => {
    loadProducts();
  }, [pagination.current, pagination.pageSize, statusFilter, accountFilter, warehouseFilter]);

  const loadProducts = async () => {
    try {
      setLoading(true);
      const skip = (pagination.current - 1) * pagination.pageSize;
      
      const params: any = { skip, limit: pagination.pageSize };
      
      if (statusFilter && statusFilter !== 'all') {
        params.status = statusFilter;
      }
      
      // Add account filter (MAIN/FBE)
      if (accountFilter && accountFilter !== 'all') {
        params.account_type = accountFilter;
      }
      
      if (warehouseFilter) {
        params.warehouse_id = warehouseFilter;
      }
      
      const response = await api.get('/inventory/low-stock-with-suppliers', { params });
      const data = response.data?.data;
      
      if (!data?.products || data.products.length === 0) {
        if (accountFilter !== 'all') {
          antMessage.info(`No low stock products found for ${accountFilter} account. Try adjusting filters or syncing eMAG data.`);
        }
      }
      
      setProducts(data?.products || []);
      setPagination(prev => ({ ...prev, total: data?.pagination?.total || 0 }));
      setStatistics(data?.summary || null);
    } catch (error: any) {
      console.error('Error loading products:', error);
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to load data';
      antMessage.error(`Error: ${errorMsg}`);
      setProducts([]);
      setPagination(prev => ({ ...prev, total: 0 }));
    } finally {
      setLoading(false);
    }
  };

  // ============================================================================
  // Reorder Point Management
  // ============================================================================

  const handleUpdateReorderPoint = async (inventoryItemId: number, newValue: number) => {
    try {
      setSavingReorder(prev => new Set(prev).add(inventoryItemId));
      
      const response = await api.patch(`/inventory/items/${inventoryItemId}`, {
        reorder_point: newValue
      });
      
      if (response.data?.status === 'success') {
        antMessage.success('Reorder point updated successfully!');
        
        // Update local state
        setProducts(prevProducts => 
          prevProducts.map(p => 
            p.inventory_item_id === inventoryItemId 
              ? { ...p, reorder_point: newValue }
              : p
          )
        );
        
        // Clear editing state
        setEditingReorder(prev => {
          const newMap = new Map(prev);
          newMap.delete(inventoryItemId);
          return newMap;
        });
      }
    } catch (error: any) {
      console.error('Error updating reorder point:', error);
      antMessage.error(error.response?.data?.detail || 'Failed to update reorder point');
    } finally {
      setSavingReorder(prev => {
        const newSet = new Set(prev);
        newSet.delete(inventoryItemId);
        return newSet;
      });
    }
  };

  const handleUpdateReorderQty = async (inventoryItemId: number, newValue: number | null) => {
    try {
      setSavingReorderQty(prev => new Set(prev).add(inventoryItemId));
      
      const response = await api.patch(`/inventory/items/${inventoryItemId}`, {
        manual_reorder_quantity: newValue
      });
      
      if (response.data?.status === 'success') {
        antMessage.success(newValue === null 
          ? 'Reorder quantity reset to automatic calculation!' 
          : 'Reorder quantity updated successfully!');
        
        // Update local state
        setProducts(prevProducts => 
          prevProducts.map(p => 
            p.inventory_item_id === inventoryItemId 
              ? { 
                  ...p, 
                  manual_reorder_quantity: newValue,
                  reorder_quantity: response.data.data.reorder_quantity
                }
              : p
          )
        );
        
        // Clear editing state
        setEditingReorderQty(prev => {
          const newMap = new Map(prev);
          newMap.delete(inventoryItemId);
          return newMap;
        });
      }
    } catch (error: any) {
      console.error('Error updating reorder quantity:', error);
      antMessage.error(error.response?.data?.detail || 'Failed to update reorder quantity');
    } finally {
      setSavingReorderQty(prev => {
        const newSet = new Set(prev);
        newSet.delete(inventoryItemId);
        return newSet;
      });
    }
  };

  // ============================================================================
  // Supplier Price Update
  // ============================================================================

  const handleUpdateSupplierPrice = async (supplierId: string, newPrice: number, currency: string = 'CNY') => {
    try {
      setSavingPrice(prev => new Set(prev).add(supplierId));
      
      // Parse supplier ID to determine type (sheet_123 or 1688_456)
      const [type, id] = supplierId.split('_');
      const numericId = parseInt(id);
      
      if (type === 'sheet') {
        // Update Google Sheets supplier
        await updateSheetSupplierPrice(numericId, newPrice);
      } else if (type === '1688') {
        // Update 1688 supplier - need to extract supplier_id from SupplierProduct
        // For now, we'll use a generic update endpoint
        await updateSupplierProduct(numericId, numericId, {
          supplier_price: newPrice,
          supplier_currency: currency
        });
      }
      
      antMessage.success('Supplier price updated successfully!');
      
      // Update local state
      setProducts(prevProducts => 
        prevProducts.map(p => ({
          ...p,
          suppliers: p.suppliers.map(s => 
            s.supplier_id === supplierId 
              ? { ...s, price: newPrice, currency: currency }
              : s
          )
        }))
      );
      
      // Clear editing state
      setEditingPrice(prev => {
        const newMap = new Map(prev);
        newMap.delete(supplierId);
        return newMap;
      });
      
    } catch (error: any) {
      console.error('Error updating supplier price:', error);
      antMessage.error(error.response?.data?.detail || 'Failed to update supplier price');
    } finally {
      setSavingPrice(prev => {
        const newSet = new Set(prev);
        newSet.delete(supplierId);
        return newSet;
      });
    }
  };

  // ============================================================================
  // Supplier Selection Logic
  // ============================================================================

  const handleSupplierSelect = (product: LowStockProduct, supplier: Supplier, checked: boolean) => {
    const newSelected = new Map(selectedSuppliers);
    
    if (checked) {
      newSelected.set(product.product_id, {
        product_id: product.product_id,
        sku: product.sku,
        supplier_id: supplier.supplier_id,
        supplier_name: supplier.supplier_name,
        reorder_quantity: product.reorder_quantity,
      });
    } else {
      newSelected.delete(product.product_id);
    }
    
    setSelectedSuppliers(newSelected);
  };

  const isSupplierSelected = (productId: number, supplierId: string): boolean => {
    const selected = selectedSuppliers.get(productId);
    return selected?.supplier_id === supplierId;
  };

  const getSelectedSupplierForProduct = (productId: number): SelectedSupplier | undefined => {
    return selectedSuppliers.get(productId);
  };

  // ============================================================================
  // Bulk Selection Functions
  // ============================================================================

  const handleBulkSelectPreferred = () => {
    const newSelected = new Map(selectedSuppliers);
    let count = 0;

    products.forEach(product => {
      // Apply verified filter if active
      const availableSuppliers = showOnlyVerified 
        ? product.suppliers.filter(s => s.is_verified)
        : product.suppliers;
      
      if (availableSuppliers.length > 0) {
        // Find preferred supplier or first verified supplier
        const preferredSupplier = availableSuppliers.find(s => s.is_preferred) || 
                                   availableSuppliers.find(s => s.is_verified) ||
                                   availableSuppliers[0];
        
        newSelected.set(product.product_id, {
          product_id: product.product_id,
          sku: product.sku,
          supplier_id: preferredSupplier.supplier_id,
          supplier_name: preferredSupplier.supplier_name,
          reorder_quantity: product.reorder_quantity,
        });
        count++;
      }
    });

    setSelectedSuppliers(newSelected);
    const filterMsg = showOnlyVerified ? ' (verified only)' : '';
    antMessage.success(`Auto-selected preferred suppliers for ${count} products${filterMsg}`);
  };

  const handleBulkSelectCheapest = () => {
    const newSelected = new Map(selectedSuppliers);
    let count = 0;

    products.forEach(product => {
      // Apply verified filter if active
      const availableSuppliers = showOnlyVerified 
        ? product.suppliers.filter(s => s.is_verified)
        : product.suppliers;
      
      if (availableSuppliers.length > 0) {
        // Find cheapest supplier
        const cheapestSupplier = availableSuppliers.reduce((prev, current) => 
          (current.price < prev.price) ? current : prev
        );
        
        newSelected.set(product.product_id, {
          product_id: product.product_id,
          sku: product.sku,
          supplier_id: cheapestSupplier.supplier_id,
          supplier_name: cheapestSupplier.supplier_name,
          reorder_quantity: product.reorder_quantity,
        });
        count++;
      }
    });

    setSelectedSuppliers(newSelected);
    const filterMsg = showOnlyVerified ? ' (verified only)' : '';
    antMessage.success(`Auto-selected cheapest suppliers for ${count} products${filterMsg}`);
  };

  const handleClearAll = () => {
    setSelectedSuppliers(new Map());
    antMessage.info('All selections cleared');
  };

  const handleExpandAll = () => {
    const allProductIds = products.map(p => p.product_id);
    setExpandedRows(allProductIds);
    antMessage.info('Expanded all products');
  };

  const handleCollapseAll = () => {
    setExpandedRows([]);
    antMessage.info('Collapsed all products');
  };

  // ============================================================================
  // Export Functionality
  // ============================================================================

  const handleExportBySupplier = async () => {
    if (selectedSuppliers.size === 0) {
      antMessage.warning('Please select at least one supplier for export');
      return;
    }

    try {
      setExporting(true);
      
      // Convert Map to array for API
      const exportData = Array.from(selectedSuppliers.values());
      
      const response = await api.post('/inventory/export/low-stock-by-supplier', exportData, {
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      });
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `low_stock_by_supplier_${new Date().toISOString().split('T')[0]}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      antMessage.success(`Excel file exported successfully! (${selectedSuppliers.size} products)`);
    } catch (error: any) {
      console.error('Error exporting:', error);
      antMessage.error('Failed to export Excel file');
    } finally {
      setExporting(false);
    }
  };

  // ============================================================================
  // Create Draft Purchase Orders
  // ============================================================================

  const handleCreateDraftPOs = async () => {
    if (selectedSuppliers.size === 0) {
      antMessage.warning('Please select at least one supplier to create purchase orders');
      return;
    }

    // Show confirmation modal
    Modal.confirm({
      title: 'Create Purchase Order Drafts',
      icon: <FileAddOutlined />,
      content: (
        <div>
          <p>This will create draft purchase orders for the selected products grouped by supplier.</p>
          <p><strong>Selected products:</strong> {selectedSuppliers.size}</p>
          <p><strong>Suppliers:</strong> {new Set(Array.from(selectedSuppliers.values()).map(s => s.supplier_name)).size}</p>
          <p style={{ marginTop: 16, color: '#666' }}>
            You can review and edit these drafts in the Purchase Orders page before sending them to suppliers.
          </p>
        </div>
      ),
      okText: 'Create Drafts',
      cancelText: 'Cancel',
      onOk: async () => {
        try {
          setCreatingDrafts(true);
          
          // Convert Map to array for API
          const selectedData = Array.from(selectedSuppliers.values());
          
          const response = await bulkCreateDrafts(selectedData);
          
          if (response.status === 'success' && response.data) {
            const { created_orders, total_orders_created, errors } = response.data;
            
            // Show success notification with details
            const hasErrors = errors && errors.length > 0;
            const notificationType = hasErrors && total_orders_created === 0 ? 'error' : 'success';
            
            const notification = {
              message: total_orders_created > 0 ? '✅ Purchase Order Drafts Created!' : '❌ Failed to Create Drafts',
              description: (
                <div>
                  {total_orders_created > 0 && (
                    <>
                      <p><strong>{total_orders_created}</strong> purchase order draft(s) created successfully!</p>
                      {created_orders.map((order) => (
                        <div key={order.id} style={{ marginTop: 8, fontSize: 12 }}>
                          • <strong>{order.order_number}</strong> - {order.supplier_name} 
                          ({order.total_products} products, {order.total_quantity} units)
                        </div>
                      ))}
                    </>
                  )}
                  {hasErrors && (
                    <div style={{ marginTop: 12, color: '#ff4d4f' }}>
                      <strong>Errors:</strong>
                      {errors.map((err, idx) => (
                        <div key={idx} style={{ fontSize: 12 }}>• {err.supplier}: {err.error}</div>
                      ))}
                    </div>
                  )}
                  {total_orders_created > 0 && (
                    <p style={{ marginTop: 12 }}>
                      Go to <a href="/purchase-orders">Purchase Orders</a> to review and send them.
                    </p>
                  )}
                </div>
              ),
              duration: 10,
            };
            
            if (notificationType === 'error') {
              notificationApi.error(notification);
            } else {
              notificationApi.success(notification);
            }
            
            // Clear selections only if at least one order was created successfully
            if (total_orders_created > 0) {
              setSelectedSuppliers(new Map());
              antMessage.info('Selections cleared. You can now make new selections.');
            }
          }
        } catch (error: any) {
          console.error('Error creating draft POs:', error);
          notificationApi.error({
            message: 'Error Creating Purchase Orders',
            description: error.response?.data?.detail || error.message || 'Failed to create purchase order drafts',
            duration: 8,
          });
        } finally {
          setCreatingDrafts(false);
        }
      },
    });
  };

  // ============================================================================
  // UI Helper Functions
  // ============================================================================

  const getStockStatusColor = (status: string): string => {
    switch (status) {
      case 'out_of_stock': return 'red';
      case 'critical': return 'orange';
      case 'low_stock': return 'gold';
      default: return 'green';
    }
  };

  const getStockStatusText = (status: string): string => {
    return status.toUpperCase().replace('_', ' ');
  };

  const getSalesVelocityIcon = (soldQty: number, avgMonthly: number) => {
    if (soldQty === 0) return null;
    if (avgMonthly >= 10) return <FireOutlined style={{ color: '#ff4d4f' }} />;
    if (avgMonthly >= 5) return <RiseOutlined style={{ color: '#faad14' }} />;
    if (avgMonthly >= 1) return <LineChartOutlined style={{ color: '#1890ff' }} />;
    return <FallOutlined style={{ color: '#8c8c8c' }} />;
  };

  const getSalesVelocityColor = (avgMonthly: number): string => {
    if (avgMonthly >= 10) return '#ff4d4f';
    if (avgMonthly >= 5) return '#faad14';
    if (avgMonthly >= 1) return '#1890ff';
    return '#8c8c8c';
  };

  const getSalesVelocityLabel = (avgMonthly: number): string => {
    if (avgMonthly >= 10) return 'High Demand';
    if (avgMonthly >= 5) return 'Medium Demand';
    if (avgMonthly >= 1) return 'Low Demand';
    return 'Very Low';
  };

  const resetFilters = () => {
    setStatusFilter('all');
    setAccountFilter('all');
    setWarehouseFilter(null);
    setShowOnlyVerified(false);
    setPagination({ current: 1, pageSize: 20, total: 0 });
    setSelectedSuppliers(new Map());
    antMessage.success('Filters reset successfully');
  };

  // ============================================================================
  // eMAG Inventory Sync
  // ============================================================================

  const syncEmagInventory = async () => {
    try {
      setSyncing(true);
      notificationApi.info({
        message: 'Sincronizare eMAG Pornită',
        description: 'Se sincronizează stocul din eMAG FBE. Vă rugăm așteptați...',
        duration: 3,
      });

      const response = await api.post('/inventory/emag-inventory-sync/sync?account_type=fbe&async_mode=false');
      
      if (response.data?.success) {
        const stats = response.data.stats || {};
        notificationApi.success({
          message: '✅ Sincronizare Completă!',
          description: `Sincronizate: ${stats.products_synced || 0} produse, Stoc scăzut: ${stats.low_stock_count || 0}, Erori: ${stats.errors || 0}`,
          duration: 8,
        });
        
        // Reload products after sync
        await loadProducts();
      } else {
        throw new Error(response.data?.message || 'Sincronizare eșuată');
      }
    } catch (error: any) {
      console.error('eMAG sync error:', error);
      notificationApi.error({
        message: 'Eroare Sincronizare eMAG',
        description: error.response?.data?.detail || error.message || 'Nu s-a putut sincroniza stocul din eMAG',
        duration: 10,
      });
    } finally {
      setSyncing(false);
    }
  };

  // ============================================================================
  // Supplier Card Component
  // ============================================================================

  const SupplierCard: React.FC<{ 
    supplier: Supplier; 
    product: LowStockProduct;
    isCheapest?: boolean;
  }> = ({ supplier, product, isCheapest = false }) => {
    const isSelected = isSupplierSelected(product.product_id, supplier.supplier_id);
    const isEditingPrice = editingPrice.has(supplier.supplier_id);
    const isSavingPrice = savingPrice.has(supplier.supplier_id);
    const editPriceValue = editingPrice.get(supplier.supplier_id) ?? supplier.price;
    
    return (
      <Card
        size="small"
        style={{
          marginBottom: 8,
          border: isSelected 
            ? '2px solid #1890ff' 
            : isCheapest 
              ? '2px solid #52c41a' 
              : '1px solid #d9d9d9',
          backgroundColor: isSelected 
            ? '#e6f7ff' 
            : isCheapest 
              ? '#f6ffed' 
              : 'white'
        }}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="small">
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <Space>
              <Checkbox
                checked={isSelected}
                onChange={(e) => handleSupplierSelect(product, supplier, e.target.checked)}
              />
              <Text strong>{supplier.supplier_name}</Text>
              {supplier.is_preferred && <Tag color="blue" icon={<CheckCircleOutlined />}>Preferred</Tag>}
              {supplier.is_verified ? (
                <Tag color="green" icon={<CheckCircleOutlined />}>Verified</Tag>
              ) : (
                <Tag color="orange" icon={<ClockCircleOutlined />}>Pending Verification</Tag>
              )}
              <Tag color="purple">{supplier.supplier_type}</Tag>
            </Space>
          </Space>
          
          <Row gutter={16}>
            <Col span={12}>
              <div style={{ marginBottom: 8 }}>
                <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
                  Price {isEditingPrice && <Text type="warning">(Editing...)</Text>}
                </Text>
                {isEditingPrice ? (
                  <Space direction="vertical" size={8} style={{ width: '100%' }}>
                    <Space size={8} style={{ width: '100%' }}>
                      <InputNumber
                        size="middle"
                        min={0}
                        step={0.01}
                        precision={2}
                        value={editPriceValue}
                        onChange={(value) => {
                          if (value !== null) {
                            setEditingPrice(prev => new Map(prev).set(supplier.supplier_id, value));
                          }
                        }}
                        style={{ width: 150 }}
                        disabled={isSavingPrice}
                        placeholder="Enter price"
                        autoFocus
                      />
                      <Tag color="blue" style={{ fontSize: 14, padding: '4px 12px' }}>
                        {supplier.currency}
                      </Tag>
                    </Space>
                    <Space size={8}>
                      <Button
                        type="primary"
                        size="middle"
                        icon={<SaveOutlined />}
                        onClick={() => handleUpdateSupplierPrice(supplier.supplier_id, editPriceValue, supplier.currency)}
                        loading={isSavingPrice}
                      >
                        Save Price
                      </Button>
                      <Button
                        size="middle"
                        onClick={() => {
                          setEditingPrice(prev => {
                            const newMap = new Map(prev);
                            newMap.delete(supplier.supplier_id);
                            return newMap;
                          });
                        }}
                        disabled={isSavingPrice}
                      >
                        Cancel
                      </Button>
                    </Space>
                    {editPriceValue !== supplier.price && (
                      <Alert
                        message={
                          <span>
                            Original: <strong>{supplier.price.toFixed(2)} {supplier.currency}</strong> → 
                            New: <strong>{editPriceValue.toFixed(2)} {supplier.currency}</strong>
                            {' '}(Difference: <strong style={{ color: editPriceValue > supplier.price ? '#cf1322' : '#52c41a' }}>
                              {editPriceValue > supplier.price ? '+' : ''}{(editPriceValue - supplier.price).toFixed(2)}
                            </strong>)
                          </span>
                        }
                        type="info"
                        showIcon
                        style={{ marginTop: 4 }}
                      />
                    )}
                  </Space>
                ) : (
                  <Space size={8} align="center">
                    <Text strong style={{ fontSize: 20, color: '#1890ff' }}>
                      {supplier.price.toFixed(2)}
                    </Text>
                    <Tag color="blue" style={{ fontSize: 14, padding: '4px 12px' }}>
                      {supplier.currency}
                    </Tag>
                    <Tooltip title="Click to edit price">
                      <Button
                        type="primary"
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => {
                          setEditingPrice(prev => new Map(prev).set(supplier.supplier_id, supplier.price));
                        }}
                      >
                        Edit
                      </Button>
                    </Tooltip>
                  </Space>
                )}
              </div>
            </Col>
            {supplier.price_ron && !isEditingPrice && (
              <Col span={6}>
                <Statistic
                  title="Price (RON)"
                  value={supplier.price_ron}
                  precision={2}
                  suffix="RON"
                  valueStyle={{ fontSize: 16 }}
                />
              </Col>
            )}
            <Col span={supplier.price_ron && !isEditingPrice ? 6 : 12}>
              <Statistic
                title={
                  <span>
                    Total Cost 
                    {isEditingPrice && (
                      <Text type="secondary" style={{ fontSize: 11, marginLeft: 4 }}>
                        (for {product.reorder_quantity} units)
                      </Text>
                    )}
                  </span>
                }
                value={(isEditingPrice ? editPriceValue : supplier.price) * product.reorder_quantity}
                precision={2}
                suffix={supplier.currency}
                valueStyle={{ fontSize: 18, color: '#cf1322', fontWeight: 'bold' }}
              />
            </Col>
          </Row>
          
          {supplier.chinese_name && (
            <Text type="secondary">Chinese: {supplier.chinese_name}</Text>
          )}
          
          {supplier.supplier_url && (
            <Button
              type="link"
              size="small"
              icon={<LinkOutlined />}
              href={supplier.supplier_url}
              target="_blank"
            >
              View Product
            </Button>
          )}
          
          {supplier.last_updated && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              Last updated: {new Date(supplier.last_updated).toLocaleDateString()}
            </Text>
          )}
        </Space>
      </Card>
    );
  };

  // ============================================================================
  // Table Columns Definition
  // ============================================================================

  const columns: ColumnsType<LowStockProduct> = [
    {
      title: 'Image',
      dataIndex: 'image_url',
      key: 'image',
      width: 180,
      render: (url: string | null) => (
        url ? (
          <Image
            src={url}
            alt="Product"
            width={170}
            height={170}
            style={{ objectFit: 'cover' }}
            fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
          />
        ) : (
          <div style={{ width: 50, height: 50, backgroundColor: '#f0f0f0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <ShopOutlined style={{ fontSize: 24, color: '#bfbfbf' }} />
          </div>
        )
      ),
    },
    {
      title: 'Product',
      key: 'product',
      width: 300,
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <Text strong>{record.name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>SKU: {record.sku}</Text>
          {record.part_number_key && record.part_number_key !== record.sku && (
            <div>
              {record.product_url ? (
                <Tooltip title="Click to open product page on your website">
                  <a 
                    href={record.product_url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    style={{ fontSize: 12, color: '#1890ff' }}
                  >
                    <LinkOutlined style={{ marginRight: 4 }} />
                    PNK: {record.part_number_key}
                  </a>
                </Tooltip>
              ) : (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  PNK: {record.part_number_key}
                </Text>
              )}
            </div>
          )}
          {record.chinese_name && (
            <Text type="secondary" style={{ fontSize: 12, color: '#52c41a' }}> {record.chinese_name}</Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Warehouse',
      dataIndex: 'warehouse_name',
      key: 'warehouse',
      width: 150,
      render: (name: string, record) => (
        <Space direction="vertical" size="small">
          <Text>{name}</Text>
          <Tag color={record.warehouse_code === 'EMAG-FBE' ? 'orange' : 'default'}>
            {record.warehouse_code === 'EMAG-FBE' ? '🛒 ' : ''}{record.warehouse_code}
          </Tag>
        </Space>
      ),
    },
    {
      title: 'Stock Status',
      key: 'stock',
      width: 240,
      render: (_, record) => {
        const isEditing = editingReorder.has(record.inventory_item_id);
        const isSaving = savingReorder.has(record.inventory_item_id);
        const editValue = editingReorder.get(record.inventory_item_id) ?? record.reorder_point;
        
        return (
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            <Tag color={getStockStatusColor(record.stock_status)}>
              {getStockStatusText(record.stock_status)}
            </Tag>
            <Text style={{ fontSize: 12 }}>
              Available: <strong>{record.available_quantity}</strong> / Min: {record.minimum_stock}
            </Text>
            
            {/* Editable Reorder Point */}
            <Space size={4} style={{ width: '100%' }}>
              <Text style={{ fontSize: 12 }}>Reorder Point:</Text>
              {isEditing ? (
                <>
                  <InputNumber
                    size="small"
                    min={0}
                    max={10000}
                    value={editValue}
                    onChange={(value) => {
                      if (value !== null) {
                        setEditingReorder(prev => new Map(prev).set(record.inventory_item_id, value));
                      }
                    }}
                    style={{ width: 70 }}
                    disabled={isSaving}
                  />
                  <Button
                    type="primary"
                    size="small"
                    icon={<SaveOutlined />}
                    onClick={() => handleUpdateReorderPoint(record.inventory_item_id, editValue)}
                    loading={isSaving}
                    style={{ padding: '0 8px' }}
                  />
                  <Button
                    size="small"
                    onClick={() => {
                      setEditingReorder(prev => {
                        const newMap = new Map(prev);
                        newMap.delete(record.inventory_item_id);
                        return newMap;
                      });
                    }}
                    disabled={isSaving}
                    style={{ padding: '0 8px' }}
                  >
                    ✕
                  </Button>
                </>
              ) : (
                <>
                  <Text strong style={{ color: '#1890ff' }}>{record.reorder_point}</Text>
                  <Tooltip title="Click to edit reorder point">
                    <Button
                      type="text"
                      size="small"
                      icon={<EditOutlined />}
                      onClick={() => {
                        setEditingReorder(prev => new Map(prev).set(record.inventory_item_id, record.reorder_point));
                      }}
                      style={{ padding: '0 4px' }}
                    />
                  </Tooltip>
                </>
              )}
            </Space>
            
            {/* Editable Reorder Quantity */}
            <Space size={4} style={{ width: '100%' }}>
              <Text style={{ fontSize: 12 }}>Reorder Qty:</Text>
              {editingReorderQty.has(record.inventory_item_id) ? (
                <>
                  <InputNumber
                    size="small"
                    min={0}
                    max={10000}
                    value={editingReorderQty.get(record.inventory_item_id) ?? record.reorder_quantity}
                    onChange={(value) => {
                      if (value !== null) {
                        setEditingReorderQty(prev => new Map(prev).set(record.inventory_item_id, value));
                      }
                    }}
                    style={{ width: 70 }}
                    disabled={savingReorderQty.has(record.inventory_item_id)}
                  />
                  <Button
                    type="primary"
                    size="small"
                    icon={<SaveOutlined />}
                    onClick={() => handleUpdateReorderQty(
                      record.inventory_item_id, 
                      editingReorderQty.get(record.inventory_item_id) ?? record.reorder_quantity
                    )}
                    loading={savingReorderQty.has(record.inventory_item_id)}
                    style={{ padding: '0 8px' }}
                  />
                  <Button
                    size="small"
                    onClick={() => {
                      setEditingReorderQty(prev => {
                        const newMap = new Map(prev);
                        newMap.delete(record.inventory_item_id);
                        return newMap;
                      });
                    }}
                    disabled={savingReorderQty.has(record.inventory_item_id)}
                    style={{ padding: '0 8px' }}
                  >
                    ✕
                  </Button>
                </>
              ) : (
                <>
                  <Text strong style={{ color: '#cf1322' }}>{record.reorder_quantity}</Text>
                  {record.manual_reorder_quantity !== null && (
                    <Tag color="blue" style={{ fontSize: 10 }}>Manual</Tag>
                  )}
                  <Tooltip title={record.manual_reorder_quantity !== null 
                    ? "Edit manual quantity or reset to automatic" 
                    : "Set manual reorder quantity"}>
                    <Button
                      type="text"
                      size="small"
                      icon={<EditOutlined />}
                      onClick={() => {
                        setEditingReorderQty(prev => new Map(prev).set(
                          record.inventory_item_id, 
                          record.manual_reorder_quantity ?? record.reorder_quantity
                        ));
                      }}
                      style={{ padding: '0 4px' }}
                    />
                  </Tooltip>
                  {record.manual_reorder_quantity !== null && (
                    <Tooltip title="Reset to automatic calculation">
                      <Button
                        type="text"
                        size="small"
                        danger
                        onClick={() => handleUpdateReorderQty(record.inventory_item_id, null)}
                        loading={savingReorderQty.has(record.inventory_item_id)}
                        style={{ padding: '0 4px', fontSize: 12 }}
                      >
                        🔄
                      </Button>
                    </Tooltip>
                  )}
                </>
              )}
            </Space>

            {/* Sold in Last 6 Months */}
            <Space size={4} style={{ width: '100%', marginTop: 4 }}>
              <Tooltip title={
                <div>
                  <div><strong>Sales in Last 6 Months</strong></div>
                  <div>Total Sold: {record.sold_last_6_months} units</div>
                  <div>Avg/Month: {record.avg_monthly_sales} units</div>
                  {record.sales_sources && Object.keys(record.sales_sources).length > 0 && (
                    <div style={{ marginTop: 8 }}>
                      <strong>Sources:</strong>
                      {Object.entries(record.sales_sources).map(([source, qty]) => (
                        <div key={source}>• {source}: {qty} units</div>
                      ))}
                    </div>
                  )}
                  <div style={{ marginTop: 8, borderTop: '1px solid rgba(255,255,255,0.2)', paddingTop: 4 }}>
                    <strong>Velocity:</strong> {getSalesVelocityLabel(record.avg_monthly_sales)}
                  </div>
                </div>
              }>
                <Space size={4}>
                  {getSalesVelocityIcon(record.sold_last_6_months, record.avg_monthly_sales)}
                  <Text style={{ fontSize: 12 }}>Sold (6m):</Text>
                  <Text 
                    strong 
                    style={{ 
                      color: getSalesVelocityColor(record.avg_monthly_sales),
                      fontSize: 12
                    }}
                  >
                    {record.sold_last_6_months}
                  </Text>
                  <Tag 
                    color={getSalesVelocityColor(record.avg_monthly_sales)} 
                    style={{ fontSize: 10, padding: '0 4px', margin: 0 }}
                  >
                    ~{record.avg_monthly_sales}/mo
                  </Tag>
                </Space>
              </Tooltip>
            </Space>
          </Space>
        );
      },
    },
    {
      title: 'Suppliers',
      key: 'suppliers',
      width: 150,
      render: (_, record) => {
        const selected = getSelectedSupplierForProduct(record.product_id);
        return (
          <Space direction="vertical" size="small">
            <Badge count={record.supplier_count} showZero>
              <Button
                type={selected ? 'primary' : 'default'}
                icon={<ShopOutlined />}
                size="small"
              >
                {record.supplier_count} Suppliers
              </Button>
            </Badge>
            {selected && (
              <Tag color="blue" style={{ fontSize: 11 }}>
                ✓ {selected.supplier_name.substring(0, 15)}...
              </Tag>
            )}
          </Space>
        );
      },
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 100,
      fixed: 'right',
      render: (_, record) => (
        <Button
          type="link"
          onClick={() => {
            if (expandedRows.includes(record.product_id)) {
              setExpandedRows(expandedRows.filter(id => id !== record.product_id));
            } else {
              setExpandedRows([...expandedRows, record.product_id]);
            }
          }}
        >
          {expandedRows.includes(record.product_id) ? 'Hide' : 'Select'} Supplier
        </Button>
      ),
    },
  ];

  // ============================================================================
  // Expandable Row Render
  // ============================================================================

  const expandedRowRender = (record: LowStockProduct) => {
    // Filter suppliers based on verified status
    const filteredSuppliers = showOnlyVerified 
      ? record.suppliers.filter(s => s.is_verified)
      : record.suppliers;
    
    // Find cheapest supplier for highlighting
    const cheapestSupplier = filteredSuppliers.length > 0 
      ? filteredSuppliers.reduce((prev, current) => 
          (current.price < prev.price) ? current : prev
        )
      : null;
    
    if (record.suppliers.length === 0) {
      return (
        <Alert
          message="No Suppliers Available"
          description="This product has no suppliers configured. Please add suppliers in the supplier management section."
          type="warning"
          showIcon
        />
      );
    }

    if (filteredSuppliers.length === 0 && showOnlyVerified) {
      return (
        <Alert
          message="No Verified Suppliers Found"
          description={
            <div>
              <p>This product has <strong>{record.suppliers.length} supplier(s)</strong>, but none are verified yet.</p>
              <p>To verify a supplier:</p>
              <ol style={{ marginTop: 8, marginBottom: 8 }}>
                <li>Go to <strong>&quot;Produse Furnizori&quot;</strong> page</li>
                <li>Find the supplier product for <strong>SKU: {record.sku}</strong></li>
                <li>Click <strong>&quot;Confirma Match&quot;</strong> to verify the match</li>
              </ol>
              <p>Or <a onClick={() => setShowOnlyVerified(false)} style={{ cursor: 'pointer', color: '#1890ff' }}>click here to show all suppliers</a> including unverified ones.</p>
            </div>
          }
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
      );
    }

    return (
      <div style={{ padding: '16px', backgroundColor: '#fafafa' }}>
        <Title level={5}>
          <ShopOutlined /> Select Supplier for {record.name}
        </Title>
        <Paragraph type="secondary">
          Choose one supplier to include this product in the export. Suppliers are sorted by preference and price.
          {showOnlyVerified && (
            <Text type="success" strong> (Showing only verified suppliers)</Text>
          )}
          {cheapestSupplier && filteredSuppliers.length > 1 && (
            <Text type="secondary" style={{ display: 'block', marginTop: 4 }}>
              💰 <strong>Best price:</strong> {cheapestSupplier.price.toFixed(2)} {cheapestSupplier.currency} from {cheapestSupplier.supplier_name}
            </Text>
          )}
        </Paragraph>
        
        <Row gutter={[16, 16]}>
          {filteredSuppliers.map((supplier) => (
            <Col span={24} key={supplier.supplier_id}>
              <SupplierCard 
                supplier={supplier} 
                product={record} 
                isCheapest={cheapestSupplier?.supplier_id === supplier.supplier_id && filteredSuppliers.length > 1}
              />
            </Col>
          ))}
        </Row>
      </div>
    );
  };

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <div style={{ padding: '24px' }}>
      {contextHolder}
      <Row gutter={[16, 16]}>
        {/* Header */}
        <Col span={24}>
          <Card>
            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <Space>
                <WarningOutlined style={{ fontSize: 24, color: '#faad14' }} />
                <Title level={3} style={{ margin: 0 }}>
                  Low Stock Products - Supplier Selection
                  {accountFilter !== 'all' && (
                    <Badge 
                      count={accountFilter} 
                      style={{ backgroundColor: accountFilter === 'FBE' ? '#52c41a' : '#1890ff', marginLeft: '12px' }} 
                    />
                  )}
                </Title>
              </Space>
              <Space wrap>
                <Tooltip title="Sincronizează stocul din eMAG FBE">
                  <Button
                    icon={<CloudSyncOutlined />}
                    onClick={syncEmagInventory}
                    loading={syncing}
                    type="default"
                    style={{ borderColor: '#fa8c16', color: '#fa8c16' }}
                  >
                    Sync eMAG FBE
                  </Button>
                </Tooltip>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={loadProducts}
                  loading={loading}
                >
                  Refresh
                </Button>
                <Tooltip title="Create draft purchase orders for selected products grouped by supplier">
                  <Button
                    type="default"
                    icon={<FileAddOutlined />}
                    onClick={handleCreateDraftPOs}
                    loading={creatingDrafts}
                    disabled={selectedSuppliers.size === 0}
                    style={{ borderColor: '#52c41a', color: '#52c41a' }}
                  >
                    Create Draft POs ({selectedSuppliers.size})
                  </Button>
                </Tooltip>
                <Button
                  type="primary"
                  icon={<DownloadOutlined />}
                  onClick={handleExportBySupplier}
                  loading={exporting}
                  disabled={selectedSuppliers.size === 0}
                >
                  Export Excel ({selectedSuppliers.size})
                </Button>
              </Space>
            </Space>
          </Card>
        </Col>

        {/* Statistics */}
        {statistics && (
          <Col span={24}>
            <Row gutter={16}>
              <Col span={4}>
                <Card>
                  <Statistic
                    title="Total Low Stock"
                    value={statistics.total_low_stock}
                    prefix={<WarningOutlined />}
                    valueStyle={{ color: '#faad14' }}
                  />
                </Card>
              </Col>
              <Col span={4}>
                <Card>
                  <Statistic
                    title="Out of Stock"
                    value={statistics.out_of_stock}
                    prefix={<CloseCircleOutlined />}
                    valueStyle={{ color: '#cf1322' }}
                  />
                </Card>
              </Col>
              <Col span={4}>
                <Card>
                  <Statistic
                    title="Critical"
                    value={statistics.critical}
                    prefix={<WarningOutlined />}
                    valueStyle={{ color: '#fa8c16' }}
                  />
                </Card>
              </Col>
              <Col span={4}>
                <Card>
                  <Statistic
                    title="Low Stock"
                    value={statistics.low_stock}
                    prefix={<InfoCircleOutlined />}
                    valueStyle={{ color: '#faad14' }}
                  />
                </Card>
              </Col>
              <Col span={4}>
                <Card>
                  <Statistic
                    title="With Suppliers"
                    value={statistics.products_with_suppliers}
                    prefix={<CheckCircleOutlined />}
                    valueStyle={{ color: '#52c41a' }}
                  />
                </Card>
              </Col>
              <Col span={4}>
                <Card>
                  <Statistic
                    title="No Suppliers"
                    value={statistics.products_without_suppliers}
                    prefix={<CloseCircleOutlined />}
                    valueStyle={{ color: '#8c8c8c' }}
                  />
                </Card>
              </Col>
            </Row>
          </Col>
        )}

        {/* Filters and Quick Actions */}
        <Col span={24}>
          <Card title={<Space><FilterOutlined /> Filters & Quick Actions</Space>}>
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              {/* Filters Row */}
              <Space size="large" wrap>
                <Select
                  style={{ width: 200 }}
                  placeholder="Account Type"
                  value={accountFilter}
                  onChange={(value) => {
                    setAccountFilter(value);
                    setPagination(prev => ({ ...prev, current: 1 }));
                  }}
                  suffixIcon={<FilterOutlined />}
                >
                  <Option value="all">🏢 All Accounts</Option>
                  <Option value="MAIN">🔵 MAIN Account</Option>
                  <Option value="FBE">🟢 FBE Account</Option>
                </Select>
                
                <Select
                  style={{ width: 200 }}
                  placeholder="Stock Status"
                  value={statusFilter}
                  onChange={(value) => {
                    setStatusFilter(value);
                    setPagination(prev => ({ ...prev, current: 1 }));
                  }}
                >
                  <Option value="all">📦 All Status</Option>
                  <Option value="out_of_stock">🔴 Out of Stock</Option>
                  <Option value="critical">🟠 Critical</Option>
                  <Option value="low_stock">🟡 Low Stock</Option>
                </Select>
                
                <Tooltip title="When enabled, only suppliers that have been manually verified in 'Produse Furnizori' page will be shown">
                  <Checkbox
                    checked={showOnlyVerified}
                    onChange={(e) => setShowOnlyVerified(e.target.checked)}
                    style={{
                      padding: '8px 12px',
                      border: showOnlyVerified ? '2px solid #52c41a' : '1px solid #d9d9d9',
                      borderRadius: '4px',
                      backgroundColor: showOnlyVerified ? '#f6ffed' : 'white'
                    }}
                  >
                    <Space>
                      {showOnlyVerified ? (
                        <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 16 }} />
                      ) : (
                        <CloseCircleOutlined style={{ color: '#8c8c8c', fontSize: 16 }} />
                      )}
                      <Text strong style={{ color: showOnlyVerified ? '#52c41a' : '#262626' }}>
                        Show Only Verified Suppliers
                      </Text>
                    </Space>
                  </Checkbox>
                </Tooltip>
                
                <Button onClick={resetFilters}>
                  Reset Filters
                </Button>
                
                {selectedSuppliers.size > 0 && (
                  <Tag color="blue" style={{ fontSize: 14, padding: '4px 12px' }}>
                    {selectedSuppliers.size} products selected
                  </Tag>
                )}
              </Space>

              {/* Quick Actions Row */}
              <Space size="middle" wrap>
                <Text strong>Quick Actions:</Text>
                <Button 
                  type="default" 
                  size="small"
                  onClick={handleBulkSelectPreferred}
                  disabled={products.length === 0}
                >
                  <CheckCircleOutlined /> Select Preferred
                </Button>
                <Button 
                  type="default" 
                  size="small"
                  onClick={handleBulkSelectCheapest}
                  disabled={products.length === 0}
                >
                  <DollarOutlined /> Select Cheapest
                </Button>
                <Button 
                  type="default" 
                  size="small"
                  onClick={handleExpandAll}
                  disabled={products.length === 0}
                >
                  Expand All
                </Button>
                <Button 
                  type="default" 
                  size="small"
                  onClick={handleCollapseAll}
                  disabled={expandedRows.length === 0}
                >
                  Collapse All
                </Button>
                <Button 
                  type="default" 
                  size="small"
                  danger
                  onClick={handleClearAll}
                  disabled={selectedSuppliers.size === 0}
                >
                  Clear All Selections
                </Button>
              </Space>
            </Space>
          </Card>
        </Col>

        {/* Instructions */}
        <Col span={24}>
          <Alert
            message="Low Stock Suppliers - Quick Guide"
            description={
              <div>
                <Paragraph strong>📦 About This Page:</Paragraph>
                <Paragraph type="secondary" style={{ marginBottom: 12 }}>
                  This page shows products with low stock from all warehouses. Use the <strong>Account Filter</strong> to view only 
                  <Tag color="blue">🔵 MAIN</Tag> or <Tag color="green">🟢 FBE</Tag> account products. 
                  You can select suppliers and export orders grouped by supplier.
                </Paragraph>
                
                <Paragraph strong>🚀 Quick Start:</Paragraph>
                <ol style={{ marginBottom: 8, paddingLeft: 20 }}>
                  <li><strong>Filter by Account:</strong> Select <Tag color="green">🟢 FBE</Tag> to see only eMAG FBE products</li>
                  <li><strong>Sync eMAG FBE:</strong> Click the <CloudSyncOutlined /> button to sync latest stock from eMAG</li>
                  <li>Use <strong>Quick Actions</strong> to auto-select suppliers (Preferred or Cheapest)</li>
                  <li>Or manually click "Select Supplier" to view and choose suppliers for each product</li>
                  <li><strong>Create Draft POs:</strong> Click <FileAddOutlined style={{ color: '#52c41a' }} /> to automatically create purchase order drafts for each supplier</li>
                  <li><strong>Export Excel:</strong> Click "Export Excel" to download spreadsheet grouped by supplier</li>
                </ol>
                
                <Paragraph strong style={{ marginTop: 8 }}>💡 Tips:</Paragraph>
                <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
                  <li><strong>Account Filter:</strong> Filter by <Tag color="blue">MAIN</Tag> or <Tag color="green">FBE</Tag> to focus on specific eMAG account</li>
                  <li><strong>Sync eMAG FBE:</strong> Synchronizes stock levels from eMAG Fulfillment warehouse</li>
                  <li><strong>Select Preferred:</strong> Auto-selects preferred/verified suppliers</li>
                  <li><strong>Select Cheapest:</strong> Auto-selects the lowest price supplier for each product</li>
                  <li><strong>Expand All:</strong> Shows all suppliers for all products at once</li>
                  <li><strong>eMag FBE:</strong> Products marked with 🛒 are from eMag Fulfillment</li>
                  <li><strong>Draft POs:</strong> Creates purchase orders in draft status - review before sending to suppliers</li>
                  <li><strong>Excel Export:</strong> Separate sheets for each supplier with all selected products</li>
                </ul>
              </div>
            }
            type="info"
            showIcon
            closable
          />
        </Col>

        {/* Products Table */}
        <Col span={24}>
          <Card>
            <Table
              columns={columns}
              dataSource={products}
              rowKey="product_id"
              loading={loading}
              pagination={{
                current: pagination.current,
                pageSize: pagination.pageSize,
                total: pagination.total,
                showSizeChanger: true,
                pageSizeOptions: ['20', '50', '100', '200', '500', '1000'],
                showTotal: (total) => `Total ${total} products`,
                onChange: (page, pageSize) => {
                  setPagination({ ...pagination, current: page, pageSize: pageSize || 20 });
                },
              }}
              expandable={{
                expandedRowRender,
                expandedRowKeys: expandedRows,
                onExpand: (expanded, record) => {
                  if (expanded) {
                    setExpandedRows([...expandedRows, record.product_id]);
                  } else {
                    setExpandedRows(expandedRows.filter(id => id !== record.product_id));
                  }
                },
              }}
              scroll={{ x: 1200 }}
              locale={{
                emptyText: (
                  <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description={
                      <div style={{ textAlign: 'center' }}>
                        <Paragraph strong>No low stock products found</Paragraph>
                        {!loading && products.length === 0 && pagination.total === 0 && (
                          <div>
                            <Paragraph type="secondary">
                              This could mean:
                            </Paragraph>
                            <ul style={{ textAlign: 'left', display: 'inline-block', marginBottom: 16 }}>
                              <li>All products have sufficient stock (great!)</li>
                              <li>No inventory items exist in the database</li>
                              <li>No warehouses are configured</li>
                            </ul>
                            <Paragraph type="secondary">
                              If you just set up the system, you may need to create inventory items first.
                            </Paragraph>
                          </div>
                        )}
                      </div>
                    }
                  />
                ),
              }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default LowStockSuppliersPage;
