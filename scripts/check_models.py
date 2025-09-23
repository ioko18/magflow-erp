"""Script to check if models are properly imported and accessible."""

from app.models.base import Base
from app.db.models import User, RefreshToken
from app.models.role import Role, Permission
from app.models.mapping import (
    ProductMapping,
    CategoryMapping,
    BrandMapping,
    CharacteristicMapping,
    ProductFieldMapping,
    SyncHistory,
    MappingConfiguration,
)

# List all tables defined in the models
print("Tables defined in models:")
for table in Base.metadata.tables.values():
    print(f"- {table.schema}.{table.name}")

# Check if all models are properly imported
models = [
    User,
    RefreshToken,
    Role,
    Permission,
    ProductMapping,
    CategoryMapping,
    BrandMapping,
    CharacteristicMapping,
    ProductFieldMapping,
    SyncHistory,
    MappingConfiguration,
]

print("\nModels imported successfully:")
for model in models:
    print(f"- {model.__name__}")
