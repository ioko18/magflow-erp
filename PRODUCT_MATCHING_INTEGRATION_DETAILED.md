# 🔧 Ghid Integrare Detaliată: Custom Hooks

## 📋 Status

- ✅ Imports adăugate
- ⏳ State management de înlocuit
- ⏳ Funcții de simplificat
- ⏳ renderSuggestions de actualizat
- ⏳ Testing

---

## 🎯 Pași Integrare

### STEP 1: Înlocuiți State Management (Liniile 66-87)

**ÎNAINTE** (Liniile 66-87):
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
const [loadingSuppliers, setLoadingSuppliers] = useState(false);
const [filterType, setFilterType] = useState<'all' | 'with-suggestions' | 'without-suggestions' | 'high-score'>('all');
const [statistics, setStatistics] = useState({...});
const [editingPrice, setEditingPrice] = useState<{ [key: number]: number }>({});
```

**DUPĂ** (Înlocuiți cu):
```typescript
const [minSimilarity, setMinSimilarity] = useState(0.85);
const [maxSuggestions, setMaxSuggestions] = useState(5);
const [supplierId, setSupplierId] = useState<number | null>(null);
const [filterType, setFilterType] = useState<'all' | 'with-suggestions' | 'without-suggestions' | 'high-score'>('all');
const [statistics, setStatistics] = useState({
  total: 0,
  withSuggestions: 0,
  withoutSuggestions: 0,
  averageScore: 0,
  highScoreCount: 0,
});
const [editingPrice, setEditingPrice] = useState<{ [key: number]: number }>({});

// Custom hooks
const { suppliers, loading: loadingSuppliers } = useSuppliers();
const { 
  products, 
  loading, 
  pagination, 
  fetchProducts, 
  confirmMatch, 
  removeSuggestion, 
  updatePrice 
} = useProductMatching({
  supplierId,
  minSimilarity,
  maxSuggestions,
  pageSize: pagination?.pageSize || 20,
  filterType,
});
```

---

### STEP 2: Eliminați Funcții Vechi (Liniile 88-117)

**ELIMINAȚI**:
```typescript
const fetchSuppliers = useCallback(async () => {
  // ... entire function
}, []);
```

**MOTIVAȚIE**: Hook-ul `useSuppliers` se ocupă de asta

---

### STEP 3: Simplificați handleMatch (Liniile 179-193)

**ÎNAINTE**:
```typescript
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
```

**DUPĂ**:
```typescript
const handleMatch = async (supplierProductId: number, localProductId: number) => {
  const result = await confirmMatch(supplierProductId, localProductId);
  if (result.success) {
    message.success('Match confirmat cu succes!');
    await fetchProducts();
  } else {
    message.error('Eroare la confirmarea match-ului');
    console.error('Error confirming match:', result.error);
  }
};
```

---

### STEP 4: Simplificați handleRemoveSuggestion (Liniile 222-254)

**ÎNAINTE**:
```typescript
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
```

**DUPĂ**:
```typescript
const handleRemoveSuggestion = async (supplierProductId: number, localProductId: number) => {
  const result = await removeSuggestion(supplierProductId, localProductId);
  if (result.success) {
    message.success('Sugestie eliminată permanent! Nu va mai reapărea.');
  } else {
    message.error('Eroare la eliminarea sugestiei');
    console.error('Error removing suggestion:', result.error);
  }
};
```

---

### STEP 5: Simplificați handlePriceUpdate (Liniile 195-220)

**ÎNAINTE**:
```typescript
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
```

**DUPĂ**:
```typescript
const handlePriceUpdate = async (supplierProductId: number, newPrice: number) => {
  const result = await updatePrice(supplierProductId, newPrice);
  if (result.success) {
    message.success('Preț actualizat cu succes!');
    
    // Clear editing state
    setEditingPrice((prev) => {
      const newState = { ...prev };
      delete newState[supplierProductId];
      return newState;
    });
  } else {
    message.error('Eroare la actualizarea prețului');
    console.error('Error updating price:', result.error);
  }
};
```

---

### STEP 6: Actualizați renderSuggestions (Liniile 315-449)

**ÎNLOCUIȚI FUNCȚIA COMPLETĂ CU**:
```typescript
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
        <div key={suggestion.local_product_id} style={{ marginBottom: index < record.suggestions.length - 1 ? '8px' : 0 }}>
          <SuggestionCard
            suggestion={suggestion}
            onConfirm={() => handleMatch(record.id, suggestion.local_product_id)}
            onRemove={() => handleRemoveSuggestion(record.id, suggestion.local_product_id)}
          />
        </div>
      ))}
    </div>
  );
};
```

---

### STEP 7: Actualizați useEffect (Liniile 171-177)

**ÎNAINTE**:
```typescript
useEffect(() => {
  fetchSuppliers();
}, [fetchSuppliers]);

useEffect(() => {
  fetchProducts();
}, [fetchProducts]);
```

**DUPĂ**:
```typescript
useEffect(() => {
  fetchProducts();
}, [fetchProducts]);
```

---

### STEP 8: Actualizați handleBulkConfirm (Liniile 256-299)

**MODIFICARE MICĂ** (Linia 284):
```typescript
// ÎNAINTE:
await handleMatch(product.id, product.suggestions[0].local_product_id);

// DUPĂ:
const result = await confirmMatch(product.id, product.suggestions[0].local_product_id);
if (!result.success) throw new Error('Match failed');
```

---

## ✅ Checklist Integrare

- [ ] STEP 1: State management înlocuit
- [ ] STEP 2: fetchSuppliers eliminat
- [ ] STEP 3: handleMatch simplificat
- [ ] STEP 4: handleRemoveSuggestion simplificat
- [ ] STEP 5: handlePriceUpdate simplificat
- [ ] STEP 6: renderSuggestions actualizat
- [ ] STEP 7: useEffect actualizat
- [ ] STEP 8: handleBulkConfirm actualizat
- [ ] TypeScript: Fără erori
- [ ] Console: Fără erori
- [ ] Testing: Funcționalități funcționează

---

## 🧪 Testing Post-Integrare

### Funcționalități de Testat
- [ ] Pagina se încarcă
- [ ] Furnizori se populează
- [ ] Produse se încarcă
- [ ] Filtrele funcționează
- [ ] Confirmare match funcționează
- [ ] Eliminare sugestie funcționează
- [ ] Editare preț funcționează
- [ ] Confirmare bulk funcționează
- [ ] Paginare funcționează

### Performance
- [ ] No memory leaks
- [ ] No console errors
- [ ] Smooth scrolling
- [ ] Fast load time

---

## 📊 Rezultat Așteptat

### Înainte
- 781 linii în componenta principală
- State management complex
- Logică duplicată

### După
- ~400 linii în componenta principală (50% reducere)
- State management simplificat
- Logică centralizată în hooks
- Better performance
- Better maintainability

---

## 🚀 Ready?

**Urmărește pașii de mai sus și integrează hooks!**

**Estimated Time**: 1-2 ore

**After Integration**: Rulează testing și deployment

---

**Versiune**: 1.0  
**Data**: 2025-10-22  
**Status**: ✅ DETAILED GUIDE READY

**Let's integrate! 🚀**
