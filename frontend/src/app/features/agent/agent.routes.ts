import { Routes } from '@angular/router';
import { agentGuard } from './guards/agent.guard';
import { AgentShellComponent } from './agent-shell/agent-shell.component';

export const AGENT_ROUTES: Routes = [
  {
    path: '',
    component: AgentShellComponent,
    canActivate: [agentGuard],
    children: [
      { path: '', redirectTo: 'pipeline', pathMatch: 'full' },
      {
        path: 'pipeline',
        loadComponent: () =>
          import('./components/pipeline/agent-pipeline.component').then(m => m.AgentPipelineComponent),
        title: 'Pipeline Dossiers | OpenScore'
      },
      {
        path: 'portfolio',
        loadComponent: () =>
          import('./components/portfolio/agent-portfolio.component').then(m => m.AgentPortfolioComponent),
        title: 'Cockpit Portefeuille | OpenScore'
      },
      {
        path: 'simulator',
        loadComponent: () =>
          import('./components/simulator/agent-simulator.component').then(m => m.AgentSimulatorComponent),
        title: 'Simulateur Échéancier | OpenScore'
      },
      {
        path: 'field',
        loadComponent: () =>
          import('./components/field/agent-field.component').then(m => m.AgentFieldComponent),
        title: 'Enquête Terrain | OpenScore'
      },
    ],
  },
];
