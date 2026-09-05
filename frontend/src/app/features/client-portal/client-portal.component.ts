import { Component, signal, computed, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { Subscription } from 'rxjs';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { OfflineSyncService } from '../../core/services/offline-sync.service';
import { ToastService } from '../../core/services/toast.service';
import { SvgIconComponent } from '../../shared/components/svg-icon/svg-icon.component';
import { SpinnerComponent } from '../../shared/components/spinner/spinner.component';
import { VoiceAssistantComponent } from '../../shared/components/voice-assistant/voice-assistant.component';
import {
  ActivitySector, CreditApplication, ExtractedData, VoiceQueryResponse, AuditLog
} from '../../shared/models/application.model';

export type ClientView = 'applications' | 'dashboard' | 'documents' | 'simulator' | 'voice' | 'guarantors';
export type Step = 'profile' | 'documents' | 'voice' | 'decision';

export interface GuarantorInfo {
  fullName: string;
  phone: string;
  relationship: string;
  activitySector: string;
  marketLocation: string;
  tontineGroup?: string;
}

@Component({
  selector: 'app-client-portal',
  standalone: true,
  imports: [CommonModule, FormsModule, SvgIconComponent, SpinnerComponent, VoiceAssistantComponent],
  templateUrl: './client-portal.component.html',
  styleUrls: ['./client-portal.component.css'],
})
export class ClientPortalComponent implements OnInit, OnDestroy {
  // Main view switcher
  currentView = signal<ClientView>('applications');
  private querySub?: Subscription;

  // Multi-step form state
  currentStep = signal<Step>('profile');
  steps: Step[] = ['profile', 'documents', 'voice', 'decision'];

  // Profile form
  activitySector = signal<ActivitySector>('Commerce');
  requestedAmount = signal<number>(500000);
  durationMonths = signal<number>(12);
  businessDescription = signal<string>('');

  // Document upload
  selectedFiles = signal<File[]>([]);
  isDragOver = signal<boolean>(false);
  extractionProgress = signal<boolean>(false);
  extractedData = signal<ExtractedData | null>(null);

  // Application & Decision
  application = signal<CreditApplication | null>(null);
  existingApplications = signal<CreditApplication[]>([]);
  loading = signal<boolean>(false);
  initialLoading = signal<boolean>(true);
  error = signal<string>('');

  // Audit log modal/drawer
  selectedAuditLogs = signal<AuditLog[]>([]);
  showAuditModal = signal<boolean>(false);
  auditLoading = signal<boolean>(false);
  currentAuditRef = signal<string>('');

  // Loan Capacity Simulator
  simAmount = signal<number>(750000);
  simDuration = signal<number>(12);
  simMonthlyRevenue = signal<number>(350000);
  simMonthlyRate = signal<number>(1.5); // 1.5% per month (standard UEMOA)

  // Guarantor & Tontine state
  guarantors = signal<GuarantorInfo[]>([
    {
      fullName: 'Ousmane Sangaré',
      phone: '+223 76 11 22 33',
      relationship: 'Président de Tontine / Voisin de stand',
      activitySector: 'Commerce de gros',
      marketLocation: 'Grand Marché de Bamako (Hall 3)',
      tontineGroup: 'Tontine Benkadi des Commerçants',
    }
  ]);
  newGuarantor = signal<GuarantorInfo>({
    fullName: '',
    phone: '',
    relationship: 'Membre Tontine',
    activitySector: 'Commerce',
    marketLocation: 'Grand Marché de Bamako',
    tontineGroup: '',
  });
  showAddGuarantorModal = signal<boolean>(false);

  // Step labels
  stepLabels: Record<Step, string> = {
    profile: 'Profil & Montant',
    documents: 'Justificatifs IA',
    voice: 'Assistant Vocal',
    decision: 'Décision & Suivi',
  };

  sectors: ActivitySector[] = ['Commerce', 'Agriculture', 'Artisanat', 'TPE'];

  formattedAmount = computed(() => {
    return this.requestedAmount().toLocaleString('fr-FR') + ' FCFA';
  });

  currentStepIndex = computed(() => this.steps.indexOf(this.currentStep()));
  isOnline = computed(() => this.offlineSync.isOnline());

  // Simulator Computed KPIs
  simMonthlyPayment = computed(() => {
    const p = this.simAmount();
    const n = this.simDuration();
    const r = (this.simMonthlyRate() / 100);
    if (r === 0) return p / n;
    return Math.round((p * r) / (1 - Math.pow(1 + r, -n)));
  });

  simTotalRepayment = computed(() => {
    return this.simMonthlyPayment() * this.simDuration();
  });

  simTotalInterest = computed(() => {
    return this.simTotalRepayment() - this.simAmount();
  });

  simDebtEffortRate = computed(() => {
    const rev = this.simMonthlyRevenue();
    if (rev <= 0) return 0;
    return Math.min(100, Math.round((this.simMonthlyPayment() / rev) * 100));
  });

  // Approved applications count for documents list
  completedApplications = computed(() => {
    return this.existingApplications().filter(a =>
      ['approved', 'adjusted', 'data_verified', 'scored', 'rejected'].includes(a.status)
    );
  });

  // ── Pagination Signals ──────────────────────────────────────────
  appsPage = signal<number>(1);
  appsPageSize = signal<number>(5);
  pagedApplications = computed(() => {
    const start = (this.appsPage() - 1) * this.appsPageSize();
    return this.existingApplications().slice(start, start + this.appsPageSize());
  });
  totalAppsPages = computed(() => Math.max(1, Math.ceil(this.existingApplications().length / this.appsPageSize())));

  docsPage = signal<number>(1);
  docsPageSize = signal<number>(5);
  pagedDocuments = computed(() => {
    const start = (this.docsPage() - 1) * this.docsPageSize();
    return this.completedApplications().slice(start, start + this.docsPageSize());
  });
  totalDocsPages = computed(() => Math.max(1, Math.ceil(this.completedApplications().length / this.docsPageSize())));

  constructor(
    private api: ApiService,
    public auth: AuthService,
    public offlineSync: OfflineSyncService,
    private router: Router,
    private route: ActivatedRoute,
    private toast: ToastService,
  ) { }

  ngOnInit(): void {
    // Listen to queryParams to switch views seamlessly
    this.querySub = this.route.queryParams.subscribe(params => {
      const view = params['view'] as ClientView;
      if (view && ['applications', 'dashboard', 'documents', 'simulator', 'voice', 'guarantors'].includes(view)) {
        this.currentView.set(view);
      }
    });

    this.loadExistingApplications();
  }

  ngOnDestroy(): void {
    this.querySub?.unsubscribe();
  }

  setView(view: ClientView): void {
    this.currentView.set(view);
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { view },
      queryParamsHandling: 'merge',
    });
  }

  async loadExistingApplications(): Promise<void> {
    this.initialLoading.set(true);
    try {
      const result = await this.api.getApplications();
      this.existingApplications.set(result.applications);

      const scored = result.applications.find(a =>
        ['approved', 'adjusted', 'rejected', 'scored'].includes(a.status)
      );
      if (scored) {
        this.application.set(scored);
      }
    } catch {
      // Handled via offline fallback
    } finally {
      this.initialLoading.set(false);
    }
  }

  // ── Step navigation ─────────────────────────────────────────────
  goToStep(step: Step): void {
    const targetIdx = this.steps.indexOf(step);
    const currentIdx = this.currentStepIndex();

    if (targetIdx <= currentIdx || this.canProceedTo(step)) {
      this.currentStep.set(step);
    }
  }

  canProceedTo(step: Step): boolean {
    if (step === 'documents') {
      return this.requestedAmount() > 0 && !!this.activitySector();
    }
    if (step === 'voice') {
      return true;
    }
    if (step === 'decision') {
      return !!this.application();
    }
    return true;
  }

  nextStep(): void {
    const nextIdx = this.currentStepIndex() + 1;
    if (nextIdx < this.steps.length) {
      this.currentStep.set(this.steps[nextIdx]);
    }
  }

  prevStep(): void {
    const prevIdx = this.currentStepIndex() - 1;
    if (prevIdx >= 0) {
      this.currentStep.set(this.steps[prevIdx]);
    }
  }

  // ── Step 1: Create / Save Application ───────────────────────────
  async submitProfile(): Promise<void> {
    this.loading.set(true);
    this.error.set('');

    try {
      const app = await this.api.createApplication({
        activity_sector: this.activitySector(),
        requested_amount: this.requestedAmount(),
        requested_duration_months: this.durationMonths(),
        business_description: this.businessDescription(),
      });

      this.application.set(app);
      await this.loadExistingApplications();

      if (app.is_offline_draft) {
        this.toast.info(
          'Dossier enregistré localement',
          'Enregistré en mode hors-ligne. Il sera synchronisé dès le retour du réseau.'
        );
      } else {
        this.toast.success(
          'Dossier initié',
          `Référence : ${app.reference}`
        );
      }

      this.nextStep();
    } catch (e: any) {
      this.error.set(e.message || 'Erreur lors de la création du dossier');
      this.toast.error('Erreur', this.error());
    } finally {
      this.loading.set(false);
    }
  }

  // ── Step 2: Document Upload ─────────────────────────────────────
  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files) {
      this.handleFiles(Array.from(input.files));
    }
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.isDragOver.set(true);
  }

  onDragLeave(): void {
    this.isDragOver.set(false);
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.isDragOver.set(false);
    if (event.dataTransfer?.files) {
      this.handleFiles(Array.from(event.dataTransfer.files));
    }
  }

  private handleFiles(files: File[]): void {
    const valid = files.filter(f =>
      f.type.startsWith('image/') || f.type === 'application/pdf'
    );
    this.selectedFiles.update(current => [...current, ...valid]);
  }

  removeFile(index: number): void {
    this.selectedFiles.update(files => files.filter((_, i) => i !== index));
  }

  async extractDocuments(): Promise<void> {
    const app = this.application();
    if (!app || app.id <= 0) {
      this.toast.warning('Attention', 'Veuillez d\'abord valider l\'étape 1');
      return;
    }

    const files = this.selectedFiles();
    if (files.length === 0) {
      this.toast.warning('Aucun fichier', 'Sélectionnez au moins un document');
      return;
    }

    this.extractionProgress.set(true);
    try {
      const data = await this.api.extractDocuments(app.id, files[0]);
      this.extractedData.set(data);
      this.toast.success('Extraction terminée', 'Les données du document ont été analysées avec succès.');
      this.nextStep();
    } catch (e: any) {
      this.toast.error('Erreur d\'extraction', e.message);
    } finally {
      this.extractionProgress.set(false);
    }
  }

  // ── Step 3: Voice assistant ─────────────────────────────────────
  onVoiceResult(result: VoiceQueryResponse): void {
    if (result.suggested_field) {
      const { field, value } = result.suggested_field;
      if (field === 'activity_sector' && this.sectors.includes(value)) {
        this.activitySector.set(value);
        this.toast.info('Secteur mis à jour', `Détecté par la voix : ${value}`);
      } else if (field === 'requested_amount' && typeof value === 'number') {
        this.requestedAmount.set(value);
        this.toast.info('Montant mis à jour', `${value.toLocaleString('fr-FR')} FCFA`);
      }
    }
  }

  // ── Audit logs ──────────────────────────────────────────────────
  async openAudit(appId: number, ref: string): Promise<void> {
    this.currentAuditRef.set(ref);
    this.showAuditModal.set(true);
    this.auditLoading.set(true);
    try {
      const res = await this.api.getAuditLogs(appId);
      this.selectedAuditLogs.set(res.logs);
    } catch (e: any) {
      this.toast.error('Erreur audit', e.message);
    } finally {
      this.auditLoading.set(false);
    }
  }

  closeAudit(): void {
    this.showAuditModal.set(false);
    this.selectedAuditLogs.set([]);
  }

  // ── Simulator Transfer ──────────────────────────────────────────
  applySimulatorToApplication(): void {
    this.requestedAmount.set(this.simAmount());
    this.durationMonths.set(this.simDuration());
    this.setView('applications');
    this.currentStep.set('profile');
    this.toast.success(
      'Paramètres transférés',
      `Demande configurée : ${this.simAmount().toLocaleString('fr-FR')} FCFA sur ${this.simDuration()} mois.`
    );
  }

  // ── Guarantor Management ────────────────────────────────────────
  openAddGuarantor(): void {
    this.newGuarantor.set({
      fullName: '',
      phone: '',
      relationship: 'Membre Tontine',
      activitySector: 'Commerce',
      marketLocation: 'Grand Marché de Bamako',
      tontineGroup: '',
    });
    this.showAddGuarantorModal.set(true);
  }

  closeAddGuarantor(): void {
    this.showAddGuarantorModal.set(false);
  }

  addGuarantor(): void {
    const g = this.newGuarantor();
    if (!g.fullName || !g.phone) {
      this.toast.warning('Champs obligatoires', 'Veuillez renseigner le nom et le téléphone');
      return;
    }
    this.guarantors.update(list => [...list, g]);
    this.toast.success('Caution Solidaire Enregistrée', `Garant ${g.fullName} associé à votre profil.`);
    this.closeAddGuarantor();
  }

  removeGuarantor(idx: number): void {
    this.guarantors.update(list => list.filter((_, i) => i !== idx));
    this.toast.info('Garant retiré', 'La caution solidaire a été retirée.');
  }

  // ── Status Helpers (100% French) ───────────────────────────────
  getStatusLabel(status?: string): string {
    if (!status) return 'En cours d\'examen';
    const labels: Record<string, string> = {
      draft: 'Brouillon',
      documents_uploaded: 'Justificatifs reçus',
      data_extracted: 'Extraction IA terminée',
      pending_verification: 'En vérification agent',
      data_verified: 'Données certifiées',
      scored: 'Scoring calculé',
      approved: 'Accordé / Validé',
      adjusted: 'Contre-proposition émise',
      rejected: 'Non éligible / Rejeté',
    };
    return labels[status] || status;
  }

  getStatusBadgeClass(status?: string): string {
    if (!status) return 'bg-slate-100 text-slate-700 border-slate-200';
    switch (status) {
      case 'approved': return 'bg-emerald-100 text-emerald-800 border border-emerald-300';
      case 'adjusted': return 'bg-blue-100 text-blue-800 border border-blue-300';
      case 'data_verified': return 'bg-indigo-100 text-indigo-800 border border-indigo-300';
      case 'pending_verification':
      case 'draft': return 'bg-amber-100 text-amber-800 border border-amber-300';
      case 'rejected': return 'bg-rose-100 text-rose-800 border border-rose-300';
      default: return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  }

  // ── Helper ──────────────────────────────────────────────────────
  formatAmount(amount: number): string {
    return (amount || 0).toLocaleString('fr-FR') + ' FCFA';
  }

  viewReceipt(appId: number): void {
    this.router.navigate(['/receipt', appId]);
  }
}
