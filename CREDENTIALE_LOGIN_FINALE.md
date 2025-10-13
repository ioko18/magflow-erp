# 🔐 Credențiale de Login - MagFlow ERP
**Data**: 2025-10-13  
**Status**: ✅ VERIFICAT ȘI CONFIRMAT

---

## ⚠️ IMPORTANT: UN SINGUR UTILIZATOR ACTIV

În baza de date există **UN SINGUR utilizator**:

| Email | Parolă | Rol | Status |
|-------|--------|-----|--------|
| **admin@magflow.local** | **secret** | Admin | ✅ Activ |

---

## 🌐 Frontend Login

**URL**: http://localhost:5173/login

### Credențiale:
```
Email:    admin@magflow.local
Parolă:   secret
```

### Screenshot:
1. Deschide: http://localhost:5173/login
2. Introdu:
   - **Email**: `admin@magflow.local`
   - **Parolă**: `secret`
3. Click pe "Login"

---

## 🔧 API Direct (pentru testare)

**Base URL**: http://localhost:8000/api/v1

### Test Login cu cURL:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@magflow.local","password":"secret"}'
```

### Răspuns așteptat:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

---

## ❓ De ce există confuzie cu mai multe conturi?

### Explicație:
În documentele și scripturile vechi din proiect apar **mai multe email-uri diferite**:
- `admin@example.com` - folosit în exemple și teste
- `admin@magflow.com` - folosit în documentație veche
- `admin@magflow.local` - **SINGURUL cont real din baza de date**

### Verificare:
```bash
# Verifică utilizatorii din baza de date
docker compose exec db psql -U app -d magflow -c \
  "SET search_path TO app, public; SELECT email, full_name, is_superuser FROM users;"
```

**Rezultat**:
```
        email        |     full_name     | is_superuser
---------------------+-------------------+--------------
 admin@magflow.local | Development Admin | t
(1 row)
```

---

## 🛠️ Cum a fost creat utilizatorul?

Utilizatorul `admin@magflow.local` este creat automat la pornirea aplicației prin:

**Fișier**: `scripts/docker-entrypoint.sh`
```bash
# Development admin user ensured
```

**Cod**: `app/main.py` - funcția `ensure_dev_admin_user()`
```python
async def ensure_dev_admin_user():
    """Ensure development admin user exists"""
    email = "admin@magflow.local"
    password = "secret"
    # ... creates user if not exists
```

---

## 📝 Rezumat

### ✅ Utilizează aceste credențiale:
```
Email:    admin@magflow.local
Parolă:   secret
```

### ❌ NU folosi (nu există în baza de date):
- ~~admin@example.com~~
- ~~admin@magflow.com~~

### 🔍 Verificare rapidă:
```bash
# Test login
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@magflow.local","password":"secret"}' | jq .

# Dacă primești un token JWT, login-ul funcționează! ✅
```

---

## 🆘 Troubleshooting

### Problema: "Invalid credentials"
**Soluție**: Verifică că folosești exact:
- Email: `admin@magflow.local` (nu `.com`)
- Parolă: `secret` (lowercase, fără spații)

### Problema: "User not found"
**Soluție**: Repornește containerele pentru a recrea utilizatorul:
```bash
docker compose restart app
```

### Problema: "Connection Error" în frontend
**Soluție**: Asigură-te că:
1. Backend-ul rulează: `curl http://localhost:8000/api/v1/health/live`
2. Frontend-ul rulează: `curl http://localhost:5173`
3. Folosești credențialele corecte de mai sus

---

**Creat**: 2025-10-13  
**Verificat**: ✅ Utilizatorul există în baza de date  
**Testat**: ✅ Login funcționează cu credențialele de mai sus
