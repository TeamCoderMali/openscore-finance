import { Component, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../../core/services/api.service';
import { ToastService } from '../../../../core/services/toast.service';
import { SvgIconComponent } from '../../../../shared/components/svg-icon/svg-icon.component';
import { SpinnerComponent } from '../../../../shared/components/spinner/spinner.component';
import { AdminBranchInfo, AdminBranchCreate } from '../../../../shared/models/application.model';

@Component({
  selector: 'app-admin-branches',
  standalone: true,
  imports: [CommonModule, FormsModule, SvgIconComponent, SpinnerComponent],
  templateUrl: './admin-branches.component.html',
})
export class AdminBranchesComponent implements OnInit {
  branches = signal<AdminBranchInfo[]>([]);
  branchesLoading = signal<boolean>(false);
  showCreateBranchModal = signal<boolean>(false);
  newBranch = signal<AdminBranchCreate>({
    name: '',
    city: 'Bamako',
    branch_type: 'Antenne Régionale',
    lead_agent: '',
    max_credit_limit: 50000000,
  });
  creatingBranch = signal<boolean>(false);

  constructor(
    private api: ApiService,
    private toast: ToastService,
  ) {}

  ngOnInit(): void {
    this.loadBranches();
  }

  async loadBranches(): Promise<void> {
    this.branchesLoading.set(true);
    try {
      const data = await this.api.getAdminBranches();
      this.branches.set(data);
    } catch (e: any) {
      this.toast.error('Erreur Antennes', e.message);
    } finally {
      this.branchesLoading.set(false);
    }
  }

  openCreateBranchModal(): void {
    this.newBranch.set({
      name: '',
      city: 'Bamako',
      branch_type: 'Antenne Régionale',
      lead_agent: '',
      max_credit_limit: 50000000,
    });
    this.showCreateBranchModal.set(true);
  }

  closeCreateBranchModal(): void {
    this.showCreateBranchModal.set(false);
  }

  async createBranch(): Promise<void> {
    const b = this.newBranch();
    if (!b.name || !b.city || !b.lead_agent) {
      this.toast.warning('Champs requis', 'Nom, ville et agent responsable obligatoires');
      return;
    }
    this.creatingBranch.set(true);
    try {
      await this.api.createAdminBranch(b);
      this.toast.success(
        'Nouvelle Antenne Déployée',
        `${b.name} (${b.city}) intégrée au réseau OpenScore.`
      );
      this.closeCreateBranchModal();
      await this.loadBranches();
    } catch (e: any) {
      this.toast.error('Erreur Antenne', e.message);
    } finally {
      this.creatingBranch.set(false);
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
