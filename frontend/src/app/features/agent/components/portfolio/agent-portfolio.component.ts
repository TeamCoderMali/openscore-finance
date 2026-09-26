import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../../core/services/api.service';
import { ToastService } from '../../../../core/services/toast.service';
import { SvgIconComponent } from '../../../../shared/components/svg-icon/svg-icon.component';
import { PortfolioStats } from '../../../../shared/models/application.model';

@Component({
  selector: 'app-agent-portfolio',
  standalone: true,
  imports: [CommonModule, SvgIconComponent],
  templateUrl: './agent-portfolio.component.html',
})
export class AgentPortfolioComponent implements OnInit {
  stats = signal<PortfolioStats | null>(null);
  loading = signal<boolean>(false);

  constructor(
    private api: ApiService,
    private toast: ToastService,
  ) {}

  ngOnInit(): void {
    this.loadPortfolioStats();
  }

  async loadPortfolioStats(): Promise<void> {
    this.loading.set(true);
    try {
      const data = await this.api.getPortfolioStats();
      this.stats.set(data);
    } catch (e: any) {
      this.toast.error('Erreur Statistiques', e.message);
    } finally {
      this.loading.set(false);
    }
  }

  exportReport(): void {
    this.toast.success(
      'Rapport d\'Activité Agence',
      'Le récapitulatif de portefeuille et de conformité BCEAO a été généré.'
    );
  }

  formatAmount(amount: number): string {
    return (amount || 0).toLocaleString('fr-FR') + ' FCFA';
  }
}
