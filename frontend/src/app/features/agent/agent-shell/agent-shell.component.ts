import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs';

@Component({
  selector: 'app-agent-shell',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './agent-shell.component.html',
})
export class AgentShellComponent implements OnInit {
  currentUrl = signal<string>('');

  currentTitle = computed(() => {
    const url = this.currentUrl();
    if (url.includes('/agent/portfolio')) return 'Cockpit Analytique & Qualité du Portefeuille Agence';
    if (url.includes('/agent/simulator')) return 'Simulateur Interactif d\'Amortissement & Mensualités';
    if (url.includes('/agent/field')) return 'Console d\'Enquête de Proximité & Garanties Terrain';
    return 'Console Agence — Pipeline des Dossiers de Crédit';
  });

  constructor(private router: Router) {}

  ngOnInit(): void {
    this.currentUrl.set(this.router.url);
    this.router.events
      .pipe(filter(e => e instanceof NavigationEnd))
      .subscribe((e: any) => {
        this.currentUrl.set(e.urlAfterRedirects || e.url);
      });
  }
}
