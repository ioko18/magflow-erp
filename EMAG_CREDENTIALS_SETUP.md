# eMAG API Credentials Setup Guide

**Date:** 2025-10-11  
**Status:** ✅ Required for Sync  
**Priority:** 🔴 CRITICAL

---

## 🎯 Overview

Pentru ca sincronizarea eMAG să funcționeze, trebuie să configurezi credențialele API pentru conturile MAIN și FBE.

---

## ⚠️ Erori Comune

### Eroare: "Missing credentials for X account"

**Cauză:** Variabilele de mediu nu sunt setate.

**Soluție:** Urmează pașii de mai jos pentru a seta credențialele.

### Eroare: "500 Internal Server Error" la test-connection

**Cauză:** Backend-ul nu găsește credențialele sau acestea sunt incorecte.

**Soluție:** Verifică și setează corect credențialele.

---

## 🔧 Setare Credențiale

### Metoda 1: Fișier .env (Recomandat)

1. **Creează/Editează fișierul .env**
   ```bash
   cd /Users/macos/anaconda3/envs/MagFlow
   nano .env
   ```

2. **Adaugă credențialele**
   ```bash
   # eMAG MAIN Account
   EMAG_MAIN_USERNAME=your_main_email@example.com
   EMAG_MAIN_PASSWORD=your_main_password
   EMAG_MAIN_BASE_URL=https://marketplace-api.emag.ro/api-3
   
   # eMAG FBE Account
   EMAG_FBE_USERNAME=your_fbe_email@example.com
   EMAG_FBE_PASSWORD=your_fbe_password
   EMAG_FBE_BASE_URL=https://marketplace-api.emag.ro/api-3
   ```

3. **Salvează fișierul**
   - Ctrl+O (save)
   - Enter
   - Ctrl+X (exit)

4. **Restart Backend**
   ```bash
   # Dacă folosești docker-compose
   docker-compose restart backend
   
   # Dacă rulezi direct
   # Oprește procesul și repornește-l
   ```

### Metoda 2: Export în Terminal

```bash
# Pentru sesiunea curentă
export EMAG_MAIN_USERNAME="your_main_email@example.com"
export EMAG_MAIN_PASSWORD="your_main_password"
export EMAG_FBE_USERNAME="your_fbe_email@example.com"
export EMAG_FBE_PASSWORD="your_fbe_password"

# Apoi pornește backend-ul
python -m uvicorn app.main:app --reload
```

### Metoda 3: Docker Compose

Editează `docker-compose.yml`:

```yaml
services:
  backend:
    environment:
      - EMAG_MAIN_USERNAME=your_main_email@example.com
      - EMAG_MAIN_PASSWORD=your_main_password
      - EMAG_FBE_USERNAME=your_fbe_email@example.com
      - EMAG_FBE_PASSWORD=your_fbe_password
```

Apoi restart:
```bash
docker-compose down
docker-compose up -d
```

---

## 🔍 Verificare Credențiale

### Pasul 1: Verifică că variabilele sunt setate

```bash
# Check MAIN
echo "MAIN Username: $EMAG_MAIN_USERNAME"
echo "MAIN Password: ${EMAG_MAIN_PASSWORD:0:3}***" # Primele 3 caractere

# Check FBE
echo "FBE Username: $EMAG_FBE_USERNAME"
echo "FBE Password: ${EMAG_FBE_PASSWORD:0:3}***"
```

**Rezultat așteptat:**
```
MAIN Username: your_email@example.com
MAIN Password: abc***
FBE Username: your_email@example.com
FBE Password: xyz***
```

### Pasul 2: Test din Python

```python
import os

# Check credentials
main_user = os.getenv("EMAG_MAIN_USERNAME")
main_pass = os.getenv("EMAG_MAIN_PASSWORD")
fbe_user = os.getenv("EMAG_FBE_USERNAME")
fbe_pass = os.getenv("EMAG_FBE_PASSWORD")

print(f"MAIN: {'✅ SET' if main_user and main_pass else '❌ MISSING'}")
print(f"FBE: {'✅ SET' if fbe_user and fbe_pass else '❌ MISSING'}")
```

### Pasul 3: Test din Browser

1. Deschide pagina "Sincronizare Produse eMAG"
2. Click "Test Conexiune MAIN"
3. Click "Test Conexiune FBE"

**Rezultat așteptat:**
- ✅ "Conectat la contul MAIN. Total produse: X"
- ✅ "Conectat la contul FBE. Total produse: Y"

---

## 📋 Unde Găsești Credențialele eMAG?

### Pentru Contul MAIN

1. Loghează-te pe [eMAG Marketplace](https://marketplace.emag.ro)
2. Mergi la **Setări** → **API**
3. Găsești:
   - **Username/Email:** Email-ul contului
   - **Password:** Parola API (NU parola de login!)

### Pentru Contul FBE

1. Loghează-te pe [eMAG FBE](https://fbe.emag.ro)
2. Mergi la **Setări** → **API**
3. Găsești:
   - **Username/Email:** Email-ul contului FBE
   - **Password:** Parola API FBE

**⚠️ IMPORTANT:**
- Parola API este DIFERITĂ de parola de login
- Dacă nu ai parolă API, trebuie să o generezi din setări
- Nu împărtăși niciodată credențialele

---

## 🔐 Securitate

### Best Practices

1. **NU pune credențiale în cod**
   ```python
   # ❌ GREȘIT
   username = "my_email@example.com"
   
   # ✅ CORECT
   username = os.getenv("EMAG_MAIN_USERNAME")
   ```

2. **Folosește .env pentru development**
   ```bash
   # Adaugă .env în .gitignore
   echo ".env" >> .gitignore
   ```

3. **Folosește secrets pentru production**
   - Docker secrets
   - Kubernetes secrets
   - AWS Secrets Manager
   - Azure Key Vault

4. **Rotează credențialele periodic**
   - Schimbă parola API la 3-6 luni
   - Actualizează în toate mediile

---

## 🧪 Testare Completă

### Checklist

- [ ] Credențiale MAIN setate
- [ ] Credențiale FBE setate
- [ ] Backend restartat
- [ ] Test conexiune MAIN reușit
- [ ] Test conexiune FBE reușit
- [ ] Sincronizare MAIN funcționează
- [ ] Sincronizare FBE funcționează

### Script de Test

```bash
#!/bin/bash
# test_emag_credentials.sh

echo "🧪 Testing eMAG Credentials..."
echo ""

# Check environment variables
echo "1. Checking environment variables..."
if [ -z "$EMAG_MAIN_USERNAME" ]; then
    echo "❌ EMAG_MAIN_USERNAME not set"
else
    echo "✅ EMAG_MAIN_USERNAME: $EMAG_MAIN_USERNAME"
fi

if [ -z "$EMAG_MAIN_PASSWORD" ]; then
    echo "❌ EMAG_MAIN_PASSWORD not set"
else
    echo "✅ EMAG_MAIN_PASSWORD: ${EMAG_MAIN_PASSWORD:0:3}***"
fi

if [ -z "$EMAG_FBE_USERNAME" ]; then
    echo "❌ EMAG_FBE_USERNAME not set"
else
    echo "✅ EMAG_FBE_USERNAME: $EMAG_FBE_USERNAME"
fi

if [ -z "$EMAG_FBE_PASSWORD" ]; then
    echo "❌ EMAG_FBE_PASSWORD not set"
else
    echo "✅ EMAG_FBE_PASSWORD: ${EMAG_FBE_PASSWORD:0:3}***"
fi

echo ""
echo "2. Testing API connection..."
echo "   Open browser and test connections in Sync page"
echo ""
echo "✅ Setup complete!"
```

---

## 🆘 Troubleshooting

### Problema: Credențialele sunt setate dar tot primesc eroare

**Soluții:**

1. **Verifică că backend-ul a fost restartat**
   ```bash
   docker-compose restart backend
   # SAU
   pkill -f uvicorn && python -m uvicorn app.main:app --reload
   ```

2. **Verifică că .env este în directorul corect**
   ```bash
   ls -la /Users/macos/anaconda3/envs/MagFlow/.env
   ```

3. **Verifică că .env este citit**
   ```bash
   # În backend, adaugă logging temporar
   import os
   print("MAIN USER:", os.getenv("EMAG_MAIN_USERNAME"))
   ```

### Problema: "Authentication failed"

**Cauze posibile:**

1. **Parolă incorectă**
   - Verifică că folosești parola API, nu parola de login
   - Regenerează parola API din eMAG

2. **Username incorect**
   - Verifică email-ul exact din eMAG
   - Verifică că nu ai spații sau caractere speciale

3. **Cont blocat**
   - Verifică că poți face login pe eMAG
   - Contactează suportul eMAG

### Problema: "Connection timeout"

**Cauze posibile:**

1. **Firewall**
   - Verifică că poți accesa https://marketplace-api.emag.ro
   - Dezactivează temporar firewall-ul pentru test

2. **Network**
   - Verifică conexiunea la internet
   - Testează cu curl:
     ```bash
     curl -I https://marketplace-api.emag.ro/api-3
     ```

3. **VPN/Proxy**
   - Dezactivează VPN-ul
   - Configurează proxy-ul corect

---

## 📚 Resurse

### Documentație eMAG

- [eMAG Marketplace API Docs](https://marketplace-api.emag.ro/docs)
- [eMAG FBE Documentation](https://fbe.emag.ro/help)

### Documentație Internă

- **Troubleshooting:** `docs/EMAG_SYNC_TROUBLESHOOTING.md`
- **User Guide:** `EMAG_SYNC_QUICK_GUIDE.md`
- **Changes Summary:** `CHANGES_SUMMARY_EMAG_SYNC_2025_10_11.md`

---

## ✅ Success Checklist

După ce ai setat credențialele, verifică:

- [x] Variabile de mediu setate corect
- [x] Backend restartat
- [x] Test conexiune MAIN: ✅ Success
- [x] Test conexiune FBE: ✅ Success
- [x] Sincronizare funcționează
- [x] Produse se încarcă în tabel

---

**Credențialele sunt setate corect când vezi:**

```
✅ Conectat la contul MAIN. Total produse: 1234
✅ Conectat la contul FBE. Total produse: 567
```

**Dacă vezi erori, consultă:**
- `docs/EMAG_SYNC_TROUBLESHOOTING.md` pentru soluții detaliate
- Logs backend pentru detalii tehnice

---

**Last Updated:** 2025-10-11  
**Status:** ✅ Complete Guide
