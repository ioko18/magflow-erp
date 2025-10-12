"""Script to check if models are properly imported and accessible."""

from app.db.base_class import Base
from app.db.models import RefreshToken, User
from app.models.mapping import (
    BrandMapping,
    CategoryMapping,
    CharacteristicMapping,
    MappingConfiguration,
    ProductFieldMapping,
    ProductMapping,
    SyncHistory,
)
from app.models.role import Permission, Role

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
