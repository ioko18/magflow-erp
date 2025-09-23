"""Test database query plans to prevent performance regressions."""

from typing import Any, Dict, List, Optional

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Define allowed scan types for different query patterns
ALLOWED_SCAN_TYPES = {
    "index": True,  # Always allowed
    "index only": True,  # Always allowed
    "bitmap index": True,  # Always allowed
    "bitmap heap": True,  # For OR conditions
    "seq scan": {  # Only allowed for small tables
        "max_rows": 1000,
        "tables": ["sessions", "migrations"],  # Small, static tables
    },
}


class ExplainPlanError(Exception):
    """Raised when a query plan doesn't meet performance requirements."""


async def explain_query(
    session: AsyncSession,
    query: str,
    params: Optional[Dict[str, Any]] = None,
) -> Any:
    """Execute EXPLAIN ANALYZE and return the execution plan."""
    result = await session.execute(
        text(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"),
        params or {},
    )
    return result.scalar()


def check_plan(plan: dict, context: str = "") -> List[str]:
    """Check a query plan for performance issues."""
    issues = []
    _check_node(plan["Plan"], context, issues)
    return issues


def _check_node(
    node: dict,
    context: str,
    issues: List[str],
    parent: Optional[dict] = None,
):
    """Recursively check a plan node and its children."""
    node_type = node.get("Node Type", "").lower()

    # Check for sequential scans on large tables
    if "seq scan" in node_type:
        table_name = node.get("Relation Name", "unknown")
        scan_rules = ALLOWED_SCAN_TYPES.get("seq scan", {})

        if table_name not in scan_rules.get("tables", []):
            rows = node.get("Plan Rows", 0)
            if rows > scan_rules.get("max_rows", 0):
                issues.append(f"Seq Scan on {table_name} ({rows} rows) in {context}")

    # Recursively check child nodes
    if "Plans" in node:
        for child in node["Plans"]:
            _check_node(child, context, issues, node)


async def assert_good_plan(
    session: AsyncSession,
    query: str,
    params: Optional[dict] = None,
    context: str = "",
) -> None:
    """Assert that a query has an efficient execution plan."""
    plan = await explain_query(session, query, params)
    if not plan:
        pytest.fail(f"No execution plan returned for query: {query}")

    issues = []
    check_plan(plan[0]["Plan"], context, issues)

    if issues:
        error_msg = f"Query plan issues found for '{query}':\n" + "\n".join(issues)
        if context:
            error_msg = f"{context}: {error_msg}"
        pytest.fail(error_msg)


# Example test case (customize based on your models)
@pytest.mark.skip(reason="Explain tests require PostgreSQL database setup")
@pytest.mark.asyncio
async def test_product_list_plan(db: AsyncSession):
    """Test that product listing uses efficient indexes."""
    query = """
    SELECT * FROM products
    WHERE is_active = true
    ORDER BY created_at DESC
    LIMIT 20
    """
    await assert_good_plan(
        db,
        query,
        context="Product listing query should use index scan on (is_active, created_at)",
    )

    # Additional assertions about the plan can go here
    # assert plan["Plan"]["Node Type"].lower() != "seq scan"
