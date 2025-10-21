# Ghid de Mentenanță - MagFlow ERP

## Verificare Zilnică

### 1. Verificare Rapidă (2 minute)
```bash
# Rulează scriptul de verificare automată
./scripts/verify_code_quality.sh
```

**Rezultat așteptat:** Toate verificările trec (exit code 0)

### 2. Verificare Funcționalitate Supplier Verification
```bash
# Testează debug endpoint
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/debug/supplier-verification/EMG411
```

**Rezultat așteptat:** JSON cu informații despre furnizori

## Reparare Erori Comune

### Eroare: "Module level import not at top of file"
**Cauză:** Importuri după cod executabil

**Soluție:**
```python
# ❌ GREȘIT
import sys
sys.path.insert(0, '/path')
from module import something

# ✅ CORECT
import sys
# Add path before other imports
sys.path.insert(0, '/path')

from module import something  # noqa: E402
```

### Eroare: "Blank line contains whitespace"
**Cauză:** Spații sau tab-uri pe linii goale

**Soluție automată:**
```bash
ruff check app/ --select=W293 --fix
```

### Eroare: "Avoid equality comparisons to True"
**Cauză:** Folosirea `== True` în SQLAlchemy

**Soluție:**
```python
# ❌ GREȘIT
.where(Model.is_active == True)

# ✅ CORECT
.where(Model.is_active.is_(True))
# sau
.where(Model.is_active)
```

### Eroare: "react/no-unescaped-entities"
**Cauză:** Ghilimele neescapate în JSX

**Soluție:**
```tsx
{/* ❌ GREȘIT */}
<p>Click "here" to continue</p>

{/* ✅ CORECT */}
<p>Click &quot;here&quot; to continue</p>
```

### Eroare: "ClockCircleOutlined is not defined"
**Cauză:** Icon neutilizat dar folosit în cod

**Soluție:**
```tsx
// Adaugă la importuri
import {
  CheckCircleOutlined,
  ClockCircleOutlined  // ← Adaugă aici
} from '@ant-design/icons';
```

## Reparare Automată

### Backend Python
```bash
# Repară toate erorile care pot fi reparate automat
ruff check app/ --fix

# Repară și erorile unsafe (folosește cu atenție)
ruff check app/ --fix --unsafe-fixes

# Repară doar erori specifice
ruff check app/ --select=W293,E712 --fix --unsafe-fixes
```

### Frontend TypeScript
```bash
cd admin-frontend

# Rulează linting
npm run lint

# Repară automat (dacă există script)
npm run lint:fix
```

## Adăugare Funcționalitate Nouă

### 1. Backend Endpoint
```python
# 1. Creează fișierul în app/api/v1/endpoints/
# 2. Adaugă router în app/api/v1/api.py:

from app.api.v1.endpoints import your_new_module

api_router.include_router(
    your_new_module.router,
    prefix="/your-prefix",
    tags=["your-tag"]
)
```

### 2. Frontend Component
```tsx
// 1. Creează component în admin-frontend/src/components/
// 2. Importă în pagina dorită
// 3. Verifică linting:

npm run lint
```

### 3. Verificare După Modificări
```bash
# 1. Verifică backend
ruff check app/

# 2. Verifică frontend
cd admin-frontend && npm run lint

# 3. Rulează verificare completă
./scripts/verify_code_quality.sh
```

## Debugging Supplier Verification

### Problemă: Furnizor verificat nu apare
**Pași de debugging:**

1. **Verifică în database:**
```bash
python3 scripts/debug_supplier_verification.py
```

2. **Verifică prin API:**
```bash
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/v1/debug/supplier-verification/SKU_HERE
```

3. **Verifică în frontend:**
- Deschide "Low Stock Products - Supplier Selection"
- Verifică dacă filtrul "Show Only Verified Suppliers" este OFF
- Click "Refresh" button
- Caută produsul și expandează

4. **Verifică manual_confirmed în DB:**
```sql
SELECT 
    sp.id,
    sp.supplier_id,
    s.name as supplier_name,
    sp.local_product_id,
    p.sku,
    sp.manual_confirmed,
    sp.is_active
FROM app.supplier_products sp
JOIN app.suppliers s ON sp.supplier_id = s.id
JOIN app.products p ON sp.local_product_id = p.id
WHERE p.sku = 'EMG411';
```

### Problemă: Script debug nu funcționează
**Cauză posibilă:** Conexiune la database

**Soluție:**
```bash
# Verifică variabilele de mediu
echo $DATABASE_URL

# Verifică conexiunea
psql $DATABASE_URL -c "SELECT 1"

# Rulează cu debugging
python3 -v scripts/debug_supplier_verification.py
```

## Pre-commit Hooks (Recomandat)

### Instalare
```bash
# Instalează pre-commit
pip install pre-commit

# Creează .pre-commit-config.yaml
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
EOF

# Instalează hooks
pre-commit install
```

### Utilizare
Acum, la fiecare commit, ruff va rula automat și va repara erorile.

## Monitorizare Continuă

### Metrici de Urmărit
1. **Număr erori critice:** Trebuie să fie 0
2. **Număr warnings:** Trebuie să scadă în timp
3. **Coverage teste:** Trebuie să crească
4. **Performance API:** Trebuie să fie < 200ms

### Comenzi de Monitorizare
```bash
# Statistici linting
ruff check app/ --statistics

# Număr erori critice
ruff check app/ --select=E9,F63,F7,F82 | wc -l

# Număr warnings
ruff check app/ --select=W | wc -l
```

## Backup și Restore

### Backup Înainte de Modificări Majore
```bash
# Backup database
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup cod
git commit -am "Backup before major changes"
git tag backup-$(date +%Y%m%d-%H%M%S)
```

### Restore Dacă Ceva Merge Greșit
```bash
# Restore database
psql $DATABASE_URL < backup_TIMESTAMP.sql

# Restore cod
git reset --hard backup-TAG
```

## Resurse Utile

### Documentație
- **Ruff:** https://docs.astral.sh/ruff/
- **SQLAlchemy:** https://docs.sqlalchemy.org/
- **FastAPI:** https://fastapi.tiangolo.com/
- **React:** https://react.dev/
- **Ant Design:** https://ant.design/

### Comenzi Rapide
```bash
# Backend
ruff check app/                    # Verifică erori
ruff check app/ --fix              # Repară automat
ruff format app/                   # Formatează cod

# Frontend
npm run lint                       # Verifică erori
npm run build                      # Build production
npm run dev                        # Development server

# Database
alembic upgrade head               # Aplică migrații
alembic revision --autogenerate    # Creează migrație

# Git
git status                         # Status
git diff                           # Modificări
git commit -am "message"           # Commit rapid
```

## Contact și Suport

Pentru probleme sau întrebări:
1. Consultă documentația din `docs/`
2. Verifică `QUICK_FIX_GUIDE.md`
3. Folosește debug tools disponibile
4. Creează issue în repository

---

**Ultima actualizare:** 15 Octombrie 2025  
**Versiune:** 1.0.0  
**Autor:** Cascade AI
