import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../../core/services/api.service';
import { ToastService } from '../../../../core/services/toast.service';
import { SvgIconComponent } from '../../../../shared/components/svg-icon/svg-icon.component';
import { SpinnerComponent } from '../../../../shared/components/spinner/spinner.component';
import {
  ScoringPolicy, ScoringVariable, GrantingMethod
} from '../../../../shared/models/application.model';

@Component({
  selector: 'app-admin-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, SvgIconComponent, SpinnerComponent],
  templateUrl: './admin-settings.component.html',
})
export class AdminSettingsComponent implements OnInit {
  // Policy & Variables
  policy = signal<ScoringPolicy | null>(null);
  policyLoading = signal<boolean>(false);
  savingPolicy = signal<boolean>(false);

  // Variable Modal
  showVarModal = signal<boolean>(false);
  editingVarId = signal<number | null>(null);
  varCode = signal<string>('');
  varName = signal<string>('');
  varDescription = signal<string>('');
  varWeight = signal<number>(20);
  varCategory = signal<string>('financial');
  varImpactDirection = signal<string>('positive');
  varIsActive = signal<boolean>(true);
  savingVar = signal<boolean>(false);

  // Granting Methods
  grantingMethods = signal<GrantingMethod[]>([]);
  methodsLoading = signal<boolean>(false);
  showMethodModal = signal<boolean>(false);
  editingMethodId = signal<number | null>(null);
  methodMinAmount = signal<number>(0);
  methodMaxAmount = signal<number>(500000);
  methodProcedureName = signal<string>('');
  methodApprovalLevel = signal<string>('');
  methodRequiredDocs = signal<string>('');
  methodMinGuaranteeRatio = signal<number>(0);
  savingMethod = signal<boolean>(false);

  // Calculated active weight sum (on 100% base)
  activeTotalWeight = computed(() => {
    const p = this.policy();
    if (!p || !p.variables) return 0;
    const sum = p.variables
      .filter(v => v.is_active)
      .reduce((acc, v) => acc + (v.weight <= 1.0 ? v.weight * 100 : v.weight), 0);
    return Math.round(sum * 10) / 10;
  });

  isWeightValid = computed(() => {
    return Math.abs(this.activeTotalWeight() - 100) < 0.5;
  });

  constructor(
    private api: ApiService,
    private toast: ToastService,
  ) {}

  ngOnInit(): void {
    this.loadPolicy();
    this.loadGrantingMethods();
  }

  async loadPolicy(): Promise<void> {
    this.policyLoading.set(true);
    try {
      const data = await this.api.getAdminScoringPolicy();
      this.policy.set(data);
    } catch (e: any) {
      this.toast.error('Erreur politique', e.message);
    } finally {
      this.policyLoading.set(false);
    }
  }

  async loadGrantingMethods(): Promise<void> {
    this.methodsLoading.set(true);
    try {
      const data = await this.api.getGrantingMethods();
      this.grantingMethods.set(data);
    } catch (e: any) {
      this.toast.error('Erreur méthodes d\'octroi', e.message);
    } finally {
      this.methodsLoading.set(false);
    }
  }

  // ── Variable Operations ──────────────────────────────────────────────
  openAddVarModal(): void {
    this.editingVarId.set(null);
    this.varCode.set('');
    this.varName.set('');
    this.varDescription.set('');
    this.varWeight.set(15);
    this.varCategory.set('financial');
    this.varImpactDirection.set('positive');
    this.varIsActive.set(true);
    this.showVarModal.set(true);
  }

  openEditVarModal(v: ScoringVariable): void {
    this.editingVarId.set(v.id || null);
    this.varCode.set(v.code);
    this.varName.set(v.name);
    this.varDescription.set(v.description || '');
    this.varWeight.set(v.weight <= 1.0 ? Math.round(v.weight * 100) : v.weight);
    this.varCategory.set(v.category);
    this.varImpactDirection.set(v.impact_direction);
    this.varIsActive.set(v.is_active);
    this.showVarModal.set(true);
  }

  async saveVariable(): Promise<void> {
    if (!this.varCode() || !this.varName()) {
      this.toast.error('Champs requis', 'Le code et le nom de la variable sont obligatoires.');
      return;
    }

    this.savingVar.set(true);
    try {
      const payload = {
        code: this.varCode(),
        name: this.varName(),
        description: this.varDescription(),
        weight: this.varWeight(),
        category: this.varCategory(),
        impact_direction: this.varImpactDirection(),
        is_active: this.varIsActive(),
      };

      const varId = this.editingVarId();
      if (varId) {
        await this.api.updateScoringVariable(varId, payload);
        this.toast.success('Variable mise à jour', `La variable ${this.varName()} a été modifiée.`);
      } else {
        await this.api.addScoringVariable(payload);
        this.toast.success('Variable ajoutée', `La variable ${this.varName()} a été ajoutée à la politique.`);
      }

      this.showVarModal.set(false);
      await this.loadPolicy();
    } catch (e: any) {
      this.toast.error('Erreur variable', e.message);
    } finally {
      this.savingVar.set(false);
    }
  }

  async toggleVarActive(v: ScoringVariable): Promise<void> {
    if (!v.id) return;
    try {
      await this.api.updateScoringVariable(v.id, { is_active: !v.is_active });
      await this.loadPolicy();
      this.toast.info('Statut variable', `${v.name} est maintenant ${!v.is_active ? 'actif' : 'inactif'}.`);
    } catch (e: any) {
      this.toast.error('Erreur', e.message);
    }
  }

  // Modal suppression variable
  showDeleteVarModal = signal<boolean>(false);
  variableToDelete = signal<ScoringVariable | null>(null);
  deletingVar = signal<boolean>(false);

  deleteVariable(v: ScoringVariable): void {
    if (!v.id) return;
    this.variableToDelete.set(v);
    this.showDeleteVarModal.set(true);
  }

  async executeDeleteVariable(): Promise<void> {
    const v = this.variableToDelete();
    if (!v || !v.id) return;
    this.deletingVar.set(true);
    try {
      await this.api.deleteScoringVariable(v.id);
      this.toast.success('Variable supprimée', `La variable ${v.name} a été retirée.`);
      this.showDeleteVarModal.set(false);
      this.variableToDelete.set(null);
      await this.loadPolicy();
    } catch (e: any) {
      this.toast.error('Erreur suppression', e.message);
    } finally {
      this.deletingVar.set(false);
    }
  }

  async savePolicyThresholds(): Promise<void> {
    const p = this.policy();
    if (!p) return;

    if (!this.isWeightValid()) {
      this.toast.error(
        'Pondération invalide',
        `La somme des poids des variables actives doit être égale à 100% (actuel: ${this.activeTotalWeight()}%).`
      );
      return;
    }

    this.savingPolicy.set(true);
    try {
      const payload = {
        version: `${p.version.split('-')[0]}-v${Date.now().toString().slice(-4)}`,
        approval_threshold: p.approval_threshold,
        counter_proposal_threshold: p.counter_proposal_threshold,
        rejection_threshold: p.rejection_threshold,
        max_debt_ratio: p.max_debt_ratio,
        min_disposable_income: p.min_disposable_income,
        variables: p.variables.map(v => ({
          code: v.code,
          name: v.name,
          description: v.description,
          weight: v.weight,
          category: v.category,
          impact_direction: v.impact_direction,
          is_active: v.is_active,
        })),
      };

      const updated = await this.api.createAdminScoringPolicy(payload);
      this.policy.set(updated);
      this.toast.success('Nouvelle Version Déployée', `La politique ${updated.version} est désormais active sur tout le réseau.`);
    } catch (e: any) {
      this.toast.error('Erreur politique', e.message);
    } finally {
      this.savingPolicy.set(false);
    }
  }

  // ── Granting Methods Operations ──────────────────────────────────────
  openAddMethodModal(): void {
    this.editingMethodId.set(null);
    this.methodMinAmount.set(0);
    this.methodMaxAmount.set(500000);
    this.methodProcedureName.set('');
    this.methodApprovalLevel.set('Conseiller Clientèle');
    this.methodRequiredDocs.set('CNI ou NINA, Justificatif de domicile');
    this.methodMinGuaranteeRatio.set(0);
    this.showMethodModal.set(true);
  }

  openEditMethodModal(m: GrantingMethod): void {
    this.editingMethodId.set(m.id);
    this.methodMinAmount.set(m.min_amount);
    this.methodMaxAmount.set(m.max_amount);
    this.methodProcedureName.set(m.procedure_name);
    this.methodApprovalLevel.set(m.approval_level);
    this.methodRequiredDocs.set(m.required_documents);
    this.methodMinGuaranteeRatio.set(Math.round(m.min_guarantee_ratio * 100));
    this.showMethodModal.set(true);
  }

  async saveGrantingMethod(): Promise<void> {
    if (!this.methodProcedureName()) {
      this.toast.error('Champs requis', 'Le nom de la procédure est obligatoire.');
      return;
    }

    this.savingMethod.set(true);
    try {
      const payload = {
        min_amount: this.methodMinAmount(),
        max_amount: this.methodMaxAmount(),
        procedure_name: this.methodProcedureName(),
        approval_level: this.methodApprovalLevel(),
        required_documents: this.methodRequiredDocs(),
        min_guarantee_ratio: this.methodMinGuaranteeRatio() / 100.0,
        is_active: true,
      };

      const id = this.editingMethodId();
      if (id) {
        await this.api.updateGrantingMethod(id, payload);
        this.toast.success('Palier mis à jour', `Procédure "${this.methodProcedureName()}" mise à jour.`);
      } else {
        await this.api.createGrantingMethod(payload);
        this.toast.success('Nouveau palier créé', `Procédure "${this.methodProcedureName()}" enregistrée.`);
      }

      this.showMethodModal.set(false);
      await this.loadGrantingMethods();
    } catch (e: any) {
      this.toast.error('Erreur méthode d\'octroi', e.message);
    } finally {
      this.savingMethod.set(false);
    }
  }

  formatAmount(amt: number): string {
    return (amt || 0).toLocaleString('fr-FR') + ' FCFA';
  }
}
