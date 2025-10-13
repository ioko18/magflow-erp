# 🔒 Securitate Credențiale - MagFlow ERP

## ⚠️ IMPORTANT: Calculator Personal - Credențiale Reale

Acest sistem rulează pe **calculatorul tău personal** și folosește **credențiale reale de producție**.

---

## 📋 Fișiere cu Credențiale Sensibile

### ✅ Fișiere care TREBUIE păstrate private:

1. **`.env.docker`** - Credențiale eMAG și baze de date
   ```bash
   # Conține:
   - EMAG_MAIN_USERNAME=<username-real>
   - EMAG_MAIN_PASSWORD=<password-real>
   - EMAG_FBE_USERNAME=<username-real>
   - EMAG_FBE_PASSWORD=<password-real>
   - DB_PASS=<password-db>
   - REDIS_PASSWORD=<password-redis>
   ```

2. **`service_account.json`** - Credențiale Google Sheets API
   ```bash
   # Conține:
   - private_key: Cheia privată Google Service Account
   - client_email: Email-ul service account
   - project_id: ID-ul proiectului Google Cloud
   ```

3. **`jwt-keys/`** - Chei JWT pentru autentificare
   ```bash
   # Conține:
   - Chei private RSA pentru semnarea token-urilor
   - Chei publice pentru verificare
   ```

---

## 🛡️ Verificare .gitignore

Aceste fișiere sunt deja în `.gitignore`:

```bash
# Verifică că sunt ignorate
cat .gitignore | grep -E "(\.env|service_account|jwt-keys)"
```

**Rezultat așteptat**:
```
.env
.env.local
.env.docker
service_account.json
jwt-keys/
```

---

## ⚠️ NU Distribui Niciodată

### ❌ NU face următoarele:
- ❌ NU commita `.env.docker` în Git
- ❌ NU commita `service_account.json` în Git
- ❌ NU partaja credențialele eMAG cu nimeni
- ❌ NU urca fișierele pe GitHub/GitLab public
- ❌ NU trimite credențialele prin email/chat

### ✅ Dacă trebuie să partajezi codul:
1. ✅ Folosește `.env.example` (fără valori reale)
2. ✅ Documentează ce credențiale sunt necesare
3. ✅ Instrucțiuni pentru a obține propriile credențiale

---

## 🔄 Backup Credențiale

### Recomandare: Backup local securizat

```bash
# Creează un backup criptat (opțional)
tar -czf credentials-backup.tar.gz \
  .env.docker \
  service_account.json \
  jwt-keys/

# Criptează backup-ul (folosind GPG)
gpg -c credentials-backup.tar.gz

# Șterge backup-ul necriptat
rm credentials-backup.tar.gz

# Păstrează credentials-backup.tar.gz.gpg într-un loc sigur
# (USB extern, cloud privat criptat, etc.)
```

---

## 🔍 Verificare Rapidă

### Verifică că fișierele sensibile NU sunt în Git:

```bash
# Verifică status Git
git status

# Verifică că fișierele sensibile sunt ignorate
git check-ignore .env.docker service_account.json jwt-keys/

# Dacă primești output, înseamnă că sunt ignorate ✅
# Dacă nu primești output, ADAUGĂ-LE în .gitignore! ⚠️
```

---

## 📝 Rezumat

### ✅ Fișiere SIGURE (pot fi în Git):
- `.env.example` - Template fără valori reale
- `docker-compose.yml` - Configurație fără credențiale
- Cod sursă Python/TypeScript
- Documentație

### ❌ Fișiere SENSIBILE (NU în Git):
- `.env.docker` - Credențiale reale
- `service_account.json` - Chei Google API
- `jwt-keys/` - Chei private JWT
- Orice fișier cu parole/token-uri

---

## 🆘 Dacă ai Commis Accidental Credențiale

### Pași de urmat IMEDIAT:

1. **Șterge din Git history**:
   ```bash
   # Folosește BFG Repo-Cleaner sau git filter-branch
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch .env.docker" \
     --prune-empty --tag-name-filter cat -- --all
   ```

2. **Schimbă TOATE credențialele**:
   - Generează noi credențiale eMAG
   - Generează nou service_account.json în Google Cloud
   - Schimbă parolele bazei de date

3. **Force push** (dacă ai push-uit deja):
   ```bash
   git push origin --force --all
   ```

---

**Data**: 2025-10-13  
**Status**: ✅ Sistem personal - Credențiale reale protejate
