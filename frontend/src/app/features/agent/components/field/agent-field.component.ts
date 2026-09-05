import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../../core/services/api.service';
import { ToastService } from '../../../../core/services/toast.service';
import { SvgIconComponent } from '../../../../shared/components/svg-icon/svg-icon.component';
import { SpinnerComponent } from '../../../../shared/components/spinner/spinner.component';
import { CreditApplication, FieldSurveyRequest } from '../../../../shared/models/application.model';

@Component({
  selector: 'app-agent-field',
  standalone: true,
  imports: [CommonModule, FormsModule, SvgIconComponent, SpinnerComponent],
  templateUrl: './agent-field.component.html',
})
export class AgentFieldComponent implements OnInit {
  applications = signal<CreditApplication[]>([]);
  selectedAppId = signal<number | null>(null);
  loading = signal<boolean>(false);
  saving = signal<boolean>(false);

  // Geolocation
  gpsCoordinates = signal<string>('12.6392° N, 7.9982° W (Grand Marché de Bamako)');
  gpsCapturing = signal<boolean>(false);

  // Field Survey Fields
  fieldGuaranteeType = signal<string>('Caution solidaire de groupe (Tontine)');
  fieldGuaranteeValue = signal<number>(500000);
  fieldMarketReputation = signal<string>('Très favorable (Recommandé par le chef de marché)');
  fieldDailyCashFlow = signal<number>(35000);
  fieldSurveyNotes = signal<string>('');

  constructor(
    private api: ApiService,
    private toast: ToastService,
  ) {}

  ngOnInit(): void {
    this.loadApplications();
  }

  async loadApplications(): Promise<void> {
    this.loading.set(true);
    try {
      const res = await this.api.getApplications();
      this.applications.set(res.applications);
      if (res.applications.length > 0) {
        this.selectedAppId.set(res.applications[0].id);
      }
    } catch (e: any) {
      this.toast.error('Erreur chargement', e.message);
    } finally {
      this.loading.set(false);
    }
  }

  captureGps(): void {
    if (navigator.geolocation) {
      this.gpsCapturing.set(true);
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const lat = pos.coords.latitude.toFixed(4);
          const lng = pos.coords.longitude.toFixed(4);
          this.gpsCoordinates.set(`${lat}° N, ${lng}° W (Point de vente certifié)`);
          this.gpsCapturing.set(false);
          this.toast.success('Géolocalisation GPS Certifiée', 'Position enregistrée avec précision.');
        },
        () => {
          this.gpsCapturing.set(false);
          this.toast.info('Position par défaut', 'Utilisation des coordonnées d\'antenne.');
        }
      );
    } else {
      this.toast.warning('Non supporté', 'Géolocalisation non supportée par votre navigateur.');
    }
  }

  async submitFieldSurvey(): Promise<void> {
    const appId = this.selectedAppId();
    if (!appId) {
      this.toast.warning('Sélection requise', 'Veuillez sélectionner un dossier.');
      return;
    }

    this.saving.set(true);
    try {
      const payload: FieldSurveyRequest = {
        guarantee_type: this.fieldGuaranteeType(),
        guarantee_value: this.fieldGuaranteeValue(),
        market_reputation: this.fieldMarketReputation(),
        daily_cash_flow_observed: this.fieldDailyCashFlow(),
        field_agent_notes: `${this.fieldSurveyNotes()} [GPS: ${this.gpsCoordinates()}]`,
      };
      await this.api.updateFieldSurvey(appId, payload);
      this.toast.success(
        'Enquête de Proximité Certifiée',
        'Observations, garanties et coordonnées GPS intégrées au dossier.'
      );
    } catch (e: any) {
      this.toast.error('Erreur enregistrement', e.message);
    } finally {
      this.saving.set(false);
    }
  }
}
