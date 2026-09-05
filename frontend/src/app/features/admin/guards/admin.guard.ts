import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';

export const adminGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const toast = inject(ToastService);

  if (!auth.isAuthenticated()) {
    router.navigate(['/login']);
    return false;
  }

  if (auth.userRole() !== 'admin') {
    toast.error('Accès refusé', 'Espace strictement réservé à la Direction Générale et aux Super Administrateurs.');
    auth.navigateToDashboard();
    return false;
  }

  return true;
};
