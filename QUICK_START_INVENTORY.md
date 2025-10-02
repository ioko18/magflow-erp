# Quick Start - Sistem Inventory Management

## 🚀 Start Rapid

### 1. Accesează Pagina Inventory

```
http://localhost:3000/inventory
```

### 2. Vezi Produsele cu Stoc Scăzut

Pagina afișează automat toate produsele care necesită recomandare:
- 🔴 **Out of Stock** - Stoc epuizat (urgent!)
- 🟠 **Critical** - Sub stoc minim
- 🟡 **Low Stock** - Sub punctul de recomandare

### 3. Export Excel pentru Furnizori

**Click pe "Export to Excel"** → Fișierul se descarcă automat

**Conținut fișier:**
- Lista completă produse low stock
- Cantități recomandate de comandat
- Informații furnizor (nume, SKU, preț, URL)
- Costuri totale calculate
- Formatare cu culori pentru urgență

### 4. Trimite Comanda către Furnizori

1. Deschide fișierul Excel
2. Verifică produsele marcate cu **roșu** (urgente)
3. Grupează pe furnizor
4. Trimite email cu fișierul atașat

---

## 📊 Dashboard Cards

| Card | Descriere |
|------|-----------|
| **Total Items** | Total produse în inventar |
| **Needs Reorder** | Produse care necesită comandă |
| **Stock Health** | Procent sănătate stoc (target: >85%) |
| **Inventory Value** | Valoare totală inventar în RON |

---

## 🔍 Filtre Disponibile

- **📦 All Products** - Toate produsele low stock
- **🔴 Out of Stock** - Doar stoc epuizat
- **🟠 Critical** - Doar stoc critic
- **🟡 Low Stock** - Doar stoc scăzut

---

## 🔄 Workflow Zilnic Recomandat

### Dimineața (9:00)
1. ✅ Accesează pagina Inventory
2. ✅ Verifică produsele **Out of Stock** (roșu)
3. ✅ Contactează furnizori pentru produse urgente

### După-amiaza (14:00)
1. ✅ Review produse **Critical** (portocaliu)
2. ✅ Planifică comenzi pentru următoarele 24-48h

### Luni (săptămânal)
1. ✅ Export Excel complet
2. ✅ Trimite comenzi către toți furnizorii
3. ✅ Actualizează praguri stoc dacă e necesar

---

## 📧 Template Email Furnizor

```
Subject: Comandă Produse - [Data]

Bună ziua,

Vă rog să confirmați disponibilitatea și termenul de livrare pentru 
produsele din fișierul Excel atașat.

Produse URGENTE (marcate cu roșu): livrare în 3-5 zile
Produse critice (marcate cu portocaliu): livrare în 7-10 zile

Cantitățile și prețurile sunt calculate automat în fișier.

Vă mulțumesc,
[Numele tău]
```

---

## ⚙️ Setări Recomandate

### Praguri Stoc (per produs)

```sql
-- Exemplu pentru produs cu vânzări medii 5 buc/zi
minimum_stock = 35      -- 7 zile vânzări
reorder_point = 70      -- 14 zile vânzări  
maximum_stock = 300     -- 60 zile vânzări
```

**Regula generală:**
- `minimum_stock` = Vânzări medii zilnice × 7
- `reorder_point` = Vânzări medii zilnice × 14
- `maximum_stock` = Vânzări medii zilnice × 60

---

## 🎯 Prioritizare Comenzi

| Urgență | Status | Acțiune | Termen |
|---------|--------|---------|--------|
| 🔴 **URGENT** | Out of Stock | Comandă ACUM | Astăzi |
| 🟠 **Ridicat** | Critical | Comandă urgent | 24-48h |
| 🟡 **Mediu** | Low Stock | Planifică comandă | 3-5 zile |

---

## 💡 Tips & Tricks

### 1. Grupează Comenzi pe Furnizor
- Economisești la transport
- Obții discounturi pentru comenzi mari
- Simplifici procesul de comandă

### 2. Monitorizează Stock Health
- Target: **>85%** = Excelent
- **70-85%** = Bun
- **<70%** = Necesită atenție

### 3. Sincronizare Automată
- eMAG se sincronizează automat la fiecare oră
- Inventarul se actualizează în timp real
- Nu e nevoie de intervenție manuală

---

## 🆘 Probleme Comune

### Q: Nu văd niciun produs în listă
**A:** Înseamnă că toate produsele au stoc suficient! 🎉

### Q: Produsul X nu apare deși are stoc 0
**A:** Verifică că `reorder_point` este setat pentru acel produs

### Q: Excel nu se descarcă
**A:** Verifică că browser-ul permite download-uri de la localhost

### Q: Lipsesc informații furnizor în Excel
**A:** Adaugă furnizori în tabela `supplier_products`

---

## 📞 Support

Pentru probleme tehnice, verifică:
1. **Backend logs:** `docker logs magflow_app`
2. **Frontend console:** Browser DevTools → Console
3. **Documentație completă:** `INVENTORY_MANAGEMENT_SYSTEM.md`

---

**Quick Start creat de:** Cascade AI Assistant  
**Data:** 2025-10-02
