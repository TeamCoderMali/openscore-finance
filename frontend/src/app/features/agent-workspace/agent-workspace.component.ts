import { Component, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, ActivatedRoute, Params } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { ToastService } from '../../core/services/toast.service';
import { SvgIconComponent } from '../../shared/components/svg-icon/svg-icon.component';
import { SpinnerComponent } from '../../shared/components/spinner/spinner.component';
import {
  CreditApplication, ExtractedData, VerifyDataRequest, AuditLog,
  PortfolioStats, ScoringResult, FieldSurveyRequest
} from '../../shared/models/application.model';

type WorkspaceView = 'pipeline' | 'portfolio' | 'simulator' | 'compliance';
type DetailTab = 'certification' | 'field_survey' | 'scoring' | 'audit_logs';

interface AmortizationRow {
  month: number;
  payment: number;
  principal: number;
  interest: number;
  insurance: number;
  remainingBalance: number;
}

@Component({
  selector: 'app-agent-workspace',
  standalone: true,
  imports: [CommonModule, FormsModule, SvgIconComponent, SpinnerComponent],
  templateUrl: './agent-workspace.component.html',
  styleUrls: ['./agent-workspace.component.css'],
})
export class AgentWorkspaceComponent implements OnInit {
  // Main views
  currentView = signal<WorkspaceView>('pipeline');
  currentDetailTab = signal<DetailTab>('certification');

  // Applications & Data
  applications = signal<CreditApplication[]>([]);
  selectedApp = signal<CreditApplication | null>(null);
  extractedData = signal<ExtractedData | null>(null);
  scoringResult = signal<ScoringResult | null>(null);
  portfolioStats = signal<PortfolioStats | null>(null);

  // Filters & Search
  searchQuery = signal<string>('');
  selectedStatusFilter = signal<string>('all');
  selectedSectorFilter = signal<string>('all');
  sortBy = signal<'date_desc' | 'amount_desc' | 'amount_asc'>('date_desc');

  // Editable verified fields
  verifiedFields = signal<VerifyDataRequest>({});
  verificationNotes = signal<string>('');

  // Field Survey Fields
  fieldGuaranteeType = signal<string>('Caution solidaire de groupe (Tontine)');
  fieldGuaranteeValue = signal<number>(500000);
  fieldMarketReputation = signal<string>('Très favorable');
  fieldDailyCashFlow = signal<number>(35000);
  fieldSurveyNotes = signal<string>('');
  savingFieldSurvey = signal<boolean>(false);

  // Reject Modal
  showRejectModal = signal<boolean>(false);
  rejectReason = signal<string>("Ratio d'endettement supérieur au plafond prudentiel BCEAO (40%)");
  rejectNotes = signal<string>('');
  rejectingApp = signal<boolean>(false);

  // Loan Amortization Simulator (Interactive Tool for Agents)
  simAmount = signal<number>(1000000);
  simDuration = signal<number>(12);
  simMonthlyRate = signal<number>(1.5); // 1.5% per month
  simGraceMonths = signal<number>(0);   // Différé d'amortissement
  simInsuranceRate = signal<number>(0.1); // 0.1% insurance

  // Loading states
  loading = signal<boolean>(false);
  detailLoading = signal<boolean>(false);
  scoringLoading = signal<boolean>(false);
  verifying = signal<boolean>(false);
  statsLoading = signal<boolean>(false);
  error = signal<string>('');
  success = signal<string>('');

  // Audit Logs
  showAuditModal = signal<boolean>(false);
  auditLogs = signal<AuditLog[]>([]);
  auditLoading = signal<boolean>(false);

  // Computed & Filtered list
  filteredApplications = computed(() => {
    let list = this.applications();
    const query = this.searchQuery().toLowerCase().trim();
    const status = this.selectedStatusFilter();
    const sector = this.selectedSectorFilter();

    if (query) {
      list = list.filter(a =>
        a.reference.toLowerCase().includes(query) ||
        (a.applicant_name && a.applicant_name.toLowerCase().includes(query)) ||
        (a.business_description && a.business_description.toLowerCase().includes(query)) ||
        a.activity_sector.toLowerCase().includes(query)
      );
    }

    if (status !== 'all') {
      if (status === 'pending') {
        list = list.filter(a => a.status === 'pending_verification');
      } else if (status === 'verified') {
        list = list.filter(a => a.status === 'data_verified');
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

  // KPI counts
  pendingCount = computed(() =>
    this.applications().filter(a => a.status === 'pending_verification').length
  );
  verifiedCount = computed(() =>
    this.applications().filter(a => ['data_verified', 'scored', 'approved', 'adjusted', 'rejected'].includes(a.status)).length
  );
  approvedCount = computed(() =>
    this.applications().filter(a => a.status === 'approved' || a.status === 'adjusted').length
  );

  // ── Pagination Signals ──────────────────────────────────────────
  pipelinePage = signal<number>(1);
  pipelinePageSize = signal<number>(5);
  pagedPipelineApplications = computed(() => {
    const start = (this.pipelinePage() - 1) * this.pipelinePageSize();
    return this.filteredApplications().slice(start, start + this.pipelinePageSize());
  });
  totalPipelinePages = computed(() => Math.max(1, Math.ceil(this.filteredApplications().length / this.pipelinePageSize())));

  schedulePage = signal<number>(1);
  schedulePageSize = signal<number>(6);
  pagedAmortizationSchedule = computed(() => {
    const start = (this.schedulePage() - 1) * this.schedulePageSize();
    return this.amortizationSchedule().slice(start, start + this.schedulePageSize());
  });
  totalSchedulePages = computed(() => Math.max(1, Math.ceil(this.amortizationSchedule().length / this.schedulePageSize())));
  totalVolumeRequested = computed(() =>
    this.applications().reduce((acc, a) => acc + a.requested_amount, 0)
  );

  // Amortization Schedule Calculation
  amortizationSchedule = computed<AmortizationRow[]>(() => {
    const P = this.simAmount();
    const n = this.simDuration();
    const r = (this.simMonthlyRate() / 100);
    const insRate = (this.simInsuranceRate() / 100);
    const grace = this.simGraceMonths();

    const schedule: AmortizationRow[] = [];
    let balance = P;

    const amortizingMonths = Math.max(1, n - grace);
    const monthlyPayment = r > 0
      ? (balance * r * Math.pow(1 + r, amortizingMonths)) / (Math.pow(1 + r, amortizingMonths) - 1)
      : balance / amortizingMonths;

    for (let m = 1; m <= n; m++) {
      const insurance = balance * insRate;
      let interest = balance * r;
      let principal = 0;
      let payment = 0;

      if (m <= grace) {
        // Grace period: pay only interest and insurance
        principal = 0;
        payment = interest + insurance;
      } else {
        principal = Math.min(balance, monthlyPayment - interest);
        interest = Math.max(0, monthlyPayment - principal);
        payment = principal + interest + insurance;
        balance -= principal;
      }

      schedule.push({
        month: m,
        payment: Math.round(payment),
        principal: Math.round(principal),
        interest: Math.round(interest),
        insurance: Math.round(insurance),
        remainingBalance: Math.max(0, Math.round(balance)),
      });
    }

    return schedule;
  });

  totalSimCost = computed(() => {
    const totalPayments = this.amortizationSchedule().reduce((acc, r) => acc + r.payment, 0);
    const totalInterest = this.amortizationSchedule().reduce((acc, r) => acc + r.interest, 0);
    const totalInsurance = this.amortizationSchedule().reduce((acc, r) => acc + r.insurance, 0);
    return { totalPayments, totalInterest, totalInsurance };
  });

  constructor(
    private api: ApiService,
    public auth: AuthService,
    private router: Router,
    private route: ActivatedRoute,
    private toast: ToastService,
  ) {}

  ngOnInit(): void {
    this.route.queryParams.subscribe(params => {
      const view = params['view'] as WorkspaceView;
      if (view && ['pipeline', 'portfolio', 'simulator'].includes(view)) {
        this.currentView.set(view);
        if (view === 'portfolio') this.loadPortfolioStats();
      }
    });

    this.loadApplications();
    this.loadPortfolioStats();
  }

  async loadApplications(): Promise<void> {
    this.loading.set(true);
    try {
      const result = await this.api.getApplications();
      this.applications.set(result.applications);
    } catch (e: any) {
      this.error.set(e.message);
      this.toast.error('Erreur chargement', 'Impossible de récupérer la liste des dossiers.');
    } finally {
      this.loading.set(false);
    }
  }

  async loadPortfolioStats(): Promise<void> {
    this.statsLoading.set(true);
    try {
      const stats = await this.api.getPortfolioStats();
      this.portfolioStats.set(stats);
    } catch {
      // Non blocking
    } finally {
      this.statsLoading.set(false);
    }
  }

  setView(view: WorkspaceView): void {
    this.currentView.set(view);
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { view },
      queryParamsHandling: 'merge',
    });
    if (view === 'portfolio') {
      this.loadPortfolioStats();
    }
  }

  setDetailTab(tab: DetailTab): void {
    this.currentDetailTab.set(tab);
    if (tab === 'audit_logs' && this.selectedApp()) {
      this.loadAppAuditLogs(this.selectedApp()!.id);
    }
  }

  async selectApplication(app: CreditApplication): Promise<void> {
    this.selectedApp.set(app);
    this.detailLoading.set(true);
    this.error.set('');
    this.success.set('');
    this.currentDetailTab.set('certification');

    try {
      const [data, sc] = await Promise.allSettled([
        this.api.getExtractedData(app.id),
        this.api.getScoringResult(app.id),
      ]);

      if (data.status === 'fulfilled') {
        const d = data.value;
        this.extractedData.set(d);
        this.verifiedFields.set({
          full_name: d.full_name || app.applicant_name,
          date_of_birth: d.date_of_birth || '',
          id_number: d.id_number || '',
          id_type: d.id_type || '',
          monthly_revenue: d.monthly_revenue || 0,
          monthly_expenses: d.monthly_expenses || 0,
          existing_debt: d.existing_debt || 0,
          business_registration_number: d.business_registration_number || '',
          business_start_date: d.business_start_date || '',
          years_in_business: d.years_in_business || 0,
          revenue_regularity_months: d.revenue_regularity_months || 12,
        });
        this.verificationNotes.set(d.verification_notes || '');
      } else {
        this.extractedData.set(null);
        this.verifiedFields.set({
          full_name: app.applicant_name || 'Demandeur',
          date_of_birth: '1988-06-12',
          id_number: 'NINA-BKO-8821',
          id_type: 'NINA',
          monthly_revenue: Math.round(Math.max(350000, app.requested_amount * 0.6)),
          monthly_expenses: Math.round(Math.max(120000, app.requested_amount * 0.25)),
          existing_debt: 0,
          business_registration_number: '',
          business_start_date: '2021-01-15',
          years_in_business: 3,
          revenue_regularity_months: 12,
        });
        this.verificationNotes.set('Évaluation directe et vérification de terrain par l\'agent.');
      }

      if (sc.status === 'fulfilled') {
        this.scoringResult.set(sc.value);
      } else {
        this.scoringResult.set(null);
      }

      // Initialize simulator with selected application's parameters
      this.simAmount.set(app.requested_amount);
      this.simDuration.set(app.requested_duration_months);

      this.toast.info('Dossier sélectionné', `Dossier ${app.reference} chargé.`);
    } catch {
      this.extractedData.set(null);
      this.scoringResult.set(null);
    } finally {
      this.detailLoading.set(false);
    }
  }

  updateField(field: string, value: any): void {
    this.verifiedFields.update(f => ({ ...f, [field]: value }));
  }

  async submitVerification(): Promise<void> {
    const app = this.selectedApp();
    if (!app) return;

    this.verifying.set(true);
    this.error.set('');
    this.success.set('');

    try {
      const fields = this.verifiedFields();
      fields.verification_notes = this.verificationNotes();
      const updatedData = await this.api.verifyData(app.id, fields);
      this.extractedData.set(updatedData);
      this.success.set('Données certifiées avec succès.');
      this.toast.success(
        'Certification effectuée',
        `Le dossier ${app.reference} est certifié et prêt pour le scoring algorithmique.`
      );

      await this.loadApplications();
      const updated = this.applications().find(a => a.id === app.id);
      if (updated) this.selectedApp.set(updated);
    } catch (e: any) {
      this.error.set(e.message);
      this.toast.error('Échec de validation', e.message);
    } finally {
      this.verifying.set(false);
    }
  }

  async saveFieldSurvey(): Promise<void> {
    const app = this.selectedApp();
    if (!app) return;

    this.savingFieldSurvey.set(true);
    try {
      const req: FieldSurveyRequest = {
        guarantee_type: this.fieldGuaranteeType(),
        guarantee_value: this.fieldGuaranteeValue(),
        market_reputation: this.fieldMarketReputation(),
        daily_cash_flow_observed: this.fieldDailyCashFlow(),
        field_agent_notes: this.fieldSurveyNotes(),
      };
      const updated = await this.api.updateFieldSurvey(app.id, req);
      this.extractedData.set(updated);
      this.toast.success('Enquête enregistrée', 'Observations terrain et garanties intégrées au dossier.');
    } catch (e: any) {
      this.toast.error('Erreur enregistrement', e.message);
    } finally {
      this.savingFieldSurvey.set(false);
    }
  }

  async evaluateApplication(): Promise<void> {
    const app = this.selectedApp();
    if (!app) return;

    this.scoringLoading.set(true);
    this.error.set('');
    this.toast.info('Calcul ML & SHAP', `Calcul des probabilités et décomposition pour ${app.reference}...`);

    try {
      const scoreRes = await this.api.evaluateApplication(app.id);
      this.scoringResult.set(scoreRes);
      this.toast.success(
        'Score Calculé avec Succès',
        `Score : ${scoreRes.score}/1000 — Avis IA : ${scoreRes.decision.toUpperCase()} (En attente de validation finale)`
      );
      await this.loadApplications();
      const updated = this.applications().find(a => a.id === app.id);
      if (updated) this.selectedApp.set(updated);
      this.currentDetailTab.set('scoring');
    } catch (e: any) {
      this.error.set(e.message);
      this.toast.error('Erreur scoring', e.message);
    } finally {
      this.scoringLoading.set(false);
    }
  }

  async approveApplication(): Promise<void> {
    const app = this.selectedApp();
    if (!app) return;

    this.scoringLoading.set(true);
    this.error.set('');
    try {
      const res = await this.api.approveCreditDecision(app.id);
      this.scoringResult.set(res);
      this.toast.success(
        'Dossier Validé & Accordé !',
        `Le microcrédit de ${this.formatAmount(app.requested_amount)} pour ${app.applicant_name} a été officiellement approuvé.`
      );
      await this.loadApplications();
      const updated = this.applications().find(a => a.id === app.id);
      if (updated) this.selectedApp.set(updated);
      this.currentDetailTab.set('scoring');
    } catch (e: any) {
      this.error.set(e.message);
      this.toast.error('Erreur validation', e.message);
    } finally {
      this.scoringLoading.set(false);
    }
  }

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
      await this.loadPortfolioStats();
    } catch (e: any) {
      this.toast.error('Erreur rejet', e.message);
    } finally {
      this.rejectingApp.set(false);
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

  viewScoring(appId: number): void {
    this.router.navigate(['/audit', appId]);
  }

  closeDetail(): void {
    this.selectedApp.set(null);
    this.extractedData.set(null);
    this.scoringResult.set(null);
    this.error.set('');
    this.success.set('');
  }

  getStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      draft: 'Brouillon',
      documents_uploaded: 'Docs reçus',
      data_extracted: 'Extraction IA',
      pending_verification: 'À certifier',
      data_verified: 'Certifié',
      scored: 'Évalué',
      approved: 'Accordé',
      adjusted: 'Ajusté',
      rejected: 'Rejeté',
    };
    return labels[status] || status;
  }

  getStatusBadgeClass(status: string): string {
    switch (status) {
      case 'pending_verification': return 'badge-warning';
      case 'data_verified': return 'badge-info';
      case 'approved': return 'badge-success';
      case 'adjusted': return 'badge-warning';
      case 'rejected': return 'badge-danger';
      default: return 'badge-neutral';
    }
  }

  getScoreColor(score: number): string {
    if (score >= 750) return 'text-emerald-700';
    if (score >= 600) return 'text-blue-900';
    if (score >= 400) return 'text-amber-700';
    return 'text-rose-700';
  }

  getScoreBgColor(score: number): string {
    if (score >= 750) return 'bg-emerald-50';
    if (score >= 600) return 'bg-blue-50';
    if (score >= 400) return 'bg-amber-50';
    return 'bg-rose-50';
  }

  formatAmount(amount: number): string {
    return (amount || 0).toLocaleString('fr-FR') + ' FCFA';
  }
}
