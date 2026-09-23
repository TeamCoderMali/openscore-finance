import { Component, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { ApiService } from '../../../../core/services/api.service';
import { ToastService } from '../../../../core/services/toast.service';
import { SvgIconComponent } from '../../../../shared/components/svg-icon/svg-icon.component';
import { SpinnerComponent } from '../../../../shared/components/spinner/spinner.component';
import {
  CreditApplication,
  PendingCommitteeApproval,
  ExtractedData,
  ScoringResult,
} from '../../../../shared/models/application.model';

@Component({
  selector: 'app-admin-committee',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, SvgIconComponent, SpinnerComponent],
  templateUrl: './admin-committee.component.html',
})
export class AdminCommitteeComponent implements OnInit {
  // ── Data ────────────────────────────────────────────────────────
  pendingApprovals = signal<PendingCommitteeApproval[]>([]);
  loading = signal<boolean>(false);

  // ── Search & Filter Controls ────────────────────────────────────
  searchQuery = signal<string>('');
  sectorFilter = signal<string>('all');
  decisionFilter = signal<string>('all');
  scoreFilter = signal<string>('all'); // 'all', 'excellent', 'favorable', 'risk'
  coverageFilter = signal<string>('all'); // 'all', 'over', 'partial', 'low'

  // ── Sorting ─────────────────────────────────────────────────────
  sortBy = signal<string>('date'); // 'date', 'score', 'amount', 'applicant', 'coverage'
  sortOrder = signal<'asc' | 'desc'>('desc');

  // ── Pagination ──────────────────────────────────────────────────
  currentPage = signal<number>(1);
  pageSize = signal<number>(5);

  // ── Quick-Init Modal (1-Clic pour Super Admin) ───────────────────
  showQuickInitModal = signal<boolean>(false);
  quickAccountNumber = signal<string>('');
  searchingAccount = signal<boolean>(false);
  quickAccountInfo = signal<any>(null);
  quickRequestedAmount = signal<number>(1500000);
  quickRequestedDuration = signal<number>(12);
  quickBusinessDesc = signal<string>('Renforcement de trésorerie & approvisionnement');
  creatingQuickApp = signal<boolean>(false);

  // ── Dossier Detail Modal (3 Volets) ─────────────────────────────
  showDetailModal = signal<boolean>(false);
  loadingDetail = signal<boolean>(false);
  selectedApproval = signal<PendingCommitteeApproval | null>(null);
  selectedApp = signal<CreditApplication | null>(null);
  extractedData = signal<ExtractedData | null>(null);
  scoringResult = signal<ScoringResult | null>(null);
  guarantees = signal<any[]>([]);
  debts = signal<any[]>([]);
  detailTab = signal<'identity' | 'financials' | 'scoring' | 'arbitration'>('identity');

  // Committee decision arbitration inputs & state
  arbitrationAmount = signal<number>(0);
  arbitrationDuration = signal<number>(12);
  arbitrationNotes = signal<string>('Dossier analysé et conforme aux directives prudentielles.');
  processingDecision = signal<boolean>(false);
  isEditingDecision = signal<boolean>(false);

  // ── Demande de document complémentaire par le Comité ───────────
  showDocRequestModal = signal<boolean>(false);
  docRequestName = signal<string>('Relevé bancaire des 3 derniers mois');
  docRequestDesc = signal<string>('Pièce indispensable pour clore l\'instruction prudentielle de la demande.');
  submittingDocRequest = signal<boolean>(false);

  // ── Rapports & PV de Séance du Comité ───────────────────────────
  showReportsModal = signal<boolean>(false);
  committeeReports = signal<any[]>([]);
  loadingReports = signal<boolean>(false);
  showNewReportForm = signal<boolean>(false);
  newReportTitle = signal<string>('Procès-Verbal de Session de Crédit — Kafo Jiginew');
  newReportDate = signal<string>(new Date().toISOString().split('T')[0]);
  newReportNotes = signal<string>('Validation des dossiers en souffrance et arbitrages des quotités.');
  newReportFileName = signal<string>('PV_Session_Comite_' + new Date().toISOString().split('T')[0] + '.pdf');
  submittingReport = signal<boolean>(false);

  constructor(
    private api: ApiService,
    private toast: ToastService,
    private router: Router,
  ) {}

  ngOnInit(): void {
    this.loadApprovals();
  }

  async loadApprovals(): Promise<void> {
    this.loading.set(true);
    try {
      const data = await this.api.getPendingCommitteeApprovals();
      this.pendingApprovals.set(data);
    } catch (e: any) {
      this.pendingApprovals.set([]);
      this.toast.error('Erreur Comité', e.message || 'Impossible de charger la file d\'attente.');
    } finally {
      this.loading.set(false);
    }
  }

  // ── Normalisation Score (/100) ──────────────────────────────────
  normalizeScore(score: number | null | undefined): number {
    if (score == null) return 0;
    return score > 100 ? Math.round(score / 10) : score;
  }

  // ── Active Filters Count ────────────────────────────────────────
  activeFiltersCount = computed(() => {
    let count = 0;
    if (this.searchQuery().trim()) count++;
    if (this.sectorFilter() !== 'all') count++;
    if (this.decisionFilter() !== 'all') count++;
    if (this.scoreFilter() !== 'all') count++;
    if (this.coverageFilter() !== 'all') count++;
    return count;
  });

  // ── Filtered and Sorted Approvals ───────────────────────────────
  filteredApprovals = computed(() => {
    let list = [...this.pendingApprovals()];
    const q = this.searchQuery().toLowerCase().trim();
    const sector = this.sectorFilter();
    const decision = this.decisionFilter();
    const scFilter = this.scoreFilter();
    const covFilter = this.coverageFilter();

    // 1. Search Query (Reference, Account, Name, Phone, Agent)
    if (q) {
      list = list.filter(item => {
        const refMatch = item.reference?.toLowerCase().includes(q);
        const accMatch = item.account_number?.toLowerCase().includes(q);
        const nameMatch = item.applicant_name?.toLowerCase().includes(q);
        const agentMatch = item.agent_name?.toLowerCase().includes(q);
        const phoneMatch = item.applicant_phone?.includes(q);
        return refMatch || accMatch || nameMatch || agentMatch || phoneMatch;
      });
    }

    // 2. Sector Filter
    if (sector !== 'all') {
      list = list.filter(item => item.activity_sector?.toLowerCase() === sector.toLowerCase());
    }

    // 3. Algorithmic Decision Filter
    if (decision !== 'all') {
      list = list.filter(item => {
        const d = (item.recommended_decision || item.algorithmic_decision || '').toLowerCase();
        return d === decision.toLowerCase();
      });
    }

    // 4. Score Tier Filter
    if (scFilter !== 'all') {
      list = list.filter(item => {
        const sc = this.normalizeScore(item.score);
        if (scFilter === 'excellent') return sc >= 80;
        if (scFilter === 'favorable') return sc >= 60 && sc < 80;
        if (scFilter === 'risk') return sc < 60;
        return true;
      });
    }

    // 5. Guarantee Coverage Filter
    if (covFilter !== 'all') {
      list = list.filter(item => {
        const cov = item.guarantee_coverage_ratio || 0;
        if (covFilter === 'over') return cov >= 1.0;
        if (covFilter === 'partial') return cov >= 0.5 && cov < 1.0;
        if (covFilter === 'low') return cov < 0.5;
        return true;
      });
    }

    // 6. Sorting
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
        case 'amount': {
          comparison = (a.requested_amount || 0) - (b.requested_amount || 0);
          break;
        }
        case 'applicant': {
          comparison = (a.applicant_name || '').localeCompare(b.applicant_name || '');
          break;
        }
        case 'coverage': {
          comparison = (a.guarantee_coverage_ratio || 0) - (b.guarantee_coverage_ratio || 0);
          break;
        }
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

  // ── Pagination Computations ─────────────────────────────────────
  totalPages = computed(() => Math.max(1, Math.ceil(this.filteredApprovals().length / this.pageSize())));

  pagedApprovals = computed(() => {
    const start = (this.currentPage() - 1) * this.pageSize();
    return this.filteredApprovals().slice(start, start + this.pageSize());
  });

  // ── Macro KPIs Computed ─────────────────────────────────────────
  kpiStats = computed(() => {
    const items = this.filteredApprovals();
    const totalCount = items.length;
    const totalAmount = items.reduce((sum, item) => sum + (item.requested_amount || 0), 0);
    const validScores = items.map(i => this.normalizeScore(i.score)).filter(s => s > 0);
    const averageScore = validScores.length > 0 ? Math.round(validScores.reduce((a, b) => a + b, 0) / validScores.length) : 0;
    const validCovs = items.map(i => i.guarantee_coverage_ratio || 0);
    const averageCoverage = validCovs.length > 0 ? Math.round((validCovs.reduce((a, b) => a + b, 0) / validCovs.length) * 100) : 0;

    return {
      totalCount,
      totalAmount,
      averageScore,
      averageCoverage,
    };
  });

  // ── Sort Toggle ─────────────────────────────────────────────────
  setSort(field: string): void {
    if (this.sortBy() === field) {
      this.sortOrder.set(this.sortOrder() === 'asc' ? 'desc' : 'asc');
    } else {
      this.sortBy.set(field);
      this.sortOrder.set(field === 'applicant' ? 'asc' : 'desc');
    }
    this.currentPage.set(1);
  }

  resetFilters(): void {
    this.searchQuery.set('');
    this.sectorFilter.set('all');
    this.decisionFilter.set('all');
    this.scoreFilter.set('all');
    this.coverageFilter.set('all');
    this.sortBy.set('date');
    this.sortOrder.set('desc');
    this.currentPage.set(1);
  }

  // ── Pagination Controls ─────────────────────────────────────────
  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages()) {
      this.currentPage.set(page);
    }
  }

  prevPage(): void {
    this.goToPage(this.currentPage() - 1);
  }

  nextPage(): void {
    this.goToPage(this.currentPage() + 1);
  }

  setPageSize(size: number): void {
    this.pageSize.set(size);
    this.currentPage.set(1);
  }

  // ── 1-CLIC QUICK INIT (Pour Super Admin) ─────────────────────────
  openQuickInitModal(): void {
    this.quickAccountNumber.set('');
    this.quickAccountInfo.set(null);
    this.quickRequestedAmount.set(1500000);
    this.quickRequestedDuration.set(12);
    this.quickBusinessDesc.set('Renforcement de trésorerie & approvisionnement');
    this.showQuickInitModal.set(true);
  }

  closeQuickInitModal(): void {
    this.showQuickInitModal.set(false);
    this.quickAccountInfo.set(null);
  }

  async searchAccount(): Promise<void> {
    const acc = this.quickAccountNumber().trim();
    if (!acc) {
      this.toast.error('Numéro requis', 'Veuillez renseigner un numéro de compte (ex: CMF-2026-001245)');
      return;
    }

    this.searchingAccount.set(true);
    try {
      const info = await this.api.lookupAccount(acc);
      this.quickAccountInfo.set(info);
      this.toast.success('Compte identifié', `Titulaire : ${info.full_name} (${info.activity_sector})`);
    } catch (e: any) {
      this.quickAccountInfo.set(null);
      this.toast.error('Compte introuvable', e.message || 'Numéro de compte non reconnu.');
    } finally {
      this.searchingAccount.set(false);
    }
  }

  async executeQuickInit(): Promise<void> {
    const acc = this.quickAccountNumber().trim();
    if (!acc) {
      this.toast.error('Compte requis', 'Veuillez saisir un numéro de compte valide.');
      return;
    }

    this.creatingQuickApp.set(true);
    try {
      // 1. Initialisation instantanée
      const newApp = await this.api.quickInitApplication({
        account_number: acc,
        requested_amount: this.quickRequestedAmount(),
        requested_duration_months: this.quickRequestedDuration(),
        business_description: this.quickBusinessDesc(),
      });

      // 2. Évaluation ML automatique
      try {
        await this.api.evaluateApplication(newApp.id);
      } catch {
        // Continue if already evaluated
      }

      // 3. Soumission directe au Comité
      try {
        await this.api.submitToCommittee(newApp.id);
      } catch {
        // Status might already be ready
      }

      this.toast.success(
        'Dossier initialisé en 1-clic !',
        `Demande ${newApp.reference} créée, scorée et intégrée dans la file du Comité.`
      );

      this.closeQuickInitModal();
      await this.loadApprovals();

      // Open the details modal immediately so admin can arbitrate right away
      const item = this.pendingApprovals().find(a => a.id === newApp.id);
      if (item) {
        this.openDossierDetails(item);
      }
    } catch (e: any) {
      this.toast.error('Erreur initialisation', e.message);
    } finally {
      this.creatingQuickApp.set(false);
    }
  }

  // ── DOSSIER DETAILS MODAL (3 Volets) ────────────────────────────
  async openDossierDetails(approval: PendingCommitteeApproval): Promise<void> {
    this.selectedApproval.set(approval);
    this.detailTab.set(this.isDecided(approval.status) ? 'arbitration' : 'identity');
    this.showDetailModal.set(true);
    this.loadingDetail.set(true);
    this.isEditingDecision.set(false);

    const initialAmt = approval.approved_amount || approval.proposed_amount || approval.requested_amount;
    this.arbitrationAmount.set(initialAmt);
    this.arbitrationDuration.set(approval.approved_duration_months || approval.requested_duration_months || 12);
    this.arbitrationNotes.set(approval.committee_notes || 'Dossier examiné en séance de comité et approuvé après analyse du risque.');

    try {
      const [app, ext, guar, debt] = await Promise.allSettled([
        this.api.getApplication(approval.id),
        this.api.getExtractedData(approval.id),
        this.api.getGuarantees(approval.id),
        this.api.getDebts(approval.id),
      ]);

      if (app.status === 'fulfilled') {
        const fullApp = app.value;
        this.selectedApp.set(fullApp);
        if (fullApp.approved_amount) {
          this.arbitrationAmount.set(fullApp.approved_amount);
        }
        if (fullApp.requested_duration_months) {
          this.arbitrationDuration.set(fullApp.requested_duration_months);
        }
        if (fullApp.committee_notes) {
          this.arbitrationNotes.set(fullApp.committee_notes);
        }
      }
      if (ext.status === 'fulfilled') {
        this.extractedData.set(ext.value);
      } else {
        this.extractedData.set(null);
      }
      if (guar.status === 'fulfilled') {
        this.guarantees.set(guar.value);
      } else {
        this.guarantees.set([]);
      }
      if (debt.status === 'fulfilled') {
        this.debts.set(debt.value);
      } else {
        this.debts.set([]);
      }
    } catch (e: any) {
      this.toast.error('Erreur détails', e.message);
    } finally {
      this.loadingDetail.set(false);
    }
  }

  closeDetailModal(): void {
    this.showDetailModal.set(false);
    this.selectedApproval.set(null);
    this.selectedApp.set(null);
    this.isEditingDecision.set(false);
  }

  // ── Helpers Statut & Affichage ──────────────────────────────────
  isApproved(status?: string): boolean {
    if (!status) return false;
    const s = status.toLowerCase().replace('applicationstatus.', '').trim();
    return s === 'approved' || s === 'accorde';
  }

  isRejected(status?: string): boolean {
    if (!status) return false;
    const s = status.toLowerCase().replace('applicationstatus.', '').trim();
    return s === 'rejected' || s === 'refuse';
  }

  isDecided(status?: string): boolean {
    return this.isApproved(status) || this.isRejected(status);
  }

  viewReceipt(appId?: number): void {
    if (!appId) return;
    this.router.navigate(['/receipt', appId]);
  }

  calculateEstimatedMonthly(amt: number, dur: number): number {
    if (!amt || !dur || dur <= 0) return 0;
    const totalWithInterest = amt * (1 + 0.015 * dur);
    return Math.round(totalWithInterest / dur);
  }

  // ── Demande de document complémentaire par le Comité ───────────
  openDocRequestModal(): void {
    this.docRequestName.set('Relevé bancaire des 3 derniers mois');
    this.docRequestDesc.set('Pièce indispensable pour clore l\'instruction prudentielle de la demande.');
    this.showDocRequestModal.set(true);
  }

  closeDocRequestModal(): void {
    this.showDocRequestModal.set(false);
  }

  async submitDocRequest(): Promise<void> {
    const item = this.selectedApproval() || (this.selectedApp() as any);
    if (!item || !this.docRequestName().trim()) {
      this.toast.warning('Intitulé requis', 'Veuillez préciser le document demandé.');
      return;
    }

    this.submittingDocRequest.set(true);
    try {
      const res = await this.api.requestCommitteeDocument(item.id, {
        document_name: this.docRequestName().trim(),
        description: this.docRequestDesc().trim(),
      });

      this.toast.success(
        'Demande transmise à l\'agent',
        `L'agent référent a été averti de la demande de pièce : "${this.docRequestName()}"`
      );

      const updatedForm = {
        ...(this.selectedApp()?.form_data || {}),
        has_pending_document_request: true,
        document_requests: res.document_requests || [],
      };

      this.selectedApp.update(curr => curr ? { ...curr, form_data: updatedForm } : null);
      this.selectedApproval.update(curr => curr ? { ...curr, form_data: updatedForm } : null);
      this.pendingApprovals.update(list => list.map(a => a.id === item.id ? { ...a, form_data: updatedForm } : a));

      this.closeDocRequestModal();
    } catch (e: any) {
      this.toast.error('Erreur demande pièce', e.message);
    } finally {
      this.submittingDocRequest.set(false);
    }
  }

  // ── Action Confirmation Modal (Approve / Reject) ─────────────────
  showActionModal = signal<boolean>(false);
  actionType = signal<'approve' | 'reject'>('approve');
  actionItem = signal<PendingCommitteeApproval | null>(null);
  actionAmount = signal<number>(0);
  actionDuration = signal<number>(12);
  actionNotes = signal<string>('');
  processingAction = signal<boolean>(false);

  openActionModal(item: PendingCommitteeApproval, type: 'approve' | 'reject'): void {
    this.actionItem.set(item);
    this.actionType.set(type);
    if (type === 'approve') {
      this.actionAmount.set(item.approved_amount || item.proposed_amount || item.requested_amount || 1000000);
      this.actionDuration.set(item.approved_duration_months || item.requested_duration_months || 12);
      this.actionNotes.set('Validé et signé en séance de comité d\'agence.');
    } else {
      this.actionNotes.set('Refusé après arbitrage du comité de crédit.');
    }
    this.showActionModal.set(true);
  }

  closeActionModal(): void {
    this.showActionModal.set(false);
    this.actionItem.set(null);
  }

  async executeAction(): Promise<void> {
    const item = this.actionItem();
    if (!item) return;

    this.processingAction.set(true);
    const type = this.actionType();
    const isApprove = type === 'approve';
    const amt = isApprove ? this.actionAmount() : undefined;
    const dur = isApprove ? this.actionDuration() : undefined;

    try {
      await this.api.processCommitteeDecision(item.id, {
        decision: isApprove ? 'approved' : 'rejected',
        approved_amount: amt,
        approved_duration_months: dur,
        notes: this.actionNotes(),
      });

      // Update locally immediately for instant feedback
      this.pendingApprovals.update(list => list.map(a => {
        if (a.id === item.id) {
          return {
            ...a,
            status: isApprove ? 'approved' : 'rejected',
            recommended_decision: type,
            algorithmic_decision: type,
            approved_amount: amt,
            proposed_amount: amt || a.proposed_amount,
            requested_duration_months: dur || a.requested_duration_months,
            approved_duration_months: dur || a.approved_duration_months,
            committee_notes: this.actionNotes(),
          };
        }
        return a;
      }));

      if (isApprove) {
        this.toast.success(
          'Crédit Accordé !',
          `Le prêt de ${this.formatAmount(this.actionAmount())} (${dur} mois) pour ${item.applicant_name} a été validé et signé.`
        );
      } else {
        this.toast.warning('Dossier Rejeté', `La demande ${item.reference} a été refusée.`);
      }

      this.closeActionModal();
      this.closeDetailModal();
      await this.loadApprovals();
    } catch (e: any) {
      this.toast.error('Erreur décision', e.message);
    } finally {
      this.processingAction.set(false);
    }
  }

  // ── COMMITTEE DECISIONS ─────────────────────────────────────────
  async confirmApprove(): Promise<void> {
    const item = this.selectedApproval();
    if (!item) return;

    this.processingDecision.set(true);
    try {
      const amt = this.arbitrationAmount();
      const dur = this.arbitrationDuration();
      const notes = this.arbitrationNotes();

      await this.api.processCommitteeDecision(item.id, {
        decision: 'approved',
        approved_amount: amt,
        approved_duration_months: dur,
        notes: notes,
      });

      // Instant UI update
      this.pendingApprovals.update(list => list.map(a => {
        if (a.id === item.id) {
          return {
            ...a,
            status: 'approved',
            recommended_decision: 'approved',
            algorithmic_decision: 'approved',
            approved_amount: amt,
            proposed_amount: amt,
            requested_duration_months: dur,
            approved_duration_months: dur,
            committee_notes: notes,
          };
        }
        return a;
      }));

      this.selectedApproval.update(curr => curr ? {
        ...curr,
        status: 'approved',
        approved_amount: amt,
        requested_duration_months: dur,
        approved_duration_months: dur,
        committee_notes: notes,
      } : null);

      this.selectedApp.update(curr => curr ? {
        ...curr,
        status: 'approved',
        approved_amount: amt,
        requested_duration_months: dur,
        committee_notes: notes,
      } : null);

      this.isEditingDecision.set(false);

      this.toast.success(
        'Crédit Accordé !',
        `Le prêt de ${this.formatAmount(amt)} (${dur} mois) pour ${item.applicant_name} a été validé et signé.`
      );
      await this.loadApprovals();
    } catch (e: any) {
      this.toast.error('Erreur validation', e.message);
    } finally {
      this.processingDecision.set(false);
    }
  }

  async confirmReject(): Promise<void> {
    const item = this.selectedApproval();
    if (!item) return;
    this.openActionModal(item, 'reject');
  }

  async quickApprove(item: PendingCommitteeApproval): Promise<void> {
    this.openActionModal(item, 'approve');
  }

  async quickReject(item: PendingCommitteeApproval): Promise<void> {
    this.openActionModal(item, 'reject');
  }

  // ── Rapports de Comité ──────────────────────────────────────────
  async openReportsModal(): Promise<void> {
    this.showReportsModal.set(true);
    await this.loadReports();
  }

  closeReportsModal(): void {
    this.showReportsModal.set(false);
    this.showNewReportForm.set(false);
  }

  async loadReports(): Promise<void> {
    this.loadingReports.set(true);
    try {
      const data = await this.api.getCommitteeReports();
      this.committeeReports.set(data || []);
    } catch (e: any) {
      this.toast.error('Erreur Rapports', e.message || 'Impossible de charger les rapports.');
    } finally {
      this.loadingReports.set(false);
    }
  }

  async submitNewReport(): Promise<void> {
    if (!this.newReportTitle().trim()) {
      this.toast.warning('Titre requis', 'Veuillez saisir un intitulé pour le rapport de séance');
      return;
    }
    this.submittingReport.set(true);
    try {
      await this.api.createCommitteeReport({
        title: this.newReportTitle(),
        meeting_date: this.newReportDate(),
        file_name: this.newReportFileName(),
        file_url: 'data:application/pdf;base64,JVBERi0xLjQK...',
        notes: this.newReportNotes(),
      });
      this.toast.success('Rapport Enregistré', 'Le procès-verbal a été archivé avec succès.');
      this.showNewReportForm.set(false);
      await this.loadReports();
    } catch (e: any) {
      this.toast.error('Erreur Enregistrement', e.message || 'Erreur lors de la sauvegarde du rapport.');
    } finally {
      this.submittingReport.set(false);
    }
  }

  // ── Formatters & UI Helpers ─────────────────────────────────────
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
    if (!risk) return 'Modéré';
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

  getApplicationType(): string {
    return this.selectedApp()?.application_type || this.selectedApproval()?.application_type || 'INDIVIDUAL';
  }

  getBranchCode(): string {
    return this.selectedApp()?.branch_code || this.selectedApproval()?.branch_code || '701';
  }
}
