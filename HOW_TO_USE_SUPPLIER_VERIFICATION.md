# Ghid de Utilizare - Verificare Furnizori

## 🎯 Scop

Acest ghid explică cum să verificați și să gestionați furnizorii pentru produse cu stoc scăzut.

## 📋 Pași Simpli

### 1. Confirmă Match-ul Furnizorului

#### În "Produse Furnizori" Page

1. **Selectează furnizorul** din dropdown (ex: YUJIA)
2. **Găsește produsul** (ex: SKU=EMG411)
3. **Click pe produs** pentru a deschide detaliile
4. **Click "Confirma Match"** button
5. **Verifică mesajul de succes**: "Match confirmat cu succes!"

✅ **Rezultat:** Furnizorul este acum verificat automat!

### 2. Verifică în Low Stock Products

#### În "Low Stock Products - Supplier Selection" Page

1. **Click "Refresh"** button (sus-dreapta)
2. **Găsește produsul** (ex: EMG411)
3. **Click "Select Supplier"** pentru a expanda
4. **Verifică badge-ul furnizorului:**
   - 🟢 **"Verified"** (verde) = Furnizor verificat ✅
   - 🟠 **"Pending Verification"** (portocaliu) = Necesită verificare

### 3. Selectează Furnizor pentru Comandă

1. **Bifează checkbox-ul** lângă furnizorul dorit
2. **Verifică cantitatea** de reordonare
3. **Click "Export Excel"** sau **"Create Draft POs"**

## 🔍 Filtre Disponibile

### Filter "Show Only Verified Suppliers"

**Locație:** În secțiunea "Filters & Quick Actions"

- **OFF** (default): Afișează TOȚI furnizorii (verificați + neverificați)
- **ON**: Afișează DOAR furnizorii verificați

**Când să folosești:**
- **OFF**: Când vrei să vezi toate opțiunile disponibile
- **ON**: Când vrei doar furnizori de încredere (verificați manual)

### Alte Filtre

- **Account Type**: MAIN / FBE / All
- **Stock Status**: Out of Stock / Critical / Low Stock / All

## ❓ Întrebări Frecvente

### Q: De ce apare "Pending Verification"?

**R:** Furnizorul nu a fost încă verificat manual. Pași:
1. Mergi la "Produse Furnizori"
2. Găsește furnizorul și produsul
3. Click "Confirma Match"

### Q: Am confirmat match-ul dar tot apare "Pending"?

**R:** Click "Refresh" în "Low Stock Products" page.

### Q: Cum verific dacă sincronizarea a funcționat?

**R:** Verifică răspunsul API după confirmare:
```json
{
  "sync_status": "synced_to_google_sheets"  // ✅ Success
}
```

### Q: Pot verifica mai mulți furnizori deodată?

**R:** Da! Folosește endpoint-ul de sincronizare în masă:
```bash
POST /api/v1/suppliers/sync-all-verifications
```

### Q: Cum văd toți furnizorii verificați?

**R:** Activează filtrul "Show Only Verified Suppliers" (ON).

## 🎨 Indicatori Vizuali

### Badge-uri Furnizor

| Badge | Culoare | Semnificație |
|-------|---------|--------------|
| **Verified** | 🟢 Verde | Furnizor verificat manual |
| **Pending Verification** | 🟠 Portocaliu | Necesită verificare |
| **Preferred** | 🔵 Albastru | Furnizor preferat |

### Status Stoc

| Status | Culoare | Semnificație |
|--------|---------|--------------|
| **Out of Stock** | 🔴 Roșu | Stoc epuizat |
| **Critical** | 🟠 Portocaliu | Stoc critic |
| **Low Stock** | 🟡 Galben | Stoc scăzut |

## 🛠️ Acțiuni Rapide

### În "Low Stock Products"

1. **Select Preferred** - Selectează automat furnizorul preferat pentru fiecare produs
2. **Select Cheapest** - Selectează automat furnizorul cel mai ieftin
3. **Create Draft POs** - Creează comenzi draft grupate pe furnizor
4. **Export Excel** - Exportă în Excel grupat pe furnizor

## 📞 Suport

### Debugging

Dacă ceva nu funcționează:

1. **Verifică în browser console** (F12)
2. **Click "Refresh"** în pagină
3. **Verifică filtrul** "Show Only Verified Suppliers"
4. **Contactează suportul** cu SKU-ul produsului

### Informații Utile pentru Suport

Când raportezi o problemă, include:
- SKU-ul produsului (ex: EMG411)
- Numele furnizorului (ex: YUJIA)
- Screenshot-uri
- Pașii urmați

---

**Versiune:** 1.0.0  
**Ultima actualizare:** 15 Octombrie 2025  
**Autor:** Cascade AI
