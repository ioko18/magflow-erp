from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..db import get_db

router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    """Get current search_path and PostgreSQL extensions"""

    # Get current search_path
    search_path_result = db.execute(text("SHOW search_path")).fetchone()
    search_path = search_path_result[0] if search_path_result else "unknown"

    # Get installed extensions
    extensions_result = db.execute(
        text(
            """
        SELECT extname, extversion
        FROM pg_extension
        ORDER BY extname
    """
        )
    ).fetchall()

    extensions = [{"name": ext[0], "version": ext[1]} for ext in extensions_result]

    return {"search_path": search_path, "extensions": extensions, "database": "magflow"}


@router.get("/active")
def get_active_processes(db: Session = Depends(get_db)):
    """List active PostgreSQL processes (limit 20)"""

    result = db.execute(
        text(
            """
        SELECT
            pid,
            usename,
            application_name,
            client_addr,
            state,
            query_start,
            LEFT(query, 100) as query_preview
        FROM pg_stat_activity
        WHERE state != 'idle'
        ORDER BY query_start DESC
        LIMIT 20
    """
        )
    ).fetchall()

    processes = []
    for row in result:
        processes.append(
            {
                "pid": row[0],
                "user": row[1],
                "application": row[2],
                "client_addr": str(row[3]) if row[3] else None,
                "state": row[4],
                "query_start": row[5].isoformat() if row[5] else None,
                "query_preview": row[6],
            }
        )

    return {"active_processes": processes, "count": len(processes)}


@router.get("/locks")
def get_locks(db: Session = Depends(get_db)):
    """List current PostgreSQL locks (simple aggregate)"""

    result = db.execute(
        text(
            """
        SELECT
            mode,
            locktype,
            COUNT(*) as count
        FROM pg_locks
        WHERE NOT granted = false
        GROUP BY mode, locktype
        ORDER BY count DESC
    """
        )
    ).fetchall()

    locks = []
    for row in result:
        locks.append({"mode": row[0], "type": row[1], "count": row[2]})

    return {"locks": locks, "total_locks": sum(lock["count"] for lock in locks)}


@router.get("/stats")
def get_query_stats(db: Session = Depends(get_db)):
    """Get top queries from pg_stat_statements"""

    result = db.execute(
        text(
            """
        SELECT
            LEFT(query, 200) as query_preview,
            calls,
            total_exec_time,
            mean_exec_time,
            rows
        FROM pg_stat_statements
        WHERE query NOT LIKE '%pg_stat_statements%'
        ORDER BY total_exec_time DESC
        LIMIT 10
    """
        )
    ).fetchall()

    stats = []
    for row in result:
        stats.append(
            {
                "query_preview": row[0],
                "calls": row[1],
                "total_exec_time": float(row[2]) if row[2] else 0.0,
                "mean_exec_time": float(row[3]) if row[3] else 0.0,
                "rows": row[4] if row[4] else 0,
            }
        )

    return {"top_queries": stats, "count": len(stats)}
