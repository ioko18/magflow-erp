"""Database initialization script for RBAC and audit logging.

This script sets up the initial roles, permissions, and creates an admin user.
Run this after creating the database tables.
"""

import asyncio
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.append('/Users/macos/anaconda3/envs/MagFlow')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

from app.core.config import settings
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.services.rbac_service import AuditService


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_initial_data():
    """Create initial roles, permissions, and admin user."""

    # Create async engine
    engine = create_async_engine(settings.DB_URI, echo=False)

    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        try:
            print("🚀 Starting database initialization...")

            # Create audit service for logging
            audit_service = AuditService(session)

            # Log the initialization action
            await audit_service.log_action(
                user=None,
                action="system_initialization",
                resource="database",
                details={"action": "initial_setup"},
                success=True
            )

            # 1. Create eMAG tables
            print("🛒 Creating eMAG tables...")
            from app.db.base_class import Base

            # Create all tables
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            print("✅ Created eMAG tables")

            # 2. Create basic permissions
            print("📝 Creating permissions...")
            permissions_data = [
                # User management permissions
                ("users_read", "users", "read", "View user information"),
                ("users_write", "users", "write", "Create and edit users"),
                ("users_delete", "users", "delete", "Delete users"),
                ("users_manage", "users", "manage", "Full user management"),

                # Role management permissions
                ("roles_read", "roles", "read", "View roles"),
                ("roles_write", "roles", "write", "Create and edit roles"),
                ("roles_delete", "roles", "delete", "Delete roles"),
                ("roles_manage", "roles", "manage", "Full role management"),

                # Product management permissions
                ("products_read", "products", "read", "View products"),
                ("products_write", "products", "write", "Create and edit products"),
                ("products_delete", "products", "delete", "Delete products"),
                ("products_manage", "products", "manage", "Full product management"),

                # Category management permissions
                ("categories_read", "categories", "read", "View categories"),
                ("categories_write", "categories", "write", "Create and edit categories"),
                ("categories_delete", "categories", "delete", "Delete categories"),
                ("categories_manage", "categories", "manage", "Full category management"),

                # Audit log permissions
                ("audit_read", "audit", "read", "View audit logs"),
                ("audit_manage", "audit", "manage", "Manage audit logs"),

                # System permissions
                ("system_read", "system", "read", "View system information"),
                ("system_manage", "system", "manage", "System administration"),
            ]

            permissions = {}
            for name, resource, action, description in permissions_data:
                permission = Permission(
                    name=name,
                    resource=resource,
                    action=action,
                    description=description
                )
                session.add(permission)
                permissions[name] = permission

            await session.flush()  # Get permission IDs
            print(f"✅ Created {len(permissions)} permissions")

            # 2. Create roles
            print("👤 Creating roles...")
            roles_data = [
                ("admin", "System Administrator", True, [
                    "users_read", "users_write", "users_delete", "users_manage",
                    "roles_read", "roles_write", "roles_delete", "roles_manage",
                    "products_read", "products_write", "products_delete", "products_manage",
                    "categories_read", "categories_write", "categories_delete", "categories_manage",
                    "audit_read", "audit_manage",
                    "system_read", "system_manage"
                ]),
                ("manager", "Manager", False, [
                    "users_read", "users_write",
                    "products_read", "products_write", "products_manage",
                    "categories_read", "categories_write", "categories_manage",
                    "audit_read"
                ]),
                ("employee", "Employee", False, [
                    "products_read",
                    "categories_read"
                ]),
                ("viewer", "Viewer", False, [
                    "products_read",
                    "categories_read"
                ])
            ]

            roles = {}
            for name, description, is_system, perm_names in roles_data:
                role = Role(
                    name=name,
                    description=description,
                    is_system_role=is_system
                )

                # Add permissions to role
                for perm_name in perm_names:
                    if perm_name in permissions:
                        role.permissions.append(permissions[perm_name])

                session.add(role)
                roles[name] = role

            await session.flush()  # Get role IDs
            print(f"✅ Created {len(roles)} roles")

            # 3. Create admin user
            print("👨‍💼 Creating admin user...")
            admin_password = "Admin123!"  # In production, this should be from environment variable
            hashed_password = pwd_context.hash(admin_password)

            admin_user = User(
                email="admin@magflow.local",
                hashed_password=hashed_password,
                full_name="System Administrator",
                is_active=True,
                is_superuser=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                last_login=None,
                failed_login_attempts=0
            )

            # Assign admin role to admin user
            admin_user.roles.append(roles["admin"])

            session.add(admin_user)
            await session.flush()  # Get user ID

            # Log admin user creation
            await audit_service.log_action(
                user=admin_user,
                action="user_created",
                resource="users",
                resource_id=str(admin_user.id),
                details={"email": admin_user.email, "role": "admin"},
                success=True
            )

            print("✅ Created admin user:")
            print(f"   Email: {admin_user.email}")
            print(f"   Password: {admin_password}")
            print(f"   Superuser: {admin_user.is_superuser}")
            print(f"   Roles: {[role.name for role in admin_user.roles]}")

            # 4. Commit all changes
            await session.commit()
            print("💾 Database initialization completed successfully!")

            # 5. Show summary
            print("📊 Summary:")
            print(f"   - Permissions created: {len(permissions)}")
            print(f"   - Roles created: {len(roles)}")
            print("   - Admin user created: 1")
            print("   - Audit logs created: 2")
            print("   - eMAG tables created: 4")

            print("\n🔐 Default Admin Credentials:")
            print("   Email: admin@magflow.local")
            print(f"   Password: {admin_password}")
            print("\n⚠️  IMPORTANT: Change the admin password after first login!")

        except Exception as e:
            await session.rollback()
            print(f"❌ Error during initialization: {e}")
            import traceback
            traceback.print_exc()
            raise


async def main():
    """Main function to run the initialization."""
    print("🗄️  MagFlow ERP Database Initialization")
    print("=" * 50)

    try:
        await create_initial_data()
        print("\n✅ Initialization completed successfully!")
    except Exception as e:
        print(f"\n❌ Initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
