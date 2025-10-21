# Ghid Complet: Persistență Eliminare Sugestii

**Data**: 21 Octombrie 2025, 17:45 UTC+03:00  
**Status**: 📋 GHID IMPLEMENTARE

---

## 🎯 OBIECTIV

Salvare sugestiilor eliminate în backend pentru a nu reapărea după refresh sau re-generare.

---

## ✅ PAȘI COMPLETAȚI (Implementați)

### 1. ✅ Migrare Database

**Fișier**: `/alembic/versions/20251021_add_eliminated_suggestions.py`

**Tabel creat**: `eliminated_suggestions`
```sql
CREATE TABLE eliminated_suggestions (
    id SERIAL PRIMARY KEY,
    supplier_product_id INTEGER NOT NULL REFERENCES supplier_products(id) ON DELETE CASCADE,
    local_product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    eliminated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    eliminated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    reason VARCHAR(500),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(supplier_product_id, local_product_id)
);

CREATE INDEX ix_eliminated_suggestions_supplier_product_id ON eliminated_suggestions(supplier_product_id);
CREATE INDEX ix_eliminated_suggestions_local_product_id ON eliminated_suggestions(local_product_id);
CREATE INDEX ix_eliminated_suggestions_eliminated_at ON eliminated_suggestions(eliminated_at);
```

**Rulare migrare**:
```bash
cd /Users/macos/anaconda3/envs/MagFlow
alembic upgrade head
```

---

### 2. ✅ Model SQLAlchemy

**Fișier**: `/app/models/eliminated_suggestion.py`

Model complet cu relationships către:
- `SupplierProduct` (supplier_product)
- `Product` (local_product)
- `User` (eliminated_by_user)

---

### 3. ✅ Update Models

**Modificări**:
- `/app/models/__init__.py` - Adăugat import și în liste
- `/app/models/supplier.py` - Adăugat relationship `eliminated_suggestions`
- `/app/models/product.py` - Adăugat relationship `eliminated_suggestions`
- `/app/api/v1/endpoints/suppliers/suppliers.py` - Adăugat import

---

## 🔄 PAȘI URMĂTORI (De implementat)

### 4. 📝 Endpoint API pentru Eliminare

**Locație**: `/app/api/v1/endpoints/suppliers/suppliers.py`

**Adaugă la sfârșitul fișierului**:

```python
@router.delete("/{supplier_id}/products/{product_id}/suggestions/{local_product_id}")
async def eliminate_suggestion(
    supplier_id: int,
    product_id: int,
    local_product_id: int,
    reason: str | None = Query(None, max_length=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Eliminate a product suggestion to prevent it from reappearing.
    
    This creates a record in eliminated_suggestions table that will be
    used to filter out this suggestion in future matching operations.
    """
    try:
        # Verify supplier product exists
        sp_query = select(SupplierProduct).where(
            and_(
                SupplierProduct.id == product_id,
                SupplierProduct.supplier_id == supplier_id
            )
        )
        sp_result = await db.execute(sp_query)
        supplier_product = sp_result.scalar_one_or_none()
        
        if not supplier_product:
            raise HTTPException(status_code=404, detail="Supplier product not found")
        
        # Verify local product exists
        lp_query = select(Product).where(Product.id == local_product_id)
        lp_result = await db.execute(lp_query)
        local_product = lp_result.scalar_one_or_none()
        
        if not local_product:
            raise HTTPException(status_code=404, detail="Local product not found")
        
        # Check if already eliminated
        check_query = select(EliminatedSuggestion).where(
            and_(
                EliminatedSuggestion.supplier_product_id == product_id,
                EliminatedSuggestion.local_product_id == local_product_id
            )
        )
        check_result = await db.execute(check_query)
        existing = check_result.scalar_one_or_none()
        
        if existing:
            return {
                "status": "success",
                "data": {
                    "message": "Suggestion already eliminated",
                    "eliminated_at": existing.eliminated_at.isoformat(),
                },
            }
        
        # Create elimination record
        elimination = EliminatedSuggestion(
            supplier_product_id=product_id,
            local_product_id=local_product_id,
            eliminated_by=current_user.id,
            reason=reason,
        )
        
        db.add(elimination)
        await db.commit()
        await db.refresh(elimination)
        
        logger.info(
            f"User {current_user.id} eliminated suggestion: "
            f"supplier_product={product_id}, local_product={local_product_id}"
        )
        
        return {
            "status": "success",
            "data": {
                "message": "Suggestion eliminated successfully",
                "id": elimination.id,
                "eliminated_at": elimination.eliminated_at.isoformat(),
            },
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminating suggestion: {e}")
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
```

---

### 5. 🔍 Modificare JiebaMatchingService

**Locație**: `/app/services/jieba_matching_service.py`

**Găsește metoda** `find_matches_for_supplier_product` și modifică-o:

```python
async def find_matches_for_supplier_product(
    self,
    supplier_product_id: int,
    threshold: float = 0.85,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Find matching local products for a supplier product."""
    
    # ... cod existent ...
    
    # ADAUGĂ DUPĂ GĂSIREA MATCH-URILOR:
    
    # Filter out eliminated suggestions
    eliminated_query = select(EliminatedSuggestion.local_product_id).where(
        EliminatedSuggestion.supplier_product_id == supplier_product_id
    )
    eliminated_result = await self.db.execute(eliminated_query)
    eliminated_ids = {row[0] for row in eliminated_result.fetchall()}
    
    # Filter matches
    filtered_matches = [
        match for match in matches
        if match["local_product_id"] not in eliminated_ids
    ]
    
    return filtered_matches[:limit]
```

**Nu uita să adaugi import**:
```python
from app.models.eliminated_suggestion import EliminatedSuggestion
```

---

### 6. 🎨 Update Frontend

**Locație**: `/admin-frontend/src/pages/products/ProductMatchingSuggestions.tsx`

**Modifică funcția** `handleRemoveSuggestion`:

```tsx
const handleRemoveSuggestion = async (supplierProductId: number, localProductId: number) => {
  try {
    // Call API to persist elimination
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
            best_match_score: updatedSuggestions.length > 0 
              ? updatedSuggestions[0].similarity_score 
              : 0,
          };
        }
        return p;
      })
    );

    message.success('Sugestie eliminată cu succes și salvată în sistem!');
  } catch (error) {
    message.error('Eroare la eliminarea sugestiei');
    console.error('Error removing suggestion:', error);
    // Revert on error
    fetchProducts();
  }
};
```

---

## 🧪 TESTARE

### Test 1: Eliminare Sugestie

```bash
# 1. Rulează migrarea
alembic upgrade head

# 2. Restart backend
docker-compose restart app

# 3. În frontend:
# - Accesează Product Matching
# - Găsește produs cu sugestii
# - Click "Elimină Sugestie"
# - Verifică mesaj succes

# 4. Verifică în database:
docker exec -it magflow_db psql -U postgres -d magflow -c "SELECT * FROM eliminated_suggestions;"
```

### Test 2: Sugestia Nu Reapare

```bash
# 1. După eliminare, refresh pagina
# 2. Verifică că sugestia eliminată NU apare
# 3. Navigează la altă pagină și revino
# 4. Verifică că sugestia NU reapare
```

### Test 3: Eliminare Duplicată

```bash
# 1. Elimină aceeași sugestie de 2 ori
# 2. Verifică că a doua eliminare returnează "already eliminated"
# 3. Verifică că există doar 1 record în database
```

---

## 📋 CHECKLIST IMPLEMENTARE

### Backend
- [x] Migrare Alembic creată
- [x] Model EliminatedSuggestion creat
- [x] Relationships adăugate în modele
- [x] Import în __init__.py
- [ ] Endpoint DELETE creat
- [ ] JiebaMatchingService modificat
- [ ] Testare backend

### Frontend
- [x] Buton "Elimină Sugestie" existent
- [x] Funcție handleRemoveSuggestion existentă
- [ ] API call adăugat în handleRemoveSuggestion
- [ ] Testare frontend

### Database
- [ ] Migrare rulată: `alembic upgrade head`
- [ ] Tabel verificat în database
- [ ] Indexuri verificate

### Testing
- [ ] Test eliminare sugestie
- [ ] Test sugestia nu reapare
- [ ] Test eliminare duplicată
- [ ] Test performance

---

## 🚀 COMENZI RAPIDE

### Rulare Migrare
```bash
cd /Users/macos/anaconda3/envs/MagFlow
alembic upgrade head
```

### Restart Backend
```bash
docker-compose restart app
```

### Verificare Tabel
```bash
docker exec -it magflow_db psql -U postgres -d magflow -c "\d eliminated_suggestions"
```

### Verificare Date
```bash
docker exec -it magflow_db psql -U postgres -d magflow -c "SELECT * FROM eliminated_suggestions;"
```

---

## 📝 NOTIȚE

1. **Unique Constraint**: Previne eliminarea duplicată a aceleiași sugestii
2. **CASCADE DELETE**: Când se șterge un produs, se șterg și eliminările
3. **Index pe eliminated_at**: Pentru queries de audit
4. **Reason opțional**: Utilizatorul poate adăuga motiv eliminare

---

## 🎯 URMĂTORII PAȘI

1. **Implementează endpoint-ul DELETE** (Pasul 4)
2. **Modifică JiebaMatchingService** (Pasul 5)
3. **Update frontend API call** (Pasul 6)
4. **Rulează migrarea**: `alembic upgrade head`
5. **Testează funcționalitatea**

---

**Implementare parțială completată! Urmează pașii 4-6 pentru funcționalitate completă.**
