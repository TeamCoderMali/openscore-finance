import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = (route) => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (!auth.isAuthenticated()) {
    router.navigate(['/login']);
    return false;
  }

  // Check role if specified in route data
  const requiredRole = route.data?.['role'] as string | undefined;
  if (requiredRole && auth.userRole() !== requiredRole) {
    auth.navigateToDashboard();
    return false;
  }

  return true;
};
