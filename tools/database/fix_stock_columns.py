#!/usr/bin/env python3
"""
Script pentru corectarea tipului coloanelor general_stock și estimated_stock.
Acestea trebuie să fie Integer, nu Boolean, conform eMAG API v4.4.9.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.core.database import engine

async def fix_stock_columns():
    """Corectează tipul coloanelor de stock."""
    
    print("\n" + "="*70)
    print("🔧 Fixing Stock Column Types")
    print("="*70)
    
    async with engine.begin() as conn:
        # Check current types
        print("\n📊 Checking current column types...")
        result = await conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'app' 
            AND table_name = 'emag_products_v2' 
            AND column_name IN ('general_stock', 'estimated_stock')
            ORDER BY column_name;
        """))
        
        current_types = dict(result.fetchall())
        print(f"Current types: {current_types}")
        
        # Fix general_stock if needed
        if current_types.get('general_stock') == 'boolean':
            print("\n🔨 Fixing general_stock column (boolean -> integer)...")
            await conn.execute(text("""
                ALTER TABLE app.emag_products_v2 
                ALTER COLUMN general_stock TYPE INTEGER 
                USING CASE WHEN general_stock THEN 1 ELSE 0 END;
            """))
            print("✅ general_stock column fixed")
        else:
            print(f"✅ general_stock is already {current_types.get('general_stock')}")
        
        # Fix estimated_stock if needed
        if current_types.get('estimated_stock') == 'boolean':
            print("\n🔨 Fixing estimated_stock column (boolean -> integer)...")
            await conn.execute(text("""
                ALTER TABLE app.emag_products_v2 
                ALTER COLUMN estimated_stock TYPE INTEGER 
                USING CASE WHEN estimated_stock THEN 1 ELSE 0 END;
            """))
            print("✅ estimated_stock column fixed")
        else:
            print(f"✅ estimated_stock is already {current_types.get('estimated_stock')}")
        
        # Verify changes
        print("\n📊 Verifying changes...")
        result = await conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'app' 
            AND table_name = 'emag_products_v2' 
            AND column_name IN ('general_stock', 'estimated_stock')
            ORDER BY column_name;
        """))
        
        new_types = dict(result.fetchall())
        print(f"New types: {new_types}")
    
    print("\n" + "="*70)
    print("✅ Stock Column Types Fixed Successfully!")
    print("="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(fix_stock_columns())
