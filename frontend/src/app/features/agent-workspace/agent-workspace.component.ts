import { Component, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { ToastService } from '../../core/services/toast.service';
import { SvgIconComponent } from '../../shared/components/svg-icon/svg-icon.component';
import { SpinnerComponent } from '../../shared/components/spinner/spinner.component';
import {
  CreditApplication, ExtractedData, VerifyDataRequest
} from '../../shared/models/application.model';

@Component({
  selector: 'app-agent-workspace',
  standalone: true,
  imports: [CommonModule, FormsModule, SvgIconComponent, SpinnerComponent],
  templateUrl: './agent-workspace.component.html',
  styleUrls: ['./agent-workspace.component.css'],
})
export class AgentWorkspaceComponent {
  applications = signal<CreditApplication[]>([]);
  selectedApp = signal<CreditApplication | null>(null);
  extractedData = signal<ExtractedData | null>(null);

  // Editable verified fields
  verifiedFields = signal<VerifyDataRequest>({});
  verificationNotes = signal('');

  loading = signal(false);
  detailLoading = signal(false);
  scoringLoading = signal(false);
  verifying = signal(false);
  error = signal('');
  success = signal('');

  // Stats
  pendingCount = computed(() =>
    this.applications().filter(a => a.status === 'pending_verification').length
  );
  verifiedCount = computed(() =>
    this.applications().filter(a => ['data_verified', 'scored', 'approved', 'adjusted', 'rejected'].includes(a.status)).length
  );

  constructor(
    private api: ApiService,
    public auth: AuthService,
    private router: Router,
    private toast: ToastService,
  ) {
    this.loadApplications();
  }

  async loadApplications(): Promise<void> {
    this.loading.set(true);
    try {
      const result = await this.api.getApplications();
      this.applications.set(result.applications);
    } catch (e: any) {
      this.error.set(e.message);
      this.toast.error('Erreur chargement', 'Impossible de recuperer la liste des dossiers.');
    } finally {
      this.loading.set(false);
    }
  }

  async selectApplication(app: CreditApplication): Promise<void> {
    this.selectedApp.set(app);
    this.detailLoading.set(true);
    this.error.set('');
    this.success.set('');

    try {
      const data = await this.api.getExtractedData(app.id);
      this.extractedData.set(data);
      this.verifiedFields.set({
        full_name: data.full_name || '',
        date_of_birth: data.date_of_birth || '',
        id_number: data.id_number || '',
        id_type: data.id_type || '',
        monthly_revenue: data.monthly_revenue || 0,
        monthly_expenses: data.monthly_expenses || 0,
        existing_debt: data.existing_debt || 0,
        business_registration_number: data.business_registration_number || '',
        business_start_date: data.business_start_date || '',
        years_in_business: data.years_in_business || 0,
        revenue_regularity_months: data.revenue_regularity_months || 0,
      });
      this.toast.info('Dossier charge', `Dossier ${app.reference} ouvert pour audit.`);
    } catch {
      this.extractedData.set(null);
      this.error.set('Aucune donnee extraite pour ce dossier');
      this.toast.warning('Extraction manquante', 'Aucun document traite par l\'IA pour cette demande.');
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
      await this.api.verifyData(app.id, fields);
      this.success.set('Donnees verifiees et certifiees avec succes');
      this.toast.success(
        'Donnees certifiees',
        `Le dossier ${app.reference} est desormais pret pour le scoring decisionnel.`
      );

      await this.loadApplications();
      const updated = this.applications().find(a => a.id === app.id);
      if (updated) this.selectedApp.set(updated);
    } catch (e: any) {
      this.error.set(e.message);
      this.toast.error('Echec de validation', e.message);
    } finally {
      this.verifying.set(false);
    }
  }

  async evaluateApplication(): Promise<void> {
    const app = this.selectedApp();
    if (!app) return;

    this.scoringLoading.set(true);
    this.error.set('');
    this.toast.info('Calcul du score', `Moteur OpenScore en cours d'execution pour ${app.reference}...`);

    try {
      const scoreRes = await this.api.evaluateApplication(app.id);
      this.toast.success(
        'Scoring termine',
        `Score : ${scoreRes.score}/1000 — Decision : ${scoreRes.decision.toUpperCase()}`
      );
      this.router.navigate(['/audit', app.id]);
    } catch (e: any) {
      this.error.set(e.message);
      this.toast.error('Erreur scoring', e.message);
    } finally {
      this.scoringLoading.set(false);
    }
  }

  closeDetail(): void {
    this.selectedApp.set(null);
    this.extractedData.set(null);
    this.error.set('');
    this.success.set('');
  }

  getStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      draft: 'Brouillon',
      pending_verification: 'A verifier',
      data_verified: 'Verifie',
      scored: 'Evalue',
      approved: 'Accorde',
      adjusted: 'Ajuste',
      rejected: 'Rejete',
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

  formatAmount(amount: number): string {
    return amount.toLocaleString('fr-FR') + ' FCFA';
  }

  viewScoring(appId: number): void {
    this.router.navigate(['/audit', appId]);
  }
}
