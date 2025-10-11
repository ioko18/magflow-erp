# ⚡ Purchase Orders - Quick Start Guide

## 🚀 Start în 5 Minute!

Acest ghid te ajută să pornești rapid sistemul Purchase Orders.

---

## ✅ Prerequisite (Verificare Rapidă)

```bash
# 1. Verifică că backend-ul rulează
curl http://localhost:8000/api/v1/health/live
# Răspuns așteptat: {"status":"alive",...}

# 2. Verifică că migrările sunt aplicate
docker-compose exec app alembic current
# Răspuns așteptat: 20251011_enhanced_po_adapted (head)

# 3. Verifică că tabelele există
docker exec magflow_db psql -U app -d magflow -c "\dt app.purchase_order*"
# Răspuns așteptat: 4 tabele
```

✅ Dacă toate verificările sunt OK, continuă!

---

## 📦 Pas 1: Configurare Frontend (2 minute)

### 1.1 Editează App.tsx

```bash
# Deschide fișierul
code admin-frontend/src/App.tsx
```

**Adaugă import-uri:**
```typescript
import {
  PurchaseOrderList,
  PurchaseOrderForm,
  PurchaseOrderDetails,
  UnreceivedItemsList,
} from './components/purchase-orders';
```

**Adaugă route-uri în <Routes>:**
```typescript
<Route path="/purchase-orders" element={<PurchaseOrderList />} />
<Route path="/purchase-orders/new" element={<PurchaseOrderForm />} />
<Route path="/purchase-orders/:id" element={<PurchaseOrderDetails />} />
<Route path="/purchase-orders/unreceived" element={<UnreceivedItemsList />} />
```

### 1.2 Adaugă în Meniu

**Editează componenta de meniu (Layout.tsx sau similar):**
```typescript
{
  label: 'Purchase Orders',
  icon: ShoppingCartIcon, // sau orice icon
  path: '/purchase-orders'
}
```

---

## 🧪 Pas 2: Testare (3 minute)

### 2.1 Pornește Frontend

```bash
cd admin-frontend
npm run dev
```

### 2.2 Testează în Browser

**Deschide:** http://localhost:5173/purchase-orders

**Verifică:**
- [ ] Vezi lista de comenzi (poate fi goală)
- [ ] Click pe "New Purchase Order"
- [ ] Vezi formularul de creare
- [ ] Toate câmpurile se afișează corect

---

## 🎯 Pas 3: Creare Primă Comandă (Test)

### 3.1 În Browser

1. Click pe **"New Purchase Order"**
2. Selectează un furnizor (mock data)
3. Adaugă un produs
4. Completează cantitate și preț
5. Click pe **"Create Purchase Order"**

### 3.2 Verificare în Backend

```bash
# Verifică că comanda a fost creată
curl http://localhost:8000/api/v1/purchase-orders \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## ✅ Success! Sistem Funcțional!

Dacă ai ajuns aici, sistemul funcționează! 🎉

---

## 📋 Next Steps (Opțional)

### Pentru Sistem Complet (3-4 ore)

**LowStock Integration:**
1. Editează `admin-frontend/src/components/inventory/LowStockWithPO.tsx`
2. Update API call la `/api/v1/inventory/low-stock-with-suppliers`
3. Adaugă indicator vizual pentru comenzi în așteptare
4. Implementează tooltip cu detalii

**Vezi:** `FINAL_IMPLEMENTATION_GUIDE.md` - Pas 5

---

## 🐛 Troubleshooting Rapid

### Backend nu răspunde
```bash
docker-compose ps
docker-compose logs app | tail -50
docker-compose restart app
```

### Frontend nu pornește
```bash
cd admin-frontend
npm install
npm run dev
```

### Eroare "Cannot find module"
```bash
cd admin-frontend
npm install axios react-router-dom
```

### Eroare "API call failed"
```bash
# Verifică că backend-ul rulează
curl http://localhost:8000/api/v1/health/live

# Verifică configurarea API
cat admin-frontend/.env
```

---

## 📚 Documentație Completă

**Pentru detalii complete:**
- `PURCHASE_ORDERS_SUCCESS_COMPLETE.md` - Overview complet
- `FINAL_IMPLEMENTATION_GUIDE.md` - Ghid pas cu pas
- `admin-frontend/src/components/purchase-orders/README.md` - Componente
- `docs/PURCHASE_ORDERS_SYSTEM.md` - API documentation

---

## 🎉 Gata!

**Sistem Purchase Orders funcțional în ~5 minute!**

Pentru sistem complet: +3-4 ore (LowStock integration)

---

**Quick Start Guide v1.0**  
**Data:** 11 Octombrie 2025  
**Status:** ✅ Ready to Use
