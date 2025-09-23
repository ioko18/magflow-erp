#!/usr/bin/env python3
"""
Database Connection Pooling Fix pentru eMAG Sync
Corectează erorile de tranzacție prin implementarea connection pooling-ului
"""

import re

def fix_database_issues():
    """Corectează problemele de database în sync_emag_sync.py"""

    with open('sync_emag_sync.py', 'r') as f:
        content = f.read()

    original_content = content

    # 1. Adaugă database engine cu connection pooling la nivel de modul
    pooling_config = '''
# Database engine cu connection pooling - creat o singură dată
DATABASE_URL = "postgresql://app:pQ4mR9tY2wX7zK3nL8vB5cD1fG6hJ0@localhost:6432/postgres"

# Engine cu connection pooling optimizat
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
    future=True
)
'''

    # 2. Înlocuiește get_db_session() cu versiune optimizată
    new_get_db_session = '''
def get_db_session():
    """Create database session cu connection pooling"""
    try:
        Session = sessionmaker(bind=engine)
        return Session()
    except Exception as e:
        logger.error(f"Error creating database session: {e}")
        raise
'''

    # 3. Adaugă retry decorator pentru database operations
    retry_decorator = '''
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
def execute_with_retry(func, *args, **kwargs):
    """Execute database operations with retry logic"""
    return func(*args, **kwargs)
'''

    # Aplică corecțiile
    corrections_applied = []

    # Corecție 1: Adaugă connection pooling după imports
    if 'from sqlalchemy import create_engine' in content:
        pattern = r'(from sqlalchemy import create_engine[^\n]*\n)'
        replacement = r'\1\n' + pooling_config
        content = re.sub(pattern, replacement, content)
        corrections_applied.append('✅ Connection pooling adăugat')

    # Corecție 2: Înlocuiește get_db_session cu versiune optimizată
    if 'def get_db_session():' in content:
        pattern = r'def get_db_session\(\):.*?except Exception as e:.*?raise'
        replacement = new_get_db_session
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        corrections_applied.append('✅ get_db_session optimizat')

    # Corecție 3: Adaugă retry decorator după imports
    if 'from tenacity import' in content:
        pattern = r'(from tenacity import [^\n]*\n)'
        replacement = r'\1\n' + retry_decorator
        content = re.sub(pattern, replacement, content)
        corrections_applied.append('✅ Retry decorator adăugat')

    # Scrie fișierul corectat
    with open('sync_emag_sync.py', 'w') as f:
        f.write(content)

    print(f"✅ Corecții aplicate: {len(corrections_applied)}")
    for correction in corrections_applied:
        print(f"   {correction}")

    return len(corrections_applied) > 0

if __name__ == "__main__":
    success = fix_database_issues()
    if success:
        print("\n🎉 Corecții aplicate cu succes!")
        print("🔄 Acum poți rula sync-ul din nou:")
        print("   python3 sync_scheduler.py sync main")
    else:
        print("\n❌ Nicio corecție aplicată")
