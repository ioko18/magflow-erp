#!/usr/bin/env python3
"""
Script pentru crearea manuală a tabelelor eMAG V2.
"""

import asyncio

from app.core.database import engine, get_async_session


async def create_emag_tables():
    """Creează tabelele eMAG V2 în baza de date."""

    print("🗄️  Creez tabelele eMAG V2...")

    try:
        # Importă Base pentru a avea acces la metadata
        from app.db.base_class import Base

        # Creează toate tabelele
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("✅ Tabelele eMAG V2 au fost create cu succes!")

        # Verifică tabelele create
        async for db in get_async_session():
            from sqlalchemy import text

            result = await db.execute(
                text(
                    """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name LIKE '%emag%'
                ORDER BY table_name
            """
                )
            )
            tables = result.fetchall()

            print("\n📋 Tabele eMAG create:")
            for table in tables:
                print(f"  ✓ {table[0]}")

            break

    except Exception as e:
        print(f"❌ Eroare la crearea tabelelor: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(create_emag_tables())
