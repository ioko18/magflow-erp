# Recreare Pagină Product Matching Suggestions - Versiune Îmbunătățită

## 📋 Descriere Generală

Această pagină este un instrument avansat pentru **matching automat între produsele furnizorilor (1688.com) și produsele locale din baza de date**. Utilizează algoritmi de similaritate bazați pe **tokenizare Jieba** pentru nume chinezești și oferă sugestii automate de potrivire.

## 🎯 Funcționalități Principale

### 1. **Afișare Produse Nematchate cu Sugestii**
- Listează produsele furnizorilor care nu au fost încă asociate cu produse locale
- Pentru fiecare produs furnizor, afișează sugestii automate de produse locale similare
- Sugestiile sunt ordonate descrescător după scorul de similaritate

### 2. **Sistem de Scoring și Confidence**
- **Scor de similaritate**: 0.00 - 1.00 (afișat ca procent)
- **Nivele de confidence**:
  - **Excelent** (≥95%): Verde închis (#52c41a)
  - **Foarte bun** (≥90%): Verde (#73d13d)
  - **Bun** (≥85%): Verde deschis (#95de64)
  - **Mediu** (<85%): Portocaliu (#faad14)

### 3. **Filtrare și Configurare**
- **Similaritate minimă**: Slider 50%-100% (default: 85%)
- **Număr maxim sugestii**: 1-10 per produs (default: 5)
- **Filtre rapide**:
  - Toate produsele
  - Doar cu sugestii
  - Doar fără sugestii
  - Doar cu scor >95% (high confidence)
- **Selector furnizor**: Dropdown pentru a selecta furnizorul dorit

### 4. **Acțiuni Disponibile**

#### A. Confirmare Match Individual
- Buton "Confirmă Match" pentru fiecare sugestie
- Creează asociere permanentă între produs furnizor și produs local
- Marchează match-ul ca `manual_confirmed: true`
- Setează `confidence_score: 1.0`

#### B. Eliminare Sugestie
- Buton "Elimină Sugestie" pentru fiecare sugestie
- Elimină permanent sugestia din baza de date
- Sugestia nu va mai reapărea în viitor
- Optimistic update în UI

#### C. Confirmare Bulk (Automată)
- Buton "Confirmă Automat (N)" în header
- Confirmă automat toate produsele cu scor >95%
- Cere confirmare utilizator înainte de execuție
- Afișează progres și rezultate (succes/erori)

#### D. Actualizare Preț Inline
- InputNumber editabil direct în tabel
- Update la blur sau Enter
- Actualizare optimistă în UI
- Salvare în baza de date via PATCH endpoint

### 5. **Statistici în Timp Real**
- **Total produse**: Număr total produse nematchate
- **Cu sugestii**: Câte produse au cel puțin o sugestie
- **Fără sugestii**: Câte produse nu au sugestii
- **Scor >95%**: Câte produse au best match >95%
- **Scor mediu**: Media scorurilor best match

## 🔧 Structura Tehnică

### Interfețe TypeScript

```typescript
interface LocalProductSuggestion {
  local_product_id: number;
  local_product_name: string;
  local_product_chinese_name?: string;
  local_product_sku: string;
  local_product_brand?: string;
  local_product_image_url?: string;
  similarity_score: number;          // 0.00 - 1.00
  similarity_percent: number;        // 0 - 100
  common_tokens: string[];           // Tokeni comuni găsiți
  common_tokens_count: number;       // Număr tokeni comuni
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
  best_match_score: number;          // Cel mai mare scor din sugestii
}
```

### State Management

```typescript
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
const [filterType, setFilterType] = useState<'all' | 'with-suggestions' | 'without-suggestions' | 'high-score'>('all');
const [statistics, setStatistics] = useState({
  total: 0,
  withSuggestions: 0,
  withoutSuggestions: 0,
  averageScore: 0,
  highScoreCount: 0,
});
const [editingPrice, setEditingPrice] = useState<{ [key: number]: number }>({});
```

## 🌐 API Endpoints

### 1. GET `/suppliers`
**Scop**: Încarcă lista de furnizori

**Response**:
```json
{
  "status": "success",
  "data": {
    "suppliers": [
      { "id": 1, "name": "Furnizor 1" },
      { "id": 2, "name": "Furnizor 2" }
    ]
  }
}
```

### 2. GET `/suppliers/{supplier_id}/products/unmatched-with-suggestions`
**Scop**: Încarcă produsele nematchate cu sugestii automate

**Query Parameters**:
- `skip`: Offset pentru paginare (default: 0)
- `limit`: Număr produse per pagină (default: 20, max: 50)
- `min_similarity`: Scor minim similaritate (default: 0.85)
- `max_suggestions`: Număr maxim sugestii per produs (default: 5)

**Response**:
```json
{
  "status": "success",
  "data": {
    "products": [
      {
        "id": 123,
        "supplier_id": 1,
        "supplier_name": "Furnizor Test",
        "supplier_product_name": "Product Name",
        "supplier_product_chinese_name": "产品名称",
        "supplier_product_url": "https://detail.1688.com/...",
        "supplier_image_url": "https://...",
        "supplier_price": 25.50,
        "supplier_currency": "CNY",
        "suggestions": [
          {
            "local_product_id": 456,
            "local_product_name": "Local Product",
            "local_product_chinese_name": "本地产品",
            "local_product_sku": "SKU123",
            "similarity_score": 0.95,
            "similarity_percent": 95,
            "common_tokens": ["token1", "token2"],
            "common_tokens_count": 2
          }
        ],
        "suggestions_count": 1,
        "best_match_score": 0.95
      }
    ],
    "pagination": {
      "total": 150,
      "skip": 0,
      "limit": 20
    }
  }
}
```

### 3. POST `/suppliers/{supplier_id}/products/{product_id}/match`
**Scop**: Confirmă match între produs furnizor și produs local

**Body**:
```json
{
  "local_product_id": 456,
  "confidence_score": 1.0,
  "manual_confirmed": true
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Match confirmed successfully"
}
```

### 4. DELETE `/suppliers/{supplier_id}/products/{product_id}/suggestions/{local_product_id}`
**Scop**: Elimină permanent o sugestie

**Response**:
```json
{
  "status": "success",
  "message": "Suggestion removed permanently"
}
```

### 5. PATCH `/suppliers/{supplier_id}/products/{product_id}`
**Scop**: Actualizează prețul produsului furnizor

**Body**:
```json
{
  "supplier_price": 30.00
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Price updated successfully"
}
```

## 🎨 Design și UI/UX

### Layout Principal
1. **Header**:
   - Titlu cu icon SyncOutlined
   - Descriere scurtă cu pragul de similaritate
   - Selector furnizor (dropdown)
   - Butoane: "Confirmă Automat (N)" și "Reîmprospătează"

2. **Card Statistici**:
   - 5 statistici în Row cu Col span={4-5}
   - Culori diferite pentru fiecare statistică
   - Icoane relevante (SyncOutlined, FireOutlined)

3. **Card Filtre**:
   - InputNumber pentru similaritate minimă (50%-100%)
   - InputNumber pentru număr maxim sugestii (1-10)
   - Butoane filtrare rapidă (Toate, Cu sugestii, Fără sugestii, Scor >95%)
   - Alert informativ când filtrarea este activă

4. **Tabel Principal**:
   - 3 coloane: Imagine Furnizor, Produs Furnizor, Sugestii Auto-Match
   - Paginare cu showSizeChanger (10, 20, 30, 50)
   - Loading state
   - Empty state când nu e selectat furnizor

### Componente Sugestii

Fiecare sugestie este afișată într-un **Card** cu:
- **Border stânga colorat** după scor (4px solid)
- **Layout Row cu 4 coloane**:
  1. **Col span={3}**: Imagine produs local (60x60px)
  2. **Col span={13}**: Detalii produs (nume, nume chinezesc, SKU, brand, tokeni comuni)
  3. **Col span={4}**: Scor mare (20px bold) + Tag confidence
  4. **Col span={4}**: Butoane acțiune (Confirmă Match, Elimină Sugestie)

### Culori și Teme
- **Verde închis** (#52c41a): Excelent (≥95%)
- **Verde** (#73d13d): Foarte bun (≥90%)
- **Verde deschis** (#95de64): Bun (≥85%)
- **Portocaliu** (#faad14): Mediu (<85%)
- **Albastru** (#1890ff): Acțiuni primare
- **Roșu** (#ff4d4f): Acțiuni destructive

## ⚡ Îmbunătățiri Recomandate pentru Versiunea Nouă

### 1. **Performance**
- [ ] Implementare **React.memo** pentru componente sugestii
- [ ] **Virtualizare tabel** pentru liste mari (react-window sau antd virtual scroll)
- [ ] **Debounce** pentru InputNumber-uri (300ms)
- [ ] **Lazy loading** pentru imagini cu IntersectionObserver
- [ ] **Caching** cu React Query sau SWR pentru requests

### 2. **Funcționalități Noi**
- [ ] **Bulk selection**: Checkbox pentru selectare multiplă
- [ ] **Bulk actions**: Confirmă/Elimină multiple sugestii simultan
- [ ] **Export CSV**: Export produse cu sugestii
- [ ] **Filtrare avansată**: Filtrare după brand, preț, SKU
- [ ] **Sortare**: Sortare după scor, preț, dată
- [ ] **Search**: Căutare în nume produse (chinezesc + englez)
- [ ] **History**: Log acțiuni utilizator (match confirmat, sugestie eliminată)
- [ ] **Undo**: Posibilitate de a anula ultima acțiune

### 3. **UX Improvements**
- [ ] **Skeleton loading**: În loc de spinner generic
- [ ] **Toast notifications**: În loc de message.success/error
- [ ] **Keyboard shortcuts**: Enter pentru confirm, Esc pentru cancel
- [ ] **Drag & drop**: Reordonare sugestii manual
- [ ] **Preview modal**: Modal cu detalii complete produs la click pe imagine
- [ ] **Comparison view**: Compară side-by-side produs furnizor vs produs local
- [ ] **Confidence explanation**: Tooltip cu explicație scor similaritate
- [ ] **Progress indicator**: Pentru bulk operations

### 4. **Validări și Error Handling**
- [ ] **Retry logic**: Retry automat pentru failed requests (3 încercări)
- [ ] **Error boundaries**: Catch errors la nivel de componentă
- [ ] **Validation**: Validare preț (min 0, max 999999)
- [ ] **Confirmation modals**: Pentru acțiuni destructive
- [ ] **Optimistic updates**: Cu rollback pe eroare
- [ ] **Network status**: Indicator conexiune internet

### 5. **Accessibility**
- [ ] **ARIA labels**: Pentru screen readers
- [ ] **Keyboard navigation**: Tab, Enter, Esc
- [ ] **Focus management**: Focus pe primul element după acțiune
- [ ] **Color contrast**: WCAG AA compliance
- [ ] **Alt text**: Pentru toate imaginile

### 6. **Code Quality**
- [ ] **TypeScript strict mode**: Activare strict mode
- [ ] **Custom hooks**: Extrage logică în hooks reutilizabile
  - `useProductMatching`
  - `useSuppliers`
  - `usePagination`
  - `useStatistics`
- [ ] **Error types**: Tipuri custom pentru erori
- [ ] **Constants**: Extrage magic numbers în constante
- [ ] **Unit tests**: Jest + React Testing Library
- [ ] **E2E tests**: Playwright sau Cypress

### 7. **Backend Improvements Necesare**
- [ ] **Server-side filtering**: Filtrare în backend, nu în frontend
- [ ] **Server-side sorting**: Sortare în backend
- [ ] **Bulk endpoints**: Endpoint pentru bulk confirm/delete
- [ ] **WebSocket**: Real-time updates pentru bulk operations
- [ ] **Rate limiting**: Protecție împotriva spam-ului
- [ ] **Caching**: Redis cache pentru sugestii

## 📦 Dependențe Necesare

```json
{
  "dependencies": {
    "react": "^18.x",
    "antd": "^5.x",
    "@ant-design/icons": "^5.x",
    "axios": "^1.x"
  },
  "devDependencies": {
    "@types/react": "^18.x",
    "typescript": "^5.x"
  }
}
```

## 🔄 Flow-uri Principale

### Flow 1: Confirmare Match Individual
1. User click "Confirmă Match" pe o sugestie
2. Call API POST `/suppliers/{id}/products/{id}/match`
3. Success → message.success + refresh lista
4. Error → message.error + log error

### Flow 2: Eliminare Sugestie
1. User click "Elimină Sugestie"
2. Optimistic update: Remove din UI imediat
3. Call API DELETE `/suppliers/{id}/products/{id}/suggestions/{id}`
4. Success → message.success
5. Error → message.error + rollback (refresh lista)

### Flow 3: Confirmare Bulk
1. User click "Confirmă Automat (N)"
2. Modal.confirm cu număr produse
3. User confirmă
4. Loop prin toate produsele cu scor >95%
5. Pentru fiecare: Call API POST match
6. Afișează progres (successCount, errorCount)
7. Refresh lista la final

### Flow 4: Actualizare Preț
1. User editează preț în InputNumber
2. User apasă Enter sau blur
3. Check dacă prețul s-a schimbat
4. Call API PATCH `/suppliers/{id}/products/{id}`
5. Success → update local state + message.success
6. Error → message.error + revert la preț vechi

### Flow 5: Schimbare Furnizor
1. User selectează furnizor din dropdown
2. Reset pagination la pagina 1
3. Fetch produse pentru noul furnizor
4. Recalculează statistici

## 🐛 Bug-uri Cunoscute și Soluții

### Bug 1: Filtrarea se aplică doar pe pagina curentă
**Problemă**: Filtrele (cu/fără sugestii, scor >95%) funcționează doar pe produsele din pagina curentă.

**Soluție**: Implementare filtrare server-side:
- Adaugă parametri `filter_type` în API request
- Backend filtrează înainte de paginare
- Frontend primește doar produsele filtrate

### Bug 2: Statistics nu reflectă filtrarea
**Problemă**: Statisticile afișează totalul, nu produsele filtrate.

**Soluție**: 
- Calculează statistici separate pentru filtered products
- Afișează ambele seturi de statistici (total vs filtered)

### Bug 3: Race condition la schimbare rapidă furnizor
**Problemă**: Dacă user schimbă rapid furnizorul, pot apărea date inconsistente.

**Soluție**:
- Folosește AbortController pentru a anula request-uri în curs
- Verifică că supplierId din response match-uiește cu cel curent

### Bug 4: Memory leak la unmount
**Problemă**: State updates după unmount.

**Soluție**:
- Cleanup în useEffect cu return function
- Check isMounted flag înainte de setState

## 📝 Exemple de Cod Îmbunătățit

### Custom Hook: useProductMatching

```typescript
import { useState, useCallback, useRef, useEffect } from 'react';
import api from '../services/api';

interface UseProductMatchingOptions {
  supplierId: number | null;
  minSimilarity: number;
  maxSuggestions: number;
  pageSize: number;
}

export const useProductMatching = (options: UseProductMatchingOptions) => {
  const [products, setProducts] = useState<SupplierProductWithSuggestions[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [pagination, setPagination] = useState({ current: 1, total: 0 });
  const abortControllerRef = useRef<AbortController | null>(null);
  const isMountedRef = useRef(true);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      abortControllerRef.current?.abort();
    };
  }, []);

  const fetchProducts = useCallback(async (page: number = 1) => {
    if (!options.supplierId) return;

    // Cancel previous request
    abortControllerRef.current?.abort();
    abortControllerRef.current = new AbortController();

    setLoading(true);
    setError(null);

    try {
      const skip = (page - 1) * options.pageSize;
      const response = await api.get(
        `/suppliers/${options.supplierId}/products/unmatched-with-suggestions`,
        {
          params: {
            skip,
            limit: options.pageSize,
            min_similarity: options.minSimilarity,
            max_suggestions: options.maxSuggestions,
          },
          signal: abortControllerRef.current.signal,
        }
      );

      if (!isMountedRef.current) return;

      if (response.data.status === 'success') {
        setProducts(response.data.data.products);
        setPagination({
          current: page,
          total: response.data.data.pagination.total,
        });
      }
    } catch (err) {
      if (!isMountedRef.current) return;
      if (err.name === 'AbortError') return;
      
      setError(err as Error);
      console.error('Error fetching products:', err);
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  }, [options.supplierId, options.minSimilarity, options.maxSuggestions, options.pageSize]);

  const confirmMatch = useCallback(async (
    supplierProductId: number,
    localProductId: number
  ) => {
    try {
      await api.post(
        `/suppliers/${options.supplierId}/products/${supplierProductId}/match`,
        {
          local_product_id: localProductId,
          confidence_score: 1.0,
          manual_confirmed: true,
        }
      );
      return { success: true };
    } catch (err) {
      return { success: false, error: err };
    }
  }, [options.supplierId]);

  const removeSuggestion = useCallback(async (
    supplierProductId: number,
    localProductId: number
  ) => {
    // Optimistic update
    setProducts((prev) =>
      prev.map((p) => {
        if (p.id === supplierProductId) {
          const updatedSuggestions = p.suggestions.filter(
            (s) => s.local_product_id !== localProductId
          );
          return {
            ...p,
            suggestions: updatedSuggestions,
            suggestions_count: updatedSuggestions.length,
            best_match_score: updatedSuggestions.length > 0 
              ? updatedSuggestions[0].similarity_score 
              : 0,
          };
        }
        return p;
      })
    );

    try {
      await api.delete(
        `/suppliers/${options.supplierId}/products/${supplierProductId}/suggestions/${localProductId}`
      );
      return { success: true };
    } catch (err) {
      // Rollback on error
      await fetchProducts(pagination.current);
      return { success: false, error: err };
    }
  }, [options.supplierId, pagination.current, fetchProducts]);

  return {
    products,
    loading,
    error,
    pagination,
    fetchProducts,
    confirmMatch,
    removeSuggestion,
  };
};
```

### Componenta Sugestie Optimizată

```typescript
import React, { memo } from 'react';
import { Card, Row, Col, Image, Typography, Tag, Button, Space } from 'antd';
import { CheckCircleOutlined, CloseOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface SuggestionCardProps {
  suggestion: LocalProductSuggestion;
  onConfirm: () => void;
  onRemove: () => void;
  loading?: boolean;
}

export const SuggestionCard = memo<SuggestionCardProps>(({
  suggestion,
  onConfirm,
  onRemove,
  loading = false,
}) => {
  const getConfidenceColor = (score: number) => {
    if (score >= 0.95) return '#52c41a';
    if (score >= 0.90) return '#73d13d';
    if (score >= 0.85) return '#95de64';
    return '#faad14';
  };

  const getConfidenceLabel = (score: number) => {
    if (score >= 0.95) return 'Excelent';
    if (score >= 0.90) return 'Foarte bun';
    if (score >= 0.85) return 'Bun';
    return 'Mediu';
  };

  return (
    <Card
      size="small"
      style={{
        borderLeft: `4px solid ${getConfidenceColor(suggestion.similarity_score)}`,
      }}
    >
      <Row gutter={16} align="middle">
        <Col span={3}>
          <Image
            src={suggestion.local_product_image_url}
            alt={suggestion.local_product_name}
            width={60}
            height={60}
            style={{ objectFit: 'cover', borderRadius: '4px' }}
            fallback="/placeholder-product.png"
            placeholder={
              <div style={{ width: 60, height: 60, background: '#f0f0f0' }} />
            }
          />
        </Col>
        <Col span={13}>
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
            Tokeni: {suggestion.common_tokens.slice(0, 5).join(', ')}
            {suggestion.common_tokens.length > 5 && '...'}
          </div>
        </Col>
        <Col span={4} style={{ textAlign: 'center' }}>
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
        </Col>
        <Col span={4} style={{ textAlign: 'right' }}>
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            <Button
              type="primary"
              icon={<CheckCircleOutlined />}
              onClick={onConfirm}
              size="small"
              block
              loading={loading}
            >
              Confirmă
            </Button>
            <Button
              danger
              icon={<CloseOutlined />}
              onClick={onRemove}
              size="small"
              block
              loading={loading}
            >
              Elimină
            </Button>
          </Space>
        </Col>
      </Row>
    </Card>
  );
});

SuggestionCard.displayName = 'SuggestionCard';
```

## 🚀 Plan de Implementare

### Faza 1: Setup și Structură (30 min)
1. Creează fișierul `ProductMatchingSuggestions.tsx`
2. Setup interfețe TypeScript
3. Setup state management
4. Implementare layout de bază

### Faza 2: API Integration (45 min)
1. Implementare fetchSuppliers
2. Implementare fetchProducts cu paginare
3. Implementare confirmMatch
4. Implementare removeSuggestion
5. Implementare updatePrice
6. Error handling și retry logic

### Faza 3: UI Components (1h)
1. Header cu statistici
2. Filtre și configurare
3. Tabel principal
4. Componente sugestii
5. Empty states și loading states

### Faza 4: Funcționalități Avansate (1h)
1. Bulk confirm
2. Inline price editing
3. Filtrare client-side
4. Calculare statistici
5. Optimistic updates

### Faza 5: Polish și Testing (45 min)
1. Responsive design
2. Accessibility
3. Error boundaries
4. Performance optimization
5. Manual testing

### Faza 6: Îmbunătățiri (opțional)
1. Custom hooks
2. Memoization
3. Virtual scrolling
4. Advanced filtering
5. Unit tests

## 📚 Resurse și Referințe

- **Ant Design Table**: https://ant.design/components/table
- **Ant Design Form**: https://ant.design/components/form
- **React Performance**: https://react.dev/learn/render-and-commit
- **TypeScript Best Practices**: https://typescript-eslint.io/
- **Jieba Tokenization**: https://github.com/fxsjy/jieba

## ✅ Checklist Final

- [ ] Toate interfețele TypeScript definite corect
- [ ] Toate API endpoints implementate
- [ ] Error handling complet
- [ ] Loading states pentru toate acțiunile
- [ ] Optimistic updates pentru acțiuni rapide
- [ ] Validare input-uri
- [ ] Responsive design (desktop + tablet)
- [ ] Accessibility (ARIA labels, keyboard nav)
- [ ] Performance optimization (memo, useMemo, useCallback)
- [ ] Empty states și fallback images
- [ ] Confirmation modals pentru acțiuni destructive
- [ ] Toast notifications pentru feedback
- [ ] Documentație inline (comments)
- [ ] Unit tests (opțional)
- [ ] E2E tests (opțional)

---

**Notă**: Această pagină este critică pentru workflow-ul de matching produse. Asigură-te că toate funcționalitățile sunt testate temeinic înainte de deployment în producție.

**Versiune document**: 1.0  
**Data**: 21 Octombrie 2025  
**Autor**: MagFlow ERP Team
