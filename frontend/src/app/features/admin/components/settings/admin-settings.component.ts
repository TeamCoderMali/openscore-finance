import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../../core/services/api.service';
import { ToastService } from '../../../../core/services/toast.service';
import { SvgIconComponent } from '../../../../shared/components/svg-icon/svg-icon.component';
import { SpinnerComponent } from '../../../../shared/components/spinner/spinner.component';
import { AdminPrudentialSettings } from '../../../../shared/models/application.model';

@Component({
  selector: 'app-admin-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, SvgIconComponent, SpinnerComponent],
  templateUrl: './admin-settings.component.html',
})
export class AdminSettingsComponent implements OnInit {
  settings = signal<AdminPrudentialSettings>({
    debt_ratio_ceiling: 0.40,
    min_disposable_income: 75000,
    approval_score_threshold: 750,
    counter_proposal_threshold: 600,
    rejection_threshold: 400,
    bceao_max_monthly_interest: 2.0,
    shap_debt_weight: 0.30,
    shap_income_weight: 0.20,
    shap_regularity_weight: 0.20,
    shap_seniority_weight: 0.15,
    shap_leverage_weight: 0.15,
  });
  settingsLoading = signal<boolean>(false);
  savingSettings = signal<boolean>(false);

  constructor(
    private api: ApiService,
    private toast: ToastService,
  ) {}

  ngOnInit(): void {
    this.loadSettings();
  }

  async loadSettings(): Promise<void> {
    this.settingsLoading.set(true);
    try {
      const data = await this.api.getPrudentialSettings();
      this.settings.set(data);
    } catch {
      // Keep defaults
    } finally {
      this.settingsLoading.set(false);
    }
  }

  async savePrudentialSettings(): Promise<void> {
    this.savingSettings.set(true);
    try {
      const updated = await this.api.updatePrudentialSettings(this.settings());
      this.settings.set(updated);
      this.toast.success(
        'Politique Prudentielle Enregistrée',
        'Les seuils d\'octroi BCEAO et poids ML sont appliqués à l\'ensemble du réseau IMF.'
      );
    } catch (e: any) {
      this.toast.error('Erreur enregistrement', e.message);
    } finally {
      this.savingSettings.set(false);
    }
  }
}
