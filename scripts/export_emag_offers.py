#!/usr/bin/env python3
"""
Export eMAG offers (MAIN/FBE) to CSV for analysis.

Usage examples:
  python3 scripts/export_emag_offers.py --account main --limit 200 --out offers_main.csv
  python3 scripts/export_emag_offers.py --search Tester --out offers_search.csv

The script resolves DB connection from:
  1) DATABASE_SYNC_URL
  2) DATABASE_URL (converts postgresql+asyncpg -> postgresql)
  3) DB_* parts (defaults: 127.0.0.1:5432/magflow)
"""
import argparse
import csv
import os
from urllib.parse import urlparse, urlunparse

from sqlalchemy import create_engine, text

# Load .env if available, to mirror app behavior
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass


def build_candidate_urls(cli_db: str | None) -> list[str]:
    candidates: list[str] = []
    if cli_db:
        candidates.append(cli_db)
    url = os.getenv("DATABASE_SYNC_URL") or os.getenv("DATABASE_URL")
    if url:
        if url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
        # Map container hostnames to localhost for host execution
        try:
            p = urlparse(url)
            host = p.hostname or ""
            if host in {"db", "pgbouncer", "magflow_pg", "magflow_pgbouncer"}:
                new_host = "127.0.0.1"
                netloc = p.netloc
                if "@" in netloc:
                    creds, hostport = netloc.split("@", 1)
                else:
                    creds, hostport = "", netloc
                # preserve port if present
                _, sep, port = hostport.partition(":")
                new_netloc = f"{creds + '@' if creds else ''}{new_host}{sep}{port}"
                url = urlunparse(p._replace(netloc=new_netloc))
        except Exception:
            pass
        candidates.append(url)

    # Compose from DB_* envs and always include localhost variants
    user = os.getenv("DB_USER", "app")
    password = os.getenv("DB_PASS", "app_password_change_me")
    host_env = os.getenv("DB_HOST", "127.0.0.1")
    hosts = {host_env, "127.0.0.1", "localhost"}
    for h in hosts:
        # Try PgBouncer first
        candidates.append(f"postgresql://{user}:{password}@{h}:6432/postgres")
        # Then direct Postgres common DBs
        candidates.append(f"postgresql://{user}:{password}@{h}:5432/magflow")
        candidates.append(f"postgresql://{user}:{password}@{h}:5432/postgres")
    return candidates


def redact(url: str) -> str:
    try:
        p = urlparse(url)
        if p.password:
            netloc = p.netloc.replace(f":{p.password}@", ":****@")
            return urlunparse(p._replace(netloc=netloc))
    except Exception:
        pass
    return url


def export_offers(
    account: str | None,
    search: str | None,
    limit: int,
    out_path: str,
    db_url: str | None,
    *,
    min_price: float | None = None,
    max_price: float | None = None,
    stock_gt: int | None = None,
    only_available: bool = False,
    sort_by: str = "updated_at",
    order: str = "desc",
):
    last_err: Exception | None = None
    engine = None
    for url in build_candidate_urls(db_url):
        try:
            print(f"Trying: {redact(url)}")
            engine = create_engine(url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"Connected: {redact(url)}")
            break
        except Exception as e:
            print(f"Failed: {redact(url)} -> {e}")
            last_err = e
            engine = None
    if engine is None:
        hint = (
            "Set DATABASE_SYNC_URL or pass --db, e.g.\n"
            "  --db postgresql://app:YOUR_PASS@127.0.0.1:5432/magflow\n"
            "or if using PgBouncer:\n"
            "  --db postgresql://app:YOUR_PASS@127.0.0.1:6432/postgres"
        )
        raise ConnectionError(f"Could not connect to database. Last error: {last_err}\n{hint}")
    where = []
    params = {}
    if account:
        where.append("account_type = :account")
        params["account"] = account
    if search:
        where.append("LOWER(product_name) LIKE LOWER(:search)")
        params["search"] = f"%{search}%"
    # Additional optional filters
    if min_price is not None:
        where.append("sale_price >= :min_price")
        params["min_price"] = min_price
    if max_price is not None:
        where.append("sale_price <= :max_price")
        params["max_price"] = max_price
    if stock_gt is not None:
        where.append("stock > :stock_gt")
        params["stock_gt"] = stock_gt
    if only_available:
        where.append("is_available = true")
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    # Build query against the convenience view to avoid multi-statement execution
    # Sorting: allow updated_at, sale_price, stock
    allowed_sorts = {"updated_at", "sale_price", "stock"}
    sort_field = sort_by if sort_by in allowed_sorts else "updated_at"
    sort_dir = "ASC" if order.lower() == "asc" else "DESC"
    sql = text(
        f"""
        SELECT emag_offer_id, emag_product_id, product_name,
               currency, sale_price, stock, is_available,
               account_type, updated_at
        FROM app.v_emag_offers
        {where_sql}
        ORDER BY {{sort_field}} {{sort_dir}} NULLS LAST
        LIMIT :limit
        """
    )
    params["limit"] = limit

    with engine.begin() as conn:
        # Ensure schema is available
        conn.exec_driver_sql("SET search_path TO app,public")
        rows = conn.execute(
            text(
                (sql.text)
                .replace("{sort_field}", sort_field)
                .replace("{sort_dir}", sort_dir)
            ),
            params,
        ).fetchall()

    print(f"Rows: {len(rows)} -> {out_path}")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "emag_offer_id",
                "emag_product_id",
                "product_name",
                "currency",
                "sale_price",
                "stock",
                "is_available",
                "account_type",
                "updated_at",
            ],
        )
        writer.writeheader()
        for r in rows:
            writer.writerow(dict(r._mapping))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export eMAG offers to CSV")
    parser.add_argument("--account", choices=["main", "fbe"], help="Filter by account type")
    parser.add_argument("--search", help="Search in product name (ILIKE)")
    parser.add_argument("--limit", type=int, default=1000, help="Limit rows")
    parser.add_argument("--out", required=True, help="Output CSV path")
    parser.add_argument("--db", help="Override DB URL (postgresql://user:pass@host:port/db)")
    # Rich filters and sorting
    parser.add_argument("--min-price", type=float, help="Minimum sale_price")
    parser.add_argument("--max-price", type=float, help="Maximum sale_price")
    parser.add_argument("--stock-gt", type=int, help="Stock strictly greater than value")
    parser.add_argument(
        "--only-available",
        action="store_true",
        help="Only offers where is_available is true",
    )
    parser.add_argument(
        "--sort-by",
        choices=["updated_at", "sale_price", "stock"],
        default="updated_at",
        help="Sort field",
    )
    parser.add_argument(
        "--order",
        choices=["asc", "desc"],
        default="desc",
        help="Sort order",
    )
    args = parser.parse_args()

    export_offers(
        args.account,
        args.search,
        args.limit,
        args.out,
        args.db,
        min_price=args.min_price,
        max_price=args.max_price,
        stock_gt=args.stock_gt,
        only_available=args.only_available,
        sort_by=args.sort_by,
        order=args.order,
    )
