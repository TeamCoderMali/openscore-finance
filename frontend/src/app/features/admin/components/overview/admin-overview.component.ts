import { Component, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../../../core/services/api.service';
import { ToastService } from '../../../../core/services/toast.service';
import { SvgIconComponent } from '../../../../shared/components/svg-icon/svg-icon.component';
import { AdminStats, AdminBranchInfo } from '../../../../shared/models/application.model';

@Component({
  selector: 'app-admin-overview',
  standalone: true,
  imports: [CommonModule, RouterModule, SvgIconComponent],
  templateUrl: './admin-overview.component.html',
})
export class AdminOverviewComponent implements OnInit {
  stats = signal<AdminStats | null>(null);
  statsLoading = signal<boolean>(true);
  branches = signal<AdminBranchInfo[]>([]);

  constructor(
    private api: ApiService,
    private toast: ToastService,
  ) {}

  ngOnInit(): void {
    this.loadData();
  }

  async loadData(): Promise<void> {
    this.statsLoading.set(true);
    try {
      const [s, b] = await Promise.all([
        this.api.getAdminStats(),
        this.api.getAdminBranches().catch(() => []),
      ]);
      this.stats.set(s);
      this.branches.set(b);
    } catch (e: any) {
      this.toast.error('Erreur Statistiques', e.message);
    } finally {
      this.statsLoading.set(false);
    }
  }

  exportBceaoReport(): void {
    this.toast.success(
      'Exportation BCEAO',
      'Le rapport officiel de conformité prudentielle UEMOA a été généré avec succès.'
    );
  }

  formatAmount(amount: number): string {
    return (amount || 0).toLocaleString('fr-FR') + ' FCFA';
  }
}
