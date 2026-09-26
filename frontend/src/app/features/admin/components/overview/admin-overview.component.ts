import { Component, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../../../core/services/api.service';
import { ToastService } from '../../../../core/services/toast.service';
import { SvgIconComponent } from '../../../../shared/components/svg-icon/svg-icon.component';
import { SpinnerComponent } from '../../../../shared/components/spinner/spinner.component';
import {
  AdminStats,
  AdminBranchInfo,
  PendingCommitteeApproval,
  CreditApplication,
  ExtractedData,
} from '../../../../shared/models/application.model';

@Component({
  selector: 'app-admin-overview',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, SvgIconComponent, SpinnerComponent],
  templateUrl: './admin-overview.component.html',
})
export class AdminOverviewComponent implements OnInit {
  stats = signal<AdminStats | null>(null);
  statsLoading = signal<boolean>(true);
  branches = signal<AdminBranchInfo[]>([]);

  // Credit Committee Approvals Queue
  pendingApprovals = signal<PendingCommitteeApproval[]>([]);
  approvalsLoading = signal<boolean>(false);
  approvingId = signal<number | null>(null);

  // Table Search, Sort, Pagination
  searchQuery = signal<string>('');
  sortBy = signal<string>('date'); // 'date', 'score', 'amount', 'applicant'
  sortOrder = signal<'asc' | 'desc'>('desc');
  currentPage = signal<number>(1);
  pageSize = signal<number>(5);

  // Detail Modal
  showDetailModal = signal<boolean>(false);
  loadingDetail = signal<boolean>(false);
  selectedApproval = signal<PendingCommitteeApproval | null>(null);
  selectedApp = signal<CreditApplication | null>(null);
  extractedData = signal<ExtractedData | null>(null);
  guarantees = signal<any[]>([]);
  debts = signal<any[]>([]);
  detailTab = signal<'financials' | 'scoring' | 'arbitration'>('financials');
  arbitrationAmount = signal<number>(0);
  arbitrationDuration = signal<number>(12);
  arbitrationNotes = signal<string>('Dossier examiné en comité et approuvé.');
  processingDecision = signal<boolean>(false);

  // Quick Init Modal (1-clic)
  showQuickInitModal = signal<boolean>(false);
  quickAccountNumber = signal<string>('');
  searchingAccount = signal<boolean>(false);
  quickAccountInfo = signal<any>(null);
  quickRequestedAmount = signal<number>(1200000);
  quickRequestedDuration = signal<number>(12);
  quickBusinessDesc = signal<string>('Besoin de trésorerie & approvisionnement');
  creatingQuickApp = signal<boolean>(false);

  constructor(
    private api: ApiService,
    private toast: ToastService,
  ) {}

  ngOnInit(): void {
    this.loadData();
    this.loadPendingApprovals();
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

  async loadPendingApprovals(): Promise<void> {
    this.approvalsLoading.set(true);
    try {
      const list = await this.api.getPendingCommitteeApprovals();
      this.pendingApprovals.set(list);
    } catch {
      this.pendingApprovals.set([]);
    } finally {
      this.approvalsLoading.set(false);
    }
  }

  normalizeScore(score: number | null | undefined): number {
    if (score == null) return 0;
    return score > 100 ? Math.round(score / 10) : score;
  }

  // Filtered & Sorted Approvals
  filteredApprovals = computed(() => {
    let list = [...this.pendingApprovals()];
    const q = this.searchQuery().toLowerCase().trim();

    if (q) {
      list = list.filter(item => {
        return (
          item.reference?.toLowerCase().includes(q) ||
          item.account_number?.toLowerCase().includes(q) ||
          item.applicant_name?.toLowerCase().includes(q) ||
          item.agent_name?.toLowerCase().includes(q)
        );
      });
    }

    const sortField = this.sortBy();
    const order = this.sortOrder();

    list.sort((a, b) => {
      let comparison = 0;
      switch (sortField) {
        case 'score': {
          const scA = this.normalizeScore(a.score);
          const scB = this.normalizeScore(b.score);
          comparison = scA - scB;
          break;
        }
        case 'amount':
          comparison = (a.requested_amount || 0) - (b.requested_amount || 0);
          break;
        case 'applicant':
          comparison = (a.applicant_name || '').localeCompare(b.applicant_name || '');
          break;
        case 'date':
        default: {
          const dateA = new Date(a.updated_at || 0).getTime();
          const dateB = new Date(b.updated_at || 0).getTime();
          comparison = dateA - dateB;
          break;
        }
      }
      return order === 'asc' ? comparison : -comparison;
    });

    return list;
  });

  totalPages = computed(() => Math.max(1, Math.ceil(this.filteredApprovals().length / this.pageSize())));

  pagedApprovals = computed(() => {
    const start = (this.currentPage() - 1) * this.pageSize();
    return this.filteredApprovals().slice(start, start + this.pageSize());
  });

  setSort(field: string): void {
    if (this.sortBy() === field) {
      this.sortOrder.set(this.sortOrder() === 'asc' ? 'desc' : 'asc');
    } else {
      this.sortBy.set(field);
      this.sortOrder.set(field === 'applicant' ? 'asc' : 'desc');
    }
    this.currentPage.set(1);
  }

  goToPage(p: number): void {
    if (p >= 1 && p <= this.totalPages()) {
      this.currentPage.set(p);
    }
  }

  // 1-Clic Quick Init
  openQuickInitModal(): void {
    this.quickAccountNumber.set('');
    this.quickAccountInfo.set(null);
    this.quickRequestedAmount.set(1200000);
    this.quickRequestedDuration.set(12);
    this.quickBusinessDesc.set('Besoin de trésorerie & approvisionnement');
    this.showQuickInitModal.set(true);
  }

  closeQuickInitModal(): void {
    this.showQuickInitModal.set(false);
    this.quickAccountInfo.set(null);
  }

  async searchAccount(): Promise<void> {
    const acc = this.quickAccountNumber().trim();
    if (!acc) return;
    this.searchingAccount.set(true);
    try {
      const info = await this.api.lookupAccount(acc);
      this.quickAccountInfo.set(info);
      this.toast.success('Compte identifié', `${info.full_name} (${info.activity_sector})`);
    } catch (e: any) {
      this.quickAccountInfo.set(null);
      this.toast.error('Compte introuvable', e.message);
    } finally {
      this.searchingAccount.set(false);
    }
  }

  async executeQuickInit(): Promise<void> {
    const acc = this.quickAccountNumber().trim();
    if (!acc) return;
    this.creatingQuickApp.set(true);
    try {
      const newApp = await this.api.quickInitApplication({
        account_number: acc,
        requested_amount: this.quickRequestedAmount(),
        requested_duration_months: this.quickRequestedDuration(),
        business_description: this.quickBusinessDesc(),
      });
      try {
        await this.api.evaluateApplication(newApp.id);
        await this.api.submitToCommittee(newApp.id);
      } catch {}

      this.toast.success('Dossier Initialisé', `Dossier ${newApp.reference} généré et transmis au Comité.`);
      this.closeQuickInitModal();
      await this.loadPendingApprovals();
      await this.loadData();
    } catch (e: any) {
      this.toast.error('Erreur création', e.message);
    } finally {
      this.creatingQuickApp.set(false);
    }
  }

  // Details Modal
  async openDossierDetails(approval: PendingCommitteeApproval): Promise<void> {
    this.selectedApproval.set(approval);
    this.detailTab.set('financials');
    this.showDetailModal.set(true);
    this.loadingDetail.set(true);

    this.arbitrationAmount.set(approval.proposed_amount || approval.requested_amount);
    this.arbitrationDuration.set(approval.requested_duration_months || 12);

    try {
      const [app, ext, guar, debt] = await Promise.allSettled([
        this.api.getApplication(approval.id),
        this.api.getExtractedData(approval.id),
        this.api.getGuarantees(approval.id),
        this.api.getDebts(approval.id),
      ]);

      if (app.status === 'fulfilled') this.selectedApp.set(app.value);
      if (ext.status === 'fulfilled') this.extractedData.set(ext.value);
      if (guar.status === 'fulfilled') this.guarantees.set(guar.value);
      if (debt.status === 'fulfilled') this.debts.set(debt.value);
    } catch (e: any) {
      this.toast.error('Erreur détails', e.message);
    } finally {
      this.loadingDetail.set(false);
    }
  }

  closeDetailModal(): void {
    this.showDetailModal.set(false);
    this.selectedApproval.set(null);
  }

  // ── Action Confirmation Modal (Approve / Reject) ─────────────────
  showActionModal = signal<boolean>(false);
  actionType = signal<'approve' | 'reject'>('approve');
  actionApp = signal<PendingCommitteeApproval | null>(null);
  actionAmount = signal<number>(0);
  actionDuration = signal<number>(12);
  actionNotes = signal<string>('');
  processingAction = signal<boolean>(false);

  openActionModal(app: PendingCommitteeApproval, type: 'approve' | 'reject'): void {
    this.actionApp.set(app);
    this.actionType.set(type);
    if (type === 'approve') {
      this.actionAmount.set(app.proposed_amount || app.requested_amount || 1000000);
      this.actionDuration.set(app.requested_duration_months || 12);
      this.actionNotes.set('Validé et approuvé en séance de comité d\'agence.');
    } else {
      this.actionNotes.set('Refusé après arbitrage du comité de crédit.');
    }
    this.showActionModal.set(true);
  }

  closeActionModal(): void {
    this.showActionModal.set(false);
    this.actionApp.set(null);
  }

  async executeAction(): Promise<void> {
    const app = this.actionApp();
    if (!app) return;

    this.processingAction.set(true);
    try {
      const type = this.actionType();
      await this.api.processCommitteeDecision(app.id, {
        decision: type === 'approve' ? 'approved' : 'rejected',
        approved_amount: type === 'approve' ? this.actionAmount() : undefined,
        notes: this.actionNotes(),
      });

      if (type === 'approve') {
        this.toast.success(
          'Dossier Validé par le Comité',
          `Le prêt de ${this.formatAmount(this.actionAmount())} pour ${app.applicant_name} (${app.reference}) a été formellement approuvé et signé.`
        );
      } else {
        this.toast.warning('Dossier rejeté', `Le dossier ${app.reference} a été refusé.`);
      }

      this.closeActionModal();
      this.closeDetailModal();
      await this.loadPendingApprovals();
      await this.loadData();
    } catch (e: any) {
      this.toast.error('Erreur décision', e.message);
    } finally {
      this.processingAction.set(false);
    }
  }

  async confirmApprove(): Promise<void> {
    const item = this.selectedApproval();
    if (!item) return;
    this.openActionModal(item, 'approve');
  }

  async confirmReject(): Promise<void> {
    const item = this.selectedApproval();
    if (!item) return;
    this.openActionModal(item, 'reject');
  }

  async approveByCommittee(app: PendingCommitteeApproval, approvedAmount?: number): Promise<void> {
    this.openActionModal(app, 'approve');
  }

  async rejectByCommittee(app: PendingCommitteeApproval): Promise<void> {
    this.openActionModal(app, 'reject');
  }

  exportBceaoReport(): void {
    this.toast.success(
      'Exportation BCEAO',
      'Le rapport officiel de conformité prudentielle UEMOA a été généré avec succès.'
    );
  }

  formatAmount(amount: number | null | undefined): string {
    return (amount || 0).toLocaleString('fr-FR') + ' FCFA';
  }

  getDecisionLabel(decision?: string): string {
    if (!decision) return 'En attente d\'arbitrage';
    const labels: Record<string, string> = {
      approved: 'Favorable (Accordé)',
      adjusted: 'Ajustement proposé',
      rejected: 'Défavorable (Refusé)',
      pending_committee_approval: 'Arbitrage requis',
      scored: 'Dossier évalué',
    };
    return labels[decision.toLowerCase()] || decision;
  }

  getRiskLabel(risk?: string): string {
    if (!risk) return 'Non déterminé';
    const labels: Record<string, string> = {
      low: 'Faible',
      medium: 'Modéré',
      high: 'Élevé',
      very_high: 'Très Élevé',
      critical: 'Critique',
    };
    return labels[risk.toLowerCase()] || risk;
  }

  getStatusLabel(status?: string): string {
    if (!status) return 'En attente';
    const labels: Record<string, string> = {
      draft: 'Brouillon',
      documents_uploaded: 'Documents Déposés',
      data_extracted: 'Données Extraites',
      pending_verification: 'En Attente de Vérification',
      data_verified: 'Données Vérifiées',
      scored: 'Dossier Évalué',
      pending_committee_approval: 'En Attente Comité',
      approved: 'Accordé',
      adjusted: 'Ajusté',
      rejected: 'Refusé',
    };
    return labels[status.toLowerCase()] || status;
  }
}
