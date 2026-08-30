import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () =>
      import('./features/login/login.component').then(m => m.LoginComponent),
  },
  {
    path: 'client',
    loadComponent: () =>
      import('./features/client-portal/client-portal.component').then(m => m.ClientPortalComponent),
    canActivate: [authGuard],
    data: { role: 'client' },
  },
  {
    path: 'agent',
    loadComponent: () =>
      import('./features/agent-workspace/agent-workspace.component').then(m => m.AgentWorkspaceComponent),
    canActivate: [authGuard],
    data: { role: 'agent' },
  },
  {
    path: 'admin',
    loadComponent: () =>
      import('./features/admin-dashboard/admin-dashboard.component').then(m => m.AdminDashboardComponent),
    canActivate: [authGuard],
    data: { role: 'admin' },
  },
  {
    path: 'audit/:id',
    loadComponent: () =>
      import('./features/score-audit/score-audit.component').then(m => m.ScoreAuditComponent),
    canActivate: [authGuard],
  },
  {
    path: 'receipt/:id',
    loadComponent: () =>
      import('./features/receipt-view/receipt-view.component').then(m => m.ReceiptViewComponent),
    canActivate: [authGuard],
  },
  {
    path: '',
    redirectTo: 'login',
    pathMatch: 'full',
  },
  {
    path: '**',
    redirectTo: 'login',
  },
];
