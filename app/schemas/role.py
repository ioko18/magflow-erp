"""Pydantic models for role and permission data validation and serialization."""


from pydantic import BaseModel, ConfigDict, Field


class PermissionBase(BaseModel):
    """Base permission schema with common fields."""

    name: str = Field(..., min_length=1, max_length=50)
    description: str | None = Field(None, max_length=255)


class PermissionCreate(PermissionBase):
    """Schema for creating a new permission."""


class PermissionUpdate(PermissionBase):
    """Schema for updating a permission."""

    name: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = Field(None, max_length=255)


class PermissionInDBBase(PermissionBase):
    """Base schema for permission data in the database."""

    id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class Permission(PermissionInDBBase):
    """Schema for permission data returned to clients."""


class PermissionInDB(PermissionInDBBase):
    """Schema for permission data stored in the database."""


class RoleBase(BaseModel):
    """Base role schema with common fields."""

    name: str = Field(..., min_length=1, max_length=50)
    description: str | None = Field(None, max_length=255)
    is_active: bool = True


class RoleCreate(RoleBase):
    """Schema for creating a new role."""


class RoleUpdate(RoleBase):
    """Schema for updating a role."""

    name: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = Field(None, max_length=255)
    is_active: bool | None = None


class RoleInDBBase(RoleBase):
    """Base schema for role data in the database."""

    id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class Role(RoleInDBBase):
    """Schema for role data returned to clients."""


class RoleInDB(RoleInDBBase):
    """Schema for role data stored in the database."""


class RoleWithPermissions(Role):
    """Role schema with permissions included."""

    permissions: list[Permission] = []


class PermissionWithRoles(Permission):
    """Permission schema with roles included."""

    roles: list[Role] = []
