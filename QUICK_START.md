# 🚀 Ghid Rapid MagFlow ERP

## 1) Instalare Dependențe (o singură dată per mediu)

Se recomandă instalarea tuturor pachetelor din `requirements.txt` în mediul curent:

```bash
python -m pip install -r requirements.txt
```

## 2) Pornirea Serverului

### Metoda Simplă (Recomandată):

Asigură-te că scriptul are permisiuni de execuție o dată:

```bash
chmod +x start_server.sh
```

Apoi pornește serverul:

```bash
./start_server.sh
```

### Metoda Manuală:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

## Accesarea Aplicației

- **📖 Documentație completă:** http://localhost:8080/docs
- **💚 Health Check:** http://localhost:8080/health
- **🔗 API Schema:** http://localhost:8080/api/v1/openapi.json

## Module Disponibile

✅ **Management Inventar** - Produse, categorii, stocuri
✅ **Management Vânzări** - Comenzi, facturi, clienți
✅ **Management Achiziții** - Furnizori, comenzi de achiziție
✅ **Autentificare JWT** - Login, token management
✅ **Integrare eMAG** - Sync produse, comenzi, stocuri
✅ **API REST** - Endpoints complete documentate

## Comenzi Utile

- **Oprire server:** `Ctrl+C`
- **Verificare procese:** `lsof -i :8080`
- **Instalare dependențe proiect:** `python -m pip install -r requirements.txt`

## 🔧 Depanare

Dacă întâmpini erori:

1. Rulează `python -m pip install -r requirements.txt` pentru a instala toate pachetele necesare (inclusiv `dependency-injector`).
2. Rulează `./start_server.sh` – scriptul verifică și instalează automat pachetele lipsă în mediul curent.
3. Verifică dacă serverul rulează pe portul 8080.
4. Accesează http://localhost:8080/docs pentru documentație.

> Eroare frecventă: `ModuleNotFoundError: No module named 'dependency_injector'` – indică faptul că pachetele nu sunt instalate în mediul curent. Soluție: reinstalează dependențele folosind comanda de la pasul 1.

**Serverul este acum complet funcțional și pregătit pentru utilizare!** 🎉
