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

export type DetailTab = 'fiche_instruction' | 'financials_guarantees' | 'committee_submission' | 'audit_logs';

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
  currentDetailTab = signal<DetailTab>('fiche_instruction');

  // Fiche d'Instruction Kafo Jiginew (Salarié & PME)
  ficheData = signal<any>({
    // Fiche Salarié / Particulier
    sal_employer: 'Ministère de l\'Éducation / Secteur Public',
    sal_position: 'Cadre Administratif',
    sal_hiring_date: '2018-03-01',
    sal_contract_type: 'CDI',
    sal_net_salary: 380000,
    sal_seizable_quota: 125000,
    sal_loan_purpose: 'Construction / Amélioration de l\'habitat',
    sal_dga_deposit: 150000,
    sal_guarantor_name: 'Drissa Coulibaly',
    sal_guarantor_phone: '+223 76 12 34 56',
    sal_guarantor_employer: 'Société Malienne de Gestion',
    sal_agent_recommendation: 'Client solvable avec prélèvement direct sur salaire. Avis très favorable.',

    // Fiche PME Kafo Jiginew
    pme_manager_name: 'Amadou Diallo',
    pme_manager_birth: '1982-05-14',
    pme_marital_status: 'Marié(e)',
    pme_dependents: 4,
    pme_manager_residence: 'Bamako, Commune IV',
    pme_company_name: 'ETS DIALLO & FRÈRES',
    pme_legal_form: 'GPE / Entreprise Individuelle',
    pme_registration_number: 'ML-BKO-2019-A-1029',
    pme_years_activity: 5,
    pme_headquarters: 'Grand Marché de Bamako',
    pme_market_outlets: 'Grossistes et détaillants Bamako, Koulikoro, Sikasso',
    pme_land_buildings_value: 12000000,
    pme_vehicles_value: 3500000,
    pme_cash_savings_dga: 750000,
    pme_stock_value: 4500000,
    pme_supplier_debts: 600000,
    pme_equity_capital: 8500000,
    pme_agent_recommendation: 'Activité en pleine expansion avec flux réguliers constatés sur le carnet Kafo Jiginew. Avis favorable.',
  });
  savingFiche = signal<boolean>(false);

  // Guarantees & Debts for Selected Application
  guarantees = signal<Guarantee[]>([]);
  debts = signal<Debt[]>([]);
  applicableGrantingMethod = signal<GrantingMethod | null>(null);
  allGrantingMethods = signal<GrantingMethod[]>([]);

  // Filters & Multi-Search (Reference OSF-... or Account CMF-...)
  searchQuery = signal<string>('');
  selectedStatusFilter = signal<string>('all');
  selectedSectorFilter = signal<string>('all');
  selectedBranchFilter = signal<string>('my_branch');
  currentUserBranch = signal<string>('701');
  sortBy = signal<'date_desc' | 'amount_desc' | 'amount_asc'>('date_desc');

  // Regional Branch options for filtering
  branchOptions = computed(() => [
    { code: 'my_branch', label: `Mon Antenne (${this.getBranchShortName(this.currentUserBranch())}) [Par défaut]` },
    { code: 'all', label: 'Toutes les antennes (Vue d\'ensemble)' },
    { code: '701', label: 'Antenne 701 - Bamako District' },
    { code: '702', label: 'Antenne 702 - Caisse Médina-Coura' },
    { code: '801', label: 'Antenne 801 - Sikasso' },
    { code: '802', label: 'Antenne 802 - Caisse Koutiala' },
    { code: '901', label: 'Antenne 901 - Ségou' },
    { code: '902', label: 'Antenne 902 - Mopti' },
    { code: '903', label: 'Antenne 903 - Kayes' },
  ]);

  // Pagination
  pipelinePage = signal<number>(1);
  pipelinePageSize = signal<number>(6);

  // Editable Financial & Personal Fields (Part 1)
  verifiedFields = signal<VerifyDataRequest>({});
  verificationNotes = signal<string>('');
  savingFinancials = signal<boolean>(false);

  // Guarantee Management Modal
  showAddGuaranteeModal = signal<boolean>(false);
  newGuaranteeType = signal<string>('gage_vehicule');
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

  // Quick Init Application Modal (By Account Number With Auto-Prefill & Type Choice)
  showQuickInitModal = signal<boolean>(false);
  quickAccountNumber = signal<string>('');
  quickAccountInfo = signal<any | null>(null);
  quickApplicationType = signal<'INDIVIDUAL' | 'PME'>('INDIVIDUAL');
  quickBranchCode = signal<string>('701');
  quickApplicantName = signal<string>('');
  quickApplicantPhone = signal<string>('');
  quickApplicantEmail = signal<string>('');
  quickActivitySector = signal<string>('Commerce');
  quickMonthlyRevenue = signal<number>(450000);
  quickMonthlyExpenses = signal<number>(200000);
  quickRequestedAmount = signal<number>(1000000);
  quickRequestedDuration = signal<number>(12);
  quickBusinessDesc = signal<string>('Renforcement de trésorerie & approvisionnement');
  searchingAccount = signal<boolean>(false);
  creatingQuickApp = signal<boolean>(false);
  forceCrossBranchOverride = signal<boolean>(false);

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

  // Upload requested document modal (Réponse à la demande du Comité)
  showUploadDocModal = signal<boolean>(false);
  targetDocRequest = signal<any>(null);
  selectedFileToUpload = signal<File | null>(null);
  uploadDocNotes = signal<string>('');
  uploadingDoc = signal<boolean>(false);

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

    const branch = this.selectedBranchFilter();
    if (branch !== 'my_branch' && branch !== 'all') {
      list = list.filter(a => (a.branch_code || '701') === branch);
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

  async ngOnInit(): Promise<void> {
    const cachedUser = this.auth.currentUser();
    if (cachedUser?.branch_code) {
      this.currentUserBranch.set(cachedUser.branch_code);
      this.quickBranchCode.set(cachedUser.branch_code);
    }
    try {
      const me = await this.api.getMe();
      if ((me as any).branch_code) {
        this.currentUserBranch.set((me as any).branch_code);
        this.quickBranchCode.set((me as any).branch_code);
      }
    } catch {}
    this.loadApplications();
    this.loadGrantingMethods();
  }

  async loadApplications(): Promise<void> {
    this.loading.set(true);
    try {
      const branchParam = this.selectedBranchFilter();
      const result = await this.api.getApplications(
        this.selectedStatusFilter() !== 'all' ? this.selectedStatusFilter() : undefined,
        this.selectedSectorFilter() !== 'all' ? this.selectedSectorFilter() : undefined,
        branchParam !== 'all' ? branchParam : undefined
      );
      this.applications.set(result.applications);
    } catch {
      this.toast.error('Erreur chargement', 'Impossible de récupérer la liste des dossiers.');
    } finally {
      this.loading.set(false);
    }
  }

  onBranchFilterChange(): void {
    this.pipelinePage.set(1);
    this.loadApplications();
  }

  getBranchName(code?: string): string {
    const map: Record<string, string> = {
      '701': 'Antenne 701 - Bamako District',
      '702': 'Antenne 702 - Caisse Médina-Coura',
      '801': 'Antenne 801 - Sikasso',
      '802': 'Antenne 802 - Caisse Koutiala',
      '901': 'Antenne 901 - Ségou',
      '902': 'Antenne 902 - Mopti',
      '903': 'Antenne 903 - Kayes',
    };
    return map[code || '701'] || `Antenne ${code || '701'}`;
  }

  getBranchShortName(code?: string): string {
    const map: Record<string, string> = {
      '701': '701 Bamako',
      '702': '702 Médina',
      '801': '801 Sikasso',
      '802': '802 Koutiala',
      '901': '901 Ségou',
      '902': '902 Mopti',
      '903': '903 Kayes',
    };
    return map[code || '701'] || `${code || '701'}`;
  }

  getBranchBadgeClass(code?: string): string {
    switch (code) {
      case '701':
      case '702':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300 border border-blue-200 dark:border-blue-800';
      case '801':
      case '802':
        return 'bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-300 border border-amber-200 dark:border-amber-800';
      case '901':
        return 'bg-purple-100 text-purple-900 dark:bg-purple-900/40 dark:text-purple-300 border border-purple-200 dark:border-purple-800';
      case '902':
      case '903':
        return 'bg-emerald-100 text-emerald-900 dark:bg-emerald-900/40 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800';
      default:
        return 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300 border border-slate-200';
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
    this.currentDetailTab.set('fiche_instruction');

    // Populate Fiche Data if available, else derive sensible defaults
    if (app.form_data && typeof app.form_data === 'object' && Object.keys(app.form_data).length > 0) {
      this.ficheData.set({ ...this.ficheData(), ...app.form_data });
    } else {
      const anyApp = app as any;
      const rev = anyApp.applicant?.monthly_revenue || 380000;
      const req = app.requested_amount || 1000000;
      this.ficheData.set({
        ...this.ficheData(),
        sal_net_salary: rev,
        sal_seizable_quota: Math.round(rev * 0.33),
        sal_dga_deposit: Math.round(req * 0.10),
        pme_company_name: anyApp.applicant?.full_name || 'ENTREPRISE DU SOCIÉTAIRE',
        pme_manager_name: app.applicant_name || anyApp.applicant?.full_name || '',
        pme_registration_number: anyApp.applicant?.id_number || 'ML-BKO-2026',
        pme_stock_value: Math.round(req * 1.3),
        pme_cash_savings_dga: Math.round(req * 0.15),
        pme_equity_capital: Math.round(req * 2.5),
      });
    }

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
      this.currentDetailTab.set('committee_submission');
    } catch (e: any) {
      this.toast.error('Erreur scoring', e.message);
    } finally {
      this.scoringLoading.set(false);
    }
  }

  // ── FICHE D'INSTRUCTION: ENREGISTREMENT ──────────────────────────────
  async saveFiche(): Promise<void> {
    const app = this.selectedApp();
    if (!app) return;

    this.savingFiche.set(true);
    try {
      const updated = await this.api.updateApplicationFormData(app.id, this.ficheData());
      this.selectedApp.set(updated);
      this.toast.success(
        'Fiche Enregistrée',
        'La fiche d\'instruction Kafo Jiginew a été mise à jour avec succès.'
      );
    } catch (e: any) {
      this.toast.error('Erreur sauvegarde', e.message);
    } finally {
      this.savingFiche.set(false);
    }
  }

  // ── TRANSMISSION AU COMITÉ (DÉCLENCHE SCORING AUTOMATIQUE) ───────────
  async submitToCommittee(): Promise<void> {
    const app = this.selectedApp();
    if (!app) return;

    this.submittingToCommittee.set(true);
    try {
      // 1. Sauvegarder d'abord la fiche d'instruction
      await this.api.updateApplicationFormData(app.id, this.ficheData());

      // 2. Transmettre au comité (génère automatiquement le scoring ML côté serveur)
      const updatedApp = await this.api.submitToCommittee(app.id);
      this.selectedApp.set(updatedApp);
      this.toast.success(
        'Dossier Transmis au Comité !',
        `Le dossier ${app.reference} a été instruit, scoré automatiquement et transmis au Comité de Crédit pour arbitrage.`
      );
      await this.loadApplications();
    } catch (e: any) {
      this.toast.error('Erreur transmission', e.message);
    } finally {
      this.submittingToCommittee.set(false);
    }
  }

  // Quick Init by Account Number With Auto-Prefill & Type Selection
  openQuickInitModal(): void {
    this.quickAccountNumber.set('');
    this.quickAccountInfo.set(null);
    this.forceCrossBranchOverride.set(false);
    this.quickApplicationType.set('INDIVIDUAL');
    this.quickBranchCode.set(this.currentUserBranch());
    this.quickApplicantName.set('');
    this.quickApplicantPhone.set('');
    this.quickApplicantEmail.set('');
    this.quickActivitySector.set('Commerce');
    this.quickMonthlyRevenue.set(450000);
    this.quickMonthlyExpenses.set(200000);
    this.quickRequestedAmount.set(1000000);
    this.quickRequestedDuration.set(12);
    this.quickBusinessDesc.set('Renforcement de trésorerie & fonds de roulement');
    this.showQuickInitModal.set(true);
  }

  closeQuickInitModal(): void {
    this.showQuickInitModal.set(false);
    this.quickAccountInfo.set(null);
    this.forceCrossBranchOverride.set(false);
  }

  abortDuplicateApplication(): void {
    const info = this.quickAccountInfo();
    const name = info?.full_name || 'le sociétaire';
    this.closeQuickInitModal();
    this.toast.info(
      'Création Annulée (Prudence BCEAO)',
      `Dossier non créé pour ${name} suite à la détection d'un dossier actif dans une autre antenne.`
    );
  }

  async searchAccount(): Promise<void> {
    const accNum = this.quickAccountNumber().trim();
    if (!accNum) {
      this.toast.error('Numéro requis', 'Veuillez saisir un numéro de compte (ex: CMF-701-001245)');
      return;
    }

    this.searchingAccount.set(true);
    this.forceCrossBranchOverride.set(false);
    try {
      const info = await this.api.lookupAccount(accNum);
      this.quickAccountInfo.set(info);
      this.quickApplicantName.set(info.full_name || '');
      this.quickApplicantPhone.set(info.phone || '');
      this.quickApplicantEmail.set(info.email || '');
      this.quickActivitySector.set(info.activity_sector || 'Commerce');
      this.quickMonthlyRevenue.set(info.monthly_revenue || 450000);
      this.quickMonthlyExpenses.set(info.monthly_expenses || 200000);
      this.quickBranchCode.set(info.branch_code || this.currentUserBranch());
      this.quickApplicationType.set(info.suggested_application_type || 'INDIVIDUAL');

      if (info.has_active_other_branch) {
        if (info.has_no_dossier_in_current_branch) {
          const firstOther = info.other_branch_applications?.[0];
          this.toast.warning(
            'Alerte Multi-Antennes : Dossier en cours !',
            `Aucun dossier dans votre antenne, mais dossier actif détecté dans ${firstOther?.branch_name || 'une autre antenne'} (${firstOther?.reference || ''}).`
          );
        } else {
          this.toast.warning(
            'Dossiers Multi-Antennes',
            'Ce sociétaire possède des dossiers en cours dans plusieurs antennes.'
          );
        }
      } else {
        this.toast.success(
          'Compte Identifié & Prérempli',
          `Client : ${info.full_name} (${info.activity_sector}) - Antenne ${info.branch_code}`
        );
      }
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

    if (this.quickAccountInfo()?.has_active_other_branch && !this.forceCrossBranchOverride()) {
      this.toast.warning(
        'Action Bloquée (Prudence)',
        "Ce client possède déjà un dossier en cours dans une autre antenne. Cochez la dérogation pour continuer ou cliquez sur 'Ne pas créer'."
      );
      return;
    }

    this.creatingQuickApp.set(true);
    try {
      const newApp = await this.api.quickInitApplication({
        account_number: this.quickAccountNumber().trim(),
        requested_amount: this.quickRequestedAmount(),
        requested_duration_months: this.quickRequestedDuration(),
        business_description: this.quickBusinessDesc(),
        branch_code: this.quickBranchCode(),
        application_type: this.quickApplicationType(),
        force_override_cross_branch: this.forceCrossBranchOverride(),
      });

      this.toast.success('Dossier créé', `Nouveau dossier généré : ${newApp.reference}`);
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

  // ── Demandes de Documents Complémentaires (Comité) ─────────────
  openUploadDocModal(req?: any): void {
    this.targetDocRequest.set(req || this.selectedApp()?.form_data?.latest_document_request || null);
    this.selectedFileToUpload.set(null);
    this.uploadDocNotes.set('');
    this.showUploadDocModal.set(true);
  }

  closeUploadDocModal(): void {
    this.showUploadDocModal.set(false);
    this.selectedFileToUpload.set(null);
    this.targetDocRequest.set(null);
  }

  onFileSelected(event: any): void {
    const file = event.target.files?.[0];
    if (file) {
      this.selectedFileToUpload.set(file);
    }
  }

  async submitRequestedDocument(): Promise<void> {
    const app = this.selectedApp();
    const file = this.selectedFileToUpload();
    if (!app || !file) {
      this.toast.warning('Fichier requis', 'Veuillez sélectionner le fichier à transmettre au Comité.');
      return;
    }

    this.uploadingDoc.set(true);
    try {
      const reqId = this.targetDocRequest()?.id;
      const res = await this.api.uploadRequestedDocument(app.id, file, reqId, this.uploadDocNotes());

      this.toast.success(
        'Document transmis au Comité',
        `La pièce "${file.name}" a été transmise à la Direction et rattachée au dossier.`
      );

      // Update local state
      const updatedForm = res.form_data || {
        ...(app.form_data || {}),
        has_pending_document_request: false,
      };

      this.selectedApp.update(curr => curr ? { ...curr, form_data: updatedForm } : null);
      this.applications.update(list => list.map(a => a.id === app.id ? { ...a, form_data: updatedForm } : a));

      this.closeUploadDocModal();
    } catch (e: any) {
      this.toast.error('Erreur téléversement', e.message || 'Impossible de téléverser le document.');
    } finally {
      this.uploadingDoc.set(false);
    }
  }
}
