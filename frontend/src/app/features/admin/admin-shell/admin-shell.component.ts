import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs';

@Component({
  selector: 'app-admin-shell',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './admin-shell.component.html',
})
export class AdminShellComponent implements OnInit {
  currentUrl = signal<string>('');

  currentTitle = computed(() => {
    const url = this.currentUrl();
    if (url.includes('/admin/clients')) return 'Gestion Complète des Clients Emprunteurs';
    if (url.includes('/admin/agents')) return 'Pilotage & Performance des Agents de Crédit';
    if (url.includes('/admin/branches')) return 'Réseau des Antennes Régionales & Guichets';
    if (url.includes('/admin/risk')) return 'Matrice PAR & Stress-Testing Prudentiel BCEAO';
    if (url.includes('/admin/settings')) return 'Politique Prudentielle & Seuils BCEAO';
    if (url.includes('/admin/audit')) return 'Piste d\'Audit Globale Consolidée';
    return 'Cockpit Direction & Liquidité IMF';
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
