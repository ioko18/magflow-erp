/**
 * Role Guard
 * 
 * Protects routes/components based on user roles
 */

import { useAuth } from '../contexts/AuthContext';
import { ROLES } from '../constants/permissions';

interface RoleGuardProps {
  roles: string[];
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export const RoleGuard: React.FC<RoleGuardProps> = ({
  roles,
  children,
  fallback = null,
}) => {
  const { user } = useAuth();

  if (!user || !roles.includes(user.role)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
};

/**
 * Hook to check if user has specific role
 */
export const useRole = (role: string): boolean => {
  const { user } = useAuth();
  return user?.role === role;
};

/**
 * Hook to check if user has any of the roles
 */
export const useAnyRole = (roles: string[]): boolean => {
  const { user } = useAuth();
  return user ? roles.includes(user.role) : false;
};

/**
 * Hook to check if user is admin
 */
export const useIsAdmin = (): boolean => {
  return useRole(ROLES.ADMIN);
};

/**
 * Hook to check if user is manager or admin
 */
export const useIsManagerOrAdmin = (): boolean => {
  return useAnyRole([ROLES.ADMIN, ROLES.MANAGER]);
};
