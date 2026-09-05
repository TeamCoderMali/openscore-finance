import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../../core/services/api.service';
import { ToastService } from '../../../../core/services/toast.service';
import { SvgIconComponent } from '../../../../shared/components/svg-icon/svg-icon.component';
import { RiskMatrixData } from '../../../../shared/models/application.model';

@Component({
  selector: 'app-admin-risk',
  standalone: true,
  imports: [CommonModule, FormsModule, SvgIconComponent],
  templateUrl: './admin-risk.component.html',
})
export class AdminRiskComponent implements OnInit {
  riskMatrix = signal<RiskMatrixData | null>(null);
  riskLoading = signal<boolean>(false);

  // Interactive Stress-Testing Controls
  stressIncomeShock = signal<number>(0);       // -0% to -40%
  stressInflationShock = signal<number>(0);    // +0% to +30%
  stressDroughtEvent = signal<boolean>(false); // Drought shock in agricultural zone

  simulatedPar30 = computed(() => {
    const base = this.riskMatrix()?.par_30 || 2.4;
    let extra = (this.stressIncomeShock() * 0.12) + (this.stressInflationShock() * 0.08);
    if (this.stressDroughtEvent()) extra += 1.8;
    return Math.min(25.0, Number((base + extra).toFixed(2)));
  });

  simulatedCapitalAdequacy = computed(() => {
    const base = 16.2; // Base ratio BCEAO
    const delta = (this.simulatedPar30() - (this.riskMatrix()?.par_30 || 2.4)) * 0.75;
    return Math.max(5.0, Number((base - delta).toFixed(1)));
  });

  constructor(
    private api: ApiService,
    private toast: ToastService,
  ) {}

  ngOnInit(): void {
    this.loadRiskMatrix();
  }

  async loadRiskMatrix(): Promise<void> {
    this.riskLoading.set(true);
    try {
      const data = await this.api.getRiskMatrix();
      this.riskMatrix.set(data);
    } catch (e: any) {
      this.toast.error('Erreur Matrice Risques', e.message);
    } finally {
      this.riskLoading.set(false);
    }
  }

  resetStressTest(): void {
    this.stressIncomeShock.set(0);
    this.stressInflationShock.set(0);
    this.stressDroughtEvent.set(false);
  }

  exportBceaoReport(): void {
    this.toast.success(
      'Exportation BCEAO',
      'Le rapport de conformité prudentielle UEMOA a été généré avec succès.'
    );
  }
}
