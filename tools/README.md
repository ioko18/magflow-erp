# MagFlow ERP - Tools & Utilities

Acest director conține tool-uri și scripturi utilitare pentru dezvoltare, testare și administrare.

## 📁 Structură

### `admin/` - Tool-uri Administrare
Scripturi pentru crearea și gestionarea utilizatorilor admin.

- `create_admin_docker.py` - Creează admin în Docker
- `create_admin_simple.py` - Creează admin simplu
- `create_admin_sql.py` - Creează admin via SQL
- `create_admin_user.py` - Creează admin user complet
- `create_test_user.py` - Creează utilizator de test

**Utilizare:**
```bash
python tools/admin/create_admin_user.py
```

### `database/` - Tool-uri Bază de Date
Scripturi pentru gestionarea bazei de date.

- `check_database.py` - Verifică starea bazei de date
- `debug_database.py` - Debug conexiuni DB
- `create_tables.py` - Creează tabele
- `create_emag_tables.py` - Creează tabele eMAG
- `create_emag_tables_safe.py` - Creează tabele eMAG (safe mode)
- `create_orders_table.py` - Creează tabel comenzi
- `fix_*.py` - Scripturi de fix pentru diverse probleme

**Utilizare:**
```bash
python tools/database/check_database.py
python tools/database/create_tables.py
```

### `emag/` - Tool-uri eMAG
Scripturi pentru integrarea și sincronizarea eMAG.

- `debug_emag_api.py` - Debug API eMAG
- `display_emag_products.py` - Afișează produse eMAG
- `simple_emag_sync.py` - Sincronizare simplă
- `simple_emag_test.py` - Test simplu eMAG
- `sync_emag_*.py` - Diverse scripturi de sincronizare
- `run_emag_sync.py` - Rulează sincronizare eMAG

**Utilizare:**
```bash
python tools/emag/simple_emag_sync.py
python tools/emag/run_emag_sync.py
```

### `testing/` - Tool-uri Testare
Scripturi pentru rularea testelor.

- `test_*.py` - Diverse teste
- `run_tests.py` - Rulează toate testele
- `run_*_tests.py` - Rulează teste specifice

**Utilizare:**
```bash
python tools/testing/run_tests.py
python tools/testing/test_emag_complete.py
```

### `deployment/` - Tool-uri Deployment
Vezi `deployment/` directory la nivel root pentru scripturi de deployment.

### `monitoring/` - Tool-uri Monitoring
Vezi `monitoring/` directory la nivel root pentru scripturi de monitoring.

## 🚀 Ghid Rapid

### Creează Admin User
```bash
cd /Users/macos/anaconda3/envs/MagFlow
python tools/admin/create_admin_user.py
```

### Verifică Baza de Date
```bash
python tools/database/check_database.py
```

### Sincronizare eMAG
```bash
python tools/emag/run_emag_sync.py
```

### Rulează Teste
```bash
python tools/testing/run_tests.py
```

## 📝 Note

- Toate scripturile presupun că ești în directorul root al proiectului
- Asigură-te că ai activat virtual environment-ul
- Verifică fișierul `.env` pentru configurări

## ⚠️ Atenție

- **NU** rula scripturi de producție pe date de test
- Fă backup înainte de a rula scripturi de migrare
- Verifică log-urile după rularea scripturilor

## 🔗 Link-uri Utile

- [Documentație Completă](../docs/)
- [Ghid Deployment](../deployment/README.md)
- [Ghid Testing](../tests/README.md)
