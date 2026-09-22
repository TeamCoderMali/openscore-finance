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
  branches = signal<AdminBranchInfo[]>([]);

  // Search & Precise Multi-Filters
  agentSearchQuery = signal<string>('');
  agentBranchFilter = signal<string>('all');
  agentStatusFilter = signal<string>('all'); // 'all', 'active', 'suspended'
  agentWorkloadFilter = signal<string>('all'); // 'all', 'with_pending', 'without_pending'
  agentRateFilter = signal<string>('all'); // 'all', 'high_80', 'low_80'

  // Sorting
  agentSortBy = signal<string>('name'); // 'name', 'branch', 'volume', 'rate', 'apps', 'delay'
  agentSortOrder = signal<'asc' | 'desc'>('asc');

  // Pagination
  agentsPage = signal<number>(1);
  agentsPageSize = signal<number>(5);

  activeFiltersCount = computed(() => {
    let count = 0;
    if (this.agentSearchQuery().trim()) count++;
    if (this.agentBranchFilter() !== 'all') count++;
    if (this.agentStatusFilter() !== 'all') count++;
    if (this.agentWorkloadFilter() !== 'all') count++;
    if (this.agentRateFilter() !== 'all') count++;
    return count;
  });

  filteredAgents = computed(() => {
    let list = this.agents();
    const branch = this.agentBranchFilter();
    const status = this.agentStatusFilter();
    const workload = this.agentWorkloadFilter();
    const rate = this.agentRateFilter();
    const q = this.agentSearchQuery().toLowerCase().trim();

    // 1. Search Query
    if (q) {
      list = list.filter(a =>
        a.full_name?.toLowerCase().includes(q) ||
        a.email?.toLowerCase().includes(q) ||
        (a.phone && a.phone.includes(q)) ||
        a.branch?.toLowerCase().includes(q)
      );
    }

    // 2. Branch Filter
    if (branch !== 'all') {
      list = list.filter(a => a.branch.toLowerCase().includes(branch.toLowerCase()));
    }

    // 3. Status Filter (Active / Suspended)
    if (status !== 'all') {
      const isActive = status === 'active';
      list = list.filter(a => a.is_active === isActive);
    }

    // 4. Workload Filter
    if (workload !== 'all') {
      if (workload === 'with_pending') list = list.filter(a => (a.pending_applications_count || 0) > 0);
      if (workload === 'without_pending') list = list.filter(a => (a.pending_applications_count || 0) === 0);
    }

    // 5. Approval Rate Filter
    if (rate !== 'all') {
      if (rate === 'high_80') list = list.filter(a => (a.approval_rate || 0) >= 80);
      if (rate === 'low_80') list = list.filter(a => (a.approval_rate || 0) < 80);
    }

    // 6. Sorting
    const sortField = this.agentSortBy();
    const sortDir = this.agentSortOrder();
    list.sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case 'branch':
          cmp = (a.branch || '').localeCompare(b.branch || '');
          break;
        case 'volume':
          cmp = (a.approved_volume || 0) - (b.approved_volume || 0);
          break;
        case 'rate':
          cmp = (a.approval_rate || 0) - (b.approval_rate || 0);
          break;
        case 'apps':
          cmp = (a.assigned_applications_count || 0) - (b.assigned_applications_count || 0);
          break;
        case 'delay':
          cmp = (a.average_processing_hours || 0) - (b.average_processing_hours || 0);
          break;
        case 'name':
        default:
          cmp = (a.full_name || '').localeCompare(b.full_name || '');
          break;
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });

    return list;
  });

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
      this.branches.set([]);
    }
  }

  setSort(field: string): void {
    if (this.agentSortBy() === field) {
      this.agentSortOrder.set(this.agentSortOrder() === 'asc' ? 'desc' : 'asc');
    } else {
      this.agentSortBy.set(field);
      this.agentSortOrder.set(field === 'name' ? 'asc' : 'desc');
    }
    this.agentsPage.set(1);
  }

  resetFilters(): void {
    this.agentSearchQuery.set('');
    this.agentBranchFilter.set('all');
    this.agentStatusFilter.set('all');
    this.agentWorkloadFilter.set('all');
    this.agentRateFilter.set('all');
    this.agentSortBy.set('name');
    this.agentSortOrder.set('asc');
    this.agentsPage.set(1);
  }

  openCreateAgentModal(): void {
    this.newAgent.set({
      full_name: '',
      email: '',
      phone: '',
      password: '',
      branch: 'Antenne Centrale Bamako-District',
      agent_code: `AGT-${Date.now().toString().slice(-4)}`,
    });
    this.showCreateAgentModal.set(true);
  }

  closeCreateAgentModal(): void {
    this.showCreateAgentModal.set(false);
  }

  async createAgent(): Promise<void> {
    const a = this.newAgent();
    if (!a.full_name || !a.email || !a.password) {
      this.toast.warning('Champs requis', 'Nom, email et mot de passe obligatoires');
      return;
    }
    this.creatingAgent.set(true);
    try {
      await this.api.createAdminUser({
        full_name: a.full_name,
        email: a.email,
        phone: a.phone,
        password: a.password,
        role: 'agent',
      });
      this.toast.success(
        'Agent de Crédit Provisionné',
        `Le compte pour ${a.full_name} est opérationnel.`
      );
      this.closeCreateAgentModal();
      await this.loadAgents();
    } catch (e: any) {
      this.toast.error('Erreur Provisionnement', e.message);
    } finally {
      this.creatingAgent.set(false);
    }
  }

  openReassignModal(agent: AdminAgentSummary): void {
    this.reassignSourceAgent.set(agent);
    this.reassignTargetAgentId.set(null);
    this.showReassignModal.set(true);
  }

  closeReassignModal(): void {
    this.showReassignModal.set(false);
    this.reassignSourceAgent.set(null);
  }

  async executeReassign(): Promise<void> {
    const src = this.reassignSourceAgent();
    const targetId = this.reassignTargetAgentId();
    if (!src || !targetId) {
      this.toast.warning('Sélection requise', 'Veuillez sélectionner l\'agent destinataire');
      return;
    }
    this.reassigning.set(true);
    try {
      const res = await this.api.reassignAgentApplications(src.id, { target_agent_id: targetId });
      this.toast.success('Dossiers Réassignés', res.message);
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

  async toggleAgentStatus(a: AdminAgentSummary): Promise<void> {
    try {
      const res = await this.api.toggleUserActive(a.id);
      a.is_active = res.is_active;
      this.toast.info(
        'Statut Agent Modifié',
        `L'accès de ${a.full_name} est désormais ${res.is_active ? 'Actif' : 'Suspendu'}.`
      );
      await this.loadAgents();
    } catch (e: any) {
      this.toast.error('Erreur Statut', e.message);
    }
  }

  formatAmount(amount: number): string {
    return (amount || 0).toLocaleString('fr-FR') + ' FCFA';
  }

  formatDelay(hours: number | null | undefined): string {
    if (hours == null) return '—';
    return `~${hours.toFixed(1)}h`;
  }
}
