import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { ApiService } from '../../../../core/services/api.service';
import { AuthService } from '../../../../core/services/auth.service';
import { ToastService } from '../../../../core/services/toast.service';
import { SvgIconComponent } from '../../../../shared/components/svg-icon/svg-icon.component';
import { SpinnerComponent } from '../../../../shared/components/spinner/spinner.component';
import {
  CreditApplication, ExtractedData, VerifyDataRequest, AuditLog,
  ScoringResult, ContactClientRequest, ApproveDecisionRequest,
  Guarantee, Debt, GrantingMethod
} from '../../../../shared/models/application.model';

export type DetailTab = 'financials_guarantees' | 'scoring_shap' | 'decision_method' | 'audit_logs';

@Component({
  selector: 'app-agent-pipeline',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, SvgIconComponent, SpinnerComponent],
  templateUrl: './agent-pipeline.component.html',
})
export class AgentPipelineComponent implements OnInit {
  // Applications & Active Selection
  applications = signal<CreditApplication[]>([]);
  selectedApp = signal<CreditApplication | null>(null);
  extractedData = signal<ExtractedData | null>(null);
  scoringResult = signal<ScoringResult | null>(null);
  currentDetailTab = signal<DetailTab>('financials_guarantees');

  // Guarantees & Debts for Selected Application
  guarantees = signal<Guarantee[]>([]);
  debts = signal<Debt[]>([]);
  applicableGrantingMethod = signal<GrantingMethod | null>(null);
  allGrantingMethods = signal<GrantingMethod[]>([]);

  // Filters & Multi-Search (Reference OSF-... or Account CMF-...)
  searchQuery = signal<string>('');
  selectedStatusFilter = signal<string>('all');
  selectedSectorFilter = signal<string>('all');
  sortBy = signal<'date_desc' | 'amount_desc' | 'amount_asc'>('date_desc');

  // Pagination
  pipelinePage = signal<number>(1);
  pipelinePageSize = signal<number>(6);

  // Editable Financial & Personal Fields (Part 1)
  verifiedFields = signal<VerifyDataRequest>({});
  verificationNotes = signal<string>('');
  savingFinancials = signal<boolean>(false);

  // Guarantee Management Modal
  showAddGuaranteeModal = signal<boolean>(false);
  newGuaranteeType = signal<string>('terrain');
  newGuaranteeDesc = signal<string>('');
  newGuaranteeEst = signal<number>(0);
  newGuaranteeRet = signal<number>(0);
  newGuaranteeProof = signal<string>('');
  savingGuarantee = signal<boolean>(false);

  // Debt Management Modal
  showAddDebtModal = signal<boolean>(false);
  newDebtCreditor = signal<string>('');
  newDebtInternal = signal<boolean>(false);
  newDebtInitial = signal<number>(0);
  newDebtRemaining = signal<number>(0);
  newDebtMonthly = signal<number>(0);
  savingDebt = signal<boolean>(false);

  // Quick Init Application Modal (By Account Number Only)
  showQuickInitModal = signal<boolean>(false);
  quickAccountNumber = signal<string>('');
  quickAccountInfo = signal<any | null>(null);
  quickRequestedAmount = signal<number>(1000000);
  quickRequestedDuration = signal<number>(12);
  quickBusinessDesc = signal<string>('Renforcement de trésorerie & approvisionnement');
  searchingAccount = signal<boolean>(false);
  creatingQuickApp = signal<boolean>(false);

  // Committee Submission (Part 3)
  submittingToCommittee = signal<boolean>(false);

  // Reject Modal
  showRejectModal = signal<boolean>(false);
  rejectReason = signal<string>("Ratio d'endettement supérieur au plafond prudentiel BCEAO (40%)");
  rejectNotes = signal<string>('');
  rejectingApp = signal<boolean>(false);

  // Approve Modal
  showApproveModal = signal<boolean>(false);
  approveAmount = signal<number>(1000000);
  approveNotes = signal<string>('');
  approvingApp = signal<boolean>(false);

  // Delete Guarantee/Debt Modal
  showDeleteConfirmModal = signal<boolean>(false);
  itemToDelete = signal<{ type: 'guarantee' | 'debt'; id: number; label: string } | null>(null);
  deletingItem = signal<boolean>(false);

  // Direct Contact Modal
  showContactModal = signal<boolean>(false);
  contactChannel = signal<'whatsapp' | 'phone' | 'email' | 'in_app'>('whatsapp');
  contactSubject = signal<string>('Complément de dossier microcrédit OpenScore');
  contactMessage = signal<string>('');
  contactingClient = signal<boolean>(false);

  // Audit Logs for selected application
  auditLogs = signal<AuditLog[]>([]);
  auditLoading = signal<boolean>(false);

  // Global Loading
  loading = signal<boolean>(false);
  detailLoading = signal<boolean>(false);
  scoringLoading = signal<boolean>(false);

  // Computed Totals & Coverage
  totalGuaranteesEstimated = computed(() =>
    this.guarantees().reduce((sum, g) => sum + (g.estimated_value || 0), 0)
  );

  totalGuaranteesRetained = computed(() =>
    this.guarantees().reduce((sum, g) => sum + (g.retained_value || 0), 0)
  );

  totalDebtsMonthly = computed(() =>
    this.debts().reduce((sum, d) => sum + (d.monthly_payment || 0), 0)
  );

  totalDebtsRemaining = computed(() =>
    this.debts().reduce((sum, d) => sum + (d.remaining_amount || 0), 0)
  );

  guaranteeCoverageRatio = computed(() => {
    const app = this.selectedApp();
    if (!app || app.requested_amount <= 0) return 0;
    return Math.round((this.totalGuaranteesRetained() / app.requested_amount) * 100);
  });

  // Filtered applications list (Multi-Search by reference or account)
  filteredApplications = computed(() => {
    let list = this.applications();
    const query = this.searchQuery().toLowerCase().trim();
    const status = this.selectedStatusFilter();
    const sector = this.selectedSectorFilter();

    if (query) {
      list = list.filter(a =>
        a.reference.toLowerCase().includes(query) ||
        (a.account_number && a.account_number.toLowerCase().includes(query)) ||
        (a.applicant_name && a.applicant_name.toLowerCase().includes(query)) ||
        (a.applicant_phone && a.applicant_phone.includes(query)) ||
        (a.applicant_email && a.applicant_email.toLowerCase().includes(query)) ||
        (a.business_description && a.business_description.toLowerCase().includes(query)) ||
        a.activity_sector.toLowerCase().includes(query)
      );
    }

    if (status !== 'all') {
      if (status === 'pending') {
        list = list.filter(a => a.status === 'pending_verification' || a.status === 'data_verified');
      } else if (status === 'committee') {
        list = list.filter(a => a.status === 'pending_committee_approval');
      } else if (status === 'scored') {
        list = list.filter(a => a.status === 'scored');
      } else if (status === 'decided') {
        list = list.filter(a => ['approved', 'adjusted', 'rejected'].includes(a.status));
      } else {
        list = list.filter(a => a.status === status);
      }
    }

    if (sector !== 'all') {
      list = list.filter(a => a.activity_sector === sector);
    }

    const sort = this.sortBy();
    return [...list].sort((a, b) => {
      if (sort === 'amount_desc') return b.requested_amount - a.requested_amount;
      if (sort === 'amount_asc') return a.requested_amount - b.requested_amount;
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
  });

  pagedApplications = computed(() => {
    const start = (this.pipelinePage() - 1) * this.pipelinePageSize();
    return this.filteredApplications().slice(start, start + this.pipelinePageSize());
  });

  totalPages = computed(() => Math.max(1, Math.ceil(this.filteredApplications().length / this.pipelinePageSize())));

  // KPI summaries
  pendingCount = computed(() => this.applications().filter(a => ['pending_verification', 'data_verified'].includes(a.status)).length);
  committeeCount = computed(() => this.applications().filter(a => a.status === 'pending_committee_approval').length);
  scoredCount = computed(() => this.applications().filter(a => a.status === 'scored').length);
  approvedCount = computed(() => this.applications().filter(a => a.status === 'approved' || a.status === 'adjusted').length);

  constructor(
    private api: ApiService,
    public auth: AuthService,
    private router: Router,
    private toast: ToastService,
  ) {}

  ngOnInit(): void {
    this.loadApplications();
    this.loadGrantingMethods();
  }

  async loadApplications(): Promise<void> {
    this.loading.set(true);
    try {
      const result = await this.api.getApplications();
      this.applications.set(result.applications);
    } catch {
      this.toast.error('Erreur chargement', 'Impossible de récupérer la liste des dossiers.');
    } finally {
      this.loading.set(false);
    }
  }

  async loadGrantingMethods(): Promise<void> {
    try {
      const methods = await this.api.getGrantingMethods();
      this.allGrantingMethods.set(methods);
    } catch {
      this.allGrantingMethods.set([]);
    }
  }

  async selectApplication(app: CreditApplication): Promise<void> {
    this.selectedApp.set(app);
    this.detailLoading.set(true);
    this.currentDetailTab.set('financials_guarantees');

    try {
      const [dataRes, scRes, guarRes, debtsRes] = await Promise.allSettled([
        this.api.getExtractedData(app.id),
        this.api.getScoringResult(app.id),
        this.api.getGuarantees(app.id),
        this.api.getDebts(app.id),
      ]);

      // 1. Extracted Financials
      if (dataRes.status === 'fulfilled') {
        const d = dataRes.value;
        this.extractedData.set(d);
        this.verifiedFields.set({
          full_name: d.full_name || app.applicant_name,
          date_of_birth: d.date_of_birth || '',
          id_number: d.id_number || '',
          id_type: d.id_type || 'NINA',
          monthly_revenue: d.monthly_revenue || 0,
          secondary_revenue: d.secondary_revenue || 0,
          monthly_expenses: d.monthly_expenses || 0,
          other_recurring_expenses: d.other_recurring_expenses || 0,
          existing_debt: d.existing_debt || 0,
          business_registration_number: d.business_registration_number || '',
          business_start_date: d.business_start_date || '',
          years_in_business: d.years_in_business || 3,
          revenue_regularity_months: d.revenue_regularity_months || 12,
        });
        this.verificationNotes.set(d.verification_notes || '');
      } else {
        this.extractedData.set(null);
        this.verifiedFields.set({
          full_name: app.applicant_name || 'Demandeur',
          date_of_birth: '1988-06-12',
          id_number: 'ML-NINA-2026',
          id_type: 'NINA',
          monthly_revenue: 450000,
          secondary_revenue: 0,
          monthly_expenses: 180000,
          other_recurring_expenses: 0,
          existing_debt: 0,
          business_registration_number: '',
          business_start_date: '2021-01-15',
          years_in_business: 3,
          revenue_regularity_months: 12,
        });
        this.verificationNotes.set('Données saisies et certifiées par l\'agent.');
      }

      // 2. Scoring Result
      if (scRes.status === 'fulfilled') {
        this.scoringResult.set(scRes.value);
      } else {
        this.scoringResult.set(null);
      }

      // 3. Guarantees
      if (guarRes.status === 'fulfilled') {
        this.guarantees.set(guarRes.value);
      } else {
        this.guarantees.set([]);
      }

      // 4. Debts
      if (debtsRes.status === 'fulfilled') {
        this.debts.set(debtsRes.value);
      } else {
        this.debts.set([]);
      }

      // 5. Granting method resolution
      this.resolveGrantingMethod(app.requested_amount);

      this.approveAmount.set(app.requested_amount);
      this.toast.info('Dossier ouvert', `Dossier ${app.reference} (${app.applicant_name || 'Client'}) chargé.`);
    } catch {
      this.extractedData.set(null);
      this.scoringResult.set(null);
    } finally {
      this.detailLoading.set(false);
    }
  }

  resolveGrantingMethod(amount: number): void {
    const match = this.allGrantingMethods().find(
      m => m.is_active && m.min_amount <= amount && m.max_amount >= amount
    );
    this.applicableGrantingMethod.set(match || null);
  }

  closeDetail(): void {
    this.selectedApp.set(null);
    this.extractedData.set(null);
    this.scoringResult.set(null);
    this.guarantees.set([]);
    this.debts.set([]);
  }

  setDetailTab(tab: DetailTab): void {
    this.currentDetailTab.set(tab);
    if (tab === 'audit_logs' && this.selectedApp()) {
      this.loadAppAuditLogs(this.selectedApp()!.id);
    }
  }

  // ── PARTIE 1: DONNÉES FINANCIÈRES, DETTES & GARANTIES (ÉDITABLE) ─────
  updateField(field: string, value: any): void {
    this.verifiedFields.update(f => ({ ...f, [field]: value }));
  }

  async saveFinancials(): Promise<void> {
    const app = this.selectedApp();
    if (!app) return;

    this.savingFinancials.set(true);
    try {
      const fields = this.verifiedFields();
      fields.verification_notes = this.verificationNotes();
      const updatedData = await this.api.verifyData(app.id, fields);
      this.extractedData.set(updatedData);
      this.toast.success(
        'Données Financières Enregistrées',
        'Les revenus, charges et informations d\'activité ont été certifiés conformes.'
      );

      await this.loadApplications();
      const updated = this.applications().find(a => a.id === app.id);
      if (updated) this.selectedApp.set(updated);
    } catch (e: any) {
      this.toast.error('Erreur enregistrement', e.message);
    } finally {
      this.savingFinancials.set(false);
    }
  }

  // Guarantee Operations
  openAddGuaranteeModal(): void {
    this.newGuaranteeType.set('terrain');
    this.newGuaranteeDesc.set('');
    this.newGuaranteeEst.set(1000000);
    this.newGuaranteeRet.set(700000);
    this.newGuaranteeProof.set('');
    this.showAddGuaranteeModal.set(true);
  }

  onEstValChange(est: number): void {
    this.newGuaranteeEst.set(est);
    // Suggest standard 70% retained value haircut
    this.newGuaranteeRet.set(Math.round(est * 0.7));
  }

  async addGuarantee(): Promise<void> {
    const app = this.selectedApp();
    if (!app) return;

    if (!this.newGuaranteeDesc() || this.newGuaranteeEst() <= 0) {
      this.toast.error('Champs requis', 'Veuillez saisir une description et une valeur estimée.');
      return;
    }

    this.savingGuarantee.set(true);
    try {
      const g = await this.api.addGuarantee(app.id, {
        guarantee_type: this.newGuaranteeType(),
        description: this.newGuaranteeDesc(),
        estimated_value: this.newGuaranteeEst(),
        retained_value: this.newGuaranteeRet() || Math.round(this.newGuaranteeEst() * 0.7),
        proof_reference: this.newGuaranteeProof() || undefined,
      });

      this.guarantees.update(list => [...list, g]);
      this.showAddGuaranteeModal.set(false);
      this.toast.success('Garantie enregistrée', `Garantie "${g.description}" ajoutée au dossier.`);
    } catch (e: any) {
      this.toast.error('Erreur garantie', e.message);
    } finally {
      this.savingGuarantee.set(false);
    }
  }

  deleteGuarantee(guaranteeId: number): void {
    const g = this.guarantees().find(item => item.id === guaranteeId);
    this.itemToDelete.set({
      type: 'guarantee',
      id: guaranteeId,
      label: g ? `${g.guarantee_type} (${g.description || ''})` : 'cette garantie'
    });
    this.showDeleteConfirmModal.set(true);
  }

  // Debt Operations
  openAddDebtModal(): void {
    this.newDebtCreditor.set('');
    this.newDebtInternal.set(false);
    this.newDebtInitial.set(500000);
    this.newDebtRemaining.set(300000);
    this.newDebtMonthly.set(50000);
    this.showAddDebtModal.set(true);
  }

  async addDebt(): Promise<void> {
    const app = this.selectedApp();
    if (!app) return;

    if (!this.newDebtCreditor() || this.newDebtMonthly() <= 0) {
      this.toast.error('Champs requis', 'Veuillez préciser le nom du créancier et la mensualité.');
      return;
    }

    this.savingDebt.set(true);
    try {
      const d = await this.api.addDebt(app.id, {
        creditor_name: this.newDebtCreditor(),
        is_internal: this.newDebtInternal(),
        initial_amount: this.newDebtInitial(),
        remaining_amount: this.newDebtRemaining(),
        monthly_payment: this.newDebtMonthly(),
      });

      this.debts.update(list => [...list, d]);
      this.showAddDebtModal.set(false);
      this.toast.success('Dette enregistrée', `Engagement envers ${d.creditor_name} consolidé.`);
    } catch (e: any) {
      this.toast.error('Erreur dette', e.message);
    } finally {
      this.savingDebt.set(false);
    }
  }

  deleteDebt(debtId: number): void {
    const d = this.debts().find(item => item.id === debtId);
    this.itemToDelete.set({
      type: 'debt',
      id: debtId,
      label: d ? `dette envers ${d.creditor_name}` : 'cet engagement financier'
    });
    this.showDeleteConfirmModal.set(true);
  }

  async executeDeleteItem(): Promise<void> {
    const item = this.itemToDelete();
    const app = this.selectedApp();
    if (!item || !app) return;

    this.deletingItem.set(true);
    try {
      if (item.type === 'guarantee') {
        await this.api.deleteGuarantee(app.id, item.id);
        this.guarantees.update(list => list.filter(g => g.id !== item.id));
        this.toast.info('Garantie retirée', 'La garantie a été supprimée.');
      } else {
        await this.api.deleteDebt(app.id, item.id);
        this.debts.update(list => list.filter(d => d.id !== item.id));
        this.toast.info('Dette retirée', 'L\'engagement financier a été supprimé.');
      }
      this.showDeleteConfirmModal.set(false);
      this.itemToDelete.set(null);
    } catch (e: any) {
      this.toast.error('Erreur suppression', e.message);
    } finally {
      this.deletingItem.set(false);
    }
  }

  // ── PARTIE 2: ANALYSE & SCORING /100 (RECALCULABLE À VOLONTÉ) ────────
  async recalculateScore(): Promise<void> {
    const app = this.selectedApp();
    if (!app) return;

    this.scoringLoading.set(true);
    this.toast.info('Calcul ML & SHAP', `Calcul de l'évaluation sur base 100 pour ${app.reference}...`);

    try {
      const scoreRes = await this.api.evaluateApplication(app.id);
      this.scoringResult.set(scoreRes);
      this.toast.success(
        'Score Calculé avec Succès',
        `Score : ${scoreRes.score} / 100 — Recommandation : ${scoreRes.decision.toUpperCase()}.`
      );
      await this.loadApplications();
      const updated = this.applications().find(a => a.id === app.id);
      if (updated) this.selectedApp.set(updated);
      this.currentDetailTab.set('scoring_shap');
    } catch (e: any) {
      this.toast.error('Erreur scoring', e.message);
    } finally {
      this.scoringLoading.set(false);
    }
  }

  // ── PARTIE 3: DÉCISION & TRANSMISSION AU COMITÉ ──────────────────────
  async submitToCommittee(): Promise<void> {
    const app = this.selectedApp();
    if (!app) return;

    if (!this.scoringResult()) {
      this.toast.error('Scoring requis', 'Veuillez évaluer et calculer le score avant de soumettre au comité.');
      return;
    }

    this.submittingToCommittee.set(true);
    try {
      const updatedApp = await this.api.submitToCommittee(app.id);
      this.selectedApp.set(updatedApp);
      this.toast.success(
        'Dossier Transmis au Comité de Crédit !',
        `Le dossier ${app.reference} est désormais en file d'attente d'approbation finale par la Direction.`
      );
      await this.loadApplications();
    } catch (e: any) {
      this.toast.error('Erreur transmission', e.message);
    } finally {
      this.submittingToCommittee.set(false);
    }
  }

  // Quick Init by Account Number
  openQuickInitModal(): void {
    this.quickAccountNumber.set('');
    this.quickAccountInfo.set(null);
    this.quickRequestedAmount.set(1000000);
    this.quickRequestedDuration.set(12);
    this.quickBusinessDesc.set('Renforcement de trésorerie & fonds de roulement');
    this.showQuickInitModal.set(true);
  }

  closeQuickInitModal(): void {
    this.showQuickInitModal.set(false);
    this.quickAccountInfo.set(null);
  }

  async searchAccount(): Promise<void> {
    const accNum = this.quickAccountNumber().trim();
    if (!accNum) {
      this.toast.error('Numéro requis', 'Veuillez saisir un numéro de compte (ex: CMF-2026-001245)');
      return;
    }

    this.searchingAccount.set(true);
    try {
      const info = await this.api.lookupAccount(accNum);
      this.quickAccountInfo.set(info);
      this.toast.success('Compte identifié', `Client : ${info.full_name} (${info.activity_sector})`);
    } catch (e: any) {
      this.quickAccountInfo.set(null);
      this.toast.error('Compte introuvable', e.message || 'Numéro de compte non reconnu.');
    } finally {
      this.searchingAccount.set(false);
    }
  }

  async createQuickApplication(): Promise<void> {
    if (!this.quickAccountNumber()) {
      this.toast.error('Compte requis', 'Veuillez renseigner le compte client.');
      return;
    }

    this.creatingQuickApp.set(true);
    try {
      const newApp = await this.api.quickInitApplication({
        account_number: this.quickAccountNumber().trim(),
        requested_amount: this.quickRequestedAmount(),
        requested_duration_months: this.quickRequestedDuration(),
        business_description: this.quickBusinessDesc(),
      });

      this.toast.success('Dossier créé', `Nouveau dossier rapide généré : ${newApp.reference}`);
      this.closeQuickInitModal();
      await this.loadApplications();
      this.selectApplication(newApp);
    } catch (e: any) {
      this.toast.error('Erreur création', e.message);
    } finally {
      this.creatingQuickApp.set(false);
    }
  }

  // Reject / Contact modals
  openRejectModal(): void {
    this.showRejectModal.set(true);
  }

  closeRejectModal(): void {
    this.showRejectModal.set(false);
  }

  async confirmReject(): Promise<void> {
    const app = this.selectedApp();
    if (!app) return;

    this.rejectingApp.set(true);
    try {
      const rejectedApp = await this.api.rejectApplication(app.id, {
        reason: this.rejectReason(),
        notes: this.rejectNotes(),
      });
      this.selectedApp.set(rejectedApp);
      this.toast.warning('Dossier rejeté', `Motif : ${this.rejectReason()}`);
      this.closeRejectModal();
      await this.loadApplications();
    } catch (e: any) {
      this.toast.error('Erreur rejet', e.message);
    } finally {
      this.rejectingApp.set(false);
    }
  }

  openContactModal(channel: 'whatsapp' | 'phone' | 'email' | 'in_app'): void {
    const app = this.selectedApp();
    if (!app) return;
    this.contactChannel.set(channel);
    this.contactSubject.set(`OpenScore Finance — Suivi de votre demande ${app.reference}`);
    const agentName = this.auth.userName() || 'Votre agent';
    this.contactMessage.set(
      `Bonjour ${app.applicant_name || 'Cher client'},\n\nConcernant votre dossier de crédit ${app.reference} de ${this.formatAmount(app.requested_amount)}, veuillez nous transmettre les précisions suivantes...\n\nCordialement,\n${agentName} - OpenScore Finance`
    );
    this.showContactModal.set(true);
  }

  closeContactModal(): void {
    this.showContactModal.set(false);
  }

  async sendClientCommunication(): Promise<void> {
    const app = this.selectedApp();
    if (!app) return;

    this.contactingClient.set(true);
    try {
      const payload: ContactClientRequest = {
        channel: this.contactChannel(),
        subject: this.contactSubject(),
        message: this.contactMessage(),
      };
      const res = await this.api.contactClient(app.id, payload);
      this.toast.success('Communication Enregistrée', res.message);

      if (this.contactChannel() === 'whatsapp' && app.applicant_phone) {
        let phone = app.applicant_phone.replace(/[^0-9+]/g, '').replace('+', '');
        if (phone.length === 8) phone = '223' + phone;
        const encodedText = encodeURIComponent(this.contactMessage());
        window.open(`https://wa.me/${phone}?text=${encodedText}`, '_blank');
      }

      this.closeContactModal();
      await this.loadAppAuditLogs(app.id);
    } catch (e: any) {
      this.toast.error('Erreur communication', e.message);
    } finally {
      this.contactingClient.set(false);
    }
  }

  async loadAppAuditLogs(appId: number): Promise<void> {
    this.auditLoading.set(true);
    try {
      const res = await this.api.getAuditLogs(appId);
      this.auditLogs.set(res.logs);
    } catch {
      this.auditLogs.set([]);
    } finally {
      this.auditLoading.set(false);
    }
  }

  viewReceipt(appId: number): void {
    this.router.navigate(['/receipt', appId]);
  }

  viewScoringAudit(appId: number): void {
    this.router.navigate(['/audit', appId]);
  }

  getStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      draft: 'Brouillon',
      documents_uploaded: 'Docs reçus',
      data_extracted: 'Extraction IA',
      pending_verification: 'À certifier',
      data_verified: 'Certifié conforme',
      scored: 'Évalué (/100)',
      pending_committee_approval: 'En attente Comité',
      approved: 'Accordé & Validé',
      adjusted: 'Contre-proposition',
      rejected: 'Refusé',
    };
    return labels[status] || status;
  }

  getStatusBadgeClass(status: string): string {
    switch (status) {
      case 'pending_verification': return 'badge-warning';
      case 'data_verified': return 'badge-info';
      case 'scored': return 'bg-purple-100 text-purple-900 border border-purple-300 dark:bg-purple-950/60 dark:text-purple-300 dark:border-purple-800';
      case 'pending_committee_approval': return 'bg-amber-100 text-amber-900 border border-amber-300 dark:bg-amber-950/60 dark:text-amber-300 font-bold';
      case 'approved': return 'badge-success';
      case 'adjusted': return 'badge-warning';
      case 'rejected': return 'badge-danger';
      default: return 'badge-neutral';
    }
  }

  getScoreColor(score: number): string {
    if (score >= 75) return 'text-emerald-700 dark:text-emerald-400';
    if (score >= 60) return 'text-blue-900 dark:text-blue-400';
    if (score >= 40) return 'text-amber-700 dark:text-amber-400';
    return 'text-rose-700 dark:text-rose-400';
  }

  getScoreBgColor(score: number): string {
    if (score >= 75) return 'bg-emerald-50 dark:bg-emerald-950/30';
    if (score >= 60) return 'bg-blue-50 dark:bg-blue-950/30';
    if (score >= 40) return 'bg-amber-50 dark:bg-amber-950/30';
    return 'bg-rose-50 dark:bg-rose-950/30';
  }

  getRiskLabel(risk?: string): string {
    if (!risk) return 'Non déterminé';
    const labels: Record<string, string> = {
      low: 'Faible (Solvabilité Élevée)',
      medium: 'Modéré (Surveillance Prudentielle)',
      high: 'Élevé (Garanties Recommandées)',
      critical: 'Critique (Risque Élevé de Défaut)',
    };
    return labels[risk.toLowerCase()] || risk.toUpperCase();
  }

  getDecisionLabel(decision?: string): string {
    if (!decision) return 'En attente d\'arbitrage';
    const labels: Record<string, string> = {
      approved: 'Favorable (Accord suggéré)',
      adjusted: 'Ajustement prudentiel requis',
      rejected: 'Défavorable (Rejet suggéré)',
    };
    return labels[decision.toLowerCase()] || decision;
  }

  formatAmount(amount: number): string {
    return (amount || 0).toLocaleString('fr-FR') + ' FCFA';
  }
}
