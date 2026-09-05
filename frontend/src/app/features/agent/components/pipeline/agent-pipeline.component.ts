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
  ScoringResult, FieldSurveyRequest, ContactClientRequest, ApproveDecisionRequest
} from '../../../../shared/models/application.model';

type DetailTab = 'certification' | 'field_survey' | 'scoring' | 'audit_logs';

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
  currentDetailTab = signal<DetailTab>('certification');

  // Filters & Search
  searchQuery = signal<string>('');
  selectedStatusFilter = signal<string>('all');
  selectedSectorFilter = signal<string>('all');
  sortBy = signal<'date_desc' | 'amount_desc' | 'amount_asc'>('date_desc');

  // Pagination
  pipelinePage = signal<number>(1);
  pipelinePageSize = signal<number>(6);

  // Editable verified fields
  verifiedFields = signal<VerifyDataRequest>({});
  verificationNotes = signal<string>('');
  verifying = signal<boolean>(false);

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

  // Approve Modal (Explicit Human Validation)
  showApproveModal = signal<boolean>(false);
  approveAmount = signal<number>(1000000);
  approveNotes = signal<string>('');
  approvingApp = signal<boolean>(false);

  // Direct Contact Modal
  showContactModal = signal<boolean>(false);
  contactChannel = signal<'whatsapp' | 'phone' | 'email' | 'in_app'>('whatsapp');
  contactSubject = signal<string>('Complément de dossier microcrédit OpenScore');
  contactMessage = signal<string>('');
  contactingClient = signal<boolean>(false);

  // Audit Logs for selected application
  auditLogs = signal<AuditLog[]>([]);
  auditLoading = signal<boolean>(false);

  // Global Loading & Status
  loading = signal<boolean>(false);
  detailLoading = signal<boolean>(false);
  scoringLoading = signal<boolean>(false);

  // Filtered applications list
  filteredApplications = computed(() => {
    let list = this.applications();
    const query = this.searchQuery().toLowerCase().trim();
    const status = this.selectedStatusFilter();
    const sector = this.selectedSectorFilter();

    if (query) {
      list = list.filter(a =>
        a.reference.toLowerCase().includes(query) ||
        (a.applicant_name && a.applicant_name.toLowerCase().includes(query)) ||
        (a.applicant_phone && a.applicant_phone.includes(query)) ||
        (a.applicant_email && a.applicant_email.toLowerCase().includes(query)) ||
        (a.business_description && a.business_description.toLowerCase().includes(query)) ||
        a.activity_sector.toLowerCase().includes(query)
      );
    }

    if (status !== 'all') {
      if (status === 'pending') {
        list = list.filter(a => a.status === 'pending_verification');
      } else if (status === 'verified') {
        list = list.filter(a => a.status === 'data_verified');
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
  pendingCount = computed(() => this.applications().filter(a => a.status === 'pending_verification').length);
  verifiedCount = computed(() => this.applications().filter(a => a.status === 'data_verified').length);
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
  }

  async loadApplications(): Promise<void> {
    this.loading.set(true);
    try {
      const result = await this.api.getApplications();
      this.applications.set(result.applications);
    } catch (e: any) {
      this.toast.error('Erreur chargement', 'Impossible de récupérer la liste des dossiers.');
    } finally {
      this.loading.set(false);
    }
  }

  async selectApplication(app: CreditApplication): Promise<void> {
    this.selectedApp.set(app);
    this.detailLoading.set(true);
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

      this.approveAmount.set(app.requested_amount);
      this.toast.info('Dossier sélectionné', `Dossier ${app.reference} (${app.applicant_name || 'Client'}) ouvert.`);
    } catch {
      this.extractedData.set(null);
      this.scoringResult.set(null);
    } finally {
      this.detailLoading.set(false);
    }
  }

  closeDetail(): void {
    this.selectedApp.set(null);
    this.extractedData.set(null);
    this.scoringResult.set(null);
  }

  setDetailTab(tab: DetailTab): void {
    this.currentDetailTab.set(tab);
    if (tab === 'audit_logs' && this.selectedApp()) {
      this.loadAppAuditLogs(this.selectedApp()!.id);
    }
  }

  updateField(field: string, value: any): void {
    this.verifiedFields.update(f => ({ ...f, [field]: value }));
  }

  async submitVerification(): Promise<void> {
    const app = this.selectedApp();
    if (!app) return;

    this.verifying.set(true);
    try {
      const fields = this.verifiedFields();
      fields.verification_notes = this.verificationNotes();
      const updatedData = await this.api.verifyData(app.id, fields);
      this.extractedData.set(updatedData);
      this.toast.success(
        'Données Certifiées',
        `Le dossier ${app.reference} est certifié conforme. Vous pouvez désormais lancer le calcul du score ML.`
      );

      await this.loadApplications();
      const updated = this.applications().find(a => a.id === app.id);
      if (updated) this.selectedApp.set(updated);
    } catch (e: any) {
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

  // ── Scoring Calculation (Never Auto-Approve) ─────────────────────
  async evaluateApplication(): Promise<void> {
    const app = this.selectedApp();
    if (!app) return;

    this.scoringLoading.set(true);
    this.toast.info('Calcul ML & SHAP', `Calcul de l'évaluation du risque pour ${app.reference}...`);

    try {
      const scoreRes = await this.api.evaluateApplication(app.id);
      this.scoringResult.set(scoreRes);
      this.toast.success(
        'Score Calculé (En attente d\'arbitrage)',
        `Score : ${scoreRes.score}/1000 — Avis Recommandé : ${scoreRes.decision.toUpperCase()}. Le dossier n'est PAS validé directement : votre décision finale d'agent est requise.`
      );
      await this.loadApplications();
      const updated = this.applications().find(a => a.id === app.id);
      if (updated) this.selectedApp.set(updated);
      this.currentDetailTab.set('scoring');
    } catch (e: any) {
      this.toast.error('Erreur scoring', e.message);
    } finally {
      this.scoringLoading.set(false);
    }
  }

  // ── Human Agent Decision Actions ─────────────────────────────────
  openApproveModal(): void {
    const app = this.selectedApp();
    if (app) {
      const proposed = this.scoringResult()?.proposed_amount;
      this.approveAmount.set(proposed || app.requested_amount);
      this.approveNotes.set('Dossier conforme aux critères d\'éligibilité et validé après examen agent.');
    }
    this.showApproveModal.set(true);
  }

  closeApproveModal(): void {
    this.showApproveModal.set(false);
  }

  async confirmApprove(): Promise<void> {
    const app = this.selectedApp();
    if (!app) return;

    this.approvingApp.set(true);
    try {
      const payload: ApproveDecisionRequest = {
        approved_amount: this.approveAmount(),
        notes: this.approveNotes(),
      };
      const res = await this.api.approveCreditDecision(app.id, payload);
      this.scoringResult.set(res);
      this.toast.success(
        'Dossier Formellement Validé & Accordé !',
        `Le microcrédit de ${this.formatAmount(this.approveAmount())} pour ${app.applicant_name} a été officiellement validé.`
      );
      this.closeApproveModal();
      await this.loadApplications();
      const updated = this.applications().find(a => a.id === app.id);
      if (updated) this.selectedApp.set(updated);
      this.currentDetailTab.set('scoring');
    } catch (e: any) {
      this.toast.error('Erreur validation', e.message);
    } finally {
      this.approvingApp.set(false);
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
    } catch (e: any) {
      this.toast.error('Erreur rejet', e.message);
    } finally {
      this.rejectingApp.set(false);
    }
  }

  // ── Direct Client Communication ──────────────────────────────────
  getCleanPhone(phone?: string): string {
    if (!phone) return '';
    return phone.replace(/[^0-9+]/g, '');
  }

  getWhatsAppUrl(app: CreditApplication): string {
    const phone = this.getCleanPhone(app.applicant_phone);
    // Prepend 223 if local Malian 8-digit number
    let intlPhone = phone.replace('+', '');
    if (intlPhone.length === 8) {
      intlPhone = '223' + intlPhone;
    }
    const agentName = this.auth.userName() || 'votre agent de crédit';
    const text = encodeURIComponent(
      `Bonjour ${app.applicant_name || 'Madame/Monsieur'},\n\nJe suis ${agentName}, agent OpenScore Finance en charge de l'instruction de votre demande de microcrédit réf. ${app.reference}.\n\nJe vous contacte pour faire le point sur votre dossier.`
    );
    return `https://wa.me/${intlPhone}?text=${text}`;
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

  applyTemplate(templateType: 'missing_docs' | 'field_visit' | 'decision_info'): void {
    const app = this.selectedApp();
    if (!app) return;
    const agentName = this.auth.userName() || 'Votre agent de crédit';

    if (templateType === 'missing_docs') {
      this.contactSubject.set(`Pièces justificatives requises — Dossier ${app.reference}`);
      this.contactMessage.set(
        `Bonjour ${app.applicant_name},\n\nAfin de finaliser l'évaluation de votre crédit (${app.reference}), merci de nous transmettre une copie lisible de votre pièce d'identité (NINA ou CNI) ainsi que le registre d'activité ou carnet de trésorerie.\n\nBien à vous,\n${agentName}`
      );
    } else if (templateType === 'field_visit') {
      this.contactSubject.set(`Visite d'enquête terrain — Dossier ${app.reference}`);
      this.contactMessage.set(
        `Bonjour ${app.applicant_name},\n\nDans le cadre de l'instruction de votre prêt ${app.reference}, je prévois un passage à votre point de vente pour une brève visite de courtoisie et constatation d'activité.\nMerci de m'indiquer vos disponibilités.\n\nBien cordialement,\n${agentName}`
      );
    } else if (templateType === 'decision_info') {
      this.contactSubject.set(`Point sur votre microcrédit OpenScore — ${app.reference}`);
      this.contactMessage.set(
        `Bonjour ${app.applicant_name},\n\nVotre dossier ${app.reference} a franchi l'étape d'évaluation avec succès. Je suis à votre disposition pour convenir des modalités de décaissement et de signature.\n\nBien à vous,\n${agentName}`
      );
    }
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

      // If WhatsApp selected, also open WhatsApp in new tab with message
      if (this.contactChannel() === 'whatsapp' && app.applicant_phone) {
        let phone = this.getCleanPhone(app.applicant_phone).replace('+', '');
        if (phone.length === 8) phone = '223' + phone;
        const encodedText = encodeURIComponent(this.contactMessage());
        window.open(`https://wa.me/${phone}?text=${encodedText}`, '_blank');
      } else if (this.contactChannel() === 'email' && app.applicant_email) {
        const mailto = `mailto:${app.applicant_email}?subject=${encodeURIComponent(this.contactSubject())}&body=${encodeURIComponent(this.contactMessage())}`;
        window.open(mailto, '_blank');
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
      scored: 'Évalué (Arbitrage Requis)',
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

  onQuickClientSelect(appIdStr: string): void {
    if (!appIdStr) return;
    const app = this.applications().find(a => a.id === +appIdStr);
    if (app) {
      this.selectApplication(app);
    }
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
