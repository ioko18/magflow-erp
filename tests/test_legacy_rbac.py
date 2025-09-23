"""Unit tests for RBAC (Role-Based Access Control) service."""

import pytest
from fastapi import HTTPException

from app.services.rbac_service import AuditService, RBACService


@pytest.mark.asyncio
class TestRBACService:
    """Test RBAC service functionality."""

    async def test_has_permission_superuser(self, db_session, test_user):
        """Test that superusers have all permissions."""
        # Make user a superuser
        test_user.is_superuser = True

        rbac_service = RBACService(db_session)

        # Test that superuser has any permission
        assert (
            await rbac_service.has_permission(test_user, "any_resource", "any_action")
            is True
        )
        assert await rbac_service.has_permission(test_user, "users", "read") is True
        assert await rbac_service.has_permission(test_user, "products", "write") is True

    async def test_has_permission_regular_user_no_roles(self, db_session, test_user):
        """Test that users without roles have no permissions."""
        rbac_service = RBACService(db_session)

        # Test that user without roles has no permissions
        assert await rbac_service.has_permission(test_user, "users", "read") is False
        assert (
            await rbac_service.has_permission(test_user, "products", "write") is False
        )

    async def test_has_permission_with_roles(self, db_session, test_user, test_roles):
        """Test permission checking with roles."""
        rbac_service = RBACService(db_session)

        # Assign user role to test user
        test_user.roles.append(test_roles["user"])
        await db_session.commit()

        # User should have user_read permission
        assert await rbac_service.has_permission(test_user, "users", "read") is True

        # User should not have user_write permission
        assert await rbac_service.has_permission(test_user, "users", "write") is False

    async def test_require_permission_success(self, db_session, test_user, test_roles):
        """Test successful permission requirement."""
        rbac_service = RBACService(db_session)

        # Assign user role to test user
        test_user.roles.append(test_roles["user"])
        await db_session.commit()

        # Should not raise exception for valid permission
        await rbac_service.require_permission(test_user, "users", "read")

    async def test_require_permission_failure(self, db_session, test_user, test_roles):
        """Test failed permission requirement."""
        rbac_service = RBACService(db_session)

        # Assign user role to test user
        test_user.roles.append(test_roles["user"])
        await db_session.commit()

        # Should raise exception for invalid permission
        with pytest.raises(HTTPException) as exc_info:
            await rbac_service.require_permission(test_user, "users", "write")

        assert exc_info.value.status_code == 403
        assert "Access denied" in str(exc_info.value.detail)

    async def test_get_user_permissions_superuser(
        self, db_session, test_user, test_permissions
    ):
        """Test getting permissions for superuser."""
        test_user.is_superuser = True

        rbac_service = RBACService(db_session)

        permissions = await rbac_service.get_user_permissions(test_user)

        # Superuser should have all permissions
        assert len(permissions) == len(test_permissions)
        permission_names = [p["resource"] + "_" + p["action"] for p in permissions]
        for perm_name in test_permissions.keys():
            assert perm_name in permission_names

    async def test_get_user_permissions_regular_user(
        self, db_session, test_user, test_roles
    ):
        """Test getting permissions for regular user."""
        rbac_service = RBACService(db_session)

        # Assign user role to test user
        test_user.roles.append(test_roles["user"])
        await db_session.commit()

        permissions = await rbac_service.get_user_permissions(test_user)

        # User should have only user_read permission
        assert len(permissions) == 1
        assert permissions[0]["resource"] == "users"
        assert permissions[0]["action"] == "read"

    async def test_assign_role_to_user(self, db_session, test_user, test_roles):
        """Test assigning role to user."""
        rbac_service = RBACService(db_session)

        # Assign role
        await rbac_service.assign_role_to_user(test_user, test_roles["user"])

        # Check that role was assigned
        assert test_roles["user"] in test_user.roles
        assert len(test_user.roles) == 1

    async def test_remove_role_from_user(self, db_session, test_user, test_roles):
        """Test removing role from user."""
        rbac_service = RBACService(db_session)

        # First assign role
        test_user.roles.append(test_roles["user"])
        await db_session.commit()

        # Then remove role
        await rbac_service.remove_role_from_user(test_user, test_roles["user"])

        # Check that role was removed
        assert test_roles["user"] not in test_user.roles
        assert len(test_user.roles) == 0


@pytest.mark.asyncio
class TestAuditService:
    """Test audit logging functionality."""

    async def test_log_action_success(self, db_session, test_user):
        """Test successful action logging."""
        audit_service = AuditService(db_session)

        # Log an action
        await audit_service.log_action(
            user=test_user,
            action="test_action",
            resource="test_resource",
            details={"key": "value"},
            success=True,
        )

        # Check that audit log was created
        result = await db_session.execute(
            "SELECT * FROM audit_logs WHERE user_id = ? AND action = ?",
            (test_user.id, "test_action"),
        )
        audit_log = result.fetchone()

        assert audit_log is not None
        assert audit_log.user_id == test_user.id
        assert audit_log.action == "test_action"
        assert audit_log.resource == "test_resource"
        assert audit_log.success
        assert '"key": "value"' in audit_log.details

    async def test_log_action_no_user(self, db_session):
        """Test logging action with no user."""
        audit_service = AuditService(db_session)

        # Log an action without user
        await audit_service.log_action(
            user=None,
            action="system_action",
            resource="system",
            success=True,
        )

        # Check that audit log was created
        result = await db_session.execute(
            "SELECT * FROM audit_logs WHERE user_id IS NULL AND action = ?",
            ("system_action",),
        )
        audit_log = result.fetchone()

        assert audit_log is not None
        assert audit_log.user_id is None
        assert audit_log.action == "system_action"
        assert audit_log.success

    async def test_get_user_audit_logs(self, db_session, test_user):
        """Test getting audit logs for a user."""
        audit_service = AuditService(db_session)

        # Create some audit logs
        for i in range(3):
            await audit_service.log_action(
                user=test_user,
                action=f"test_action_{i}",
                resource="test_resource",
                success=True,
            )

        # Get user audit logs
        audit_logs = await audit_service.get_user_audit_logs(test_user, limit=10)

        assert len(audit_logs) == 3
        assert all(log.user_id == test_user.id for log in audit_logs)

        # Check ordering (should be newest first)
        assert audit_logs[0].action == "test_action_2"
        assert audit_logs[1].action == "test_action_1"
        assert audit_logs[2].action == "test_action_0"

    async def test_get_audit_logs_with_filters(self, db_session, test_user):
        """Test getting audit logs with filters."""
        audit_service = AuditService(db_session)

        # Create audit logs with different actions and resources
        await audit_service.log_action(test_user, "login", "auth", success=True)
        await audit_service.log_action(test_user, "logout", "auth", success=True)
        await audit_service.log_action(test_user, "create", "products", success=True)
        await audit_service.log_action(test_user, "update", "users", success=False)

        # Test filtering by action
        login_logs = await audit_service.get_audit_logs(action="login")
        assert len(login_logs) == 1
        assert login_logs[0].action == "login"

        # Test filtering by resource
        auth_logs = await audit_service.get_audit_logs(resource="auth")
        assert len(auth_logs) == 2
        assert all(log.resource == "auth" for log in auth_logs)

        # Test filtering by user_id
        user_logs = await audit_service.get_audit_logs(user_id=test_user.id)
        assert len(user_logs) == 4
        assert all(log.user_id == test_user.id for log in user_logs)

        # Test filtering by multiple criteria
        failed_logs = await audit_service.get_audit_logs(
            user_id=test_user.id,
            success=False,
        )
        assert len(failed_logs) == 1
        assert not failed_logs[0].success
