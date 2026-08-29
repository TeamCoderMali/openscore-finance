import { Component, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { ToastService } from '../../core/services/toast.service';
import { SvgIconComponent } from '../../shared/components/svg-icon/svg-icon.component';
import { SpinnerComponent } from '../../shared/components/spinner/spinner.component';
import { ScoringResult, CreditApplication } from '../../shared/models/application.model';

@Component({
  selector: 'app-score-audit',
  standalone: true,
  imports: [CommonModule, FormsModule, SvgIconComponent, SpinnerComponent],
  templateUrl: './score-audit.component.html',
  styleUrls: ['./score-audit.component.css'],
})
export class ScoreAuditComponent implements OnInit {
  appId = 0;
  application = signal<CreditApplication | null>(null);
  scoring = signal<ScoringResult | null>(null);
  loading = signal(true);
  error = signal('');

  // Counter-proposal controls
  proposedAmount = signal(0);
  proposedDuration = signal(12);
  recalculating = signal(false);
  recalcResult = signal<ScoringResult | null>(null);

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private api: ApiService,
    public auth: AuthService,
    private toast: ToastService,
  ) {}

  ngOnInit(): void {
    this.appId = Number(this.route.snapshot.paramMap.get('id'));
    this.loadData();
  }

  async loadData(): Promise<void> {
    this.loading.set(true);
    try {
      const [app, scoring] = await Promise.all([
        this.api.getApplication(this.appId),
        this.api.getScoringResult(this.appId),
      ]);
      this.application.set(app);
      this.scoring.set(scoring);

      this.proposedAmount.set(scoring.proposed_amount || app.requested_amount);
      this.proposedDuration.set(scoring.proposed_duration_months || app.requested_duration_months);
    } catch (e: any) {
      this.error.set(e.message);
      this.toast.error('Erreur audit', 'Impossible de charger les resultats de scoring.');
    } finally {
      this.loading.set(false);
    }
  }

  async recalculate(): Promise<void> {
    this.recalculating.set(true);
    try {
      const result = await this.api.recalculateScore(this.appId, {
        proposed_amount: this.proposedAmount(),
        proposed_duration_months: this.proposedDuration(),
      });
      this.recalcResult.set(result);
      this.toast.success(
        'Contre-proposition recalculee',
        `Nouveau score : ${result.score}/1000 — Decision : ${result.decision.toUpperCase()}`
      );
    } catch (e: any) {
      this.error.set(e.message);
      this.toast.error('Erreur calcul', e.message);
    } finally {
      this.recalculating.set(false);
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

  getGaugeWidth(score: number): number {
    return Math.min(100, Math.max(0, score / 10));
  }

  getGaugeColor(score: number): string {
    if (score >= 750) return 'bg-emerald-600';
    if (score >= 600) return 'bg-blue-700';
    if (score >= 400) return 'bg-amber-500';
    return 'bg-rose-600';
  }

  getRiskLabel(risk: string): string {
    const labels: Record<string, string> = {
      low: 'Faible',
      medium: 'Moyen',
      high: 'Eleve',
      very_high: 'Tres eleve',
    };
    return labels[risk] || risk;
  }

  getRiskBadgeClass(risk: string): string {
    switch (risk) {
      case 'low': return 'badge-success';
      case 'medium': return 'badge-info';
      case 'high': return 'badge-warning';
      case 'very_high': return 'badge-danger';
      default: return 'badge-neutral';
    }
  }

  getDecisionLabel(decision: string): string {
    switch (decision) {
      case 'approved': return 'Accorde';
      case 'adjusted': return 'Montant ajuste';
      case 'rejected': return 'Non eligible';
      default: return decision;
    }
  }

  getDecisionBadgeClass(decision: string): string {
    switch (decision) {
      case 'approved': return 'badge-success';
      case 'adjusted': return 'badge-warning';
      case 'rejected': return 'badge-danger';
      default: return 'badge-neutral';
    }
  }

  getImpactIcon(impact: string): string {
    return impact === 'positive' ? 'check-circle' : 'alert';
  }

  getImpactColor(impact: string): string {
    return impact === 'positive' ? 'text-emerald-600' : 'text-rose-600';
  }

  formatAmount(amount: number): string {
    return amount.toLocaleString('fr-FR') + ' FCFA';
  }

  goToReceipt(): void {
    this.router.navigate(['/receipt', this.appId]);
  }

  goBack(): void {
    if (this.auth.userRole() === 'agent') {
      this.router.navigate(['/agent']);
    } else {
      this.router.navigate(['/client']);
    }
  }
}
