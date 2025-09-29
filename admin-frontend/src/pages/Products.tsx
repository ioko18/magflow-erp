import { useState, useEffect, useCallback, useMemo } from 'react';
import { 
  Table, 
  Space, 
  Button, 
  Input, 
  Tag, 
  Typography, 
  message, 
  Segmented, 
  Card, 
  Select, 
  InputNumber, 
  Row, 
  Col, 
  Statistic, 
  Drawer, 
  Form, 
  DatePicker, 
  Switch, 
  Slider, 
  Checkbox, 
  Divider,
  Badge,
  Modal,
  Progress,
  Alert,
  List,
  Tooltip,
  Descriptions,
  Timeline,
  Empty,
  Popconfirm,
  Popover
} from 'antd';
import { 
  SearchOutlined, 
  ReloadOutlined, 
  ShopOutlined, 
  LinkOutlined, 
  DatabaseOutlined, 
  FilterOutlined, 
  ExportOutlined, 
  ImportOutlined, 
  PlusOutlined, 
  DownloadOutlined, 
  UploadOutlined,
  ClearOutlined,
  AppstoreOutlined,
  TableOutlined,
  SaveOutlined,
  DeleteOutlined,
  SettingOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type {
  FilterDropdownProps,
  FilterValue,
  SorterResult,
  TableCurrentDataSource,
  TablePaginationConfig,
} from 'antd/es/table/interface';
import api from '../services/api';

import dayjs, { Dayjs } from 'dayjs';

const { Title } = Typography;

interface Product {
  // Basic identification
  id: number;
  emag_id?: string;
  name: string;
  part_number?: string;
  part_number_key?: string;
  account_type?: string;
  
  // Product information
  description?: string | null;
  brand?: string;
  manufacturer?: string;
  
  // Pricing information
  price?: number | null;
  sale_price?: number | null;
  original_price?: number | null;
  min_sale_price?: number | null;
  max_sale_price?: number | null;
  recommended_price?: number | null;
  effective_price?: number | null;
  currency?: string;
  
  // Stock information
  stock: number;
  reserved_stock?: number;
  available_stock?: number;
  
  // Status information
  status: 'active' | 'inactive';
  offer_status?: number | null;
  marketplace_status?: string;
  visibility?: string;
  is_available?: boolean;
  
  // Category information
  category?: string;
  category_id?: number | null;
  emag_category_id?: string;
  
  // eMAG specific fields
  green_tax?: number | null;
  supply_lead_time?: number | null;
  handling_time?: number | null;
  shipping_weight?: number | null;
  shipping_size?: any;
  
  // Safety and compliance
  safety_information?: string;
  manufacturer_info?: any;
  eu_representative?: any;
  
  // Product attributes
  ean?: string[] | string | null;
  attributes?: any;
  emag_characteristics?: any;
  specifications?: any;
  vat_id?: number | null;
  warranty?: number | null;
  
  // Media
  images?: any;
  images_overwrite?: boolean;
  
  // Sync information
  sync_status?: string;
  last_synced_at?: string;
  sync_error?: string;
  sync_attempts?: number;
  
  // Timestamps
  created_at?: string;
  updated_at?: string;
  emag_created_at?: string;
  emag_modified_at?: string;
  offer_created_at?: string;
  offer_updated_at?: string;
  
  // Raw data for debugging
  raw_emag_data?: any;
  offer_raw_data?: any;
}

type ProductType = 'all' | 'emag_main' | 'emag_fbe' | 'local';
type SyncStatus = 'synced' | 'pending' | 'failed' | 'never_synced';

interface TopBrandSummary {
  brand: string;
  count: number;
}

interface ProductSummary {
  totalProducts: number;
  activeProducts: number;
  inactiveProducts: number;
  availableProducts: number;
  unavailableProducts: number;
  zeroPriceProducts: number;
  avgPrice: number;
  minPrice: number;
  maxPrice: number;
  topBrands: TopBrandSummary[];
}

type QuickFilterState = {
  hasImages: boolean;
  hasDescription: boolean;
  lowStock: boolean;
  highPrice: boolean;
  recentlyUpdated: boolean;
};

interface ProductFilterState {
  statusFilter: 'active' | 'inactive' | 'all';
  availabilityFilter: 'all' | 'available' | 'unavailable';
  priceRange: [number | undefined, number | undefined];
  selectedBrands: string[];
  selectedCategories: string[];
  stockRange: [number, number];
  dateRange: [string | null, string | null] | null;
  quickFilters: QuickFilterState;
  productType: ProductType;
  searchValue: string;
  syncStatus: SyncStatus | 'all';
  emagAccountType: 'all' | 'main' | 'fbe';
}

interface FilterPreset {
  id: string;
  name: string;
  createdAt: string;
  filters: ProductFilterState;
}

const PRESET_STORAGE_KEY = 'magflow_products_filter_presets';

const defaultQuickFilters: QuickFilterState = {
  hasImages: false,
  hasDescription: false,
  lowStock: false,
  highPrice: false,
  recentlyUpdated: false,
};

const columnKeyList = [
  'id',
  'emag_id',
  'name',
  'description',
  'brand',
  'manufacturer',
  'part_number',
  'part_number_key',
  'account_type',
  'offer',
  'price',
  'stock',
  'status',
  'category',
  'ean',
  'attributes',
  'sync_info',
  'images',
  'shipping',
  'safety',
  'created_at',
  'actions',
] as const;

type ColumnKey = (typeof columnKeyList)[number];
type ColumnVisibilityMap = Record<ColumnKey, boolean>;

interface TablePageSummaryMetrics {
  productCount: number;
  totalStock: number;
  activeCount: number;
  inactiveCount: number;
  accountMainCount: number;
  accountFbeCount: number;
  availableCount: number;
  unavailableCount: number;
  invalidOfferCount: number;
  warningOfferCount: number;
  avgEffectivePrice: number | null;
  minEffectivePrice: number | null;
  maxEffectivePrice: number | null;
  preferredCurrency: string | null;
}

type ChecklistStatus = 'pass' | 'warn' | 'fail';

interface OfferChecklistItem {
  key: string;
  label: string;
  status: ChecklistStatus;
  message: string;
}

interface OfferValidationResult {
  statusLabel: string;
  isActive: boolean;
  errors: string[];
  warnings: string[];
  isValid: boolean;
  checklist: OfferChecklistItem[];
  complianceScore: number;
  complianceTotal: number;
  complianceLevel: ChecklistStatus;
}

const COLUMN_VISIBILITY_STORAGE_KEY = 'magflow_products_column_visibility';

const defaultColumnVisibility: ColumnVisibilityMap = columnKeyList.reduce<ColumnVisibilityMap>((acc, key) => {
  return { ...acc, [key]: true };
}, {} as ColumnVisibilityMap);

const columnLabels: Record<ColumnKey, string> = {
  id: 'ID',
  emag_id: 'eMAG ID',
  name: 'Nume produs',
  description: 'Descriere',
  brand: 'Brand',
  manufacturer: 'Producător',
  part_number: 'Part Number',
  part_number_key: 'Part Number Key',
  account_type: 'Cont',
  offer: 'Ofertă',
  price: 'Preț',
  stock: 'Stoc',
  status: 'Status',
  category: 'Categorie',
  ean: 'Coduri EAN',
  attributes: 'Atribute',
  sync_info: 'Info Sincronizare',
  images: 'Imagini',
  shipping: 'Transport',
  safety: 'Siguranță',
  created_at: 'Creat la',
  actions: 'Acțiuni',
};

const loadColumnVisibilityFromStorage = (): ColumnVisibilityMap => {
  if (typeof window === 'undefined') {
    return { ...defaultColumnVisibility };
  }

  const raw = window.localStorage.getItem(COLUMN_VISIBILITY_STORAGE_KEY);
  if (!raw) {
    return { ...defaultColumnVisibility };
  }

  try {
    const parsed = JSON.parse(raw) as Partial<Record<ColumnKey, boolean>>;
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      const persisted: Partial<ColumnVisibilityMap> = {};
      columnKeyList.forEach((key) => {
        if (typeof parsed[key] === 'boolean') {
          persisted[key] = parsed[key] as boolean;
        }
      });
      return { ...defaultColumnVisibility, ...persisted };
    }
  } catch (error) {
    console.warn('Failed to parse column visibility from storage', error);
  }

  return { ...defaultColumnVisibility };
};

const persistColumnVisibilityToStorage = (visibility: ColumnVisibilityMap) => {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem(
    COLUMN_VISIBILITY_STORAGE_KEY,
    JSON.stringify(visibility),
  );
};

const loadPresetsFromStorage = (): FilterPreset[] => {
  if (typeof window === 'undefined') {
    return [];
  }

  const raw = window.localStorage.getItem(PRESET_STORAGE_KEY);
  if (!raw) {
    return [];
  }

  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      return parsed;
    }
  } catch (error) {
    console.warn('Failed to parse filter presets from storage', error);
  }

  return [];
};

const persistPresetsToStorage = (presets: FilterPreset[]) => {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem(PRESET_STORAGE_KEY, JSON.stringify(presets));
};

const complianceStatusColors: Record<ChecklistStatus, string> = {
  pass: '#52c41a',
  warn: '#faad14',
  fail: '#ff4d4f',
};

const complianceLevelLabels: Record<ChecklistStatus, string> = {
  pass: 'Conform',
  warn: 'Avertismente',
  fail: 'Erori',
};

const renderChecklistIcon = (status: ChecklistStatus) => {
  switch (status) {
    case 'pass':
      return <CheckCircleOutlined style={{ color: complianceStatusColors.pass }} />;
    case 'warn':
      return <ExclamationCircleOutlined style={{ color: complianceStatusColors.warn }} />;
    case 'fail':
      return <CloseCircleOutlined style={{ color: complianceStatusColors.fail }} />;
    default:
      return null;
  }
};

const serializeDateRange = (
  range: [Dayjs | null, Dayjs | null] | null,
): [string | null, string | null] | null => {
  if (!range) {
    return null;
  }

  const [start, end] = range;
  return [
    start && start.isValid() ? start.toISOString() : null,
    end && end.isValid() ? end.toISOString() : null,
  ];
};

const deserializeDateRange = (
  range: [string | null, string | null] | null,
): [Dayjs | null, Dayjs | null] | null => {
  if (!range) {
    return null;
  }

  const [start, end] = range;
  const startDayjs = start ? dayjs(start) : null;
  const endDayjs = end ? dayjs(end) : null;

  return [
    startDayjs && startDayjs.isValid() ? startDayjs : null,
    endDayjs && endDayjs.isValid() ? endDayjs : null,
  ];
};

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchValue, setSearchValue] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [productType, setProductType] = useState<ProductType>('all');
  const [tablePagination, setTablePagination] = useState({ current: 1, pageSize: 50, total: 0 });
  const [statusFilter, setStatusFilter] = useState<'active' | 'inactive' | 'all'>('active');
  const [availabilityFilter, setAvailabilityFilter] = useState<'all' | 'available' | 'unavailable'>('all');
  const [priceRange, setPriceRange] = useState<[number | undefined, number | undefined]>([undefined, undefined]);
  const [syncStatus, setSyncStatus] = useState<SyncStatus | 'all'>('all');
  const [emagAccountType, setEmagAccountType] = useState<'all' | 'main' | 'fbe'>('all');
  
  // Enhanced filtering states
  const [filterDrawerVisible, setFilterDrawerVisible] = useState(false);
  const [selectedBrands, setSelectedBrands] = useState<string[]>([]);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [stockRange, setStockRange] = useState<[number, number]>([0, 1000]);
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null] | null>(null);
  const [viewMode, setViewMode] = useState<'table' | 'grid'>('table');
  const [selectedProducts, setSelectedProducts] = useState<number[]>([]);
  const [exportModalVisible, setExportModalVisible] = useState(false);
  const [importModalVisible, setImportModalVisible] = useState(false);
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [activeProduct, setActiveProduct] = useState<Product | null>(null);
  const [quickFilters, setQuickFilters] = useState<QuickFilterState>({ ...defaultQuickFilters });
  const [filterPresets, setFilterPresets] = useState<FilterPreset[]>([]);
  const [selectedPresetId, setSelectedPresetId] = useState<string | null>(null);
  const [presetModalVisible, setPresetModalVisible] = useState(false);
  const [presetName, setPresetName] = useState('');
  const defaultSummary: ProductSummary = {
    totalProducts: 0,
    activeProducts: 0,
    inactiveProducts: 0,
    availableProducts: 0,
    unavailableProducts: 0,
    zeroPriceProducts: 0,
    avgPrice: 0,
    minPrice: 0,
    maxPrice: 0,
    topBrands: [],
  };
  const [summary, setSummary] = useState<ProductSummary>(defaultSummary);
  const [messageApi, contextHolder] = message.useMessage();
  const [sortState, setSortState] = useState<{ field: string; order: 'ascend' | 'descend' } | null>({
    field: 'price',
    order: 'descend',
  });
  const [columnVisibility, setColumnVisibility] = useState<ColumnVisibilityMap>(() => loadColumnVisibilityFromStorage());
  const visibleColumnCount = useMemo(
    () => columnKeyList.reduce((count, key) => (columnVisibility[key] ? count + 1 : count), 0),
    [columnVisibility],
  );

  useEffect(() => {
    persistColumnVisibilityToStorage(columnVisibility);
  }, [columnVisibility]);

  const toggleColumnVisibility = useCallback((key: ColumnKey, checked: boolean) => {
    setColumnVisibility((prev) => ({
      ...prev,
      [key]: checked,
    }));
  }, []);

  const resetColumnVisibility = useCallback(() => {
    setColumnVisibility({ ...defaultColumnVisibility });
    messageApi.success('Vizibilitatea coloanelor a fost resetată.');
  }, [messageApi]);

  const columnVisibilityMenu = useMemo(
    () => (
      <div style={{ maxWidth: 220 }}>
        <Typography.Text strong style={{ display: 'block', marginBottom: 8 }}>
          Gestionare coloane
        </Typography.Text>
        <Space direction="vertical" style={{ width: '100%' }}>
          {columnKeyList.map((key) => (
            <Checkbox
              key={key}
              checked={columnVisibility[key]}
              onChange={(event) => {
                const nextChecked = event.target.checked;
                if (!nextChecked && visibleColumnCount <= 1) {
                  messageApi.warning('Trebuie să rămână vizibilă cel puțin o coloană.');
                  return;
                }
                toggleColumnVisibility(key, nextChecked);
              }}
            >
              {columnLabels[key]}
            </Checkbox>
          ))}
        </Space>
        <Divider style={{ margin: '12px 0' }} />
        <Button type="link" size="small" icon={<ReloadOutlined />} onClick={resetColumnVisibility}>
          Resetează coloanele
        </Button>
      </div>
    ),
    [columnVisibility, messageApi, resetColumnVisibility, toggleColumnVisibility, visibleColumnCount],
  );

  const inventoryInsights = useMemo(() => {
    const totalFromSummary = summary.totalProducts > 0 ? summary.totalProducts : products.length;
    const availableFromSummary = summary.availableProducts > 0 ? summary.availableProducts : products.filter((product) => product.stock > 0).length;
    const totalProducts = totalFromSummary;

    const zeroStockProducts = products.filter((product) => product.stock === 0);
    const lowStockProducts = products.filter((product) => product.stock > 0 && product.stock <= 10);
    const recentlyUpdatedProducts = products.filter((product) => {
      if (!product.updated_at) {
        return false;
      }
      return dayjs().diff(dayjs(product.updated_at), 'day') <= 7;
    });

    const averagePrice = summary.avgPrice || 0;
    const highPriceThreshold = averagePrice > 0 ? averagePrice * 1.2 : null;
    const highPriceProducts = highPriceThreshold
      ? products.filter((product) => {
          const effectivePrice = product.effective_price ?? product.sale_price ?? product.price ?? 0;
          return effectivePrice > highPriceThreshold;
        })
      : [];

    const availabilityRate = totalProducts > 0 ? Math.round((availableFromSummary / totalProducts) * 100) : 0;

    return {
      totalProducts,
      availabilityRate: Math.min(100, Math.max(0, availabilityRate)),
      zeroStockCount: zeroStockProducts.length,
      lowStockCount: lowStockProducts.length,
      recentlyUpdatedCount: recentlyUpdatedProducts.length,
      highPriceCount: highPriceProducts.length,
    };
  }, [products, summary]);

  const lowStockHighlights = useMemo(() => {
    return products
      .filter((product) => product.stock >= 0 && product.stock <= 20)
      .sort((a, b) => a.stock - b.stock)
      .slice(0, 5);
  }, [products]);

  useEffect(() => {
    setFilterPresets(loadPresetsFromStorage());
  }, []);

  useEffect(() => {
    persistPresetsToStorage(filterPresets);
  }, [filterPresets]);

  const markPresetDirty = useCallback(() => {
    setSelectedPresetId((current) => (current ? null : current));
  }, []);

  const buildFilterState = (): ProductFilterState => ({
    statusFilter,
    availabilityFilter,
    priceRange,
    selectedBrands: [...selectedBrands],
    selectedCategories: [...selectedCategories],
    stockRange,
    dateRange: serializeDateRange(dateRange),
    quickFilters: { ...quickFilters },
    productType,
    searchValue,
    syncStatus,
    emagAccountType,
  });

  const applyFilterState = (state: ProductFilterState) => {
    setStatusFilter(state.statusFilter);
    setAvailabilityFilter(state.availabilityFilter);
    setPriceRange(state.priceRange);
    setSelectedBrands([...state.selectedBrands]);
    setSelectedCategories([...state.selectedCategories]);
    setStockRange(state.stockRange);
    setDateRange(deserializeDateRange(state.dateRange));
    setQuickFilters({ ...state.quickFilters });
    setProductType(state.productType);
    setSearchValue(state.searchValue);
    setSyncStatus(state.syncStatus);
    setEmagAccountType(state.emagAccountType);
    setSearchTerm(state.searchValue);
    setTablePagination((prev) => ({ ...prev, current: 1 }));
  };

  const handlePresetSelect = (value: string | null) => {
    if (!value) {
      setSelectedPresetId(null);
      return;
    }

    const preset = filterPresets.find((item) => item.id === value);
    if (!preset) {
      setSelectedPresetId(null);
      return;
    }

    setSelectedPresetId(preset.id);
    applyFilterState(preset.filters);
    messageApi.success(`Presetul "${preset.name}" a fost aplicat.`);
  };

  const handleOpenPresetModal = () => {
    const selectedPreset = selectedPresetId
      ? filterPresets.find((item) => item.id === selectedPresetId)
      : undefined;

    setPresetName(selectedPreset?.name || `Preset ${filterPresets.length + 1}`);
    setPresetModalVisible(true);
  };

  const handlePresetModalCancel = () => {
    setPresetModalVisible(false);
  };

  const handlePresetModalSave = () => {
    const trimmedName = presetName.trim();
    if (!trimmedName) {
      messageApi.warning('Introduceți un nume pentru preset.');
      return;
    }

    const filterState = buildFilterState();
    const existingIndex = filterPresets.findIndex(
      (preset) => preset.name.toLowerCase() === trimmedName.toLowerCase(),
    );

    let nextPresets: FilterPreset[];
    if (existingIndex >= 0) {
      const updatedPreset: FilterPreset = {
        ...filterPresets[existingIndex],
        name: trimmedName,
        filters: filterState,
        createdAt: new Date().toISOString(),
      };
      nextPresets = [...filterPresets];
      nextPresets[existingIndex] = updatedPreset;
      setSelectedPresetId(updatedPreset.id);
      messageApi.success('Presetul a fost actualizat.');
    } else {
      const newPreset: FilterPreset = {
        id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
        name: trimmedName,
        filters: filterState,
        createdAt: new Date().toISOString(),
      };
      nextPresets = [...filterPresets, newPreset];
      setSelectedPresetId(newPreset.id);
      messageApi.success('Presetul a fost salvat.');
    }

    setFilterPresets(nextPresets);
    setPresetModalVisible(false);
  };

  const handleDeletePreset = () => {
    if (!selectedPresetId) {
      return;
    }

    const nextPresets = filterPresets.filter((preset) => preset.id !== selectedPresetId);
    setFilterPresets(nextPresets);
    setSelectedPresetId(null);
    messageApi.success('Presetul a fost șters.');
  };

  const fetchProducts = useCallback(async (
    page: number,
    pageSize: number,
    options: { withSuccessFeedback?: boolean } = {}
  ) => {
    setLoading(true);
    try {
      const accountType = productType === 'emag_main' ? 'main' : 'fbe';
      const [minPrice, maxPrice] = priceRange;
      const availabilityParam =
        availabilityFilter === 'all' ? undefined : availabilityFilter === 'available';

      const response = await api.get('/admin/emag-products-by-account', {
        params: {
          account_type: accountType,
          skip: (page - 1) * pageSize,
          limit: pageSize,
          search: searchTerm || undefined,
          status: statusFilter,
          availability: availabilityParam,
          min_price: typeof minPrice === 'number' ? minPrice : undefined,
          max_price: typeof maxPrice === 'number' ? maxPrice : undefined,
          sort_by:
            sortState?.field === 'price'
              ? 'effective_price'
              : sortState?.field === 'sale_price'
              ? 'sale_price'
              : sortState?.field === 'created_at'
              ? 'created_at'
              : sortState?.field === 'updated_at'
              ? 'updated_at'
              : sortState?.field === 'name'
              ? 'name'
              : undefined,
          sort_order:
            sortState?.order === 'ascend'
              ? 'asc'
              : sortState?.order === 'descend'
              ? 'desc'
              : undefined,
        },
      });
      const data = response.data;

      if (data.status === 'success' && data.data) {
        const responseData = data.data;
        const normalizedProducts = Array.isArray(responseData.products)
          ? responseData.products.map((product: Product) => {
              const basePrice =
                typeof product.price === 'number'
                  ? product.price
                  : null;
              const salePrice =
                typeof product.sale_price === 'number'
                  ? product.sale_price
                  : null;
              const effectivePrice =
                typeof product.effective_price === 'number'
                  ? product.effective_price
                  : salePrice ?? basePrice;

              const normalizedCategoryId =
                typeof product.category_id === 'number' && product.category_id > 0
                  ? product.category_id
                  : null;
              const normalizedDescription =
                typeof product.description === 'string' && product.description.trim().length > 0
                  ? product.description
                  : null;
              const normalizedVatId =
                typeof product.vat_id === 'number' && product.vat_id > 0
                  ? product.vat_id
                  : null;
              const normalizedWarranty =
                typeof product.warranty === 'number' && product.warranty >= 0
                  ? product.warranty
                  : null;

              let normalizedEan: string[] | null = null;
              if (Array.isArray(product.ean)) {
                const cleanedEan = product.ean
                  .filter((code) => typeof code === 'string')
                  .map((code) => code.trim())
                  .filter((code) => code.length > 0);
                normalizedEan = cleanedEan.length > 0 ? cleanedEan : null;
              } else if (typeof product.ean === 'string') {
                const trimmed = product.ean.trim();
                normalizedEan = trimmed.length > 0 ? [trimmed] : null;
              }

              return {
                ...product,
                price: basePrice,
                sale_price: salePrice,
                effective_price: effectivePrice,
                category_id: normalizedCategoryId,
                description: normalizedDescription,
                vat_id: normalizedVatId,
                warranty: normalizedWarranty,
                ean: normalizedEan,
              };
            })
          : [];
        setProducts(normalizedProducts);

        const paginationData = responseData.pagination ?? {};
        setTablePagination((prev) => ({
          ...prev,
          current: page,
          pageSize,
          total: typeof paginationData.total === 'number' ? paginationData.total : prev.total,
        }));

        const summaryData = responseData.summary ?? {};
        setSummary({
          totalProducts: summaryData.total_products ?? summaryData.totalProducts ?? 0,
          activeProducts: summaryData.active_products ?? summaryData.activeProducts ?? 0,
          inactiveProducts: summaryData.inactive_products ?? summaryData.inactiveProducts ?? 0,
          availableProducts: summaryData.available_products ?? summaryData.availableProducts ?? 0,
          unavailableProducts: summaryData.unavailable_products ?? summaryData.unavailableProducts ?? 0,
          zeroPriceProducts: summaryData.zero_price_products ?? summaryData.zeroPriceProducts ?? 0,
          avgPrice: summaryData.avg_price ?? summaryData.avgPrice ?? 0,
          minPrice: summaryData.min_price ?? summaryData.minPrice ?? 0,
          maxPrice: summaryData.max_price ?? summaryData.maxPrice ?? 0,
          topBrands: Array.isArray(summaryData.top_brands || summaryData.topBrands)
            ? (summaryData.top_brands || summaryData.topBrands)
            : [],
        });

        if (options.withSuccessFeedback) {
          messageApi.success(`Produsele eMAG ${accountType.toUpperCase()} au fost reîmprospătate cu succes`);
        }
      } else {
        throw new Error('Invalid response from eMAG products API');
      }
    } catch (error) {
      console.error('Error fetching products:', error);
      messageApi.error(`Eroare la încărcarea produselor eMAG ${productType === 'emag_main' ? 'MAIN' : 'FBE'}`);
      // Fallback to empty array
      setProducts([]);
      setSummary(defaultSummary);
    } finally {
      setLoading(false);
    }
  }, [productType, searchTerm, statusFilter, availabilityFilter, priceRange, sortState, messageApi]);

  useEffect(() => {
    fetchProducts(tablePagination.current, tablePagination.pageSize);
  }, [fetchProducts, tablePagination.current, tablePagination.pageSize]);

  useEffect(() => {
    const handler = setTimeout(() => {
      setSearchTerm(searchValue);
    }, 400);

    return () => {
      clearTimeout(handler);
    };
  }, [searchValue]);

  const handleRefresh = () => {
    fetchProducts(tablePagination.current, tablePagination.pageSize, { withSuccessFeedback: true });
  };

  const handleTableChange = useCallback(
    (
      paginationConfig: TablePaginationConfig,
      _filters: Record<string, FilterValue | null>,
      sorter: SorterResult<Product> | SorterResult<Product>[],
      _extra: TableCurrentDataSource<Product>,
    ) => {
      setTablePagination((prev) => ({
        ...prev,
        current: paginationConfig.current ?? prev.current,
        pageSize: paginationConfig.pageSize ?? prev.pageSize,
      }));

      const primarySorter = Array.isArray(sorter) ? sorter[0] : sorter;
      if (primarySorter && primarySorter.order && typeof primarySorter.field === 'string') {
        setSortState({ field: primarySorter.field, order: primarySorter.order });
      } else {
        setSortState(null);
      }
    },
    [],
  );

  const handleStatusChange = (value: 'active' | 'inactive' | 'all') => {
    markPresetDirty();
    setStatusFilter(value);
  };

  const handleAvailabilityChange = (value: 'all' | 'available' | 'unavailable') => {
    markPresetDirty();
    setAvailabilityFilter(value);
  };

  const handleMinPriceChange = (value: number | null) => {
    markPresetDirty();
    setPriceRange(([_, max]) => [typeof value === 'number' ? value : undefined, max]);
  };

  const handleMaxPriceChange = (value: number | null) => {
    markPresetDirty();
    setPriceRange(([min]) => [min, typeof value === 'number' ? value : undefined]);
  };

  const handleResetFilters = () => {
    markPresetDirty();
    setStatusFilter('active');
    setAvailabilityFilter('all');
    setPriceRange([undefined, undefined]);
    setSearchValue('');
  };

  const handleSearchValueChange = (value: string) => {
    markPresetDirty();
    setSearchValue(value);
  };

  const handleProductTypeChange = (value: ProductType) => {
    markPresetDirty();
    setProductType(value);
  };

  const handleStockRangeChange = (value: number[]) => {
    markPresetDirty();
    setStockRange(value as [number, number]);
  };

  const handleDateRangeChange = (value: [Dayjs | null, Dayjs | null] | null) => {
    markPresetDirty();
    setDateRange(value);
  };

  const handleBrandSelectionChange = (value: string[]) => {
    markPresetDirty();
    setSelectedBrands(value);
  };

  const handleCategorySelectionChange = (value: string[]) => {
    markPresetDirty();
    setSelectedCategories(value);
  };

  const handleQuickFilterToggle = (key: keyof QuickFilterState, checked: boolean) => {
    markPresetDirty();
    setQuickFilters((prev) => ({
      ...prev,
      [key]: checked,
    }));
  };

  const handleQuickFilterReset = (key: keyof QuickFilterState) => {
    markPresetDirty();
    setQuickFilters((prev) => ({
      ...prev,
      [key]: false,
    }));
  };

  const openProductDetails = (product: Product) => {
    setActiveProduct(product);
    setDetailDrawerVisible(true);
  };

  const closeProductDetails = () => {
    setDetailDrawerVisible(false);
    setActiveProduct(null);
  };

  const getSearchProps = (dataIndex: keyof Product) => ({
    filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }: FilterDropdownProps) => (
      <div style={{ padding: 8 }} onKeyDown={(e) => e.stopPropagation()}>
        <Input
          placeholder={`Caută ${dataIndex}`}
          value={selectedKeys[0]}
          onChange={(e) => setSelectedKeys(e.target.value ? [e.target.value] : [])}
          onPressEnter={() => confirm()}
          style={{ marginBottom: 8, display: 'block' }}
        />
        <Space>
          <Button
            type="primary"
            onClick={() => confirm()}
            icon={<SearchOutlined />}
            size="small"
            style={{ width: 90 }}
          >
            Caută
          </Button>
          <Button
            onClick={() => clearFilters && clearFilters()}
            size="small"
            style={{ width: 90 }}
          >
            Reset
          </Button>
        </Space>
      </div>
    ),
    filterIcon: (filtered: boolean) => (
      <SearchOutlined style={{ color: filtered ? '#1890ff' : undefined }} />
    ),
  });

  const formatPrice = (price: number | null | undefined, currency?: string) => {
    if (price === null || price === undefined) return 'Preț indisponibil';
    if (price === 0) return 'Nu este disponibil';
    return `${price.toFixed(2)} ${currency || 'RON'}`;
  };
  const resolveEffectivePrice = useCallback((product: Product): number | null => {
    if (typeof product.effective_price === 'number') {
      return product.effective_price;
    }
    if (typeof product.sale_price === 'number') {
      return product.sale_price;
    }
    if (typeof product.price === 'number') {
      return product.price;
    }
    return null;
  }, []);
  const buildOfferComplianceChecklist = useCallback((product: Product): OfferChecklistItem[] => {
    const checklist: OfferChecklistItem[] = [];
    const addItem = (key: string, label: string, status: ChecklistStatus, message: string) => {
      checklist.push({ key, label, status, message });
    };

    const nameValue = typeof product.name === 'string' ? product.name.trim() : '';
    const brandValue = typeof product.brand === 'string' ? product.brand.trim() : '';
    const sanitizedPartNumber =
      typeof product.part_number === 'string'
        ? product.part_number.replace(/[\s,;]+/g, '').trim()
        : '';
    const categoryValid = typeof product.category_id === 'number' && product.category_id > 0;
    const salePrice = typeof product.sale_price === 'number' ? product.sale_price : null;
    const minSalePrice = typeof product.min_sale_price === 'number' ? product.min_sale_price : null;
    const maxSalePrice = typeof product.max_sale_price === 'number' ? product.max_sale_price : null;
    const recommendedPrice =
      typeof product.recommended_price === 'number' ? product.recommended_price : null;
    const vatValid = typeof product.vat_id === 'number' && product.vat_id > 0;
    const hasStock = typeof product.stock === 'number' && product.stock > 0;

    const rawEanInput = product.ean;
    const rawEanList = Array.isArray(rawEanInput)
      ? rawEanInput
      : typeof rawEanInput === 'string'
      ? [rawEanInput]
      : [];
    const cleanedEanList = rawEanList
      .filter((code): code is string => typeof code === 'string')
      .map((code) => code.trim())
      .filter((code) => code.length > 0);
    const hasEan = cleanedEanList.length > 0;
    const invalidEan = cleanedEanList.some((code) => !/^[0-9]{6,14}$/.test(code));

    const hasPartNumberKey =
      typeof product.part_number_key === 'string' && product.part_number_key.trim().length > 0;
    const hasDescription =
      typeof product.description === 'string' && product.description.trim().length > 0;
    const hasWarranty = typeof product.warranty === 'number' && product.warranty >= 0;

    const nameValid = nameValue.length >= 1 && nameValue.length <= 255;
    addItem(
      'name',
      'Nume produs (1-255 caractere)',
      nameValid ? 'pass' : 'fail',
      nameValid
        ? 'Numele produsului respectă standardul eMAG.'
        : 'Numele produsului este obligatoriu și trebuie să aibă între 1 și 255 de caractere.'
    );

    const brandValid = brandValue.length > 0 && brandValue.length <= 255;
    addItem(
      'brand',
      'Brand definit',
      brandValid ? 'pass' : 'fail',
      brandValid
        ? 'Brandul este completat.'
        : 'Brandul trebuie completat (1-255 caractere) conform standardului eMAG.'
    );

    addItem(
      'category',
      'Categorie eMAG (category_id)',
      categoryValid ? 'pass' : 'fail',
      categoryValid
        ? 'Categoria eMAG este setată.'
        : 'Setează un category_id valid pentru produs (ID numeric > 0).'
    );

    const partNumberValid = sanitizedPartNumber.length >= 1 && sanitizedPartNumber.length <= 25;
    addItem(
      'part_number',
      'Part Number (1-25 caractere)',
      partNumberValid ? 'pass' : 'fail',
      partNumberValid
        ? 'Part number este valid.'
        : 'Part number este obligatoriu și trebuie să aibă 1-25 caractere (fără spații, virgule sau punct și virgulă).'
    );

    const salePriceValid = salePrice !== null && salePrice > 0;
    addItem(
      'sale_price',
      'Sale price (>0)',
      salePriceValid ? 'pass' : 'fail',
      salePriceValid ? 'Sale price este setat.' : 'Setează sale_price (>0) la prima publicare a ofertei.'
    );

    const minSalePriceValid = minSalePrice !== null && minSalePrice > 0;
    addItem(
      'min_sale_price',
      'Min sale price (>0)',
      minSalePriceValid ? 'pass' : 'fail',
      minSalePriceValid
        ? 'Min sale price respectă cerința.'
        : 'min_sale_price este obligatoriu (>0) la prima publicare.'
    );

    const maxSalePriceValid = maxSalePrice !== null && maxSalePrice > 0;
    addItem(
      'max_sale_price',
      'Max sale price (>0)',
      maxSalePriceValid ? 'pass' : 'fail',
      maxSalePriceValid
        ? 'Max sale price respectă cerința.'
        : 'max_sale_price este obligatoriu (>0) la prima publicare.'
    );

    if (minSalePrice !== null && maxSalePrice !== null) {
      const rangeValid = maxSalePrice > minSalePrice;
      addItem(
        'sale_price_range',
        'Interval preț (min < max)',
        rangeValid ? 'pass' : 'fail',
        rangeValid
          ? 'Intervalul de preț este valid.'
          : 'max_sale_price trebuie să fie mai mare decât min_sale_price.'
      );
    }

    if (salePrice !== null && minSalePrice !== null && maxSalePrice !== null) {
      const withinBounds = salePrice >= minSalePrice && salePrice <= maxSalePrice;
      addItem(
        'sale_price_bounds',
        'Sale price în intervalul [min, max]',
        withinBounds ? 'pass' : 'fail',
        withinBounds
          ? 'sale_price este în intervalul acceptat.'
          : 'sale_price trebuie să rămână între min_sale_price și max_sale_price conform regulilor eMAG.'
      );
    }

    if (recommendedPrice !== null && salePrice !== null) {
      const recommendedValid = recommendedPrice > salePrice;
      addItem(
        'recommended_price',
        'Recommended price (> sale price)',
        recommendedValid ? 'pass' : 'warn',
        recommendedValid
          ? 'recommended_price este setat corespunzător.'
          : 'recommended_price trebuie să fie mai mare decât sale_price pentru a activa promoțiile recomandate.'
      );
    }

    addItem(
      'vat_id',
      'VAT ID setat',
      vatValid ? 'pass' : 'fail',
      vatValid ? 'VAT ID este setat.' : 'Selectează un vat_id valid (folosind endpoint-ul vat/read).'
    );

    addItem(
      'stock',
      'Stoc disponibil',
      hasStock ? 'pass' : 'warn',
      hasStock
        ? 'Produsul are stoc disponibil pentru ofertă.'
        : 'Trimite cel puțin o linie de stoc la publicarea inițială (warehouse_id + value).'
    );

    if (invalidEan) {
      addItem(
        'ean_format',
        'EAN valid (6-14 cifre)',
        'fail',
        'EAN-urile trebuie să conțină 6-14 caractere numerice (EAN/JAN/UPC/GTIN).'
      );
    } else if (hasEan) {
      addItem(
        'ean_presence',
        'EAN asociat ofertei',
        'pass',
        'EAN-urile sunt completate corect.'
      );
    } else {
      addItem(
        'ean_presence',
        'EAN asociat ofertei',
        'warn',
        'Adaugă EAN-uri valide atunci când categoria le solicită. Ele ajută la atașarea la catalogul eMAG.'
      );
    }

    if (hasPartNumberKey && hasEan) {
      addItem(
        'part_number_key_exclusivity',
        'part_number_key vs EAN',
        'warn',
        'Când atașezi la un produs existent folosește fie part_number_key, fie EAN (nu ambele simultan).'
      );
    }

    addItem(
      'description',
      'Descriere produs',
      hasDescription ? 'pass' : 'warn',
      hasDescription
        ? 'Descrierea respectă standardul minim.'
        : 'Adaugă descriere conform standardului eMAG pentru validare mai rapidă.'
    );

    addItem(
      'warranty',
      'Garanție (luni)',
      hasWarranty ? 'pass' : 'warn',
      hasWarranty
        ? 'Garanția produsului este setată.'
        : 'Setează warranty (0-255 luni) conform cerințelor categoriei.'
    );

    return checklist;
  }, []);
  const validateOffer = useCallback((product: Product): OfferValidationResult => {
    const statusValue = typeof product.offer_status === 'number' ? product.offer_status : null;
    const isActive = statusValue === 1;
    const statusLabel = isActive ? 'Activă' : statusValue === 0 ? 'Inactivă' : 'Necunoscută';

    const checklist = buildOfferComplianceChecklist(product);
    const errors = checklist.filter((item) => item.status === 'fail').map((item) => item.message);
    const warnings = checklist.filter((item) => item.status === 'warn').map((item) => item.message);
    const complianceTotal = checklist.length;
    const complianceScore = checklist.filter((item) => item.status === 'pass').length;

    let complianceLevel: ChecklistStatus = 'pass';
    if (errors.length > 0) {
      complianceLevel = 'fail';
    } else if (warnings.length > 0) {
      complianceLevel = 'warn';
    }

    return {
      statusLabel,
      isActive,
      errors,
      warnings,
      isValid: errors.length === 0,
      checklist,
      complianceScore,
      complianceTotal,
      complianceLevel,
    };
  }, [buildOfferComplianceChecklist]);
  const pageSummaryMetrics = useMemo<TablePageSummaryMetrics>(() => {
    if (products.length === 0) {
    return {
      productCount: 0,
      totalStock: 0,
      activeCount: 0,
      inactiveCount: 0,
      accountMainCount: 0,
      accountFbeCount: 0,
      availableCount: 0,
      unavailableCount: 0,
      invalidOfferCount: 0,
      warningOfferCount: 0,
      avgEffectivePrice: null,
      minEffectivePrice: null,
      maxEffectivePrice: null,
      preferredCurrency: null,
    };
    }

    let totalStock = 0;
    let activeCount = 0;
    let inactiveCount = 0;
    let accountMainCount = 0;
    let accountFbeCount = 0;
    let availableCount = 0;
    let unavailableCount = 0;
    const priceValues: number[] = [];
    const currencyCounts = new Map<string, number>();
    let invalidOfferCount = 0;
    let warningOfferCount = 0;

    products.forEach((product) => {
      totalStock += typeof product.stock === 'number' ? product.stock : 0;

      if (product.status === 'active') {
        activeCount += 1;
      } else if (product.status === 'inactive') {
        inactiveCount += 1;
      }

      if (product.account_type === 'fbe') {
        accountFbeCount += 1;
      } else {
        accountMainCount += 1;
      }

      if (product.is_available === true) {
        availableCount += 1;
      } else if (product.is_available === false) {
        unavailableCount += 1;
      }

      const offerValidation = validateOffer(product);
      if (!offerValidation.isValid) {
        invalidOfferCount += 1;
      }
      if (offerValidation.errors.length === 0 && offerValidation.warnings.length > 0) {
        warningOfferCount += 1;
      }

      const price = resolveEffectivePrice(product);
      if (price !== null) {
        priceValues.push(price);
        if (product.currency) {
          currencyCounts.set(product.currency, (currencyCounts.get(product.currency) ?? 0) + 1);
        }
      }
    });

    const avgEffectivePrice = priceValues.length
      ? priceValues.reduce((acc, value) => acc + value, 0) / priceValues.length
      : null;
    const minEffectivePrice = priceValues.length ? Math.min(...priceValues) : null;
    const maxEffectivePrice = priceValues.length ? Math.max(...priceValues) : null;

    let preferredCurrency: string | null = null;
    let bestCurrencyCount = 0;
    currencyCounts.forEach((count, currency) => {
      if (count > bestCurrencyCount) {
        bestCurrencyCount = count;
        preferredCurrency = currency;
      }
    });

    return {
      productCount: products.length,
      totalStock,
      activeCount,
      inactiveCount,
      accountMainCount,
      accountFbeCount,
      availableCount,
      unavailableCount,
      invalidOfferCount,
      warningOfferCount,
      avgEffectivePrice,
      minEffectivePrice,
      maxEffectivePrice,
      preferredCurrency,
    };
  }, [products, resolveEffectivePrice, validateOffer]);
  const formatSummaryPrice = useCallback(
    (value: number | null) => {
      if (value === null) {
        return 'N/A';
      }
      const currencyLabel = pageSummaryMetrics.preferredCurrency ?? 'RON';
      return `${value.toFixed(2)} ${currencyLabel}`;
    },
    [pageSummaryMetrics.preferredCurrency],
  );
  const columns = useMemo<ColumnsType<Product>>(() => [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
      sorter: (a, b) => a.id - b.id,
    },
    {
      title: 'eMAG ID',
      dataIndex: 'emag_id',
      key: 'emag_id',
      width: 120,
      render: (emag_id: string) => emag_id ? <code style={{ fontSize: '11px' }}>{emag_id}</code> : '-',
    },
    {
      title: 'Nume Produs',
      dataIndex: 'name',
      key: 'name',
      ...getSearchProps('name'),
      render: (name: string) => (
        <div style={{ maxWidth: '300px' }}>
          <div style={{ fontWeight: 500, marginBottom: '4px' }}>{name}</div>
        </div>
      ),
    },
    {
      title: 'Brand',
      dataIndex: 'brand',
      key: 'brand',
      width: 120,
      render: (brand: string) => brand || '-',
    },
    {
      title: 'Part Number',
      dataIndex: 'part_number',
      key: 'part_number',
      width: 140,
      ...getSearchProps('part_number'),
      render: (part_number: string) => part_number ? <code style={{ fontSize: '11px' }}>{part_number}</code> : '-',
    },
    {
      title: 'Part Number Key',
      dataIndex: 'part_number_key',
      key: 'part_number_key',
      width: 140,
      ...getSearchProps('part_number_key'),
      render: (part_number_key: string) => part_number_key ? <code style={{ fontSize: '11px', backgroundColor: '#f0f8ff', padding: '2px 4px', borderRadius: '3px' }}>{part_number_key}</code> : '-',
    },
    {
      title: 'Ofertă',
      key: 'offer',
      width: 220,
      render: (_value, record) => {
        const offer = validateOffer(record);
        const priceFormatter = (value: number | null | undefined) => {
          if (typeof value === 'number') {
            return value.toFixed(2);
          }
          return '—';
        };
        const compliancePercentage = offer.complianceTotal > 0
          ? Math.round((offer.complianceScore / offer.complianceTotal) * 100)
          : 0;
        const complianceProgressStatus =
          offer.complianceLevel === 'fail'
            ? 'exception'
            : offer.complianceLevel === 'warn'
            ? 'active'
            : 'success';
        const checklistContent = (
          <div style={{ maxWidth: 360 }}>
            <Typography.Text strong style={{ display: 'block', marginBottom: 8 }}>
              Checklist conformitate eMAG
            </Typography.Text>
            <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
              Respectă ghidul product_offer v4.4.8 pentru a evita respingerile manuale.
            </Typography.Text>
            <Progress
              percent={compliancePercentage}
              status={complianceProgressStatus}
              size="small"
              showInfo
            />
            <Divider style={{ margin: '12px 0' }} />
            <List
              size="small"
              itemLayout="horizontal"
              dataSource={offer.checklist}
              renderItem={(item) => (
                <List.Item key={item.key} style={{ padding: '4px 0' }}>
                  <Space align="start" size={8} style={{ width: '100%' }}>
                    {renderChecklistIcon(item.status)}
                    <div style={{ flex: 1 }}>
                      <Typography.Text strong>{item.label}</Typography.Text>
                      <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
                        {item.message}
                      </Typography.Paragraph>
                    </div>
                  </Space>
                </List.Item>
              )}
            />
          </div>
        );

        return (
          <Space direction="vertical" size={4} style={{ width: '100%' }}>
            <Space size={6} align="center">
              <Tag color={offer.isActive ? 'green' : 'default'}>{offer.statusLabel}</Tag>
              {!offer.isValid ? (
                <Tooltip title={offer.errors.join('\n')} color="red">
                  <WarningOutlined style={{ color: '#ff4d4f' }} />
                </Tooltip>
              ) : offer.warnings.length ? (
                <Tooltip title={offer.warnings.join('\n')} color="orange">
                  <InfoCircleOutlined style={{ color: '#faad14' }} />
                </Tooltip>
              ) : null}
            </Space>
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="Sale" labelStyle={{ width: '80px' }}>
                {priceFormatter(record.sale_price)}
              </Descriptions.Item>
              <Descriptions.Item label="Min" labelStyle={{ width: '80px' }}>
                {priceFormatter(record.min_sale_price)}
              </Descriptions.Item>
              <Descriptions.Item label="Max" labelStyle={{ width: '80px' }}>
                {priceFormatter(record.max_sale_price)}
              </Descriptions.Item>
              <Descriptions.Item label="RRP" labelStyle={{ width: '80px' }}>
                {priceFormatter(record.recommended_price)}
              </Descriptions.Item>
            </Descriptions>
            <Popover
              trigger={['click', 'hover']}
              placement="bottomLeft"
              content={checklistContent}
            >
              <Tag
                icon={renderChecklistIcon(offer.complianceLevel)}
                color={complianceStatusColors[offer.complianceLevel]}
                style={{ cursor: 'pointer', alignSelf: 'flex-start' }}
              >
                {`${complianceLevelLabels[offer.complianceLevel]} · ${compliancePercentage}%`}
              </Tag>
            </Popover>
          </Space>
        );
      },
    },
    {
      title: 'Cont',
      dataIndex: 'account_type',
      key: 'account_type',
      width: 100,
      render: (account: string | undefined) => (
        <Tag color={account === 'fbe' ? 'cyan' : 'geekblue'}>
          {(account || 'MAIN').toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Preț',
      dataIndex: 'price',
      key: 'price',
      width: 140,
      sorter: (a, b) => (a.effective_price ?? -1) - (b.effective_price ?? -1),
      sortOrder: sortState?.field === 'price' ? sortState?.order : undefined,
      render: (_price: number | null | undefined, record: Product) => {
        const effectivePrice = record.effective_price ?? null;
        const hasSale = typeof record.sale_price === 'number' && record.sale_price > 0;
        const hasBase = typeof record.price === 'number' && record.price > 0;
        const showStrikethrough = hasSale && hasBase && record.price !== record.sale_price;
        const color = typeof effectivePrice === 'number' && effectivePrice > 0 ? '#52c41a' : '#999';

        return (
          <div>
            <div style={{ fontWeight: 600, color }}>
              {formatPrice(effectivePrice, record.currency)}
            </div>
            {showStrikethrough && (
              <div style={{ fontSize: '12px', color: '#999', textDecoration: 'line-through' }}>
                {formatPrice(record.price, record.currency)}
              </div>
            )}
          </div>
        );
      },
    },
    {
      title: 'Stoc',
      dataIndex: 'stock',
      key: 'stock',
      width: 80,
      sorter: (a, b) => a.stock - b.stock,
      render: (stock: number) => (
        <Tag color={stock > 0 ? 'green' : 'red'}>
          {stock}
        </Tag>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      filters: [
        { text: 'Activ', value: 'active' },
        { text: 'Inactiv', value: 'inactive' },
      ],
      onFilter: (value, record) => record.status === value,
      render: (status: string, record: Product) => (
        <div>
          <Tag color={status === 'active' ? 'green' : 'red'}>
            {status === 'active' ? 'Activ' : 'Inactiv'}
          </Tag>
          {record.is_available !== undefined && (
            <Tag color={record.is_available ? 'blue' : 'orange'} style={{ marginTop: '2px' }}>
              {record.is_available ? 'Disponibil' : 'Indisponibil'}
            </Tag>
          )}
        </div>
      ),
    },
    {
      title: 'Categorie',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      render: (category: string) => category || '-',
    },
    {
      title: 'Descriere',
      dataIndex: 'description',
      key: 'description',
      width: 200,
      render: (description: string) => description ? (
        <Tooltip title={description}>
          <div style={{ 
            maxWidth: '180px', 
            overflow: 'hidden', 
            textOverflow: 'ellipsis', 
            whiteSpace: 'nowrap' 
          }}>
            {description}
          </div>
        </Tooltip>
      ) : '-',
    },
    {
      title: 'Producător',
      dataIndex: 'manufacturer',
      key: 'manufacturer',
      width: 120,
      render: (manufacturer: string) => manufacturer || '-',
    },
    {
      title: 'Coduri EAN',
      dataIndex: 'ean',
      key: 'ean',
      width: 150,
      render: (ean: string[] | string | null) => {
        if (!ean) return '-';
        const eanArray = Array.isArray(ean) ? ean : [ean];
        return (
          <Space direction="vertical" size={2}>
            {eanArray.slice(0, 2).map((code, index) => (
              <Tag key={index} color="blue" style={{ fontSize: '11px' }}>
                {code}
              </Tag>
            ))}
            {eanArray.length > 2 && (
              <Tooltip title={eanArray.slice(2).join(', ')}>
                <Tag color="default" style={{ fontSize: '10px' }}>
                  +{eanArray.length - 2} mai multe
                </Tag>
              </Tooltip>
            )}
          </Space>
        );
      },
    },
    {
      title: 'Atribute',
      dataIndex: 'attributes',
      key: 'attributes',
      width: 120,
      render: (attributes: any) => {
        if (!attributes || typeof attributes !== 'object') return '-';
        const keys = Object.keys(attributes);
        return (
          <Tooltip title={
            <div>
              {keys.slice(0, 5).map(key => (
                <div key={key}><strong>{key}:</strong> {String(attributes[key])}</div>
              ))}
              {keys.length > 5 && <div>... și {keys.length - 5} mai multe</div>}
            </div>
          }>
            <Tag color="purple">
              {keys.length} atribute
            </Tag>
          </Tooltip>
        );
      },
    },
    {
      title: 'Info Sincronizare',
      key: 'sync_info',
      width: 150,
      render: (_value, record) => (
        <Space direction="vertical" size={2}>
          <Tag color={
            record.sync_status === 'completed' ? 'green' :
            record.sync_status === 'failed' ? 'red' :
            record.sync_status === 'running' ? 'blue' : 'default'
          }>
            {record.sync_status || 'necunoscut'}
          </Tag>
          {record.last_synced_at && (
            <Typography.Text type="secondary" style={{ fontSize: '11px' }}>
              {new Date(record.last_synced_at).toLocaleString('ro-RO')}
            </Typography.Text>
          )}
          {record.sync_error && (
            <Tooltip title={record.sync_error}>
              <Tag color="red" style={{ fontSize: '10px' }}>
                Eroare
              </Tag>
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: 'Imagini',
      dataIndex: 'images',
      key: 'images',
      width: 100,
      render: (images: any) => {
        if (!images || !Array.isArray(images) || images.length === 0) {
          return <Tag color="default">Fără imagini</Tag>;
        }
        return (
          <Tooltip title={`${images.length} imagini disponibile`}>
            <Tag color="green">
              {images.length} imagini
            </Tag>
          </Tooltip>
        );
      },
    },
    {
      title: 'Transport',
      key: 'shipping',
      width: 120,
      render: (_value, record) => (
        <Space direction="vertical" size={2}>
          {record.shipping_weight && (
            <Tag color="blue" style={{ fontSize: '11px' }}>
              {record.shipping_weight} kg
            </Tag>
          )}
          {record.handling_time && (
            <Tag color="orange" style={{ fontSize: '11px' }}>
              {record.handling_time} zile
            </Tag>
          )}
          {record.supply_lead_time && (
            <Tag color="purple" style={{ fontSize: '11px' }}>
              Lead: {record.supply_lead_time} zile
            </Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'Siguranță',
      key: 'safety',
      width: 100,
      render: (_value, record) => {
        const hasInfo = record.safety_information || record.manufacturer_info || record.eu_representative;
        if (!hasInfo) return <Tag color="default">N/A</Tag>;
        
        return (
          <Tooltip title={
            <div>
              {record.safety_information && <div>Info siguranță: Da</div>}
              {record.manufacturer_info && <div>Info producător: Da</div>}
              {record.eu_representative && <div>Reprezentant UE: Da</div>}
            </div>
          }>
            <Tag color="green">GPSR</Tag>
          </Tooltip>
        );
      },
    },
    {
      title: 'Creat la',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 120,
      sorter: (a, b) => new Date(a.created_at || '').getTime() - new Date(b.created_at || '').getTime(),
      render: (date: string) => date ? new Date(date).toLocaleDateString('ro-RO') : '-',
    },
    {
      title: 'Acțiuni',
      key: 'actions',
      width: 120,
      render: (_value, record) => (
        <Button type="link" onClick={() => openProductDetails(record)}>
          Detalii
        </Button>
      ),
    },
  ], [getSearchProps, openProductDetails, sortState]);

  const filteredColumns = useMemo(() => {
    return columns.filter((column) => {
      const visibilityKey = column.key as ColumnKey | undefined;

      if (!visibilityKey || !(visibilityKey in columnVisibility)) {
        return true;
      }

      return columnVisibility[visibilityKey];
    });
  }, [columnVisibility, columns]);

  // Enhanced helper functions
  const clearAllFilters = () => {
    markPresetDirty();
    setSearchValue('');
    setSearchTerm('');
    setStatusFilter('active');
    setAvailabilityFilter('all');
    setPriceRange([undefined, undefined]);
    setSelectedBrands([]);
    setSelectedCategories([]);
    setStockRange([0, 1000]);
    setDateRange(null);
    setQuickFilters({ ...defaultQuickFilters });
    setSelectedPresetId(null);
  };

  const handleProductSelection = (productId: number, checked: boolean) => {
    setSelectedProducts((prev) => {
      if (checked) {
        if (prev.includes(productId)) {
          return prev;
        }
        return [...prev, productId];
      }
      return prev.filter((id) => id !== productId);
    });
  };

  const handleListPaginationChange = (page: number, pageSize: number) => {
    setTablePagination((prev) => ({
      ...prev,
      current: page,
      pageSize,
    }));
  };

  const renderGridView = () => (
    <List
      grid={{ gutter: 16, xs: 1, sm: 2, md: 2, lg: 3, xl: 3, xxl: 4 }}
      dataSource={products}
      loading={loading}
      locale={{ emptyText: 'Nu există produse pentru criteriile selectate.' }}
      pagination={{
        total: tablePagination.total,
        current: tablePagination.current,
        pageSize: tablePagination.pageSize,
        showSizeChanger: true,
        pageSizeOptions: ['10', '20', '50', '100'],
        showQuickJumper: true,
        showTotal: (total, range) => `${range[0]}-${range[1]} din ${total} produse`,
        onChange: handleListPaginationChange,
        onShowSizeChange: handleListPaginationChange,
      }}
      renderItem={(product) => {
        const isSelected = selectedProducts.includes(product.id);
        const hasSale = typeof product.sale_price === 'number' && product.sale_price > 0;
        const hasBase = typeof product.price === 'number' && product.price > 0;
        const showStrikethrough = hasSale && hasBase && product.price !== product.sale_price;

        return (
          <List.Item key={product.id}>
            <Card
              size="small"
              title={
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, marginBottom: 8 }}>{product.name}</div>
                    <Space size={[6, 6]} wrap>
                      <Tag color="blue">ID {product.id}</Tag>
                      {product.emag_id && (
                        <Tag icon={<LinkOutlined />} color="geekblue">
                          {product.emag_id}
                        </Tag>
                      )}
                      {product.brand && <Tag color="purple">{product.brand}</Tag>}
                      {product.category && <Tag color="green">{product.category}</Tag>}
                    </Space>
                  </div>
                  <Checkbox
                    checked={isSelected}
                    onChange={(event) => handleProductSelection(product.id, event.target.checked)}
                    style={{ alignSelf: 'flex-start' }}
                  >
                    Selectează
                  </Checkbox>
                </div>
              }
              extra={
                <Space size={4} wrap>
                  <Tag color={product.account_type === 'fbe' ? 'cyan' : 'geekblue'}>
                    {(product.account_type || 'MAIN').toUpperCase()}
                  </Tag>
                  <Tag color={product.status === 'active' ? 'green' : 'red'}>
                    {product.status === 'active' ? 'Activ' : 'Inactiv'}
                  </Tag>
                  {product.is_available !== undefined && (
                    <Tag color={product.is_available ? 'blue' : 'orange'}>
                      {product.is_available ? 'Disponibil' : 'Indisponibil'}
                    </Tag>
                  )}
                </Space>
              }
            >
              <Space direction="vertical" size={12} style={{ width: '100%' }}>
                <div>
                  <div style={{ fontSize: 18, fontWeight: 600, color: '#52c41a' }}>
                    {formatPrice(product.effective_price ?? product.sale_price ?? product.price, product.currency)}
                  </div>
                  {showStrikethrough && (
                    <div style={{ fontSize: 12, color: '#999', textDecoration: 'line-through' }}>
                      {formatPrice(product.price, product.currency)}
                    </div>
                  )}
                </div>

                <Row gutter={16}>
                  <Col xs={12}>
                    <Statistic title="Stoc" value={product.stock} suffix="buc" valueStyle={{ fontSize: 16 }} />
                  </Col>
                  <Col xs={12}>
                    <Statistic
                      title="Preț promoțional"
                      value={product.sale_price ?? '-'}
                      valueRender={() => (
                        <div>
                          {product.sale_price ? formatPrice(product.sale_price, product.currency) : 'N/A'}
                        </div>
                      )}
                    />
                  </Col>
                </Row>

                <Divider style={{ margin: '12px 0' }} />

                <Row gutter={[8, 8]}>
                  {product.part_number && (
                    <Col xs={24}>
                      <Tooltip title="Part Number">
                        <Tag color="volcano">PN: {product.part_number}</Tag>
                      </Tooltip>
                    </Col>
                  )}
                  {product.part_number_key && (
                    <Col xs={24}>
                      <Tooltip title="Part Number Key">
                        <Tag color="magenta">Key: {product.part_number_key}</Tag>
                      </Tooltip>
                    </Col>
                  )}
                  {product.created_at && (
                    <Col xs={24}>
                      <Tooltip title="Creat la">
                        <Tag icon={<DatabaseOutlined />} color="default">
                          {new Date(product.created_at).toLocaleString('ro-RO')}
                        </Tag>
                      </Tooltip>
                    </Col>
                  )}
                </Row>
              </Space>
              <Divider style={{ margin: '12px 0 8px' }} />
              <Space wrap>
                <Button type="link" onClick={() => openProductDetails(product)}>
                  Vezi detalii
                </Button>
              </Space>
            </Card>
          </List.Item>
        );
      }}
    />
  );

  const handleBulkAction = (action: string) => {
    switch (action) {
      case 'export':
        setExportModalVisible(true);
        break;
      case 'delete':
        Modal.confirm({
          title: 'Confirmare ștergere',
          content: `Sigur doriți să ștergeți ${selectedProducts.length} produse selectate?`,
          onOk: () => {
            messageApi.success(`${selectedProducts.length} produse au fost șterse`);
            setSelectedProducts([]);
          }
        });
        break;
      case 'activate':
        messageApi.success(`${selectedProducts.length} produse au fost activate`);
        setSelectedProducts([]);
        break;
      case 'deactivate':
        messageApi.success(`${selectedProducts.length} produse au fost dezactivate`);
        setSelectedProducts([]);
        break;
    }
  };

  return (
    <div style={{ padding: '24px' }}>
      {contextHolder}
      
      {/* Enhanced Header */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div>
            <Title level={2} style={{ margin: 0 }}>
              <ShopOutlined style={{ marginRight: '8px' }} />
              Produse eMAG
            </Title>
            <p style={{ color: '#666', margin: 0 }}>
              Vizualizează și gestionează produsele sincronizate din conturile eMAG MAIN și FBE
            </p>
          </div>
          <Space>
            <Button icon={<ImportOutlined />} onClick={() => setImportModalVisible(true)}>
              Import
            </Button>
            <Button icon={<ExportOutlined />} onClick={() => setExportModalVisible(true)}>
              Export
            </Button>
            <Button type="primary" icon={<PlusOutlined />}>
              Adaugă Produs
            </Button>
          </Space>
        </div>

        {/* Quick Stats Cards */}
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={12} md={6}>
            <Card size="small">
              <Statistic
                title="Total Produse"
                value={summary.totalProducts}
                prefix={<ShopOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card size="small">
              <Statistic
                title="Active"
                value={summary.activeProducts}
                prefix={<Badge status="success" />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card size="small">
              <Statistic
                title="În Stoc"
                value={summary.availableProducts}
                prefix={<Badge status="processing" />}
                valueStyle={{ color: '#fa8c16' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card size="small">
              <Statistic
                title="Preț Mediu"
                value={summary.avgPrice}
                precision={2}
                suffix="RON"
                prefix={<Badge status="warning" />}
                valueStyle={{ color: '#722ed1' }}
              />
            </Card>
          </Col>
        </Row>
      </div>

      <Card title="Indicatori sănătate stoc" style={{ marginBottom: '24px' }}>
        <Row gutter={[24, 24]} align="stretch">
          <Col xs={24} lg={8}>
            <Space direction="vertical" align="center" style={{ width: '100%' }}>
              <Progress
                type="dashboard"
                percent={inventoryInsights.availabilityRate}
                status={
                  inventoryInsights.availabilityRate < 60
                    ? 'exception'
                    : inventoryInsights.availabilityRate < 85
                    ? 'active'
                    : 'success'
                }
                format={(value) => `${value ?? 0}% disponibilitate`}
              />
              <Typography.Text type="secondary">
                Raport dintre produsele disponibile și totalul produselor gestionate
              </Typography.Text>
              <Typography.Text>
                Total produse monitorizate: <strong>{inventoryInsights.totalProducts}</strong>
              </Typography.Text>
            </Space>
          </Col>
          <Col xs={24} lg={8}>
            <Space direction="vertical" style={{ width: '100%' }} size={12}>
              <Statistic
                title="Produse fără stoc"
                value={inventoryInsights.zeroStockCount}
                valueStyle={{ color: inventoryInsights.zeroStockCount > 0 ? '#cf1322' : '#389e0d' }}
              />
              <Statistic
                title="Produse cu stoc redus (≤10)"
                value={inventoryInsights.lowStockCount}
                valueStyle={{ color: inventoryInsights.lowStockCount > 0 ? '#fa8c16' : '#389e0d' }}
              />
              <Statistic
                title="Actualizate în ultimele 7 zile"
                value={inventoryInsights.recentlyUpdatedCount}
                valueStyle={{ color: '#1890ff' }}
              />
              {inventoryInsights.highPriceCount > 0 && (
                <Alert
                  type="warning"
                  message="Produse cu preț peste media curentă"
                  description={`${inventoryInsights.highPriceCount} produse au un preț cu peste 20% mai mare decât media.`}
                  showIcon
                />
              )}
            </Space>
          </Col>
          <Col xs={24} lg={8}>
            <List
              size="small"
              header={
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography.Text strong>Produse critice</Typography.Text>
                  <Tag color="orange">Top 5 stoc minim</Tag>
                </div>
              }
              locale={{ emptyText: 'Nu există produse cu stoc critic în acest moment.' }}
              dataSource={lowStockHighlights}
              renderItem={(item) => (
                <List.Item
                  key={item.id}
                  actions={[
                    <Tag key="stock" color={item.stock === 0 ? 'red' : 'gold'}>{`${item.stock} buc`}</Tag>,
                  ]}
                  onClick={() => openProductDetails(item)}
                  style={{ cursor: 'pointer' }}
                >
                  <List.Item.Meta
                    title={
                      <Space size={6} wrap>
                        <Typography.Text>{item.name}</Typography.Text>
                        {item.part_number && <Tag color="volcano">PN: {item.part_number}</Tag>}
                      </Space>
                    }
                    description={
                      item.updated_at
                        ? `Actualizat: ${new Date(item.updated_at).toLocaleString('ro-RO')}`
                        : 'Fără dată actualizare'
                    }
                  />
                </List.Item>
              )}
            />
          </Col>
        </Row>
      </Card>

      {/* Enhanced Search and Filter Section */}
      <Card style={{ marginBottom: '24px' }}>
        <div style={{ marginBottom: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <Title level={4} style={{ margin: 0 }}>
              Filtrare și Căutare Avansată
            </Title>
            <Space>
              <Select
                allowClear
                placeholder="Aplică preset"
                style={{ minWidth: 200 }}
                value={selectedPresetId || undefined}
                onChange={(value) => handlePresetSelect(value || null)}
                options={filterPresets.map((preset) => ({
                  label: preset.name,
                  value: preset.id,
                }))}
                popupRender={(menu) => (
                  <div>
                    {menu}
                    <Divider style={{ margin: '4px 0' }} />
                    <Space style={{ padding: '4px 8px', justifyContent: 'space-between', width: '100%' }}>
                      <Button
                        type="link"
                        icon={<SaveOutlined />}
                        onClick={handleOpenPresetModal}
                      >
                        Salvează preset
                      </Button>
                      <Popconfirm
                        title="Ștergere preset"
                        description="Sigur ștergi presetul selectat?"
                        onConfirm={handleDeletePreset}
                        okText="Da"
                        cancelText="Nu"
                        disabled={!selectedPresetId}
                      >
                        <Button type="link" danger icon={<DeleteOutlined />} disabled={!selectedPresetId}>
                          Șterge
                        </Button>
                      </Popconfirm>
                    </Space>
                  </div>
                )}
              />
              <Segmented
                value={viewMode}
                onChange={setViewMode}
                options={[
                  { label: <TableOutlined />, value: 'table' },
                  { label: <AppstoreOutlined />, value: 'grid' }
                ]}
              />
              <Popover content={columnVisibilityMenu} trigger="click" placement="bottomRight">
                <Button icon={<SettingOutlined />}>
                  Coloane
                </Button>
              </Popover>
              <Button icon={<FilterOutlined />} onClick={() => setFilterDrawerVisible(true)}>
                Filtre Avansate
              </Button>
            </Space>
          </div>

          {/* Account Type and Main Search */}
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={24} md={8}>
              <Segmented
                value={productType}
                onChange={(value) => handleProductTypeChange(value as ProductType)}
                options={[
                  {
                    label: (
                      <div style={{ padding: '4px 8px' }}>
                        <AppstoreOutlined style={{ marginRight: '8px' }} />
                        <span>Toate</span>
                      </div>
                    ),
                    value: 'all',
                  },
                  {
                    label: (
                      <div style={{ padding: '4px 8px' }}>
                        <DatabaseOutlined style={{ marginRight: '8px' }} />
                        <span>eMAG MAIN</span>
                      </div>
                    ),
                    value: 'emag_main',
                  },
                  {
                    label: (
                      <div style={{ padding: '4px 8px' }}>
                        <LinkOutlined style={{ marginRight: '8px' }} />
                        <span>eMAG FBE</span>
                      </div>
                    ),
                    value: 'emag_fbe',
                  },
                  {
                    label: (
                      <div style={{ padding: '4px 8px' }}>
                        <ShopOutlined style={{ marginRight: '8px' }} />
                        <span>Local</span>
                      </div>
                    ),
                    value: 'local',
                  },
                ]}
                block
              />
            </Col>
            <Col xs={24} md={12}>
              <Input.Search
                placeholder="Caută după nume, cod produs, brand..."
                value={searchValue}
                onChange={(e) => handleSearchValueChange(e.target.value)}
                onSearch={handleRefresh}
                enterButton={<SearchOutlined />}
                allowClear
                size="large"
              />
            </Col>
            <Col xs={24} md={4}>
              <Button
                icon={<ReloadOutlined />}
                onClick={handleRefresh}
                loading={loading}
                size="large"
                block
              >
                Refresh
              </Button>
            </Col>
          </Row>

          {/* Quick Filters */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ marginBottom: 8, fontWeight: 500 }}>Filtre Rapide:</div>
            <Space wrap>
              <Checkbox
                checked={quickFilters.hasImages}
                onChange={(e) => handleQuickFilterToggle('hasImages', e.target.checked)}
              >
                Cu imagini
              </Checkbox>
              <Checkbox
                checked={quickFilters.hasDescription}
                onChange={(e) => handleQuickFilterToggle('hasDescription', e.target.checked)}
              >
                Cu descriere
              </Checkbox>
              <Checkbox
                checked={quickFilters.lowStock}
                onChange={(e) => handleQuickFilterToggle('lowStock', e.target.checked)}
              >
                Stoc redus
              </Checkbox>
              <Checkbox
                checked={quickFilters.highPrice}
                onChange={(e) => handleQuickFilterToggle('highPrice', e.target.checked)}
              >
                Preț ridicat
              </Checkbox>
              <Checkbox
                checked={quickFilters.recentlyUpdated}
                onChange={(e) => handleQuickFilterToggle('recentlyUpdated', e.target.checked)}
              >
                Actualizate recent
              </Checkbox>
            </Space>
          </div>

          {/* Standard Filters */}
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} md={6}>
              <Select
                value={statusFilter}
                onChange={handleStatusChange}
                style={{ width: '100%' }}
                placeholder="Status"
              >
                <Select.Option value="active">Produse active</Select.Option>
                <Select.Option value="inactive">Produse inactive</Select.Option>
                <Select.Option value="all">Toate produsele</Select.Option>
              </Select>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Select
                value={availabilityFilter}
                onChange={handleAvailabilityChange}
                style={{ width: '100%' }}
                placeholder="Disponibilitate"
              >
                <Select.Option value="all">Toate</Select.Option>
                <Select.Option value="available">Disponibile</Select.Option>
                <Select.Option value="unavailable">Indisponibile</Select.Option>
              </Select>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Space.Compact style={{ width: '100%' }}>
                <InputNumber
                  placeholder="Preț min"
                  value={priceRange[0]}
                  min={0}
                  onChange={handleMinPriceChange}
                  style={{ width: '50%' }}
                />
                <InputNumber
                  placeholder="Preț max"
                  value={priceRange[1]}
                  min={0}
                  onChange={handleMaxPriceChange}
                  style={{ width: '50%' }}
                />
              </Space.Compact>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Space style={{ width: '100%' }}>
                <Button onClick={handleResetFilters} icon={<ClearOutlined />}>
                  Reset
                </Button>
                <Button onClick={clearAllFilters} icon={<ClearOutlined />}>
                  Clear All
                </Button>
              </Space>
            </Col>
          </Row>
        </div>

        {/* Active Filters Display */}
        {(selectedBrands.length > 0 || selectedCategories.length > 0 || Object.values(quickFilters).some(Boolean)) && (
          <div style={{ marginTop: 16, padding: 12, background: '#f5f5f5', borderRadius: 6 }}>
            <div style={{ marginBottom: 8, fontWeight: 500 }}>Filtre active:</div>
            <Space wrap>
              {selectedBrands.map(brand => (
                <Tag 
                  key={brand} 
                  closable 
                  onClose={() => handleBrandSelectionChange(selectedBrands.filter((b) => b !== brand))}
                  color="blue"
                >
                  Brand: {brand}
                </Tag>
              ))}
              {selectedCategories.map(category => (
                <Tag 
                  key={category} 
                  closable 
                  onClose={() => handleCategorySelectionChange(selectedCategories.filter((c) => c !== category))}
                  color="green"
                >
                  Categorie: {category}
                </Tag>
              ))}
              {Object.entries(quickFilters).map(([key, value]) => 
                value && (
                  <Tag 
                    key={key} 
                    closable 
                    onClose={() => handleQuickFilterReset(key as keyof QuickFilterState)}
                    color="orange"
                  >
                    {key === 'hasImages' ? 'Cu imagini' :
                     key === 'hasDescription' ? 'Cu descriere' :
                     key === 'lowStock' ? 'Stoc redus' :
                     key === 'highPrice' ? 'Preț ridicat' : 'Actualizate recent'}
                  </Tag>
                )
              )}
            </Space>
          </div>
        )}

        {/* Top Brands Display */}
        {summary.topBrands.length > 0 && (
          <div style={{ marginTop: '16px', display: 'flex', flexWrap: 'wrap', gap: '8px', color: '#666' }}>
            <span style={{ fontWeight: 500 }}>Top branduri:</span>
            {summary.topBrands.map((brandInfo) => (
              <Tag 
                key={`${brandInfo.brand}-${brandInfo.count}`} 
                color="blue"
                style={{ cursor: 'pointer' }}
                onClick={() => {
                  if (!selectedBrands.includes(brandInfo.brand)) {
                    handleBrandSelectionChange([...selectedBrands, brandInfo.brand]);
                  }
                }}
              >
                {brandInfo.brand} · {brandInfo.count}
              </Tag>
            ))}
          </div>
        )}
      </Card>

      {/* Bulk Actions Bar */}
      {selectedProducts.length > 0 && (
        <Alert
          message={
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>{selectedProducts.length} produse selectate</span>
              <Space>
                <Button size="small" onClick={() => handleBulkAction('activate')}>
                  Activează
                </Button>
                <Button size="small" onClick={() => handleBulkAction('deactivate')}>
                  Dezactivează
                </Button>
                <Button size="small" onClick={() => handleBulkAction('export')}>
                  Exportă
                </Button>
                <Button size="small" danger onClick={() => handleBulkAction('delete')}>
                  Șterge
                </Button>
                <Button size="small" onClick={() => setSelectedProducts([])}>
                  Anulează
                </Button>
              </Space>
            </div>
          }
          type="info"
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Enhanced Products Table */}
      {viewMode === 'table' ? (
        <Card>
          <Table
            columns={filteredColumns}
            dataSource={products}
            rowKey="id"
            loading={loading}
            onChange={handleTableChange}
            rowSelection={{
              selectedRowKeys: selectedProducts,
              onChange: (selectedRowKeys) => setSelectedProducts(selectedRowKeys as number[]),
              selections: [
                Table.SELECTION_ALL,
                Table.SELECTION_INVERT,
                Table.SELECTION_NONE,
              ],
            }}
            pagination={{
              total: tablePagination.total,
              current: tablePagination.current,
              pageSize: tablePagination.pageSize,
              showSizeChanger: true,
              pageSizeOptions: ['10', '20', '50', '100'],
              showQuickJumper: true,
              showTotal: (total, range) =>
                `${range[0]}-${range[1]} din ${total} produse`,
            }}
            scroll={{ x: 1400 }}
            size="small"
          />
        </Card>
      ) : (
        <Card>{renderGridView()}</Card>
      )}

      <Card size="small" style={{ marginTop: 16 }} title="Sumar listă curentă">
        {pageSummaryMetrics.productCount > 0 ? (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Produse afișate"
                  value={pageSummaryMetrics.productCount}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Stoc total"
                  value={pageSummaryMetrics.totalStock}
                  suffix="buc"
                  valueStyle={{ color: '#722ed1' }}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Active"
                  value={pageSummaryMetrics.activeCount}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Inactive"
                  value={pageSummaryMetrics.inactiveCount}
                  valueStyle={{ color: '#fa541c' }}
                />
              </Col>
            </Row>
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Cont MAIN"
                  value={pageSummaryMetrics.accountMainCount}
                  valueStyle={{ color: '#2f54eb' }}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Cont FBE"
                  value={pageSummaryMetrics.accountFbeCount}
                  valueStyle={{ color: '#13c2c2' }}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Disponibile"
                  value={pageSummaryMetrics.availableCount}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Indisponibile"
                  value={pageSummaryMetrics.unavailableCount}
                  valueStyle={{ color: '#faad14' }}
                />
              </Col>
            </Row>
            <Divider style={{ margin: '0' }} />
            <Descriptions column={{ xs: 1, sm: 2, md: 3 }} size="small">
              <Descriptions.Item label="Preț mediu">
                {formatSummaryPrice(pageSummaryMetrics.avgEffectivePrice)}
              </Descriptions.Item>
              <Descriptions.Item label="Preț minim">
                {formatSummaryPrice(pageSummaryMetrics.minEffectivePrice)}
              </Descriptions.Item>
              <Descriptions.Item label="Preț maxim">
                {formatSummaryPrice(pageSummaryMetrics.maxEffectivePrice)}
              </Descriptions.Item>
            </Descriptions>
          </Space>
        ) : (
          <Typography.Text type="secondary">
            Nu există produse în lista curentă pentru a calcula un sumar.
          </Typography.Text>
        )}
      </Card>

      {products.length > 0 && (
        <Card
          size="small"
          style={{ marginTop: 16 }}
          title="Monitorizare conformitate eMAG product_offer"
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} md={8}>
              <Card size="small" variant="borderless" style={{ background: '#fafafa' }}>
                <Statistic
                  title="Oferte valide (fără erori)"
                  value={pageSummaryMetrics.productCount - pageSummaryMetrics.invalidOfferCount}
                  suffix={`/ ${pageSummaryMetrics.productCount}`}
                  valueStyle={{ color: '#52c41a' }}
                />
                <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>
                  Ofertele fără erori sunt pregătite pentru publicare conform criteriilor obligatorii eMAG.
                </Typography.Paragraph>
              </Card>
            </Col>
            <Col xs={24} md={8}>
              <Card size="small" variant="borderless" style={{ background: '#fafafa' }}>
                <Statistic
                  title="Oferte cu avertizări"
                  value={pageSummaryMetrics.warningOfferCount}
                  valueStyle={{ color: '#faad14' }}
                />
                <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>
                  Revizuiește avertizările pentru a îmbunătăți șansele de aprobare și relevanță.
                </Typography.Paragraph>
              </Card>
            </Col>
            <Col xs={24} md={8}>
              <Card size="small" variant="borderless" style={{ background: '#fafafa' }}>
                <Statistic
                  title="Oferte cu erori critice"
                  value={pageSummaryMetrics.invalidOfferCount}
                  valueStyle={{ color: '#ff4d4f' }}
                />
                <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>
                  Erorile trebuie remediate înainte de publicare: prețuri, categorie, part number, VAT și alte câmpuri obligatorii.
                </Typography.Paragraph>
              </Card>
            </Col>
          </Row>
        </Card>
      )}

      {/* Advanced Filters Drawer */}
      <Drawer
        title="Filtre Avansate"
        placement="right"
        width={400}
        open={filterDrawerVisible}
        onClose={() => setFilterDrawerVisible(false)}
        extra={
          <Space>
            <Button onClick={clearAllFilters}>Reset All</Button>
            <Button type="primary" onClick={() => setFilterDrawerVisible(false)}>
              Aplică
            </Button>
          </Space>
        }
      >
        <Form layout="vertical">
          <Form.Item label="Interval Stoc">
            <Slider
              range
              min={0}
              max={1000}
              value={stockRange}
              onChange={(value) => handleStockRangeChange(value as number[])}
              marks={{
                0: '0',
                250: '250',
                500: '500',
                750: '750',
                1000: '1000+'
              }}
            />
          </Form.Item>

          <Form.Item label="Perioada Actualizare">
            <DatePicker.RangePicker
              value={dateRange}
              onChange={handleDateRangeChange}
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item label="Branduri">
            <Select
              mode="multiple"
              placeholder="Selectează branduri"
              value={selectedBrands}
              onChange={handleBrandSelectionChange}
              style={{ width: '100%' }}
              options={summary.topBrands.map(brand => ({
                label: `${brand.brand} (${brand.count})`,
                value: brand.brand
              }))}
            />
          </Form.Item>

          <Form.Item label="Categorii">
            <Select
              mode="multiple"
              placeholder="Selectează categorii"
              value={selectedCategories}
              onChange={handleCategorySelectionChange}
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Divider />

          <Form.Item label="Opțiuni Avansate">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Switch
                checkedChildren="Cu imagini"
                unCheckedChildren="Fără imagini"
                checked={quickFilters.hasImages}
                onChange={(checked) => handleQuickFilterToggle('hasImages', checked)}
              />
              <Switch
                checkedChildren="Cu descriere"
                unCheckedChildren="Fără descriere"
                checked={quickFilters.hasDescription}
                onChange={(checked) => handleQuickFilterToggle('hasDescription', checked)}
              />
              <Switch
                checkedChildren="Stoc redus"
                unCheckedChildren="Stoc normal"
                checked={quickFilters.lowStock}
                onChange={(checked) => handleQuickFilterToggle('lowStock', checked)}
              />
            </Space>
          </Form.Item>
        </Form>
      </Drawer>

      {/* Save Preset Modal */}
      <Modal
        title="Salvează preset"
        open={presetModalVisible}
        onCancel={handlePresetModalCancel}
        onOk={handlePresetModalSave}
        okText="Salvează"
        cancelText="Renunță"
      >
        <Input
          value={presetName}
          onChange={(e) => setPresetName(e.target.value)}
          placeholder="Introduceți un nume pentru preset"
        />
      </Modal>

      {/* Product Detail Drawer */}
      <Drawer
        title={activeProduct ? activeProduct.name : 'Detalii produs'}
        placement="right"
        width={480}
        open={detailDrawerVisible}
        onClose={closeProductDetails}
      >
        {!activeProduct && <Empty description="Selectează un produs pentru a vedea detalii" />}
        {activeProduct && (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Space size={[8, 8]} wrap>
              <Tag color={activeProduct.status === 'active' ? 'green' : 'red'}>
                {activeProduct.status === 'active' ? 'Activ' : 'Inactiv'}
              </Tag>
              {activeProduct.is_available !== undefined && (
                <Tag color={activeProduct.is_available ? 'blue' : 'orange'}>
                  {activeProduct.is_available ? 'Disponibil' : 'Indisponibil'}
                </Tag>
              )}
              <Tag color={activeProduct.account_type === 'fbe' ? 'cyan' : 'geekblue'}>
                {(activeProduct.account_type || 'MAIN').toUpperCase()}
              </Tag>
            </Space>

            <Card size="small" variant="borderless" style={{ background: '#fafafa' }}>
              <Row gutter={16}>
                <Col span={12}>
                  <Statistic
                    title="Preț curent"
                    valueRender={() => (
                      <div style={{ fontSize: 18, fontWeight: 600, color: '#52c41a' }}>
                        {formatPrice(activeProduct.effective_price ?? activeProduct.sale_price ?? activeProduct.price, activeProduct.currency)}
                      </div>
                    )}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="Preț listă"
                    valueRender={() => (
                      <div>
                        {activeProduct.price ? formatPrice(activeProduct.price, activeProduct.currency) : 'N/A'}
                      </div>
                    )}
                  />
                </Col>
              </Row>
              {activeProduct.sale_price && activeProduct.price && activeProduct.price !== activeProduct.sale_price && (
                <div style={{ marginTop: 12 }}>
                  <Alert
                    message="Reducere activă"
                    description={`Reducere de ${((1 - (activeProduct.sale_price / activeProduct.price)) * 100).toFixed(1)}% față de prețul de listă`}
                    type="success"
                    showIcon
                  />
                </div>
              )}
            </Card>

            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="Brand">{activeProduct.brand || 'Nespecificat'}</Descriptions.Item>
              <Descriptions.Item label="Categorie">{activeProduct.category || 'Nespecificat'}</Descriptions.Item>
              <Descriptions.Item label="Part Number">{activeProduct.part_number || '-'}</Descriptions.Item>
              <Descriptions.Item label="Part Number Key">{activeProduct.part_number_key || '-'}</Descriptions.Item>
              <Descriptions.Item label="Monedă">{activeProduct.currency || 'RON'}</Descriptions.Item>
              <Descriptions.Item label="eMAG ID">{activeProduct.emag_id || '-'}</Descriptions.Item>
              <Descriptions.Item label="Stoc">
                <Space direction="vertical" size={4} style={{ width: '100%' }}>
                  <Tag color={activeProduct.stock > 0 ? 'green' : 'red'}>{activeProduct.stock} buc</Tag>
                  <Progress
                    percent={Math.min(100, Math.round((activeProduct.stock / 200) * 100))}
                    size="small"
                    status={activeProduct.stock === 0 ? 'exception' : activeProduct.stock < 20 ? 'active' : 'normal'}
                  />
                </Space>
              </Descriptions.Item>
            </Descriptions>

            <Card size="small" title="Cronologie" variant="outlined">
              <Timeline
                items={[
                  {
                    color: 'green',
                    children: (
                      <div>
                        <strong>Creat:</strong>{' '}
                        {activeProduct.created_at
                          ? new Date(activeProduct.created_at).toLocaleString('ro-RO')
                          : 'N/A'}
                      </div>
                    ),
                  },
                  {
                    color: 'blue',
                    children: (
                      <div>
                        <strong>Ultima actualizare:</strong>{' '}
                        {activeProduct.updated_at
                          ? new Date(activeProduct.updated_at).toLocaleString('ro-RO')
                          : 'N/A'}
                      </div>
                    ),
                  },
                ]}
              />
            </Card>
          </Space>
        )}
      </Drawer>

      {/* Export Modal */}
      <Modal
        title="Exportă Produse"
        open={exportModalVisible}
        onCancel={() => setExportModalVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setExportModalVisible(false)}>
            Anulează
          </Button>,
          <Button key="export" type="primary" icon={<DownloadOutlined />}>
            Exportă
          </Button>
        ]}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>Selectează formatul de export:</div>
          <Select defaultValue="excel" style={{ width: '100%' }}>
            <Select.Option value="excel">Excel (.xlsx)</Select.Option>
            <Select.Option value="csv">CSV (.csv)</Select.Option>
            <Select.Option value="json">JSON (.json)</Select.Option>
          </Select>
          <Checkbox>Include doar produsele selectate</Checkbox>
          <Checkbox>Include imagini</Checkbox>
          <Checkbox>Include descrieri complete</Checkbox>
        </Space>
      </Modal>

      {/* Import Modal */}
      <Modal
        title="Importă Produse"
        open={importModalVisible}
        onCancel={() => setImportModalVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setImportModalVisible(false)}>
            Anulează
          </Button>,
          <Button key="import" type="primary" icon={<UploadOutlined />}>
            Importă
          </Button>
        ]}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Alert
            message="Importă produse din fișiere Excel sau CSV"
            description="Asigură-te că fișierul respectă formatul standard pentru a evita erorile."
            type="info"
            showIcon
          />
          <Button icon={<UploadOutlined />} block>
            Selectează Fișier
          </Button>
          <Progress percent={0} status="active" />
        </Space>
      </Modal>
    </div>
  );
}
