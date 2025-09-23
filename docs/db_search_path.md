# search_path în Postgres (nu în client)

## Configurarea actuală

Folosim: `ALTER ROLE app IN DATABASE magflow SET search_path = app, public;`

Această configurare setează `search_path` la nivel de rol și bază de date în PostgreSQL, eliminând necesitatea de a trimite parametrul prin conexiunea client.

## Motivația schimbării

Anterior, `search_path` era setat prin parametrul `options` în conexiunea SQLAlchemy:
```python
connect_args={
    "options": f"-c search_path={settings.search_path}",
    "application_name": "magflow-app"
}
```

Această abordare cauzează probleme cu PgBouncer, care poate respinge parametrii de startup non-standard cu eroarea:
```
unsupported startup parameter: options
```

## Soluția implementată

1. **Eliminarea parametrului din client**: Am eliminat `options` din `connect_args` în `app/db.py`
2. **Setarea la nivel de DB**: Am aplicat `ALTER ROLE app IN DATABASE magflow SET search_path = app, public;`

## Fallback pentru PgBouncer (dacă este necesar)

Dacă în viitor apar alte probleme cu parametrii de startup, se poate configura PgBouncer să ignore anumiți parametri:
```ini
ignore_startup_parameters = extra_float_digits
```

## Verificare

Pentru a verifica că configurarea funcționează:
```sql
SHOW search_path;
```

Rezultatul așteptat: `app, public`

## Note

- Configurarea se aplică automat la toate conexiunile noi pentru rolul `app` în baza de date `magflow`
- Nu mai este nevoie să specificați `search_path` în client
- Evitați trimiterea parametrilor non-standard prin `options` pentru compatibilitate cu PgBouncer
