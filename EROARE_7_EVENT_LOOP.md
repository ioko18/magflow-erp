# Eroare #7 - Event Loop Conflict în Teste Async

**Data:** 11 Octombrie 2025, 10:51 AM  
**Severitate:** 🟡 Medie  
**Status:** ✅ Rezolvată

---

## 📋 Descriere

Testul `tests/scripts/test_app_db.py` eșua când era rulat împreună cu alte teste din cauza unui conflict de event loop în pytest.

## ❌ Eroare

```
RuntimeError: Task <Task pending name='Task-5' coro=<test_connection()>> 
got Future <Future pending> attached to a different loop

RuntimeError: Event loop is closed
```

## 🔍 Cauză

**Problema:** Engine-ul SQLAlchemy era creat la nivel de modul (global), dar pytest creează un nou event loop pentru fiecare test.

**Cod problematic:**
```python
# La nivel de modul - GREȘIT!
engine = create_async_engine(
    settings.DB_URI,
    echo=settings.DB_ECHO,
    ...
)

async_session_factory = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    ...
)

async def test_connection():
    async with engine.connect() as conn:  # ❌ Engine legat de alt event loop!
        ...
```

**De ce eșua:**
1. Primul test creează engine-ul cu event loop A
2. Al doilea test rulează cu event loop B (nou)
3. Engine-ul încă este legat de loop A (care e închis)
4. → RuntimeError: "Task attached to different loop"

## ✅ Soluție

**Creare engine per-test** - fiecare test creează propriul engine în event loop-ul curent:

```python
def get_engine():
    """Create async engine for the current event loop."""
    return create_async_engine(
        settings.DB_URI,
        echo=settings.DB_ECHO,
        pool_pre_ping=settings.DB_POOL_PRE_PING,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
    )


def get_session_factory(engine):
    """Create async session factory for the given engine."""
    return sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def test_connection():
    """Test database connection and basic queries."""
    engine = get_engine()  # ✅ Nou engine pentru event loop-ul curent
    try:
        async with engine.connect() as conn:
            # Test queries...
            ...
    finally:
        await engine.dispose()  # ✅ Cleanup


async def test_models():
    """Test database models."""
    engine = get_engine()  # ✅ Nou engine
    async_session_factory = get_session_factory(engine)
    
    try:
        async with async_session_factory() as session:
            # Test models...
            ...
    finally:
        await engine.dispose()  # ✅ Cleanup
```

## 📊 Modificări

**Fișier:** `tests/scripts/test_app_db.py`

**Linii modificate:** ~40

**Schimbări:**
1. ✅ Convertit engine global → funcție `get_engine()`
2. ✅ Convertit session_factory global → funcție `get_session_factory()`
3. ✅ Adăugat `engine = get_engine()` în fiecare test
4. ✅ Adăugat `finally: await engine.dispose()` pentru cleanup
5. ✅ Eliminat cleanup din `main()` (nu mai e nevoie)

## 🧪 Verificare

**Înainte:**
```bash
$ pytest tests/scripts/ -v
...
FAILED tests/scripts/test_app_db.py::test_connection - RuntimeError
```

**După:**
```bash
$ pytest tests/scripts/ -v
...
tests/scripts/test_app_db.py::test_connection PASSED
tests/scripts/test_app_db.py::test_models PASSED
========================= 7 passed in 0.35s =========================
```

## 📚 Lecție Învățată

### Anti-pattern: Global Async Resources

```python
# ❌ NU - Resurse async la nivel de modul
engine = create_async_engine(...)  # Legat de primul event loop

async def test_1():
    async with engine.connect():  # OK - primul test
        ...

async def test_2():
    async with engine.connect():  # ❌ EROARE - alt event loop!
        ...
```

### Best Practice: Factory Functions

```python
# ✅ DA - Factory functions pentru resurse async
def get_engine():
    return create_async_engine(...)  # Nou engine pentru fiecare test

async def test_1():
    engine = get_engine()  # Event loop A
    try:
        async with engine.connect():
            ...
    finally:
        await engine.dispose()

async def test_2():
    engine = get_engine()  # Event loop B (nou)
    try:
        async with engine.connect():
            ...
    finally:
        await engine.dispose()
```

## 🎯 Reguli pentru Teste Async în Pytest

### 1. **Nu creați resurse async la nivel de modul**
```python
# ❌ NU
engine = create_async_engine(...)
client = httpx.AsyncClient()

# ✅ DA
def get_engine():
    return create_async_engine(...)

def get_client():
    return httpx.AsyncClient()
```

### 2. **Folosiți fixture-uri pytest pentru resurse partajate**
```python
@pytest_asyncio.fixture
async def engine():
    engine = create_async_engine(...)
    yield engine
    await engine.dispose()

async def test_something(engine):
    async with engine.connect() as conn:
        ...
```

### 3. **Cleanup-ul este obligatoriu**
```python
async def test_connection():
    engine = get_engine()
    try:
        # Use engine...
        ...
    finally:
        await engine.dispose()  # ✅ Întotdeauna cleanup!
```

### 4. **Evitați state partajat între teste**
```python
# ❌ NU - State global
connections = []

async def test_1():
    conn = await engine.connect()
    connections.append(conn)  # ❌ Leak!

# ✅ DA - State local
async def test_1():
    async with engine.connect() as conn:
        # Conn se închide automat
        ...
```

## 🔗 Resurse Similare

Această problemă poate apărea și în:
- `httpx.AsyncClient` creat global
- `aiohttp.ClientSession` creat global
- `asyncpg.Pool` creat global
- Orice resursă async creată înaintea event loop-ului

**Soluție universală:** Folosiți factory functions sau pytest fixtures!

## ✅ Impact

- ✅ Toate testele din `tests/scripts/` trec acum
- ✅ Nu mai există conflicte de event loop
- ✅ Cleanup corect al resurselor
- ✅ Testele pot rula în orice ordine

---

**Autor:** Cascade AI Assistant  
**Timp rezolvare:** ~10 minute  
**Complexitate:** Medie
