/**
 * Permission Guard
 * 
 * Protects routes/components based on user permissions
 */

import { useAuth } from '../contexts/AuthContext';
import { hasPermission } from '../constants/permissions';

interface PermissionGuardProps {
  permission: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export const PermissionGuard: React.FC<PermissionGuardProps> = ({
  permission,
  children,
  fallback = null,
}) => {
  const { user } = useAuth();

  if (!user || !hasPermission(user.role, permission)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
};

/**
 * Hook to check permissions
 */
export const usePermission = (permission: string): boolean => {
  const { user } = useAuth();
  
  if (!user) return false;
  return hasPermission(user.role, permission);
};

/**
 * Hook to check multiple permissions (requires all)
 */
export const usePermissions = (permissions: string[]): boolean => {
  const { user } = useAuth();
  
  if (!user) return false;
  return permissions.every(permission => hasPermission(user.role, permission));
};

/**
 * Hook to check if user has any of the permissions
 */
export const useAnyPermission = (permissions: string[]): boolean => {
  const { user } = useAuth();
  
  if (!user) return false;
  return permissions.some(permission => hasPermission(user.role, permission));
};
