# Fix TZT vs TZT-T Supplier Confusion - 20 Octombrie 2025

## Problema Identificată

Există **2 furnizori diferiți** în sistem:

### 1. TZT (Furnizor Principal)
- **Total produse:** 793
- **Produse verificate:** 394 ✅ CORECT
- **Produse neverificate:** 399
- **Status:** Corect - produsele sunt verificate legitim

### 2. TZT-T (Furnizor Secundar)
- **Total produse:** 45 (nu 114 cum apare în pagina Produse Furnizori)
- **Produse verificate:** 30 ❌ GREȘIT (ar trebui să fie 0)
- **Produse neverificate:** 15
- **Status:** INCORECT - produsele sunt marcate ca verificate când nu ar trebui

## Cauza Problemei

Endpoint-ul `/suppliers/sync-verification-status` a setat automat `is_verified = True` pentru produsele Google Sheets când produsele 1688 corespunzătoare aveau `manual_confirmed = True`.

Aceasta a afectat **AMBII** furnizori (TZT și TZT-T), dar:
- Pentru **TZT**: Verificarea este legitimă (utilizatorul a verificat produsele)
- Pentru **TZT-T**: Verificarea este GREȘITĂ (utilizatorul NU a verificat produsele)

## De ce apare confuzia în "Low Stock Products"?

Când un produs are furnizori de la **AMBII** TZT și TZT-T:
1. Backend-ul returnează **TOȚI** furnizorii pentru produsul respectiv
2. Dacă TZT-T are `is_verified = true` în baza de date, va apărea ca "Verified" în frontend
3. Chiar dacă utilizatorul nu a verificat niciodată TZT-T

**Exemplu din imagine:**
- Produsul "Modul GPS VK172 GMOUSE USB"
- Are 2 furnizori:
  - **TZT** - 15.28 CNY - ✅ Verified (corect)
  - **TZT-T** - 15.90 CNY - ❌ Verified (GREȘIT!)

## Diferența între cele 2 pagini

### Pagina "Produse Furnizori"
- Afișează statistici pentru **TOATE** produsele furnizorului
- Include produse care **NU** sunt în stoc scăzut
- **TZT-T**: 114 produse total, 0 verificate ✅

### Pagina "Low Stock Products"
- Afișează **DOAR** produsele cu stoc scăzut
- Pentru fiecare produs, afișează **TOȚI** furnizorii disponibili
- **TZT-T**: 45 produse în low stock, 30 marcate greșit ca verificate ❌

## Soluția

### Script Creat: `reset_tzt-t_only.sh`

Script-ul va:
1. ✅ Verifica statusul curent al ambilor furnizori
2. ✅ Reseta **DOAR** TZT-T la 0 produse verificate
3. ✅ Lăsa TZT **NESCHIMBAT** (394 produse verificate rămân)
4. ✅ Verifica că resetarea a avut succes

### Rezultat Așteptat

**După rulare:**
- **TZT**: 793 produse, 394 verificate ✅ (NESCHIMBAT)
- **TZT-T**: 45 produse, 0 verificate ✅ (RESETAT)

**În pagina "Low Stock Products":**
- Produsele **TZT** vor avea tag-ul "Verified" (verde) ✅
- Produsele **TZT-T** vor avea tag-ul "Pending Verification" (portocaliu) ✅

## Cum să Rulezi Script-ul

Script-ul este deja pornit și așteaptă confirmarea ta:

```bash
# În terminal, tastează:
yes

# Sau, pentru a rula din nou:
cd /Users/macos/anaconda3/envs/MagFlow
./scripts/reset_tzt-t_only.sh
```

## Verificare După Rulare

### 1. Verifică în baza de date
```sql
-- TZT (ar trebui să rămână neschimbat)
SELECT COUNT(*) as verified FROM app.product_supplier_sheets
WHERE supplier_name = 'TZT' AND is_verified = true;
-- Rezultat așteptat: 394

-- TZT-T (ar trebui să fie 0)
SELECT COUNT(*) as verified FROM app.product_supplier_sheets
WHERE supplier_name = 'TZT-T' AND is_verified = true;
-- Rezultat așteptat: 0
```

### 2. Verifică în "Low Stock Products"
1. Refresh pagina "Low Stock Products - Supplier Selection"
2. Găsește un produs care are ambii furnizori (ex: "Modul GPS VK172")
3. Verifică:
   - **TZT**: Tag "Verified" (verde) ✅
   - **TZT-T**: Tag "Pending Verification" (portocaliu) ✅

### 3. Verifică în "Produse Furnizori"
1. Selectează furnizorul TZT-T
2. Verifică statisticile:
   - **Confirmate**: 0 ✅
   - **În Așteptare**: 114 ✅

## Prevenire Viitoare

### Recomandări

1. **Eliminare endpoint `/suppliers/sync-verification-status`**
   - Acest endpoint creează confuzie între matching și verificare
   - Ar trebui eliminat sau modificat

2. **Adăugare buton "Mark as Verified" în frontend**
   - Permite utilizatorului să marcheze manual produsele ca verificate
   - Evită setarea automată greșită

3. **Separare clară între furnizori**
   - TZT și TZT-T sunt furnizori diferiți
   - Ar trebui tratați independent în toate operațiunile

4. **Documentare diferență între matching și verificare**
   - `manual_confirmed` = Matching confirmat (asociere corectă)
   - `is_verified` = Furnizor verificat (calitate/fiabilitate)

## Fișiere Create

### Scripts
1. `/scripts/reset_tzt-t_only.sh` - Script principal pentru resetare ✅
2. `/scripts/sql/check_tzt_vs_tzt-t.sql` - Query-uri pentru verificare
3. `/scripts/sql/reset_tzt_verified_status.sql` - SQL manual (backup)

### Documentație
1. `/FIX_TZT_VS_TZT-T_CONFUSION.md` - Acest document
2. `/FIX_LOW_STOCK_SUPPLIERS_FINAL_2025_10_20.md` - Documentație anterioară

## Rezumat

### Problema
- **TZT-T** are 30 produse marcate greșit ca "Verified" în baza de date
- Acestea apar ca "Verified" în pagina "Low Stock Products" când nu ar trebui

### Cauza
- Endpoint-ul `/suppliers/sync-verification-status` a setat automat `is_verified = True`
- A afectat ambii furnizori (TZT și TZT-T)
- Pentru TZT este corect, pentru TZT-T este greșit

### Soluția
- Script `reset_tzt-t_only.sh` resetează DOAR TZT-T
- TZT rămâne neschimbat (394 produse verificate)
- TZT-T va avea 0 produse verificate

### Status
⏳ **Script-ul așteaptă confirmarea ta pentru a continua**

---

**Data:** 20 Octombrie 2025  
**Verificat de:** Cascade AI Assistant  
**Status:** ⏳ Așteaptă confirmare utilizator
