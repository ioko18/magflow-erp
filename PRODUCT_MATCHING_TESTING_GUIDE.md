# 🧪 Ghid Testing: Product Matching Suggestions Page

## 📋 Pre-Testing Checklist

### Backend
- [ ] Verifică că endpoint `/unmatched-with-suggestions` este disponibil
- [ ] Verifică că ProductMatchingService funcționează
- [ ] Verifică că Jieba tokenization funcționează
- [ ] Verifică că database are produse nematchate

### Frontend
- [ ] Verifică că pagina se încarcă fără erori console
- [ ] Verifică că API client este configurat corect
- [ ] Verifică că TypeScript nu are erori

---

## 🧪 Test Cases

### Test 1: Încărcare Pagină
**Scop**: Verifică că pagina se încarcă corect

**Pași**:
1. Navighează la `/admin/product-matching-suggestions`
2. Așteptă încărcarea completă

**Rezultat Așteptat**:
- Pagina se încarcă fără erori
- Dropdown furnizor este populat
- Statistici sunt afișate
- Tabel este gol sau populat cu produse

**Rezultat Actual**: ___________

---

### Test 2: Selectare Furnizor
**Scop**: Verifică că selectarea furnizorului funcționează

**Pași**:
1. Deschide dropdown "Furnizor"
2. Selectează un furnizor (ex: TZT)
3. Așteptă încărcarea produselor

**Rezultat Așteptat**:
- Produsele se încarcă
- Statistici se actualizează
- Sugestii sunt afișate pentru fiecare produs

**Rezultat Actual**: ___________

---

### Test 3: Filtrare - Cu Sugestii
**Scop**: Verifică filtrarea "Cu sugestii"

**Pași**:
1. Apasă butonul "Cu sugestii"
2. Observă tabelul

**Rezultat Așteptat**:
- Doar produsele cu sugestii sunt afișate
- Statistici se actualizează
- Alert informativ apare

**Rezultat Actual**: ___________

---

### Test 4: Filtrare - Fără Sugestii
**Scop**: Verifică filtrarea "Fără sugestii"

**Pași**:
1. Apasă butonul "Fără sugestii"
2. Observă tabelul

**Rezultat Așteptat**:
- Doar produsele fără sugestii sunt afișate
- Statistici se actualizează

**Rezultat Actual**: ___________

---

### Test 5: Filtrare - Scor >95%
**Scop**: Verifică filtrarea "Scor >95%"

**Pași**:
1. Apasă butonul "Scor >95%"
2. Observă tabelul

**Rezultat Așteptat**:
- Doar produsele cu best_match_score >= 0.95 sunt afișate
- Butonul "Confirmă Automat" este activ

**Rezultat Actual**: ___________

---

### Test 6: Ajustare Similaritate Minimă
**Scop**: Verifică ajustarea pragului de similaritate

**Pași**:
1. Schimbă "Similaritate minimă" de la 85% la 90%
2. Așteptă refresh

**Rezultat Așteptat**:
- Sugestiile se actualizează
- Doar sugestii cu scor >= 90% sunt afișate
- Statistici se actualizează

**Rezultat Actual**: ___________

---

### Test 7: Ajustare Număr Maxim Sugestii
**Scop**: Verifică ajustarea numărului maxim de sugestii

**Pași**:
1. Schimbă "Număr maxim sugestii" de la 5 la 3
2. Așteptă refresh

**Rezultat Așteptat**:
- Fiecare produs afișează max 3 sugestii
- Sugestiile sunt ordonate descrescător după scor

**Rezultat Actual**: ___________

---

### Test 8: Confirmare Match Individual
**Scop**: Verifică confirmarea unui match individual

**Pași**:
1. Găsește un produs cu sugestii
2. Apasă "Confirmă Match" pe o sugestie
3. Confirmă în dialog

**Rezultat Așteptat**:
- Mesaj "Match confirmat cu succes!"
- Produsul dispare din tabel
- Statistici se actualizează

**Rezultat Actual**: ___________

---

### Test 9: Eliminare Sugestie
**Scop**: Verifică eliminarea unei sugestii

**Pași**:
1. Găsește un produs cu sugestii
2. Apasă "Elimină Sugestie" pe o sugestie
3. Observă UI

**Rezultat Așteptat**:
- Sugestia dispare din UI imediat (optimistic update)
- Mesaj "Sugestie eliminată permanent!"
- Alte sugestii rămân

**Rezultat Actual**: ___________

---

### Test 10: Confirmare Bulk (Automat)
**Scop**: Verifică confirmarea automată a tuturor cu scor >95%

**Pași**:
1. Apasă "Confirmă Automat (N)"
2. Confirmă în dialog

**Rezultat Așteptat**:
- Mesaj cu numărul de matches confirmate
- Produsele dispar din tabel
- Statistici se actualizează

**Rezultat Actual**: ___________

---

### Test 11: Editare Preț Inline
**Scop**: Verifică editarea prețului inline

**Pași**:
1. Găsește un produs
2. Click pe InputNumber preț
3. Schimbă valoarea
4. Apasă Enter

**Rezultat Așteptat**:
- Preț se actualizează în UI
- Mesaj "Preț actualizat cu succes!"
- Valoarea se salvează în DB

**Rezultat Actual**: ___________

---

### Test 12: Paginare
**Scop**: Verifică paginarea

**Pași**:
1. Observă pagina curentă
2. Apasă pe pagina 2
3. Observă produsele

**Rezultat Așteptat**:
- Produsele din pagina 2 sunt afișate
- Paginare funcționează corect
- Total produse este afișat

**Rezultat Actual**: ___________

---

### Test 13: Schimbare Page Size
**Scop**: Verifică schimbarea numărului de produse pe pagină

**Pași**:
1. Apasă pe "20" în paginare
2. Selectează "50"

**Rezultat Așteptat**:
- 50 de produse sunt afișate
- Paginare se actualizează
- Produsele se reîncarcă

**Rezultat Actual**: ___________

---

### Test 14: Reîmprospătare
**Scop**: Verifică butonul de reîmprospătare

**Pași**:
1. Apasă butonul "Reîmprospătează"
2. Așteptă refresh

**Rezultat Așteptat**:
- Produsele se reîncarcă
- Statistici se recalculează
- Spinner apare și dispare

**Rezultat Actual**: ___________

---

### Test 15: Responsive Design
**Scop**: Verifică responsive design pe mobile

**Pași**:
1. Deschide DevTools (F12)
2. Selectează "Mobile" view
3. Navighează prin pagină

**Rezultat Așteptat**:
- Layout se adapteaza la mobile
- Tabelul este scrollabil
- Butoanele sunt accesibile

**Rezultat Actual**: ___________

---

### Test 16: Error Handling - Furnizor Fără Produse
**Scop**: Verifică comportament când furnizor nu are produse

**Pași**:
1. Selectează furnizor fără produse nematchate
2. Observă UI

**Rezultat Așteptat**:
- Tabel gol cu mesaj "Nu există produse"
- Statistici afișează 0

**Rezultat Actual**: ___________

---

### Test 17: Error Handling - API Error
**Scop**: Verifică comportament la API error

**Pași**:
1. Simulează API error (ex: offline)
2. Observă UI

**Rezultat Așteptat**:
- Mesaj de eroare apare
- Pagina nu se blochează
- Buton "Reîmprospătează" funcționează

**Rezultat Actual**: ___________

---

### Test 18: Performance - Lista Mare
**Scop**: Verifică performance cu lista mare

**Pași**:
1. Selectează furnizor cu 1000+ produse
2. Observă încărcarea și scrolling

**Rezultat Așteptat**:
- Pagina se încarcă în < 3 secunde
- Scrolling este smooth
- UI nu se blochează

**Rezultat Actual**: ___________

---

### Test 19: Sugestii cu Tokeni Comuni
**Scop**: Verifică afișarea tokenilor comuni

**Pași**:
1. Observă sugestiile
2. Verifică secțiunea "Tokeni comuni"

**Rezultat Așteptat**:
- Tokeni comuni sunt afișați
- Tokeni sunt relevanți la produs

**Rezultat Actual**: ___________

---

### Test 20: Culori Confidence
**Scop**: Verifică culori în funcție de scor

**Pași**:
1. Observă sugestiile
2. Verifică culori border stânga

**Rezultat Așteptat**:
- Scor >= 95%: Verde închis (#52c41a)
- Scor >= 90%: Verde (#73d13d)
- Scor >= 85%: Verde deschis (#95de64)
- Scor < 85%: Portocaliu (#faad14)

**Rezultat Actual**: ___________

---

## 📊 Raport Testing

### Rezumat
- **Total Test Cases**: 20
- **Passed**: ___
- **Failed**: ___
- **Blocked**: ___

### Probleme Găsite

| # | Descriere | Severitate | Status |
|---|-----------|-----------|--------|
| 1 | | | |
| 2 | | | |
| 3 | | | |

### Recomandări

1. ___________
2. ___________
3. ___________

---

## 🚀 Deployment Checklist

- [ ] Toate test cases au trecut
- [ ] Nu sunt erori console
- [ ] Performance este acceptabil
- [ ] Responsive design funcționează
- [ ] Error handling funcționează
- [ ] Documentație este actualizată
- [ ] Code review a trecut
- [ ] Merge în main branch

---

## 📝 Notă Finală

Pagina este **READY FOR PRODUCTION** după ce toate test cases trec.

**Data Testing**: ___________  
**Testat de**: ___________  
**Aprobat de**: ___________
