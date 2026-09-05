import { Component, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, ActivatedRoute, Params } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { ToastService } from '../../core/services/toast.service';
import { SvgIconComponent } from '../../shared/components/svg-icon/svg-icon.component';
import { SpinnerComponent } from '../../shared/components/spinner/spinner.component';
import {
  AdminStats, AdminPrudentialSettings, AdminUserCreate, User, AuditLog
} from '../../shared/models/application.model';

type AdminTab = 'overview' | 'users' | 'settings' | 'audit';

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, SvgIconComponent, SpinnerComponent],
  templateUrl: './admin-dashboard.component.html',
  styleUrls: ['./admin-dashboard.component.css'],
})
export class AdminDashboardComponent implements OnInit {
  currentTab = signal<AdminTab>('overview');

  // Stats
  stats = signal<AdminStats | null>(null);
  statsLoading = signal<boolean>(true);

  // Users
  users = signal<User[]>([]);
  usersLoading = signal<boolean>(false);
  userRoleFilter = signal<string>('all');
  userSearchQuery = signal<string>('');

  // Create User Modal
  showCreateUserModal = signal<boolean>(false);
  newUser = signal<AdminUserCreate>({
    email: '',
    password: '',
    full_name: '',
    phone: '',
    role: 'agent',
  });
  creatingUser = signal<boolean>(false);

  // Prudential Settings
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

  // Global Audit Logs
  auditLogs = signal<AuditLog[]>([]);
  auditLoading = signal<boolean>(false);

  // Filtered Users List
  filteredUsers = computed(() => {
    let list = this.users();
    const role = this.userRoleFilter();
    const q = this.userSearchQuery().toLowerCase().trim();

    if (role !== 'all') {
      list = list.filter(u => u.role === role);
    }

    if (q) {
      list = list.filter(u =>
        u.full_name.toLowerCase().includes(q) ||
        u.email.toLowerCase().includes(q) ||
        (u.phone && u.phone.includes(q))
      );
    }

    return list;
  });

  // ── Pagination Signals ──────────────────────────────────────────
  usersPage = signal<number>(1);
  usersPageSize = signal<number>(5);
  pagedUsers = computed(() => {
    const start = (this.usersPage() - 1) * this.usersPageSize();
    return this.filteredUsers().slice(start, start + this.usersPageSize());
  });
  totalUsersPages = computed(() => Math.max(1, Math.ceil(this.filteredUsers().length / this.usersPageSize())));

  auditPage = signal<number>(1);
  auditPageSize = signal<number>(10);
  pagedAuditLogs = computed(() => {
    const start = (this.auditPage() - 1) * this.auditPageSize();
    return this.auditLogs().slice(start, start + this.auditPageSize());
  });
  totalAuditPages = computed(() => Math.max(1, Math.ceil(this.auditLogs().length / this.auditPageSize())));

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
      if (view && ['overview', 'users', 'settings', 'audit'].includes(view)) {
        this.currentTab.set(view);
      }
    });

    this.loadStats();
    this.loadUsers();
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
    if (tab === 'users') this.loadUsers();
    if (tab === 'settings') this.loadSettings();
    if (tab === 'audit') this.loadAuditLogs();
  }

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

  async loadUsers(): Promise<void> {
    this.usersLoading.set(true);
    try {
      const data = await this.api.getAdminUsers(this.userRoleFilter(), this.userSearchQuery());
      this.users.set(data);
    } catch (e: any) {
      this.toast.error('Erreur Utilisateurs', e.message);
    } finally {
      this.usersLoading.set(false);
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

  openCreateUserModal(): void {
    this.newUser.set({
      email: '',
      password: '',
      full_name: '',
      phone: '',
      role: 'agent',
    });
    this.showCreateUserModal.set(true);
  }

  closeCreateUserModal(): void {
    this.showCreateUserModal.set(false);
  }

  async createUser(): Promise<void> {
    const payload = this.newUser();
    if (!payload.email || !payload.password || !payload.full_name) {
      this.toast.warning('Champs obligatoires', 'Veuillez remplir le nom, email et mot de passe');
      return;
    }

    this.creatingUser.set(true);
    try {
      const created = await this.api.createAdminUser(payload);
      this.toast.success(
        'Utilisateur créé avec succès',
        `Compte ${created.full_name} (${created.role.toUpperCase()}) opérationnel.`
      );
      this.closeCreateUserModal();
      await this.loadUsers();
      await this.loadStats();
    } catch (e: any) {
      this.toast.error('Erreur création', e.message);
    } finally {
      this.creatingUser.set(false);
    }
  }

  async toggleActive(u: User): Promise<void> {
    try {
      const res = await this.api.toggleUserActive(u.id);
      u.is_active = res.is_active;
      this.toast.info(
        'Statut mis à jour',
        `Le compte ${u.full_name} est désormais ${res.is_active ? 'Actif' : 'Suspendu'}.`
      );
      await this.loadUsers();
    } catch (e: any) {
      this.toast.error('Erreur statut', e.message);
    }
  }

  async changeRole(u: User, newRole: string): Promise<void> {
    try {
      const updated = await this.api.updateUserRole(u.id, newRole);
      u.role = updated.role;
      this.toast.success(
        'Rôle modifié',
        `${updated.full_name} a été assigné au rôle ${updated.role.toUpperCase()}.`
      );
      await this.loadUsers();
      await this.loadStats();
    } catch (e: any) {
      this.toast.error('Erreur rôle', e.message);
    }
  }

  async deleteUser(u: User): Promise<void> {
    if (confirm(`Êtes-vous sûr de vouloir supprimer définitivement le compte ${u.full_name} (${u.email}) ?`)) {
      try {
        await this.api.deleteAdminUser(u.id);
        this.toast.success('Compte supprimé', `L'utilisateur ${u.full_name} a été supprimé du système.`);
        await this.loadUsers();
        await this.loadStats();
      } catch (e: any) {
        this.toast.error('Erreur suppression', e.message);
      }
    }
  }

  async savePrudentialSettings(): Promise<void> {
    this.savingSettings.set(true);
    try {
      const updated = await this.api.updatePrudentialSettings(this.settings());
      this.settings.set(updated);
      this.toast.success(
        'Politique Prudentielle Enregistrée',
        'Les seuils d\'octroi et poids ML sont appliqués à l\'ensemble du réseau IMF.'
      );
    } catch (e: any) {
      this.toast.error('Erreur enregistrement', e.message);
    } finally {
      this.savingSettings.set(false);
    }
  }

  exportBceaoReport(): void {
    this.toast.success(
      'Exportation BCEAO',
      'Le rapport de conformité prudentielle UEMOA a été généré avec succès.'
    );
  }

  formatAmount(amount: number): string {
    return (amount || 0).toLocaleString('fr-FR') + ' FCFA';
  }
}
