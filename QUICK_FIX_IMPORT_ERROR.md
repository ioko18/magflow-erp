# 🔧 Quick Fix: Import Error Resolution

## Problema Identificată

**Eroare**: `ModuleNotFoundError: No module named 'gspread'`

Backend-ul nu pornește din cauza lipsei dependențelor Google Sheets în container.

## Soluție Rapidă

### Opțiunea 1: Rebuild Container (Recomandat)

```bash
cd /Users/macos/anaconda3/envs/MagFlow

# Rebuild containerul cu noile dependențe
docker-compose build app

# Restart serviciile
docker-compose up -d

# Verifică logs
docker logs magflow_app --tail 50
```

### Opțiunea 2: Instalare Manuală în Container (Temporar)

```bash
# Intră în container
docker exec -it magflow_app bash

# Instalează dependențele
pip install gspread>=5.12.0 oauth2client>=4.1.3

# Exit din container
exit

# Restart container
docker restart magflow_app
```

## Verificare După Fix

```bash
# Verifică că backend-ul pornește corect
curl http://localhost:8000/health

# Ar trebui să primești: {"status":"healthy"}
```

## Următorii Pași

După ce backend-ul pornește:

1. **Accesează frontend**: http://localhost:5173
2. **Login**: admin@example.com / secret
3. **Test import**: http://localhost:5173/products/import

## Dependențe Adăugate

Am adăugat în `requirements.txt`:
- `gspread>=5.12.0` - Client Google Sheets API
- `oauth2client>=4.1.3` - OAuth2 authentication

## Status Implementare

✅ **Backend Code**: Complet implementat
✅ **Frontend Code**: Complet implementat  
✅ **Database Models**: Create
✅ **API Endpoints**: Configurate
✅ **Dependencies**: Adăugate în requirements.txt
⏳ **Container Build**: În curs...

## Troubleshooting

### Dacă backend-ul tot nu pornește:

```bash
# Verifică logs detaliate
docker logs magflow_app --tail 100

# Verifică că requirements.txt conține gspread
grep gspread requirements.txt

# Force rebuild fără cache
docker-compose build --no-cache app
docker-compose up -d
```

### Dacă ai erori de import în Python:

```bash
# Verifică versiunea Python în container
docker exec magflow_app python --version

# Verifică pachetele instalate
docker exec magflow_app pip list | grep gspread
```

## Note Importante

- ⚠️ **service_account.json** trebuie să fie în root-ul proiectului
- ⚠️ Google Sheets trebuie partajat cu service account email
- ⚠️ Migrarea bazei de date trebuie rulată: `alembic upgrade head`

## Contact

Pentru probleme persistente, verifică:
1. Docker logs: `docker logs magflow_app`
2. Database logs: `docker logs magflow_db`
3. Frontend console: Browser DevTools → Console
