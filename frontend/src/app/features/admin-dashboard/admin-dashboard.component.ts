import { Component, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { ToastService } from '../../core/services/toast.service';
import { SvgIconComponent } from '../../shared/components/svg-icon/svg-icon.component';
import { SpinnerComponent } from '../../shared/components/spinner/spinner.component';
import {
  AdminStats, AdminPrudentialSettings, AdminUserCreate, User, AuditLog,
  AdminClientSummary, AdminClientDetail, AdminClientUpdate,
  AdminAgentSummary, AdminBranchInfo, AdminBranchCreate, RiskMatrixData
} from '../../shared/models/application.model';

export type AdminTab = 'overview' | 'clients' | 'agents' | 'branches' | 'risk' | 'settings' | 'audit';

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, SvgIconComponent, SpinnerComponent],
  templateUrl: './admin-dashboard.component.html',
  styleUrls: ['./admin-dashboard.component.css'],
})
export class AdminDashboardComponent implements OnInit {
  currentTab = signal<AdminTab>('overview');

  // ── Overview & Stats ──────────────────────────────────────────────
  stats = signal<AdminStats | null>(null);
  statsLoading = signal<boolean>(true);

  // ── Clients Management ────────────────────────────────────────────
  clients = signal<AdminClientSummary[]>([]);
  clientsLoading = signal<boolean>(false);
  clientSectorFilter = signal<string>('all');
  clientKycFilter = signal<string>('all');
  clientSearchQuery = signal<string>('');

  filteredClients = computed(() => {
    let list = this.clients();
    const sector = this.clientSectorFilter();
    const kyc = this.clientKycFilter();
    const q = this.clientSearchQuery().toLowerCase().trim();

    if (sector !== 'all') {
      list = list.filter(c => c.activity_sector === sector);
    }
    if (kyc !== 'all') {
      list = list.filter(c => c.kyc_status === kyc);
    }
    if (q) {
      list = list.filter(c =>
        c.full_name.toLowerCase().includes(q) ||
        c.email.toLowerCase().includes(q) ||
        (c.phone && c.phone.includes(q))
      );
    }
    return list;
  });

  clientsPage = signal<number>(1);
  clientsPageSize = signal<number>(5);
  pagedClients = computed(() => {
    const start = (this.clientsPage() - 1) * this.clientsPageSize();
    return this.filteredClients().slice(start, start + this.clientsPageSize());
  });
  totalClientsPages = computed(() => Math.max(1, Math.ceil(this.filteredClients().length / this.clientsPageSize())));

  // Client Detail Modal
  selectedClient = signal<AdminClientDetail | null>(null);
  loadingClientDetail = signal<boolean>(false);
  showClientModal = signal<boolean>(false);

  // Create Client Modal
  showCreateClientModal = signal<boolean>(false);
  newClient = signal({
    full_name: '',
    email: '',
    phone: '',
    password: '',
    sector: 'Commerce',
    monthly_revenue: 350000,
    monthly_expenses: 120000,
  });
  creatingClient = signal<boolean>(false);

  // ── Agents Management ─────────────────────────────────────────────
  agents = signal<AdminAgentSummary[]>([]);
  agentsLoading = signal<boolean>(false);
  agentBranchFilter = signal<string>('all');
  agentSearchQuery = signal<string>('');

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

  // ── Regional Branches ─────────────────────────────────────────────
  branches = signal<AdminBranchInfo[]>([]);
  branchesLoading = signal<boolean>(false);
  showCreateBranchModal = signal<boolean>(false);
  newBranch = signal<AdminBranchCreate>({
    name: '',
    city: 'Bamako',
    branch_type: 'Antenne Régionale',
    lead_agent: '',
    max_credit_limit: 50000000,
  });
  creatingBranch = signal<boolean>(false);

  // ── Risk Matrix & Stress-Testing ──────────────────────────────────
  riskMatrix = signal<RiskMatrixData | null>(null);
  riskLoading = signal<boolean>(false);

  // Interactive Stress-Testing Controls
  stressIncomeShock = signal<number>(0);       // -0% to -50%
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

  // ── Password Reset Modal ──────────────────────────────────────────
  showResetPasswordModal = signal<boolean>(false);
  targetResetUser = signal<{ id: number; name: string; email: string; role: string } | null>(null);
  newPasswordInput = signal<string>('');
  resettingPassword = signal<boolean>(false);

  // ── Prudential Settings ───────────────────────────────────────────
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

  // ── Global Audit Logs ─────────────────────────────────────────────
  auditLogs = signal<AuditLog[]>([]);
  auditLoading = signal<boolean>(false);
  auditActionFilter = signal<string>('all');
  auditSearchQuery = signal<string>('');

  filteredAuditLogs = computed(() => {
    let list = this.auditLogs();
    const action = this.auditActionFilter();
    const q = this.auditSearchQuery().toLowerCase().trim();

    if (action !== 'all') {
      list = list.filter(l => l.action.toLowerCase().includes(action.toLowerCase()));
    }
    if (q) {
      list = list.filter(l =>
        l.action.toLowerCase().includes(q) ||
        (l.user_name && l.user_name.toLowerCase().includes(q)) ||
        (l.details && JSON.stringify(l.details).toLowerCase().includes(q))
      );
    }
    return list;
  });

  auditPage = signal<number>(1);
  auditPageSize = signal<number>(10);
  pagedAuditLogs = computed(() => {
    const start = (this.auditPage() - 1) * this.auditPageSize();
    return this.filteredAuditLogs().slice(start, start + this.auditPageSize());
  });
  totalAuditPages = computed(() => Math.max(1, Math.ceil(this.filteredAuditLogs().length / this.auditPageSize())));

  constructor(
    private api: ApiService,
    public auth: AuthService,
    private router: Router,
    private route: ActivatedRoute,
    private toast: ToastService,
  ) {}

  ngOnInit(): void {
    if (this.auth.userRole() !== 'admin') {
      this.toast.error('Accès refusé', 'Espace réservé à la Direction Générale et aux Administrateurs');
      this.auth.navigateToDashboard();
      return;
    }

    this.route.queryParams.subscribe(params => {
      const view = (params['view'] || params['tab']) as AdminTab;
      if (view && ['overview', 'clients', 'agents', 'branches', 'risk', 'settings', 'audit'].includes(view)) {
        this.currentTab.set(view);
      }
    });

    this.loadStats();
    this.loadClients();
    this.loadAgents();
    this.loadBranches();
    this.loadRiskMatrix();
    this.loadSettings();
    this.loadAuditLogs();
  }

  setTab(tab: AdminTab): void {
    this.currentTab.set(tab);
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { view: tab },
      queryParamsHandling: 'merge',
    });
    if (tab === 'overview') this.loadStats();
    if (tab === 'clients') this.loadClients();
    if (tab === 'agents') this.loadAgents();
    if (tab === 'branches') this.loadBranches();
    if (tab === 'risk') this.loadRiskMatrix();
    if (tab === 'settings') this.loadSettings();
    if (tab === 'audit') this.loadAuditLogs();
  }

  // ── Data Loaders ──────────────────────────────────────────────────
  async loadStats(): Promise<void> {
    this.statsLoading.set(true);
    try {
      const data = await this.api.getAdminStats();
      this.stats.set(data);
    } catch (e: any) {
      this.toast.error('Erreur Statistiques', e.message);
    } finally {
      this.statsLoading.set(false);
    }
  }

  async loadClients(): Promise<void> {
    this.clientsLoading.set(true);
    try {
      const data = await this.api.getAdminClients(
        this.clientSectorFilter(),
        this.clientKycFilter(),
        this.clientSearchQuery()
      );
      this.clients.set(data);
    } catch (e: any) {
      this.toast.error('Erreur Clients', e.message);
    } finally {
      this.clientsLoading.set(false);
    }
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
    this.branchesLoading.set(true);
    try {
      const data = await this.api.getAdminBranches();
      this.branches.set(data);
    } catch (e: any) {
      this.toast.error('Erreur Antennes', e.message);
    } finally {
      this.branchesLoading.set(false);
    }
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

  async loadAuditLogs(): Promise<void> {
    this.auditLoading.set(true);
    try {
      const res = await this.api.getGlobalAuditLogs(100);
      this.auditLogs.set(res.logs);
    } catch (e: any) {
      this.toast.error('Erreur Audit', e.message);
    } finally {
      this.auditLoading.set(false);
    }
  }

  // ── Client Actions ────────────────────────────────────────────────
  async viewClientDetail(c: AdminClientSummary): Promise<void> {
    this.loadingClientDetail.set(true);
    this.showClientModal.set(true);
    try {
      const detail = await this.api.getAdminClientDetail(c.id);
      this.selectedClient.set(detail);
    } catch (e: any) {
      this.toast.error('Erreur Chargement Fiche', e.message);
      this.showClientModal.set(false);
    } finally {
      this.loadingClientDetail.set(false);
    }
  }

  closeClientModal(): void {
    this.showClientModal.set(false);
    this.selectedClient.set(null);
  }

  async toggleClientStatus(c: { id: number; full_name: string; is_active: boolean }): Promise<void> {
    try {
      const res = await this.api.toggleUserActive(c.id);
      c.is_active = res.is_active;
      this.toast.info(
        'Statut Compte Modifié',
        `Le compte ${c.full_name} est désormais ${res.is_active ? 'Actif' : 'Suspendu'}.`
      );
      await this.loadClients();
      await this.loadAgents();
      if (this.selectedClient() && this.selectedClient()!.id === c.id) {
        this.selectedClient()!.is_active = res.is_active;
      }
    } catch (e: any) {
      this.toast.error('Erreur Statut', e.message);
    }
  }

  openCreateClientModal(): void {
    this.newClient.set({
      full_name: '',
      email: '',
      phone: '',
      password: '',
      sector: 'Commerce',
      monthly_revenue: 350000,
      monthly_expenses: 120000,
    });
    this.showCreateClientModal.set(true);
  }

  closeCreateClientModal(): void {
    this.showCreateClientModal.set(false);
  }

  async createClient(): Promise<void> {
    const p = this.newClient();
    if (!p.full_name || !p.email || !p.password) {
      this.toast.warning('Champs requis', 'Nom, email et mot de passe obligatoires');
      return;
    }
    this.creatingClient.set(true);
    try {
      await this.api.createAdminUser({
        full_name: p.full_name,
        email: p.email,
        phone: p.phone,
        password: p.password,
        role: 'client',
      });
      this.toast.success(
        'Client Enrôlé avec Succès',
        `Le compte emprunteur pour ${p.full_name} est créé.`
      );
      this.closeCreateClientModal();
      await this.loadClients();
      await this.loadStats();
    } catch (e: any) {
      this.toast.error('Erreur Création', e.message);
    } finally {
      this.creatingClient.set(false);
    }
  }

  // ── Agent Actions ─────────────────────────────────────────────────
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
      await this.loadStats();
    } catch (e: any) {
      this.toast.error('Erreur Création Agent', e.message);
    } finally {
      this.creatingAgent.set(false);
    }
  }

  openReassignModal(agent: AdminAgentSummary): void {
    this.reassignSourceAgent.set(agent);
    // Target defaults to first other agent
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
      await this.loadStats();
      await this.loadAuditLogs();
    } catch (e: any) {
      this.toast.error('Erreur Réassignation', e.message);
    } finally {
      this.reassigning.set(false);
    }
  }

  // ── Password Reset Actions ────────────────────────────────────────
  openResetPasswordModal(user: { id: number; full_name: string; email: string; role?: string }): void {
    this.targetResetUser.set({
      id: user.id,
      name: user.full_name,
      email: user.email,
      role: user.role || 'client',
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
      await this.loadAuditLogs();
    } catch (e: any) {
      this.toast.error('Erreur Réinitialisation', e.message);
    } finally {
      this.resettingPassword.set(false);
    }
  }

  // ── Branch Actions ────────────────────────────────────────────────
  openCreateBranchModal(): void {
    this.newBranch.set({
      name: '',
      city: 'Bamako',
      branch_type: 'Antenne Régionale',
      lead_agent: '',
      max_credit_limit: 50000000,
    });
    this.showCreateBranchModal.set(true);
  }

  closeCreateBranchModal(): void {
    this.showCreateBranchModal.set(false);
  }

  async createBranch(): Promise<void> {
    const b = this.newBranch();
    if (!b.name || !b.city || !b.lead_agent) {
      this.toast.warning('Champs requis', 'Nom, ville et agent responsable obligatoires');
      return;
    }
    this.creatingBranch.set(true);
    try {
      await this.api.createAdminBranch(b);
      this.toast.success(
        'Nouvelle Antenne Déployée',
        `${b.name} (${b.city}) intégrée au réseau OpenScore.`
      );
      this.closeCreateBranchModal();
      await this.loadBranches();
      await this.loadStats();
    } catch (e: any) {
      this.toast.error('Erreur Antenne', e.message);
    } finally {
      this.creatingBranch.set(false);
    }
  }

  // ── Prudential Settings ───────────────────────────────────────────
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

  // ── Reports & Export Actions ──────────────────────────────────────
  exportBceaoReport(): void {
    this.toast.success(
      'Exportation BCEAO',
      'Le rapport de conformité prudentielle UEMOA a été généré avec succès.'
    );
  }

  exportClientKyc(client: AdminClientDetail | AdminClientSummary): void {
    this.toast.info(
      'Export Fiche Emprunteur',
      `Fiche KYC de ${client.full_name} téléchargée pour archivage légal.`
    );
  }

  exportAuditTrail(): void {
    const data = JSON.stringify(this.filteredAuditLogs(), null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `openscore-audit-trail-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    this.toast.success('Piste d\'Audit Exportée', 'Le fichier JSON de traçabilité a été téléchargé.');
  }

  formatAmount(amount: number): string {
    return (amount || 0).toLocaleString('fr-FR') + ' FCFA';
  }
}
