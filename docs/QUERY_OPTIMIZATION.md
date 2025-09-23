# Query Optimization Guide

This document outlines the tools and practices for optimizing database queries in the application.

## ORM Helpers

The `app.db.orm_helpers` module provides utilities for efficient data loading with SQLAlchemy.

### Loading Strategies

1. **Select-in Loading** (Recommended for most cases)
   ```python
   from app.db.orm_helpers import with_joinedload

   # Basic usage
   query = session.query(Product).options(
       *with_joinedload('category', 'tags', strategy='selectin')
   )
   ```

2. **Joined Loading** (Use for small, frequently accessed relationships)
   ```python
   from app.db.orm_helpers import with_joinedload

   query = session.query(Order).options(
       *with_joinedload('customer', 'items', strategy='joined')
   )
   ```

3. **Model-Specific Loading**
   ```python
   from app.db.orm_helpers import get_loader

   # Automatically loads all columns for Product model
   query = session.query(Product).options(
       *get_loader(Product, 'category', 'tags')
   )
   ```

## Explain Plan Testing

We use PostgreSQL's EXPLAIN ANALYZE to verify query performance.

### Running Tests

```bash
# Run all explain plan tests
pytest tests/explain -v

# Run tests for a specific module
pytest tests/explain/test_plans.py -v
```

### Writing Tests

```python
def test_product_list_plan(db):
    """Test that product listing uses efficient indexes."""
    query = """
    SELECT p.*, c.name as category_name
    FROM products p
    JOIN categories c ON p.category_id = c.id
    WHERE p.is_active = true
    ORDER BY p.created_at DESC
    LIMIT 20
    """

    plan = assert_good_plan(
        db, query,
        context="Product listing should use index for sorting and filtering"
    )

    # Additional assertions
    assert plan['Plan']['Node Type'].lower() != 'seq scan'
```

### Allowed Scan Types

| Scan Type       | Allowed | Notes                           |
|-----------------|---------|---------------------------------|
| Index Scan      | ✅      | Always allowed                  |
| Index Only Scan | ✅      | Always allowed                  |
| Bitmap Scan     | ✅      | For OR conditions               |
| Seq Scan        | ⚠️      | Only on small tables (<1000 rows) |

## Performance Best Practices

1. **Always use EXPLAIN ANALYZE** for new queries
2. **Avoid N+1 queries** by using eager loading
3. **Add indexes** for all foreign keys and frequently filtered columns
4. **Use pagination** for large result sets
5. **Monitor slow queries** in production

## CI Integration

Explain plan tests run automatically in CI and will fail if:
- A sequential scan is detected on large tables
- A query doesn't use available indexes
- Query performance degrades significantly

## Troubleshooting

### Common Issues

1. **Seq Scan on Large Table**
   - Add an appropriate index
   - Check if the query can be optimized
   - Consider materialized views for complex queries

2. **Slow COUNT Queries**
   - Use `EXPLAIN ANALYZE` to identify bottlenecks
   - Consider approximate counts for large tables
   - Cache count results when possible

3. **High Memory Usage**
   - Reduce the result set size
   - Use server-side cursors for large results
   - Check for cartesian products in joins
