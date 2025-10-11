# Sincronizare Produse eMAG - Ghid Rapid

## 🎯 Ce Face Această Pagină?

Pagina **"Sincronizare Produse eMAG"** sincronizează automat toate produsele din conturile tale eMAG (MAIN și FBE) în baza de date locală.

---

## 🚀 Cum Să Folosești

### Pasul 1: Deschide Pagina
Navighează la **"Sincronizare Produse eMAG"** din meniul principal.

### Pasul 2: Testează Conexiunea (IMPORTANT!)

Înainte de sincronizare, testează conexiunea:

1. Click pe **"Test Conexiune MAIN"** pentru contul MAIN
2. SAU click pe **"Test Conexiune FBE"** pentru contul FBE
3. Așteaptă mesajul de confirmare:
   - ✅ **Succes:** "Conectat la contul X. Total produse: Y"
   - ❌ **Eroare:** Verifică credențialele (vezi mai jos)

### Pasul 3: Pornește Sincronizarea

După ce testul conexiunii reușește:

1. Click pe butonul mare de sincronizare:
   - **"Sincronizare MAIN"** - pentru contul MAIN
   - **"Sincronizare FBE"** - pentru contul FBE  
   - **"Sincronizare AMBELE"** - pentru ambele conturi (recomandat)

2. Așteaptă notificarea:
   - "Sincronizare Pornită" - procesul a început
   - Progres la fiecare 30 secunde
   - "✅ Sincronizare Completă" - gata!

3. **NU închide pagina** în timpul sincronizării!

### Pasul 4: Verifică Rezultatele

După sincronizare:
- Statisticile se actualizează automat
- Produsele apar în tabel
- Istoricul sincronizărilor se actualizează

---

## 📊 Înțelegerea Interfeței

### Carduri Statistici

- **Total Produse** - Toate produsele sincronizate
- **Cont MAIN** - Produse din contul MAIN
- **Cont FBE** - Produse din contul FBE
- **Status** - Inactiv sau Sincronizare...

### Butoane Sincronizare

| Buton | Culoare | Funcție |
|-------|---------|---------|
| Sincronizare MAIN | Albastru | Sincronizează doar MAIN |
| Sincronizare FBE | Violet | Sincronizează doar FBE |
| Sincronizare AMBELE | Turcoaz | Sincronizează MAIN + FBE |

### Butoane Test

| Buton | Funcție |
|-------|---------|
| Test Conexiune MAIN | Verifică credențiale MAIN |
| Test Conexiune FBE | Verifică credențiale FBE |

---

## ⏱️ Cât Durează?

### Timpi Estimați

- **Cont mic** (< 100 produse): ~30 secunde
- **Cont mediu** (100-1000 produse): ~2 minute
- **Cont mare** (> 1000 produse): ~5 minute
- **Ambele conturi**: ~3-7 minute

### Progres

Vei vedea notificări la fiecare 30 secunde:
- "⏱️ 30s / ~120s - Procesare în curs..."
- "⏱️ 60s / ~120s - Procesare în curs..."
- etc.

---

## ❌ Probleme Comune & Soluții

### Problema 1: "Authentication failed" sau "Missing credentials"

**Ce înseamnă:**
Credențialele eMAG lipsesc sau sunt greșite.

**Soluție:**
1. Contactează administratorul sistemului
2. Verifică că variabilele de mediu sunt setate:
   - `EMAG_MAIN_USERNAME`
   - `EMAG_MAIN_PASSWORD`
   - `EMAG_FBE_USERNAME`
   - `EMAG_FBE_PASSWORD`

### Problema 2: "Timeout" sau durează prea mult

**Ce înseamnă:**
Sincronizarea durează mai mult de 5 minute.

**Soluție:**
1. Verifică conexiunea la internet
2. Încearcă să sincronizezi un singur cont (MAIN sau FBE)
3. Așteaptă câteva minute și încearcă din nou

### Problema 3: Sincronizarea pornește dar nu se termină

**Ce înseamnă:**
Procesul s-a blocat.

**Soluție:**
1. Reîmprospătează pagina (F5)
2. Verifică dacă backend-ul rulează
3. Contactează administratorul

### Problema 4: Nu apar produse după sincronizare

**Ce înseamnă:**
Produsele au fost sincronizate dar nu se afișează.

**Soluție:**
1. Șterge filtrul de căutare
2. Schimbă filtrul de cont la "All"
3. Click pe "Reîmprospătare"

---

## 💡 Sfaturi Pro

### 1. Testează Întotdeauna Conexiunea

Înainte de fiecare sincronizare:
- Click "Test Conexiune"
- Verifică că numărul de produse este corect
- Doar apoi pornește sincronizarea

### 2. Sincronizează Regulat

Frecvență recomandată:
- **Zilnic**: Pentru actualizări de stoc și prețuri
- **Săptămânal**: Pentru produse noi
- **După modificări**: Când adaugi/modifici produse în eMAG

### 3. Monitorizează Progresul

În timpul sincronizării:
- Nu închide browser-ul
- Nu închide tab-ul
- Urmărește notificările de progres

### 4. Verifică Istoricul

Tab "Istoric Sincronizări":
- Vezi sincronizările anterioare
- Verifică statusul (completed/failed)
- Identifică probleme recurente

### 5. Folosește Filtrele

După sincronizare:
- Filtrează după cont (MAIN/FBE)
- Caută după nume sau SKU
- Exportă în CSV dacă e necesar

---

## 📋 Checklist Sincronizare

Înainte de sincronizare:
- [ ] Backend-ul rulează
- [ ] Test conexiune reușit
- [ ] Ai timp să aștepți (2-5 minute)
- [ ] Browser-ul nu va fi închis

În timpul sincronizării:
- [ ] Notificări de progres apar
- [ ] Nu închizi pagina
- [ ] Monitorizezi timpul

După sincronizare:
- [ ] Notificare de succes apare
- [ ] Statistici actualizate
- [ ] Produse vizibile în tabel
- [ ] Verifici istoricul

---

## 🎨 Înțelegerea Culorilor

### Butoane

- **Albastru** (MAIN) = Cont principal eMAG
- **Violet** (FBE) = Fulfillment by eMAG
- **Turcoaz** (AMBELE) = Sincronizare completă

### Status Produse

- **Verde** (Activ) = Produs activ în eMAG
- **Gri** (Inactiv) = Produs inactiv
- **Verde** (Stoc > 0) = Produs în stoc
- **Roșu** (Stoc = 0) = Produs fără stoc

---

## 📊 Tab-uri Disponibile

### 1. Produse Sincronizate

- Tabel cu toate produsele
- Filtrare după cont și căutare
- Export CSV
- Paginare

### 2. Istoric Sincronizări

- Lista sincronizărilor recente
- Status (completed/failed/running)
- Număr produse procesate
- Dată și oră

---

## 🆘 Când Să Contactezi Suportul

Contactează administratorul dacă:

1. **Test conexiune eșuează constant**
   - Eroare: "Missing credentials" sau "Authentication failed"
   - Soluție: Credențiale trebuie configurate

2. **Sincronizarea eșuează mereu**
   - Eroare repetată la fiecare încercare
   - Timeout constant
   - Soluție: Verificare backend și configurare

3. **Produse lipsă după sincronizare**
   - Sincronizare reușită dar 0 produse
   - Statistici nu se actualizează
   - Soluție: Verificare bază de date

4. **Erori necunoscute**
   - Mesaje de eroare ciudate
   - Comportament neașteptat
   - Soluție: Investigare tehnică necesară

---

## 📈 Indicatori de Succes

Știi că totul funcționează când:

- ✅ Test conexiune reușește
- ✅ Sincronizarea se termină în 2-5 minute
- ✅ Notificare de succes apare
- ✅ Statistici se actualizează
- ✅ Produse apar în tabel
- ✅ Istoric arată "completed"

---

## 🔄 Workflow Recomandat

### Sincronizare Zilnică

```
1. Deschide pagina
2. Test Conexiune MAIN ✓
3. Test Conexiune FBE ✓
4. Click "Sincronizare AMBELE"
5. Așteaptă 3-5 minute
6. Verifică statistici
7. Gata!
```

### Sincronizare Selectivă

```
1. Deschide pagina
2. Test Conexiune pentru contul dorit
3. Click "Sincronizare MAIN" sau "Sincronizare FBE"
4. Așteaptă 2-3 minute
5. Verifică produse
6. Gata!
```

### Verificare Rapidă

```
1. Deschide pagina
2. Verifică statistici
3. Dacă e nevoie, click "Reîmprospătare"
4. Gata!
```

---

## 📱 Suport Mobil

Pagina funcționează pe mobil, dar:
- Recomandăm desktop pentru sincronizare
- Pe mobil: doar vizualizare și verificare
- Butoanele sunt adaptate pentru touch

---

## 🎓 Termeni Utili

- **MAIN** = Contul principal eMAG
- **FBE** = Fulfillment by eMAG (depozit eMAG)
- **SKU** = Cod unic produs
- **Sincronizare** = Copiere produse din eMAG în sistem
- **Timeout** = Timp maxim de așteptare (5 minute)

---

**Succes cu sincronizarea! 🚀**

*Pentru probleme tehnice, vezi: `docs/EMAG_SYNC_TROUBLESHOOTING.md`*
