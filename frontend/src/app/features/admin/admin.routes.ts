import { Routes } from '@angular/router';
import { adminGuard } from './guards/admin.guard';
import { AdminShellComponent } from './admin-shell/admin-shell.component';

export const ADMIN_ROUTES: Routes = [
  {
    path: '',
    component: AdminShellComponent,
    canActivate: [adminGuard],
    children: [
      { path: '', redirectTo: 'overview', pathMatch: 'full' },
      {
        path: 'overview',
        loadComponent: () =>
          import('./components/overview/admin-overview.component').then(m => m.AdminOverviewComponent),
        title: 'Cockpit Direction IMF | OpenScore'
      },
      {
        path: 'clients',
        loadComponent: () =>
          import('./components/clients/admin-clients.component').then(m => m.AdminClientsComponent),
        title: 'Gestion Clients Emprunteurs | OpenScore'
      },
      {
        path: 'agents',
        loadComponent: () =>
          import('./components/agents/admin-agents.component').then(m => m.AdminAgentsComponent),
        title: 'Pilotage Agents de Crédit | OpenScore'
      },
      {
        path: 'branches',
        loadComponent: () =>
          import('./components/branches/admin-branches.component').then(m => m.AdminBranchesComponent),
        title: 'Antennes Régionales & Guichets | OpenScore'
      },
      {
        path: 'risk',
        loadComponent: () =>
          import('./components/risk/admin-risk.component').then(m => m.AdminRiskComponent),
        title: 'Matrice Risque & Stress-Testing | OpenScore'
      },
      {
        path: 'settings',
        loadComponent: () =>
          import('./components/settings/admin-settings.component').then(m => m.AdminSettingsComponent),
        title: 'Politique Prudentielle BCEAO | OpenScore'
      },
      {
        path: 'audit',
        loadComponent: () =>
          import('./components/audit/admin-audit.component').then(m => m.AdminAuditComponent),
        title: 'Piste d\'Audit Institutionnelle | OpenScore'
      },
    ],
  },
];
