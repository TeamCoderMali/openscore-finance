import { Component, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../../core/services/api.service';
import { ToastService } from '../../../../core/services/toast.service';
import { SvgIconComponent } from '../../../../shared/components/svg-icon/svg-icon.component';
import { SpinnerComponent } from '../../../../shared/components/spinner/spinner.component';
import { AdminAgentSummary, AdminBranchInfo } from '../../../../shared/models/application.model';

@Component({
  selector: 'app-admin-agents',
  standalone: true,
  imports: [CommonModule, FormsModule, SvgIconComponent, SpinnerComponent],
  templateUrl: './admin-agents.component.html',
})
export class AdminAgentsComponent implements OnInit {
  agents = signal<AdminAgentSummary[]>([]);
  agentsLoading = signal<boolean>(false);
  agentBranchFilter = signal<string>('all');
  agentSearchQuery = signal<string>('');
  branches = signal<AdminBranchInfo[]>([]);

  filteredAgents = computed(() => {
    let list = this.agents();
    const branch = this.agentBranchFilter();
    const q = this.agentSearchQuery().toLowerCase().trim();

    if (branch !== 'all') {
      list = list.filter(a => a.branch.toLowerCase().includes(branch.toLowerCase()));
    }
    if (q) {
      list = list.filter(a =>
        a.full_name.toLowerCase().includes(q) ||
        a.email.toLowerCase().includes(q) ||
        (a.phone && a.phone.includes(q)) ||
        a.branch.toLowerCase().includes(q)
      );
    }
    return list;
  });

  agentsPage = signal<number>(1);
  agentsPageSize = signal<number>(5);
  pagedAgents = computed(() => {
    const start = (this.agentsPage() - 1) * this.agentsPageSize();
    return this.filteredAgents().slice(start, start + this.agentsPageSize());
  });
  totalAgentsPages = computed(() => Math.max(1, Math.ceil(this.filteredAgents().length / this.agentsPageSize())));

  // Create Agent Modal
  showCreateAgentModal = signal<boolean>(false);
  newAgent = signal({
    full_name: '',
    email: '',
    phone: '',
    password: '',
    branch: 'Antenne Centrale Bamako-District',
    agent_code: 'AGT-BKO-01',
  });
  creatingAgent = signal<boolean>(false);

  // Reassign Applications Modal
  showReassignModal = signal<boolean>(false);
  reassignSourceAgent = signal<AdminAgentSummary | null>(null);
  reassignTargetAgentId = signal<number | null>(null);
  reassigning = signal<boolean>(false);

  // Password Reset Modal
  showResetPasswordModal = signal<boolean>(false);
  targetResetUser = signal<{ id: number; name: string; email: string } | null>(null);
  newPasswordInput = signal<string>('');
  resettingPassword = signal<boolean>(false);

  constructor(
    private api: ApiService,
    private toast: ToastService,
  ) {}

  ngOnInit(): void {
    this.loadAgents();
    this.loadBranches();
  }

  async loadAgents(): Promise<void> {
    this.agentsLoading.set(true);
    try {
      const data = await this.api.getAdminAgents(
        this.agentBranchFilter(),
        this.agentSearchQuery()
      );
      this.agents.set(data);
    } catch (e: any) {
      this.toast.error('Erreur Agents', e.message);
    } finally {
      this.agentsLoading.set(false);
    }
  }

  async loadBranches(): Promise<void> {
    try {
      const b = await this.api.getAdminBranches();
      this.branches.set(b);
    } catch {
      // Keep defaults
    }
  }

  async toggleAgentStatus(a: { id: number; full_name: string; is_active: boolean }): Promise<void> {
    try {
      const res = await this.api.toggleUserActive(a.id);
      a.is_active = res.is_active;
      this.toast.info(
        'Statut Compte Modifié',
        `Le compte ${a.full_name} est désormais ${res.is_active ? 'Actif' : 'Suspendu'}.`
      );
      await this.loadAgents();
    } catch (e: any) {
      this.toast.error('Erreur Statut', e.message);
    }
  }

  openCreateAgentModal(): void {
    this.newAgent.set({
      full_name: '',
      email: '',
      phone: '',
      password: '',
      branch: 'Antenne Centrale Bamako-District',
      agent_code: `AGT-${Math.floor(100 + Math.random() * 900)}`,
    });
    this.showCreateAgentModal.set(true);
  }

  closeCreateAgentModal(): void {
    this.showCreateAgentModal.set(false);
  }

  async createAgent(): Promise<void> {
    const p = this.newAgent();
    if (!p.full_name || !p.email || !p.password) {
      this.toast.warning('Champs requis', 'Nom, email et mot de passe obligatoires');
      return;
    }
    this.creatingAgent.set(true);
    try {
      await this.api.createAdminUser({
        full_name: p.full_name,
        email: p.email,
        phone: p.phone,
        password: p.password,
        role: 'agent',
      });
      this.toast.success(
        'Agent de Crédit Provisionné',
        `L'agent ${p.full_name} est rattaché à l'antenne ${p.branch}.`
      );
      this.closeCreateAgentModal();
      await this.loadAgents();
    } catch (e: any) {
      this.toast.error('Erreur Création Agent', e.message);
    } finally {
      this.creatingAgent.set(false);
    }
  }

  openReassignModal(agent: AdminAgentSummary): void {
    this.reassignSourceAgent.set(agent);
    const other = this.agents().find(a => a.id !== agent.id);
    this.reassignTargetAgentId.set(other ? other.id : null);
    this.showReassignModal.set(true);
  }

  closeReassignModal(): void {
    this.showReassignModal.set(false);
    this.reassignSourceAgent.set(null);
    this.reassignTargetAgentId.set(null);
  }

  async executeReassign(): Promise<void> {
    const src = this.reassignSourceAgent();
    const tgtId = this.reassignTargetAgentId();
    if (!src || !tgtId) {
      this.toast.warning('Sélection requise', 'Veuillez désigner un agent receveur');
      return;
    }
    this.reassigning.set(true);
    try {
      const res = await this.api.reassignAgentApplications(src.id, { target_agent_id: tgtId });
      this.toast.success('Portefeuille Réassigné', res.message);
      this.closeReassignModal();
      await this.loadAgents();
    } catch (e: any) {
      this.toast.error('Erreur Réassignation', e.message);
    } finally {
      this.reassigning.set(false);
    }
  }

  openResetPasswordModal(user: { id: number; full_name: string; email: string }): void {
    this.targetResetUser.set({
      id: user.id,
      name: user.full_name,
      email: user.email,
    });
    this.newPasswordInput.set('');
    this.showResetPasswordModal.set(true);
  }

  closeResetPasswordModal(): void {
    this.showResetPasswordModal.set(false);
    this.targetResetUser.set(null);
  }

  async executeResetPassword(): Promise<void> {
    const u = this.targetResetUser();
    const pwd = this.newPasswordInput();
    if (!u || !pwd || pwd.length < 4) {
      this.toast.warning('Mot de passe trop court', 'Le mot de passe doit comporter au moins 4 caractères');
      return;
    }
    this.resettingPassword.set(true);
    try {
      const res = await this.api.resetUserPassword(u.id, { new_password: pwd });
      this.toast.success('Sécurité Compte', res.message);
      this.closeResetPasswordModal();
    } catch (e: any) {
      this.toast.error('Erreur Réinitialisation', e.message);
    } finally {
      this.resettingPassword.set(false);
    }
  }

  formatAmount(amount: number): string {
    return (amount || 0).toLocaleString('fr-FR') + ' FCFA';
  }
}
