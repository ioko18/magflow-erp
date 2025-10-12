#!/usr/bin/env python3
"""Verifică statusul sincronizării."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import func, select

from app.core.database import async_session_factory
from app.models.emag_models import EmagProductV2


async def check_status():
    """Check current sync status."""

    print("\n" + "="*70)
    print("📊 Current Synchronization Status")
    print("="*70)

    async with async_session_factory() as session:
        # Count by account
        stmt = select(
            EmagProductV2.account_type,
            func.count(EmagProductV2.id)
        ).group_by(EmagProductV2.account_type)

        result = await session.execute(stmt)
        counts = dict(result.fetchall())

        print("\n🔢 Product Counts:")
        print(f"  MAIN Account: {counts.get('main', 0):4d} products")
        print(f"  FBE Account:  {counts.get('fbe', 0):4d} products")
        print(f"  {'─'*40}")
        print(f"  Total:        {sum(counts.values()):4d} products")

        # Expected counts
        expected_main = 1274
        expected_fbe = 1271
        expected_total = expected_main + expected_fbe

        print("\n📈 Expected Counts:")
        print(f"  MAIN Account: {expected_main:4d} products")
        print(f"  FBE Account:  {expected_fbe:4d} products")
        print(f"  {'─'*40}")
        print(f"  Total:        {expected_total:4d} products")

        # Progress
        main_progress = (counts.get('main', 0) / expected_main * 100) if expected_main > 0 else 0
        fbe_progress = (counts.get('fbe', 0) / expected_fbe * 100) if expected_fbe > 0 else 0
        total_progress = (sum(counts.values()) / expected_total * 100) if expected_total > 0 else 0

        print("\n✅ Progress:")
        print(f"  MAIN Account: {main_progress:5.1f}% complete")
        print(f"  FBE Account:  {fbe_progress:5.1f}% complete")
        print(f"  {'─'*40}")
        print(f"  Overall:      {total_progress:5.1f}% complete")

        # Status
        print("\n🎯 Status:")
        if counts.get('main', 0) >= expected_main:
            print(f"  MAIN:  ✅ Complete ({counts.get('main', 0)}/{expected_main})")
        else:
            print(f"  MAIN:  🔄 In Progress ({counts.get('main', 0)}/{expected_main})")

        if counts.get('fbe', 0) >= expected_fbe:
            print(f"  FBE:   ✅ Complete ({counts.get('fbe', 0)}/{expected_fbe})")
        else:
            print(f"  FBE:   🔄 In Progress ({counts.get('fbe', 0)}/{expected_fbe})")

        if sum(counts.values()) >= expected_total:
            print("\n🎉 SINCRONIZAREA ESTE COMPLETĂ!")
        else:
            remaining = expected_total - sum(counts.values())
            print(f"\n⏳ {remaining} products remaining...")

    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(check_status())
